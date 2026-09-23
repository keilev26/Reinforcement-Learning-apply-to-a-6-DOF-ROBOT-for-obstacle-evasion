#!/usr/bin/env python3
"""Verificación de la línea base con la geometría y las poses REALES del contrato 3.1.

Expande cada escenario de shared_scenarios/escenarios.yaml en TODAS sus variantes, con
shared_scenarios/contrato.py (la misma expansión que usa PyBullet), y para cada una comprueba:
  1. que p_pick y p_place tengan cinemática inversa libre de colisión, con el efector adjunto;
  2. que el obstáculo obstruya de verdad el camino directo (usando las MISMAS configuraciones
     articulares del escenario 1, para no confundir el efecto del obstáculo con un cambio de
     rama de la cinemática inversa). En el escenario de paso estrecho, que el camino lo cruce;
  3. que RRT-Connect planifique pick -> place y que ninguna trayectoria choque en la
     validación independiente.

Contrato >= 2.0 (Magician E6): las poses de la tarea son del TCP, la punta del efector.
Requiere planning_e6.launch.py corriendo.

Uso: p6_contrato.py [<escenarios.yaml>] [--escenarios 1,2,...] [--n 5]
"""
import argparse, math, os, sys, time
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rclpy
from diagnostico_pendientes import Diag, J, GRUPO, TCP, CODIGOS
from moveit_msgs.srv import GetPositionIK, GetPlanningScene, ApplyPlanningScene, GetStateValidity
from moveit_msgs.msg import (MotionPlanRequest, PositionIKRequest, RobotState, Constraints,
                             JointConstraint, PlanningScene, CollisionObject, AttachedCollisionObject,
                             PlanningSceneComponents)
from moveit_msgs.srv import GetMotionPlan
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose, PoseStamped, Point, Quaternion


def _raiz_repo() -> Path:
    """Raíz del repositorio: el script corre desde src/ o desde install/ (symlink)."""
    for base in (Path(__file__).resolve(), Path(os.path.abspath(__file__))):
        for padre in base.parents:
            if (padre / "shared_scenarios" / "contrato.py").exists():
                return padre
    sys.exit("no se encuentra shared_scenarios/contrato.py")


sys.path.insert(0, str(_raiz_repo() / "shared_scenarios"))
import contrato  # noqa: E402

PASOS_RECTA = 100


def escalado_velocidad() -> float:
    """Escalado de paridad de M4, de config/e6/joint_limits.yaml (MoveIt no lo aplica solo)."""
    import yaml
    from ament_index_python.packages import get_package_share_directory
    ruta = Path(get_package_share_directory("rl6gdl_planning")) / "config" / "e6" / "joint_limits.yaml"
    return float(yaml.safe_load(ruta.read_text())["default_velocity_scaling_factor"])


def quat_rpy(r, p, y):
    cr, sr, cp, sp, cy, sy = (math.cos(r / 2), math.sin(r / 2), math.cos(p / 2),
                              math.sin(p / 2), math.cos(y / 2), math.sin(y / 2))
    return Quaternion(x=sr * cp * cy - cr * sp * sy, y=cr * sp * cy + sr * cp * sy,
                      z=cr * cp * sy - sr * sp * cy, w=cr * cp * cy + sr * sp * sy)


def primitivo(o) -> SolidPrimitive:
    sp = SolidPrimitive()
    sp.type = {"caja": SolidPrimitive.BOX, "cilindro": SolidPrimitive.CYLINDER,
               "esfera": SolidPrimitive.SPHERE}[o["forma"]]
    sp.dimensions = list(o["dims"])
    return sp


def pose_de(o) -> Pose:
    x, y, z = o["pose"][:3]
    return Pose(position=Point(x=x, y=y, z=z), orientation=quat_rpy(*o["pose"][3:6]))


def a_collision(o, marco="base_link"):
    c = CollisionObject(); c.header.frame_id = marco; c.id = o["id"]
    c.primitives.append(primitivo(o)); c.primitive_poses.append(Pose(orientation=Quaternion(w=1.0)))
    c.pose = pose_de(o); c.operation = CollisionObject.ADD
    return c


def estado(q) -> RobotState:
    # is_diff: conserva el efector adjunto a la escena
    rs = RobotState(); rs.is_diff = True
    rs.joint_state.name = J; rs.joint_state.position = list(q)
    return rs


