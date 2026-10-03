#!/usr/bin/env python3
import argparse, json, math, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import rclpy
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from moveit_msgs.msg import PlanningSceneComponents, RobotState
from moveit_msgs.srv import GetPlanningScene, GetPositionFK, GetStateValidity
from rcl_interfaces.srv import GetParameters
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectoryPoint

from p6_contrato import GRUPO, J, MARGEN_PLANIFICACION_M, P6, _raiz_repo, contrato, estado

ESLABONES = ["Link1", "Link2", "Link3", "Link4", "Link5", "Link6", "tool0"]


def pose_gz(eslabon: str):
    salida = subprocess.run(["gz", "model", "-m", "magician_e6", "-l", eslabon],
                            capture_output=True, text=True, timeout=20).stdout
    bloque = salida.split("- Pose [ XYZ (m) ] [ RPY (rad) ]:")[1]
    nums = [[float(v) for v in fila.split()] for fila in re.findall(r"\[([^\]]+)\]", bloque)[:2]]
    return nums[0], nums[1]


class Recolector(P6):
    def __init__(self, C):
        super().__init__(C)
        self.q_actual = None
        self.create_subscription(JointState, "/joint_states", self._js, 10)
        self.accion = ActionClient(self, FollowJointTrajectory, "/brazo_controller/follow_joint_trajectory")

    def _js(self, m):
        if set(J) <= set(m.name):
            self.q_actual = [m.position[list(m.name).index(j)] for j in J]

    def fk(self, q):
        r = GetPositionFK.Request(); r.header.frame_id = "base_link"; r.fk_link_names = ESLABONES
        rs = RobotState(); rs.joint_state.name = J; rs.joint_state.position = list(q); r.robot_state = rs
        res = self._call("compute_fk", r)
        return {n: [[p.pose.position.x, p.pose.position.y, p.pose.position.z],
                    [p.pose.orientation.x, p.pose.orientation.y, p.pose.orientation.z, p.pose.orientation.w]]
                for n, p in zip(res.fk_link_names, res.pose_stamped)}

    def limites(self):
        cli = self.create_client(GetParameters, "/move_group/get_parameters")
        cli.wait_for_service(timeout_sec=10)
        nombres = [f"robot_description_planning.joint_limits.{j}.max_velocity" for j in J]
        req = GetParameters.Request(); req.names = nombres
        f = cli.call_async(req); rclpy.spin_until_future_complete(self, f, timeout_sec=10)
        return {j: v.double_value for j, v in zip(J, f.result().values)}

    def escena(self):
        r = GetPlanningScene.Request()
        r.components.components = (PlanningSceneComponents.WORLD_OBJECT_NAMES |
                                   PlanningSceneComponents.WORLD_OBJECT_GEOMETRY)
        objs = self._call("get_planning_scene", r).scene.world.collision_objects
        out = []
        for o in objs:
            pr = o.primitives[0]
            out.append({"id": o.id, "tipo": pr.type, "dims": list(pr.dimensions),
                        "pos": [o.pose.position.x, o.pose.position.y, o.pose.position.z],
                        "quat": [o.pose.orientation.x, o.pose.orientation.y, o.pose.orientation.z,
                                 o.pose.orientation.w]})
        return out

    def llevar_a(self, q, dur=3.0):
        self.accion.wait_for_server(timeout_sec=10)
        g = FollowJointTrajectory.Goal(); g.trajectory.joint_names = J
        pt = JointTrajectoryPoint(); pt.positions = list(q)
        pt.time_from_start.sec = int(dur); pt.time_from_start.nanosec = int((dur % 1) * 1e9)
        g.trajectory.points = [pt]
        f = self.accion.send_goal_async(g); rclpy.spin_until_future_complete(self, f, timeout_sec=10)
        r = f.result().get_result_async(); rclpy.spin_until_future_complete(self, r, timeout_sec=dur + 10)
        fin = time.time() + 1.0
        while time.time() < fin:
            rclpy.spin_once(self, timeout_sec=0.05)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variante", default="2")
    ap.add_argument("--n-fk", type=int, default=200)
    ap.add_argument("--n-gazebo", type=int, default=6)
    ap.add_argument("--semilla", type=int, default=0)
    a = ap.parse_args()
    rng = np.random.default_rng(a.semilla)
    C = contrato.cargar()
    variantes = {et: o for n in C["escenarios"] for et, o in contrato.variantes(C, n)}
    rclpy.init(); d = Recolector(C)
    d.cargar(variantes[a.variante])

    lim = np.array([6.27, 2.356, 2.6878, 2.7925, 3.0194, 6.27])
    qs = [rng.uniform(-lim, lim) for _ in range(a.n_fk)]
    datos = {"variante": a.variante, "margen_planificacion_m": MARGEN_PLANIFICACION_M,
             "fk": [{"q": list(q), "poses": d.fk(q)} for q in qs],
             "limites_velocidad": d.limites(), "escena": d.escena(), "gazebo": []}

    T = C["tarea_nominal"]
    qa, qb = d.ik("p_pick", T["q_inicial_rad"]), d.ik("p_place", T["q_inicial_rad"])
    candidatas = [np.array(qa) + (np.array(qb) - np.array(qa)) * s + rng.normal(0, 0.15, 6)
                  for s in np.linspace(0, 1, a.n_gazebo * 3)]
    for q in candidatas:
        if len(datos["gazebo"]) >= a.n_gazebo:
            break
        r = GetStateValidity.Request(); r.group_name = GRUPO; r.robot_state = estado(q)
        if not d._call("check_state_validity", r).valid:
            continue
        d.llevar_a(q)
        datos["gazebo"].append({"q_objetivo": list(q), "q_gazebo": d.q_actual,
                                "poses_gz": {e: pose_gz(e) for e in ESLABONES[:-1]}})
        print(f"gazebo {len(datos['gazebo'])}/{a.n_gazebo}", flush=True)

    salida = _raiz_repo() / "results" / f"equivalencia_ros_{time.strftime('%Y%m%d_%H%M')}.json"
    salida.write_text(json.dumps(datos))
    print(f"guardado en {salida}")
    d.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
