#!/usr/bin/env python3
"""Hipotesis: RRT* falla porque la tolerancia de meta (0.001 rad) hace que la
region objetivo sea practicamente un punto en 6D. RRT-Connect no lo sufre porque
crece un arbol desde la meta; RRT*, de arbol unico, debe acertarla muestreando.

Se barre la tolerancia y se mide la tasa de exito de cada planificador.
"""
import statistics, sys, time
import rclpy
from rclpy.node import Node
from moveit_msgs.srv import GetMotionPlan, ApplyPlanningScene
from moveit_msgs.msg import (MotionPlanRequest, Constraints, JointConstraint,
                             PlanningScene, CollisionObject)
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose

GRUPO="ur_manipulator"
J=["shoulder_pan_joint","shoulder_lift_joint","elbow_joint","wrist_1_joint","wrist_2_joint","wrist_3_joint"]
Q0=[0.0,-1.5708,1.5708,-1.5708,-1.5708,0.0]
Q1=[1.2,-1.0472,1.0472,-1.5708,-1.5708,0.0]
N=10; TIEMPO=5.0
TOLERANCIAS=[0.001, 0.01, 0.05, 0.10]

class T(Node):
    def __init__(self):
        super().__init__("test_tolerancia")
        self.plan=self.create_client(GetMotionPlan,"/plan_kinematic_path")
        self.esc=self.create_client(ApplyPlanningScene,"/apply_planning_scene")
        for c in (self.plan,self.esc):
            if not c.wait_for_service(timeout_sec=30.0): sys.exit("falta servicio")
    def obstaculo(self):
        o=CollisionObject(); o.header.frame_id="base_link"; o.id="obstaculo"
        b=SolidPrimitive(); b.type=SolidPrimitive.BOX; b.dimensions=[0.20,0.20,0.40]
        pz=Pose(); pz.position.x,pz.position.y,pz.position.z=0.422,0.450,0.473; pz.orientation.w=1.0
        o.primitives.append(b); o.primitive_poses.append(pz); o.operation=CollisionObject.ADD
        s=PlanningScene(); s.is_diff=True; s.world.collision_objects.append(o)
        r=ApplyPlanningScene.Request(); r.scene=s
        f=self.esc.call_async(r); rclpy.spin_until_future_complete(self,f,timeout_sec=15.0)
    def consulta(self,planner,tol):
        req=MotionPlanRequest(); req.group_name=GRUPO; req.planner_id=planner
        req.allowed_planning_time=TIEMPO; req.num_planning_attempts=1
        req.start_state.joint_state.name=J; req.start_state.joint_state.position=Q0
        cs=Constraints()
        for n,v in zip(J,Q1):
            jc=JointConstraint(); jc.joint_name=n; jc.position=v
            jc.tolerance_above=tol; jc.tolerance_below=tol; jc.weight=1.0
            cs.joint_constraints.append(jc)
        req.goal_constraints.append(cs)
        pet=GetMotionPlan.Request(); pet.motion_plan_request=req
        f=self.plan.call_async(pet); rclpy.spin_until_future_complete(self,f,timeout_sec=TIEMPO+10)
        if f.result() is None: return None
        r=f.result().motion_plan_response
        pts=r.trajectory.joint_trajectory.points
        import math
        L=sum(math.dist(a.positions,b.positions) for a,b in zip(pts,pts[1:]))
        return (r.error_code.val==1, r.planning_time*1000.0, L)

def main():
    rclpy.init(); n=T(); n.obstaculo(); time.sleep(1.0)
    print(f"\n{'='*72}\nEfecto de la tolerancia de meta — {N} consultas, presupuesto {TIEMPO}s")
    print(f"{'='*72}\n{'planner':<12}{'tol(rad)':>10}{'exito':>10}{'t(ms)':>12}{'long(rad)':>12}")
    print("-"*72)
    for planner in ("RRTConnect","RRTstar"):
        for tol in TOLERANCIAS:
            res=[n.consulta(planner,tol) for _ in range(N)]
            res=[r for r in res if r]
            ok=[(t,L) for o,t,L in res if o]
            tm=statistics.mean([t for t,_ in ok]) if ok else float("nan")
            Lm=statistics.mean([L for _,L in ok]) if ok else float("nan")
            print(f"{planner:<12}{tol:>10.3f}{len(ok):>6}/{len(res):<3}{tm:>12.1f}{Lm:>12.4f}")
        print()
    n.destroy_node(); rclpy.shutdown()

if __name__=="__main__": main()
