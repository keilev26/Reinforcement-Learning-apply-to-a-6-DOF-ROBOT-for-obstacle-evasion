#!/usr/bin/env python3
"""Diagnostico de los pendientes P1-P3 del paquete 3.9.

Para cada consulta planifica y, si hay solucion, VALIDA INDEPENDIENTEMENTE la
trayectoria devuelta: la interpola finamente y comprueba cada estado contra la
escena con /check_state_validity. Asi se distingue entre:
  - un plan rechazado cuya trayectoria era realmente segura  (artefacto), y
  - un plan rechazado cuya trayectoria ejecutable si choca   (rechazo correcto).

Uso:
  diagnostico_pendientes.py --escala 1.0 --meta articular --n 20
  diagnostico_pendientes.py --escala 1.0 --meta pose --planners RRTstar --dcc 0
"""
import argparse, math, statistics, sys, time
from collections import Counter

import rclpy
from rclpy.node import Node
from moveit_msgs.srv import (GetMotionPlan, ApplyPlanningScene, GetPlanningScene,
                             GetStateValidity, GetPositionFK, SetPlannerParams)
from moveit_msgs.msg import (MotionPlanRequest, Constraints, JointConstraint,
                             PositionConstraint, OrientationConstraint, BoundingVolume,
                             PlanningScene, CollisionObject, PlanningSceneComponents,
                             RobotState, PlannerParams)
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose, Point, Quaternion

GRUPO = "ur_manipulator"
TCP = "tool0"
J = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
     "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
Q0 = [0.0, -1.5708, 1.5708, -1.5708, -1.5708, 0.0]
Q1 = [1.2, -1.0472, 1.0472, -1.5708, -1.5708, 0.0]
POSE_OBS = [0.422, 0.450, 0.473]          # punto medio real del recorrido del TCP
DIM_OBS = [0.20, 0.20, 0.40]              # prisma del escenario 2 del contrato
# Tolerancias de meta del contrato 3.1 (shared_scenarios/metricas.yaml)
TOL_POS_M, TOL_ORI_RAD, TOL_ART_RAD = 0.010, 0.050, 0.010
PASO_INTERP = 0.02                        # rad, maximo salto articular al validar

CODIGOS = {1: "OK", 99999: "FAILURE", -1: "PLANNING_FAILED", -2: "INVALID_MOTION_PLAN",
           -6: "TIMED_OUT", -10: "START_IN_COLLISION", -12: "GOAL_IN_COLLISION",
           -31: "NO_IK_SOLUTION"}