class P6(Diag):
    def __init__(self, C):
        super().__init__()
        self.C = C
        self.c["compute_ik"] = self.create_client(GetPositionIK, "/compute_ik")
        if not self.c["compute_ik"].wait_for_service(timeout_sec=20):
            sys.exit("falta el servicio /compute_ik")
        self.celda = contrato.celda(C)
        self.escalado = escalado_velocidad()
        self.adjuntar_efector()

    def adjuntar_efector(self):
        a = AttachedCollisionObject(); a.link_name = TCP
        a.object = a_collision(contrato.objeto_efector(self.C), marco=TCP)
        a.touch_links = [TCP, "Link6"]
        s = PlanningScene(); s.is_diff = True; s.robot_state.is_diff = True
        s.robot_state.attached_collision_objects.append(a)
        rq = ApplyPlanningScene.Request(); rq.scene = s
        self._call("apply_planning_scene", rq); time.sleep(0.5)

    def cargar(self, obstaculos):
        r = GetPlanningScene.Request(); r.components.components = PlanningSceneComponents.WORLD_OBJECT_NAMES
        quitar = []
        for o in self._call("get_planning_scene", r).scene.world.collision_objects:
            c = CollisionObject(); c.id = o.id; c.header.frame_id = "base_link"
            c.operation = CollisionObject.REMOVE; quitar.append(c)
        s = PlanningScene(); s.is_diff = True
        s.world.collision_objects.extend(quitar + [a_collision(o) for o in self.celda + obstaculos])
        rq = ApplyPlanningScene.Request(); rq.scene = s
        self._call("apply_planning_scene", rq); time.sleep(0.8)

    def ik(self, nombre, semilla):
        punto = self.C["tarea_nominal"][nombre]
        x, y, z = contrato.tool0_desde_tcp(self.C, punto["pos"], punto["rpy"])
        ps = PoseStamped(); ps.header.frame_id = "base_link"
        ps.pose = Pose(position=Point(x=x, y=y, z=z), orientation=quat_rpy(*punto["rpy"]))
        pik = PositionIKRequest()
        pik.group_name = GRUPO; pik.ik_link_name = TCP; pik.pose_stamped = ps
        pik.avoid_collisions = True; pik.timeout.sec = 2
        pik.robot_state = estado(semilla)
        req = GetPositionIK.Request(); req.ik_request = pik
        res = self._call("compute_ik", req, t=10)
        if res.error_code.val != 1:
            return None
        n = list(res.solution.joint_state.name)
        return [res.solution.joint_state.position[n.index(j)] for j in J]

    def estados_en_colision(self, qa, qb):
        malos = 0
        for i in range(PASOS_RECTA + 1):
            r = GetStateValidity.Request(); r.group_name = GRUPO
            r.robot_state = estado([a + (b - a) * i / PASOS_RECTA for a, b in zip(qa, qb)])
            malos += 0 if self._call("check_state_validity", r).valid else 1
        return malos

    def planificar_n(self, qa, qb, n):
        cs = Constraints()
        for nm, v in zip(J, qb):
            jc = JointConstraint(); jc.joint_name = nm; jc.position = v
            jc.tolerance_above = jc.tolerance_below = 0.01; jc.weight = 1.0
            cs.joint_constraints.append(jc)
        ok = choca = 0
        tiempos, fallos = [], Counter()
        for _ in range(n):
            req = MotionPlanRequest(); req.group_name = GRUPO; req.planner_id = "RRTConnect"
            req.allowed_planning_time = 5.0; req.num_planning_attempts = 1
            req.max_velocity_scaling_factor = self.escalado; req.max_acceleration_scaling_factor = 1.0
            req.start_state = estado(qa)
            req.goal_constraints.append(cs)
            p = GetMotionPlan.Request(); p.motion_plan_request = req
            res = self._call("plan_kinematic_path", p, t=20).motion_plan_response
            if res.error_code.val == 1:
                ok += 1; tiempos.append(res.planning_time * 1000)
                _, col = self.validar_trayectoria(res.trajectory.joint_trajectory.points)
                choca += 1 if col else 0
            else:
                fallos[CODIGOS.get(res.error_code.val, res.error_code.val)] += 1
        return ok, choca, (sum(tiempos) / len(tiempos) if tiempos else float("nan")), fallos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("contrato", nargs="?", default=str(contrato.RUTA))
    ap.add_argument("--escenarios", default="1,2,3,4,5,6,7,8")
    ap.add_argument("--n", type=int, default=5)
    a = ap.parse_args()
    C = contrato.cargar(a.contrato)
    if not C["version"].startswith("2"):
        sys.exit(f"contrato {C['version']}: este script es para el contrato >= 2.0 (Magician E6)")

    rclpy.init(); d = P6(C)
    T = C["tarea_nominal"]
    print(f"\nContrato {C['version']} | p_pick {T['p_pick']['pos']} | "
          f"p_place {T['p_place']['pos']} | RRT-Connect x{a.n} por variante")

    # Configuraciones de referencia: las del escenario 1 (solo la celda)
    d.cargar([])
    ref = (d.ik("p_pick", T["q_inicial_rad"]), d.ik("p_place", T["q_inicial_rad"]))
    if None in ref:
        sys.exit("la tarea nominal no tiene solución libre de colisión ni en la celda vacía")
    print(f"q_pick  = {[round(v, 4) for v in ref[0]]}\nq_place = {[round(v, 4) for v in ref[1]]}\n")

    print(f"{'variante':<24}{'pick':>6}{'place':>7}{'recta obstruida':>17}{'planif.':>9}"
          f"{'t_med ms':>10}{'choca':>7}   veredicto")
    for n in [int(x) for x in a.escenarios.split(",")]:
        paso = C["escenarios"][n].get("prueba") == "paso_estrecho"
        for etiqueta, obst in contrato.variantes(C, n):
            d.cargar(obst)
            qa, qb = d.ik("p_pick", ref[0]), d.ik("p_place", ref[1])
            recta = d.estados_en_colision(*ref)
            if qa and qb:
                ok, choca, tm, fallos = d.planificar_n(qa, qb, a.n)
                plan = f"{ok}/{a.n}"
            else:
                ok = choca = 0; tm = float("nan"); plan = "-"; fallos = Counter()
            if not (qa and qb):
                ver = "INFACTIBLE: pose de la tarea en colisión"
            elif choca:
                ver = "ERROR: trayectorias con colisión"
            elif ok < a.n:
                ver = "planificación incompleta"
            elif paso:
                ver = "válido" if recta == 0 else "válido, pero la recta NO cruza el paso"
            elif n != 1 and recta == 0:
                ver = "válido, pero el obstáculo NO obstruye"
            else:
                ver = "válido"
            print(f"{etiqueta:<24}{'ok' if qa else 'NO':>6}{'ok' if qb else 'NO':>7}"
                  f"{recta:>11}/{PASOS_RECTA + 1:<5}{plan:>9}{tm:>10.0f}{choca:>7}   {ver}"
                  + (f"  [{', '.join(f'{k}={v}' for k, v in fallos.items())}]" if fallos else ""))
    d.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
