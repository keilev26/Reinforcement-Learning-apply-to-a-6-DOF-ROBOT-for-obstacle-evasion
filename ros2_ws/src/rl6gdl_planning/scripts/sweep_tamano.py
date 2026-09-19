#!/usr/bin/env python3
"""Paquete 3.9 — Sensibilidad de la linea base al tamano del obstaculo.

Caracteriza a partir de que tamano de obstruccion los planificadores clasicos
empiezan a fallar con un presupuesto dado. Es informacion directamente util
para el escenario 7 del contrato (paso estrecho, prueba de estres).
"""
import math, statistics, time, sys
import rclpy
from rclpy.node import Node
from moveit_msgs.srv import GetMotionPlan, ApplyPlanningScene, GetPlanningScene
from moveit_msgs.msg import (MotionPlanRequest, Constraints, JointConstraint,
                             PlanningScene, CollisionObject, PlanningSceneComponents)
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose, Point, Quaternion

J = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
     "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]
Q0 = [0.0, -1.5708, 1.5708, -1.5708, -1.5708, 0.0]
Q1 = [1.2, -1.0472, 1.0472, -1.5708, -1.5708, 0.0]
POSE = [0.422, 0.450, 0.473]     # punto medio real del recorrido del TCP
BASE = [0.20, 0.20, 0.40]        # prisma del escenario 2 del contrato
N, T = 10, 5.0
ESCALAS = [0.0, 0.25, 0.50, 0.75, 1.00]


class B(Node):
    def __init__(self):
        super().__init__("sweep_tamano")
        self.plan = self.create_client(GetMotionPlan, "/plan_kinematic_path")
        self.ap = self.create_client(ApplyPlanningScene, "/apply_planning_scene")
        self.gs = self.create_client(GetPlanningScene, "/get_planning_scene")
        for c in (self.plan, self.ap, self.gs):
            if not c.wait_for_service(timeout_sec=30.0):
                sys.exit("falta un servicio de move_group")

    def _leer(self):
        r = GetPlanningScene.Request()
        r.components.components = PlanningSceneComponents.WORLD_OBJECT_NAMES
        f = self.gs.call_async(r)
        rclpy.spin_until_future_complete(self, f, timeout_sec=15)
        return f.result().scene.world.collision_objects if f.result() else []

    def _aplicar(self, objs):
        s = PlanningScene(); s.is_diff = True
        s.world.collision_objects.extend(objs)
        r = ApplyPlanningScene.Request(); r.scene = s
        f = self.ap.call_async(r)
        rclpy.spin_until_future_complete(self, f, timeout_sec=15)

    def poner(self, escala):
        viejos = []
        for o in self._leer():
            c = CollisionObject(); c.id = o.id
            c.header.frame_id = "base_link"; c.operation = CollisionObject.REMOVE
            viejos.append(c)
        if viejos:
            self._aplicar(viejos)
        if escala == 0:
            time.sleep(0.5); return
        o = CollisionObject(); o.header.frame_id = "base_link"; o.id = "obs"
        b = SolidPrimitive(); b.type = SolidPrimitive.BOX
        b.dimensions = [d * escala for d in BASE]
        o.primitives.append(b)
        o.primitive_poses.append(Pose(orientation=Quaternion(w=1.0)))
        o.pose = Pose(position=Point(x=POSE[0], y=POSE[1], z=POSE[2]),
                      orientation=Quaternion(w=1.0))
        o.operation = CollisionObject.ADD
        self._aplicar([o]); time.sleep(0.6)

    def consulta(self, planner):
        r = MotionPlanRequest()
        r.group_name = "ur_manipulator"; r.planner_id = planner
        r.allowed_planning_time = T; r.num_planning_attempts = 1
        r.start_state.joint_state.name = J
        r.start_state.joint_state.position = Q0
        cs = Constraints()
        for nm, v in zip(J, Q1):
            jc = JointConstraint(); jc.joint_name = nm; jc.position = v
            jc.tolerance_above = 0.01; jc.tolerance_below = 0.01; jc.weight = 1.0
            cs.joint_constraints.append(jc)
        r.goal_constraints.append(cs)
        p = GetMotionPlan.Request(); p.motion_plan_request = r
        f = self.plan.call_async(p)
        rclpy.spin_until_future_complete(self, f, timeout_sec=T + 10)
        if f.result() is None:
            return None
        res = f.result().motion_plan_response
        pts = res.trajectory.joint_trajectory.points
        L = sum(math.dist(a.positions, b.positions) for a, b in zip(pts, pts[1:]))
        return (res.error_code.val == 1, res.planning_time * 1000.0, L)


def main():
    rclpy.init(); n = B()
    print("\n" + "=" * 76)
    print(f"Sensibilidad al tamano del obstaculo — {N} consultas, presupuesto {T}s")
    print("=" * 76)
    print(f"{'escala':>7}{'dim (m)':>22}{'planner':>13}{'exito':>9}{'t(ms)':>11}{'long(rad)':>12}")
    print("-" * 76)
    for esc in ESCALAS:
        n.poner(esc)
        dim = "sin obstaculo" if esc == 0 else "x".join(f"{d*esc:.2f}" for d in BASE)
        for pl in ("RRTConnect", "RRTstar"):
            res = [n.consulta(pl) for _ in range(N)]
            res = [r for r in res if r]
            ok = [(t, L) for o, t, L in res if o]
            tm = statistics.mean([t for t, _ in ok]) if ok else float("nan")
            Lm = statistics.mean([L for _, L in ok]) if ok else float("nan")
            print(f"{esc:>7.2f}{dim:>22}{pl:>13}{len(ok):>5}/{len(res):<3}{tm:>11.1f}{Lm:>12.3f}")
        print()
    n.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
