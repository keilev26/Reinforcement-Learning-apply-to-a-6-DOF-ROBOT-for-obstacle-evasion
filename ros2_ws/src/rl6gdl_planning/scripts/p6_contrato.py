#!/usr/bin/env python3
"""Pendiente P6 — verificacion con la geometria y las poses REALES del contrato 3.1.

Carga la celda base (y opcionalmente los obstaculos de un escenario) desde
shared_scenarios/escenarios.yaml, y comprueba:
  1. que p_pick y p_place tengan cinematica inversa CON la orientacion pedida,
     con y sin evitar colisiones, para distinguir "inalcanzable" de "en colision";
  2. si ambas son alcanzables, que la linea base planifique entre ellas sin chocar.

Convencion de poses (el contrato 1.0 no la declara; ver el reporte):
  - estructuras (tipo: estructura): 'pose' = centro de la BASE de la caja
  - obstaculos: 'pose' = CENTRO de la caja
El contrato expresa todo respecto al origen de la celda; base_link esta 0.75 m
mas arriba (robot sobre el pedestal).

Uso: p6_contrato.py <escenarios.yaml> [--escenario 1] [--n 10]
"""
import argparse, math, sys, os, time
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rclpy
from diagnostico_pendientes import Diag, J, GRUPO, CODIGOS
from moveit_msgs.srv import GetPositionIK, GetMotionPlan, ApplyPlanningScene
from moveit_msgs.msg import (MotionPlanRequest, PositionIKRequest, RobotState,
                             PlanningScene, CollisionObject, PlanningSceneComponents)
from moveit_msgs.srv import GetPlanningScene
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose, PoseStamped, Point, Quaternion

HOLGURA_PEDESTAL = 0.01   # el pedestal toca base_link; 1 cm evita un falso choque de arranque


def quat_rpy(r, p, y):
    cr, sr, cp, sp, cy, sy = (math.cos(r / 2), math.sin(r / 2), math.cos(p / 2),
                              math.sin(p / 2), math.cos(y / 2), math.sin(y / 2))
    return Quaternion(x=sr * cp * cy - cr * sp * sy, y=cr * sp * cy + sr * cp * sy,
                      z=cr * cp * sy - sr * sp * cy, w=cr * cp * cy + sr * sp * sy)


