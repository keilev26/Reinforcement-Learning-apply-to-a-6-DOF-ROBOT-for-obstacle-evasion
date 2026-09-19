#!/usr/bin/env python3
"""Paquete 3.9 — Barrido de parametros de OMPL.

Justifica empiricamente los valores de range y longest_valid_segment_fraction
en vez de fijarlos por intuicion. Cambia los parametros en caliente via
/set_planner_params, sin relanzar move_group.
"""
import statistics, sys, time
import rclpy
from rclpy.node import Node
from moveit_msgs.srv import GetMotionPlan, SetPlannerParams, ApplyPlanningScene
from moveit_msgs.msg import (MotionPlanRequest, Constraints, JointConstraint,
                             PlannerParams, PlanningScene, CollisionObject)
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose

GRUPO = "ur_manipulator"
J = ["shoulder_pan_joint","shoulder_lift_joint","elbow_joint",
     "wrist_1_joint","wrist_2_joint","wrist_3_joint"]
Q0 = [0.0,-1.5708,1.5708,-1.5708,-1.5708,0.0]
Q1 = [1.2,-1.0472,1.0472,-1.5708,-1.5708,0.0]
PRISMA_DIM, PRISMA_POSE = [0.20,0.20,0.40], [0.422,0.450,0.473]

N = 10
TIEMPO = 5.0
RANGOS = [0.5, 1.0, 2.0, 5.76]        # 5.76 = default de OMPL (0.2 x extension)
LVSF   = [0.005, 0.020]


class Barrido(Node):
    def __init__(self):
        super().__init__("barrido_ompl")
        self.plan = self.create_client(GetMotionPlan, "/plan_kinematic_path")
        self.setp = self.create_client(SetPlannerParams, "/set_planner_params")
        self.esc  = self.create_client(ApplyPlanningScene, "/apply_planning_scene")
        for c, n in ((self.plan,"plan_kinematic_path"),(self.setp,"set_planner_params"),
                     (self.esc,"apply_planning_scene")):
            if not c.wait_for_service(timeout_sec=30.0):
                self.get_logger().error(f"falta el servicio {n}"); sys.exit(1)

    def obstaculo(self):
        o = CollisionObject(); o.header.frame_id="base_link"; o.id="obstaculo"
        b = SolidPrimitive(); b.type=SolidPrimitive.BOX; b.dimensions=PRISMA_DIM
        pz = Pose(); pz.position.x,pz.position.y,pz.position.z = PRISMA_POSE
        pz.orientation.w=1.0
        o.primitives.append(b); o.primitive_poses.append(pz); o.operation=CollisionObject.ADD
        s = PlanningScene(); s.is_diff=True; s.world.collision_objects.append(o)
        r = ApplyPlanningScene.Request(); r.scene=s
        f = self.setp and self.esc.call_async(r)
        rclpy.spin_until_future_complete(self,f,timeout_sec=15.0)

    def fijar(self, planner, rango, lvsf):
        r = SetPlannerParams.Request()
        r.pipeline_id="ompl"; r.planner_config=planner; r.group=GRUPO; r.replace=False
        p = PlannerParams()
        p.keys   = ["range","longest_valid_segment_fraction"]
        p.values = [str(rango), str(lvsf)]
        r.params = p
        f = self.setp.call_async(r)
        rclpy.spin_until_future_complete(self,f,timeout_sec=10.0)

    def consulta(self, planner):
        req = MotionPlanRequest()
        req.group_name=GRUPO; req.planner_id=planner
        req.allowed_planning_time=TIEMPO; req.num_planning_attempts=1
        req.start_state.joint_state.name=J; req.start_state.joint_state.position=Q0
        cs = Constraints()
        for n,v in zip(J,Q1):
            jc=JointConstraint(); jc.joint_name=n; jc.position=v
            jc.tolerance_above=0.001; jc.tolerance_below=0.001; jc.weight=1.0
            cs.joint_constraints.append(jc)
        req.goal_constraints.append(cs)
        pet=GetMotionPlan.Request(); pet.motion_plan_request=req
        f=self.plan.call_async(pet)
        rclpy.spin_until_future_complete(self,f,timeout_sec=TIEMPO+10)
        if f.result() is None: return None
        r=f.result().motion_plan_response
        return (r.error_code.val==1, r.planning_time*1000.0)


def main():
    rclpy.init(); n = Barrido(); n.obstaculo(); time.sleep(1.0)
    print(f"\n{'='*78}")
    print(f"Barrido de parametros de OMPL — {N} consultas por celda, presupuesto {TIEMPO}s")
    print(f"escena: prisma 0.20x0.20x0.40 obstruyendo la trayectoria")
    print(f"{'='*78}")
    print(f"{'planner':<12}{'range':>7}{'lvsf':>8}{'exito':>9}{'t medio(ms)':>14}")
    print("-"*78)
    mejor = {}
    for planner in ("RRTConnect","RRTstar"):
        for lvsf in LVSF:
            for rango in RANGOS:
                n.fijar(planner,rango,lvsf); time.sleep(0.3)
                res=[n.consulta(planner) for _ in range(N)]
                res=[r for r in res if r]
                ok=[t for o,t in res if o]
                tasa=len(ok)/len(res) if res else 0
                tm=statistics.mean(ok) if ok else float("nan")
                print(f"{planner:<12}{rango:>7.2f}{lvsf:>8.3f}{len(ok):>5}/{len(res):<3}{tm:>14.1f}")
                clave=(planner,)
                if clave not in mejor or (tasa,-tm) > mejor[clave][0]:
                    mejor[clave]=((tasa,-tm),rango,lvsf,tasa,tm)
    print("-"*78)
    print("\nMejor combinacion por planificador (max tasa de exito, luego min tiempo):")
    for (p,),(_,r,l,tasa,tm) in mejor.items():
        print(f"  {p:<12} range={r:.2f}  lvsf={l:.3f}  ->  exito {tasa:.0%}, {tm:.1f} ms")
    n.destroy_node(); rclpy.shutdown()

if __name__=="__main__":
    main()