class Diag(Node):
    def __init__(self):
        super().__init__("diagnostico_pendientes")
        self.c = {n: self.create_client(t, "/" + n) for n, t in (
            ("plan_kinematic_path", GetMotionPlan), ("apply_planning_scene", ApplyPlanningScene),
            ("get_planning_scene", GetPlanningScene), ("check_state_validity", GetStateValidity),
            ("compute_fk", GetPositionFK), ("set_planner_params", SetPlannerParams))}
        for n, cli in self.c.items():
            if not cli.wait_for_service(timeout_sec=30.0):
                sys.exit(f"falta el servicio /{n}: move_group no esta corriendo")

    def _call(self, nombre, req, t=15.0):
        f = self.c[nombre].call_async(req)
        rclpy.spin_until_future_complete(self, f, timeout_sec=t)
        return f.result()

    # ---------- escena ----------
    def escena(self, escala):
        r = GetPlanningScene.Request()
        r.components.components = PlanningSceneComponents.WORLD_OBJECT_NAMES
        viejos = []
        for o in self._call("get_planning_scene", r).scene.world.collision_objects:
            c = CollisionObject(); c.id = o.id; c.header.frame_id = "base_link"
            c.operation = CollisionObject.REMOVE; viejos.append(c)
        objs = viejos
        if escala > 0:
            o = CollisionObject(); o.header.frame_id = "base_link"; o.id = "obs"
            b = SolidPrimitive(); b.type = SolidPrimitive.BOX
            b.dimensions = [d * escala for d in DIM_OBS]
            o.primitives.append(b)
            o.primitive_poses.append(Pose(orientation=Quaternion(w=1.0)))
            o.pose = Pose(position=Point(x=POSE_OBS[0], y=POSE_OBS[1], z=POSE_OBS[2]),
                          orientation=Quaternion(w=1.0))
            o.operation = CollisionObject.ADD
            objs = viejos + [o]
        s = PlanningScene(); s.is_diff = True; s.world.collision_objects.extend(objs)
        r = ApplyPlanningScene.Request(); r.scene = s
        self._call("apply_planning_scene", r)
        time.sleep(0.8)
        # verificacion: la pose debe ser la pedida
        r = GetPlanningScene.Request()
        r.components.components = (PlanningSceneComponents.WORLD_OBJECT_NAMES |
                                   PlanningSceneComponents.WORLD_OBJECT_GEOMETRY)
        objs = self._call("get_planning_scene", r).scene.world.collision_objects
        if escala > 0:
            p = objs[0].pose.position if objs else None
            if p is None or max(abs(p.x - POSE_OBS[0]), abs(p.y - POSE_OBS[1]), abs(p.z - POSE_OBS[2])) > 1e-3:
                sys.exit("ERROR: el obstaculo no quedo en la pose pedida; medicion invalida")
        return len(objs)

    # ---------- validez de estados ----------
    def valido(self, q):
        r = GetStateValidity.Request(); r.group_name = GRUPO
        rs = RobotState(); rs.joint_state.name = J; rs.joint_state.position = list(q)
        r.robot_state = rs
        return self._call("check_state_validity", r).valid

    def validar_trayectoria(self, puntos):
        """Devuelve (estados_revisados, estados_en_colision)."""
        revisados = colision = 0
        prev = None
        for pt in puntos:
            q = list(pt.positions)
            if prev is None:
                seq = [q]
            else:
                salto = max(abs(a - b) for a, b in zip(prev, q))
                k = max(1, math.ceil(salto / PASO_INTERP))
                seq = [[a + (b - a) * i / k for a, b in zip(prev, q)] for i in range(1, k + 1)]
            for s in seq:
                revisados += 1
                if not self.valido(s):
                    colision += 1
            prev = q
        return revisados, colision

    # ---------- metas ----------
    def meta_articular(self):
        cs = Constraints()
        for n, v in zip(J, Q1):
            jc = JointConstraint(); jc.joint_name = n; jc.position = v
            jc.tolerance_above = TOL_ART_RAD; jc.tolerance_below = TOL_ART_RAD; jc.weight = 1.0
            cs.joint_constraints.append(jc)
        return cs

    def meta_pose(self):
        r = GetPositionFK.Request(); r.header.frame_id = "base_link"; r.fk_link_names = [TCP]
        rs = RobotState(); rs.joint_state.name = J; rs.joint_state.position = Q1
        r.robot_state = rs
        pose = self._call("compute_fk", r).pose_stamped[0].pose
        cs = Constraints()
        pc = PositionConstraint(); pc.header.frame_id = "base_link"; pc.link_name = TCP
        esfera = SolidPrimitive(); esfera.type = SolidPrimitive.SPHERE; esfera.dimensions = [TOL_POS_M]
        bv = BoundingVolume(); bv.primitives.append(esfera)
        bv.primitive_poses.append(Pose(position=pose.position, orientation=Quaternion(w=1.0)))
        pc.constraint_region = bv; pc.weight = 1.0
        oc = OrientationConstraint(); oc.header.frame_id = "base_link"; oc.link_name = TCP
        oc.orientation = pose.orientation
        oc.absolute_x_axis_tolerance = oc.absolute_y_axis_tolerance = oc.absolute_z_axis_tolerance = TOL_ORI_RAD
        oc.weight = 1.0
        cs.position_constraints.append(pc); cs.orientation_constraints.append(oc)
        return cs

    # ---------- planificador ----------
    def fijar(self, planner, claves, valores):
        r = SetPlannerParams.Request()
        r.pipeline_id = "ompl"; r.planner_config = planner; r.group = GRUPO; r.replace = False
        p = PlannerParams(); p.keys = claves; p.values = [str(v) for v in valores]
        r.params = p
        self._call("set_planner_params", r)

    def planificar(self, planner, meta, tiempo):
        req = MotionPlanRequest(); req.group_name = GRUPO; req.planner_id = planner
        req.allowed_planning_time = tiempo; req.num_planning_attempts = 1
        req.start_state.joint_state.name = J; req.start_state.joint_state.position = Q0
        req.goal_constraints.append(meta)
        p = GetMotionPlan.Request(); p.motion_plan_request = req
        res = self._call("plan_kinematic_path", p, t=tiempo + 15).motion_plan_response
        pts = res.trajectory.joint_trajectory.points
        L = sum(math.dist(a.positions, b.positions) for a, b in zip(pts, pts[1:]))
        return res.error_code.val, res.planning_time * 1000.0, L, pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--planners", default="RRTConnect,RRTstar")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--tiempo", type=float, default=5.0)
    ap.add_argument("--escala", type=float, default=1.0)
    ap.add_argument("--meta", choices=["articular", "pose"], default="articular")
    ap.add_argument("--dcc", type=int, default=None, help="delay_collision_checking para RRTstar")
    ap.add_argument("--set", action="append", default=[], metavar="CLAVE=VALOR",
                    help="parametro de OMPL aplicado a cada planificador listado (repetible)")
    ap.add_argument("--etiqueta", default="")
    a = ap.parse_args()

    rclpy.init(); d = Diag()
    nobj = d.escena(a.escala)
    meta = d.meta_articular() if a.meta == "articular" else d.meta_pose()
    if a.dcc is not None:
        d.fijar("RRTstar", ["delay_collision_checking"], [a.dcc])
    if a.set:
        claves = [kv.split("=", 1)[0] for kv in a.set]
        valores = [kv.split("=", 1)[1] for kv in a.set]
        for planner in a.planners.split(","):
            d.fijar(planner, claves, valores)

    esc = "sin obstaculo" if a.escala == 0 else "x".join(f"{x * a.escala:.2f}" for x in DIM_OBS)
    print(f"\n### {a.etiqueta} | obstaculo {esc} | meta {a.meta} | n={a.n} | "
          f"{a.tiempo}s" + (f" | dcc={a.dcc}" if a.dcc is not None else "")
          + (f" | {' '.join(a.set)}" if a.set else ""))
    print(f"{'planner':<11}{'exito':>8}{'t_med(ms)':>11}{'long(rad)':>11}"
          f"{'  choca al validar':>20}   fallos")
    for planner in a.planners.split(","):
        filas = [d.planificar(planner, meta, a.tiempo) for _ in range(a.n)]
        ok = [f for f in filas if f[0] == 1]
        choca = 0
        for f in ok:
            _, col = d.validar_trayectoria(f[3])
            if col:
                choca += 1
        fallos = Counter(CODIGOS.get(f[0], f[0]) for f in filas if f[0] != 1)
        tm = statistics.mean(f[1] for f in ok) if ok else float("nan")
        Lm = statistics.mean(f[2] for f in ok) if ok else float("nan")
        print(f"{planner:<11}{len(ok):>4}/{a.n:<3}{tm:>11.1f}{Lm:>11.3f}"
              f"{choca:>12}/{len(ok):<7}   " + (", ".join(f"{k}={v}" for k, v in fallos.items()) or "-"))
    d.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