def caja(id_, dims, centro, rpy=(0, 0, 0)):
    o = CollisionObject(); o.header.frame_id = "base_link"; o.id = id_
    b = SolidPrimitive(); b.type = SolidPrimitive.BOX; b.dimensions = list(dims)
    o.primitives.append(b)
    o.primitive_poses.append(Pose(orientation=Quaternion(w=1.0)))
    o.pose = Pose(position=Point(x=centro[0], y=centro[1], z=centro[2]), orientation=quat_rpy(*rpy))
    o.operation = CollisionObject.ADD
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("contrato")
    ap.add_argument("--escenario", type=int, default=1)
    ap.add_argument("--n", type=int, default=10)
    a = ap.parse_args()

    C = yaml.safe_load(open(a.contrato))
    z_base = C["robot"]["base_pose"][2]                  # 0.75
    bib = C["biblioteca"]

    rclpy.init(); d = Diag()
    d.c["compute_ik"] = d.create_client(GetPositionIK, "/compute_ik")
    if not d.c["compute_ik"].wait_for_service(timeout_sec=20):
        sys.exit("falta el servicio /compute_ik")

    # ---------- escena: limpiar y cargar la celda base + obstaculos ----------
    r = GetPlanningScene.Request(); r.components.components = PlanningSceneComponents.WORLD_OBJECT_NAMES
    viejos = []
    for o in d._call("get_planning_scene", r).scene.world.collision_objects:
        c = CollisionObject(); c.id = o.id; c.header.frame_id = "base_link"
        c.operation = CollisionObject.REMOVE; viejos.append(c)

    objs = []
    for comp in C["celda_base"]:
        dims = bib[comp["componente"]]["dim"]
        x, y, z = comp["pose"][:3]
        cz = z + dims[2] / 2 - z_base                      # base-anclada -> centro, en base_link
        if comp["componente"] == "pedestal":
            cz -= HOLGURA_PEDESTAL
        objs.append(caja(comp["componente"], dims, (x, y, cz), comp["pose"][3:6]))
    esc = C["escenarios"][a.escenario]
    for i, ob in enumerate(esc.get("obstaculos", [])):
        info = bib[ob["componente"]]
        if "dim" not in info:
            continue                                        # cilindro/esfera: no aplica a esta prueba
        esc_f = ob.get("escala", [1, 1, 1])
        dims = [dd * e for dd, e in zip(info["dim"], esc_f)]
        x, y, z = ob["pose"][:3]
        objs.append(caja(f"obs{i}_{ob['componente']}", dims, (x, y, z - z_base), ob["pose"][3:6]))

    s = PlanningScene(); s.is_diff = True; s.world.collision_objects.extend(viejos + objs)
    rq = ApplyPlanningScene.Request(); rq.scene = s
    d._call("apply_planning_scene", rq); time.sleep(1.0)
    print(f"\n### P6 | escenario {a.escenario}: {esc['nombre']} | objetos cargados: "
          f"{', '.join(o.id for o in objs)}")

    # ---------- 1. cinematica inversa con la orientacion del contrato ----------
    def resolver_ik(nombre, evitar):
        punto = C["tarea_nominal"][nombre]
        x, y, z = punto["pos"]
        ps = PoseStamped(); ps.header.frame_id = "base_link"
        ps.pose = Pose(position=Point(x=x, y=y, z=z - z_base), orientation=quat_rpy(*punto["rpy"]))
        req = GetPositionIK.Request()
        pik = PositionIKRequest(); pik.group_name = GRUPO; pik.ik_link_name = "tool0"
        pik.pose_stamped = ps; pik.avoid_collisions = evitar
        pik.timeout.sec = 2
        rs = RobotState(); rs.joint_state.name = J
        rs.joint_state.position = C["tarea_nominal"]["q_inicial_rad"]; pik.robot_state = rs
        req.ik_request = pik
        res = d._call("compute_ik", req, t=10)
        q = None
        if res.error_code.val == 1:
            nombres = list(res.solution.joint_state.name)
            q = [res.solution.joint_state.position[nombres.index(j)] for j in J]
        return res.error_code.val, q

    print(f"{'pose':<9}{'sin colisiones':>18}{'con colisiones':>18}   diagnostico")
    sol = {}
    for nombre in ("p_pick", "p_place"):
        c_sin, _ = resolver_ik(nombre, evitar=False)
        c_con, q = resolver_ik(nombre, evitar=True)
        if c_sin != 1:
            diag = "INALCANZABLE con esa orientacion"
        elif c_con != 1:
            diag = "alcanzable, pero TODA solucion choca con la celda"
        else:
            diag = "alcanzable y libre de colision"
            sol[nombre] = q
        print(f"{nombre:<9}{CODIGOS.get(c_sin, c_sin):>18}{CODIGOS.get(c_con, c_con):>18}   {diag}")

    # ---------- 2. planificacion pick -> place ----------
    if len(sol) == 2:
        from moveit_msgs.msg import Constraints, JointConstraint
        cs = Constraints()
        for nm, v in zip(J, sol["p_place"]):
            jc = JointConstraint(); jc.joint_name = nm; jc.position = v
            jc.tolerance_above = jc.tolerance_below = 0.01; jc.weight = 1.0
            cs.joint_constraints.append(jc)
        ok = choca = 0
        for _ in range(a.n):
            req = MotionPlanRequest(); req.group_name = GRUPO; req.planner_id = "RRTConnect"
            req.allowed_planning_time = 5.0; req.num_planning_attempts = 1
            req.start_state.joint_state.name = J; req.start_state.joint_state.position = sol["p_pick"]
            req.goal_constraints.append(cs)
            p = GetMotionPlan.Request(); p.motion_plan_request = req
            res = d._call("plan_kinematic_path", p, t=20).motion_plan_response
            if res.error_code.val == 1:
                ok += 1
                _, col = d.validar_trayectoria(res.trajectory.joint_trajectory.points)
                choca += 1 if col else 0
        print(f"\nRRTConnect p_pick -> p_place: exito {ok}/{a.n}, chocan al validar {choca}/{ok}")
    else:
        print("\nNo se planifica: alguna pose del contrato no tiene solucion libre de colision.")

    d.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
