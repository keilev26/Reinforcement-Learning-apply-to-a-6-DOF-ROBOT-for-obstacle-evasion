#!/usr/bin/env python3
"""Verificacion de la linea base con la geometria y las poses REALES del contrato 3.1.

Expande cada escenario de shared_scenarios/escenarios.yaml en TODAS sus variantes
(desplazamientos del 4, escalas del 5, formas del 6, holguras del 7) y, para cada
una, comprueba:
  1. que p_pick y p_place tengan cinematica inversa libre de colision;
  2. que el obstaculo obstruya de verdad el camino directo (usando las MISMAS
     configuraciones articulares del escenario 1, para no confundir el efecto
     del obstaculo con un cambio de rama de la cinematica inversa);
  3. que RRT-Connect planifique pick -> place y que ninguna trayectoria choque
     en la validacion independiente.

Convencion (contrato >= 1.1): toda 'pose' es el CENTRO geometrico del componente,
en el marco de la celda. base_link esta 0.75 m por encima del origen de la celda.

Uso: p6_contrato.py <escenarios.yaml> [--escenarios 1,2,...] [--n 5]
"""
import argparse, math, os, sys, time
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rclpy
from diagnostico_pendientes import Diag, J, GRUPO, CODIGOS
from moveit_msgs.srv import GetPositionIK, GetMotionPlan, ApplyPlanningScene, GetPlanningScene, GetStateValidity
from moveit_msgs.msg import (MotionPlanRequest, PositionIKRequest, RobotState, Constraints,
                             JointConstraint, PlanningScene, CollisionObject, PlanningSceneComponents)
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose, PoseStamped, Point, Quaternion

HOLGURA_PEDESTAL = 0.01   # el pedestal toca base_link; 1 cm evita un falso choque de arranque
PASOS_RECTA = 100


def quat_rpy(r, p, y):
    cr, sr, cp, sp, cy, sy = (math.cos(r / 2), math.sin(r / 2), math.cos(p / 2),
                              math.sin(p / 2), math.cos(y / 2), math.sin(y / 2))
    return Quaternion(x=sr * cp * cy - cr * sp * sy, y=cr * sp * cy + sr * cp * sy,
                      z=cr * cp * sy - sr * sp * cy, w=cr * cp * cy + sr * sp * sy)


# ---------------------------------------------------------------------------
# Expansion del contrato en variantes: lista de (etiqueta, [objeto, ...])
# objeto = dict(id, forma, dims, pose)  -- pose en el marco de la celda
# ---------------------------------------------------------------------------
def objeto(bib, id_, comp, pose, escala=1.0):
    info = bib[comp]
    if "dim" in info:
        e = escala if isinstance(escala, list) else [escala] * 3
        return dict(id=id_, forma="caja", dims=[d * k for d, k in zip(info["dim"], e)], pose=list(pose))
    k = escala[0] if isinstance(escala, list) else escala
    if comp == "cilindro":
        return dict(id=id_, forma="cilindro", dims=[info["altura"] * k, info["radio"] * k], pose=list(pose))
    if comp == "esfera":
        return dict(id=id_, forma="esfera", dims=[info["radio"] * k], pose=list(pose))
    raise ValueError(f"componente sin geometria conocida: {comp}")


def expandir(C, n):
    bib, e = C["biblioteca"], C["escenarios"][n]
    if "obstaculos" in e:
        return [(f"{n}", [objeto(bib, f"o{i}_{o['componente']}", o["componente"], o["pose"], o.get("escala", 1.0))
                          for i, o in enumerate(e["obstaculos"])])]
    if "desplazamientos_m" in e:
        b = e["base"]
        return [(f"{n}.{i + 1} d={d}", [objeto(bib, "obs", b["componente"],
                 [p + q for p, q in zip(b["pose"][:3], d)] + b["pose"][3:])])
                for i, d in enumerate(e["desplazamientos_m"])]
    if "factores_de_escala" in e:
        b = e["base"]
        return [(f"{n} escala={k}", [objeto(bib, "obs", b["componente"], b["pose"], k)])
                for k in e["factores_de_escala"]]
    if "formas" in e:
        return [(f"{n} {f}", [objeto(bib, "obs", f, e["pose_comun"])]) for f in e["formas"]]
    if "holguras_m" in e:
        cx, cy, cz = 0.250, -0.275, 0.900            # punto medio (contrato v1.1)
        media = bib["prisma"]["dim"][1] / 2
        return [(f"{n} holgura={h}", [objeto(bib, "izq", "prisma", [cx, cy + h / 2 + media, cz, 0, 0, 0]),
                                      objeto(bib, "der", "prisma", [cx, cy - h / 2 - media, cz, 0, 0, 0])])
                for h in e["holguras_m"]]
    raise ValueError(f"escenario {n}: estructura no reconocida")


def a_collision(o, z_base):
    c = CollisionObject(); c.header.frame_id = "base_link"; c.id = o["id"]
    sp = SolidPrimitive()
    sp.type = {"caja": SolidPrimitive.BOX, "cilindro": SolidPrimitive.CYLINDER,
               "esfera": SolidPrimitive.SPHERE}[o["forma"]]
    sp.dimensions = list(o["dims"])
    c.primitives.append(sp); c.primitive_poses.append(Pose(orientation=Quaternion(w=1.0)))
    x, y, z = o["pose"][:3]
    c.pose = Pose(position=Point(x=x, y=y, z=z - z_base), orientation=quat_rpy(*o["pose"][3:6]))
    c.operation = CollisionObject.ADD
    return c


