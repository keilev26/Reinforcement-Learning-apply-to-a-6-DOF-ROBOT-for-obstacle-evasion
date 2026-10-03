#!/usr/bin/env python3
import argparse, math, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rclpy
from rclpy.action import ActionClient
from control_msgs.msg import JointTrajectoryControllerState
from moveit_msgs.action import ExecuteTrajectory
from moveit_msgs.msg import Constraints, JointConstraint, MotionPlanRequest, RobotState
from moveit_msgs.srv import GetMotionPlan, GetPositionFK
from sensor_msgs.msg import JointState

from p6_contrato import P6, contrato, estado, J, GRUPO, TCP


class Ejecutor(P6):
    def __init__(self, C):
        super().__init__(C)
        self.q_actual = None
        self.err_max = 0.0
        self.grabando, self.grabados = False, []
        self.create_subscription(JointState, "/joint_states", self._js, 10)
        self.create_subscription(JointTrajectoryControllerState, "/brazo_controller/controller_state",
                                 self._estado_ctrl, 10)
        self.ejecutar = ActionClient(self, ExecuteTrajectory, "/execute_trajectory")
        if not self.ejecutar.wait_for_server(timeout_sec=20):
            sys.exit("falta la acción /execute_trajectory: ¿corre gazebo_e6.launch.py?")

    def _js(self, m):
        if set(J) <= set(m.name):
            self.q_actual = [m.position[list(m.name).index(j)] for j in J]
            if self.grabando:
                self.grabados.append(self.q_actual)

    def _estado_ctrl(self, m):
        if m.error.positions:
            self.err_max = max(self.err_max, max(abs(e) for e in m.error.positions))

    def esperar_estado(self):
        fin = time.time() + 10
        while self.q_actual is None and time.time() < fin:
            rclpy.spin_once(self, timeout_sec=0.1)
        if self.q_actual is None:
            sys.exit("no llegan /joint_states desde Gazebo")

    def planificar(self, meta):
        cs = Constraints()
        for nm, v in zip(J, meta):
            jc = JointConstraint(); jc.joint_name = nm; jc.position = v
            jc.tolerance_above = jc.tolerance_below = 0.001; jc.weight = 1.0
            cs.joint_constraints.append(jc)
        req = MotionPlanRequest(); req.group_name = GRUPO; req.planner_id = "RRTConnect"
        req.allowed_planning_time = 5.0; req.num_planning_attempts = 1
        req.max_velocity_scaling_factor = self.escalado; req.max_acceleration_scaling_factor = 1.0
        req.start_state = estado(self.q_actual)
        req.goal_constraints.append(cs)
        p = GetMotionPlan.Request(); p.motion_plan_request = req
        return self._call("plan_kinematic_path", p, t=25).motion_plan_response

    def ejecutar_plan(self, trayectoria):
        self.err_max = 0.0
        self.grabados, self.grabando = [], True
        objetivo = ExecuteTrajectory.Goal(); objetivo.trajectory = trayectoria
        f = self.ejecutar.send_goal_async(objetivo)
        rclpy.spin_until_future_complete(self, f, timeout_sec=10)
        r = f.result().get_result_async()
        rclpy.spin_until_future_complete(self, r, timeout_sec=60)
        fin = time.time() + 0.5
        while time.time() < fin:
            rclpy.spin_once(self, timeout_sec=0.05)
        self.grabando = False
        return r.result().result.error_code.val

    def ejecutados_en_colision(self):
        muestra = self.grabados[::2]
        return sum(not self.valido(q) for q in muestra), len(muestra)

    def tcp(self, q):
        r = GetPositionFK.Request(); r.header.frame_id = "base_link"; r.fk_link_names = [TCP]
        rs = RobotState(); rs.joint_state.name = J; rs.joint_state.position = list(q); r.robot_state = rs
        f = self._call("compute_fk", r).pose_stamped[0].pose
        o = f.orientation
        z = (2 * (o.x * o.z + o.w * o.y), 2 * (o.y * o.z - o.w * o.x), 1 - 2 * (o.x ** 2 + o.y ** 2))
        largo = self.C["efector"]["largo_m"]
        return [f.position.x + z[0] * largo, f.position.y + z[1] * largo, f.position.z + z[2] * largo]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--escenario", type=int, default=1)
    ap.add_argument("--variante", default="")
    a = ap.parse_args()
    C = contrato.cargar()
    variantes = contrato.variantes(C, a.escenario)
    etiqueta, obst = next((v for v in variantes if v[0] == a.variante), variantes[0]) \
        if a.variante else variantes[0]

    rclpy.init(); d = Ejecutor(C)
    d.cargar(obst)
    d.esperar_estado()
    T = C["tarea_nominal"]
    metas = [("p_pick", d.ik("p_pick", T["q_inicial_rad"]))]
    metas.append(("p_place", d.ik("p_place", metas[0][1] or T["q_inicial_rad"])))
    if any(q is None for _, q in metas):
        sys.exit("sin cinemática inversa libre de colisión para la tarea")

    print(f"\nGazebo | contrato {C['version']} | variante {etiqueta} | escalado de velocidad {d.escalado}")
    print(f"{'tramo':<18}{'plan':>6}{'ejecución':>11}{'duración s':>12}{'err. seguim. rad':>18}"
          f"{'err. final rad':>16}{'err. TCP mm':>13}{'ejecutados en colisión':>25}")
    origen = "actual"
    for nombre, q_meta in metas:
        res = d.planificar(q_meta)
        if res.error_code.val != 1:
            print(f"{origen + ' -> ' + nombre:<18}{'FALLA':>6}"); break
        pts = res.trajectory.joint_trajectory.points
        dur = pts[-1].time_from_start.sec + pts[-1].time_from_start.nanosec * 1e-9
        cod = d.ejecutar_plan(res.trajectory)
        err_final = max(abs(a_ - b) for a_, b in zip(d.q_actual, q_meta))
        err_tcp = math.dist(d.tcp(d.q_actual), T[nombre]["pos"]) * 1000
        malos, total = d.ejecutados_en_colision()
        print(f"{origen + ' -> ' + nombre:<18}{'ok':>6}{'ok' if cod == 1 else f'código {cod}':>11}"
              f"{dur:>12.2f}{d.err_max:>18.4f}{err_final:>16.4f}{err_tcp:>13.2f}{malos:>18}/{total}")
        origen = nombre
    d.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