class P6(Diag):
    def __init__(self, C):
        super().__init__()
        self.C = C; self.z_base = C["robot"]["base_pose"][2]
        self.c["compute_ik"] = self.create_client(GetPositionIK, "/compute_ik")
        if not self.c["compute_ik"].wait_for_service(timeout_sec=20):
            sys.exit("falta el servicio /compute_ik")
        self.celda = []
        for comp in C["celda_base"]:
            o = objeto(C["biblioteca"], comp["componente"], comp["componente"], comp["pose"])
            if comp["componente"] == "pedestal":
                o["pose"][2] -= HOLGURA_PEDESTAL
            self.celda.append(o)

    def cargar(self, obstaculos):
        r = GetPlanningScene.Request(); r.components.components = PlanningSceneComponents.WORLD_OBJECT_NAMES
        quitar = []
        for o in self._call("get_planning_scene", r).scene.world.collision_objects:
            c = CollisionObject(); c.id = o.id; c.header.frame_id = "base_link"
            c.operation = CollisionObject.REMOVE; quitar.append(c)
        s = PlanningScene(); s.is_diff = True
        s.world.collision_objects.extend(quitar + [a_collision(o, self.z_base) for o in self.celda + obstaculos])
        rq = ApplyPlanningScene.Request(); rq.scene = s
        self._call("apply_planning_scene", rq); time.sleep(0.8)

    def ik(self, nombre):
        punto = self.C["tarea_nominal"][nombre]; x, y, z = punto["pos"]
        ps = PoseStamped(); ps.header.frame_id = "base_link"
        ps.pose = Pose(position=Point(x=x, y=y, z=z - self.z_base), orientation=quat_rpy(*punto["rpy"]))
        req = GetPositionIK.Request(); pik = PositionIKRequest()
        pik.group_name = GRUPO; pik.ik_link_name = "tool0"; pik.pose_stamped = ps
        pik.avoid_collisions = True; pik.timeout.sec = 2
        rs = RobotState(); rs.joint_state.name = J
        rs.joint_state.position = self.C["tarea_nominal"]["q_inicial_rad"]; pik.robot_state = rs
        req.ik_request = pik
        res = self._call("compute_ik", req, t=10)
        if res.error_code.val != 1:
            return None
        n = list(res.solution.joint_state.name)
        return [res.solution.joint_state.position[n.index(j)] for j in J]

    def estados_en_colision(self, qa, qb):
        malos = 0
        for i in range(PASOS_RECTA + 1):
            q = [a + (b - a) * i / PASOS_RECTA for a, b in zip(qa, qb)]
            r = GetStateValidity.Request(); r.group_name = GRUPO
            rs = RobotState(); rs.joint_state.name = J; rs.joint_state.position = q; r.robot_state = rs
            malos += 0 if self._call("check_state_validity", r).valid else 1
        return malos

    def planificar_n(self, qa, qb, n):
        cs = Constraints()
        for nm, v in zip(J, qb):
            jc = JointConstraint(); jc.joint_name = nm; jc.position = v
            jc.tolerance_above = jc.tolerance_below = 0.01; jc.weight = 1.0
            cs.joint_constraints.append(jc)
        ok = choca = 0
        for _ in range(n):
            req = MotionPlanRequest(); req.group_name = GRUPO; req.planner_id = "RRTConnect"
            req.allowed_planning_time = 5.0; req.num_planning_attempts = 1
            req.start_state.joint_state.name = J; req.start_state.joint_state.position = qa
            req.goal_constraints.append(cs)
            p = GetMotionPlan.Request(); p.motion_plan_request = req
            res = self._call("plan_kinematic_path", p, t=20).motion_plan_response
            if res.error_code.val == 1:
                ok += 1
                _, col = self.validar_trayectoria(res.trajectory.joint_trajectory.points)
                choca += 1 if col else 0
        return ok, choca


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("contrato")
    ap.add_argument("--escenarios", default="1,2,3,4,5,6,7,8")
    ap.add_argument("--n", type=int, default=5)
    a = ap.parse_args()
    C = yaml.safe_load(open(a.contrato))

    rclpy.init(); d = P6(C)
    print(f"\nContrato {C['version']} | p_pick {C['tarea_nominal']['p_pick']['pos']} | "
          f"p_place {C['tarea_nominal']['p_place']['pos']} | RRT-Connect x{a.n} por variante")

    # Configuraciones de referencia: las del escenario 1 (solo la celda)
    d.cargar([])
    ref = (d.ik("p_pick"), d.ik("p_place"))
    if None in ref:
        sys.exit("la tarea nominal no tiene solucion libre de colision ni en la celda vacia")

    print(f"{'variante':<22}{'pick':>6}{'place':>7}{'recta obstruida':>17}{'planif.':>9}{'choca':>7}   veredicto")
    for n in [int(x) for x in a.escenarios.split(",")]:
        for etiqueta, obst in expandir(C, n):
            d.cargar(obst)
            qa, qb = d.ik("p_pick"), d.ik("p_place")
            recta = d.estados_en_colision(*ref)
            pick, place = ("ok" if qa else "NO"), ("ok" if qb else "NO")
            if qa and qb:
                ok, choca = d.planificar_n(qa, qb, a.n)
                plan = f"{ok}/{a.n}"
            else:
                ok = choca = 0; plan = "-"
            if not (qa and qb):
                ver = "INFACTIBLE: pose de la tarea en colision"
            elif choca:
                ver = "ERROR: trayectorias con colision"
            elif ok < a.n:
                ver = "planificacion incompleta"
            elif n != 1 and recta == 0:
                ver = "valido, pero el obstaculo NO obstruye"
            else:
                ver = "valido"
            print(f"{etiqueta:<22}{pick:>6}{place:>7}{recta:>11}/{PASOS_RECTA + 1:<5}{plan:>9}{choca:>7}   {ver}")
    d.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
