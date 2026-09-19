#!/usr/bin/env python3
"""Paquete 3.9 — Verificacion de la configuracion de OMPL.

Planifica N veces con cada planificador via el servicio /plan_kinematic_path y
reporta tasa de exito, tiempo de planificacion y longitud articular.

No ejecuta la trayectoria: solo verifica que RRT-Connect y RRT* quedan
seleccionables con los parametros fijados y que ambos resuelven la consulta.

Uso:  ros2 run rl6gdl_planning test_planners.py [--n 10] [--tiempo 5.0]
"""
import argparse
import math
import statistics
import sys
import time

import rclpy
from rclpy.node import Node
from moveit_msgs.srv import GetMotionPlan, ApplyPlanningScene, GetPlanningScene
from moveit_msgs.msg import (MotionPlanRequest, Constraints, JointConstraint,
                             PlanningScene, CollisionObject, PlanningSceneComponents)
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose, Point, Quaternion

GRUPO = "ur_manipulator"
ARTICULACIONES = ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
                  "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"]

# Pose de reposo -> configuracion de recogida, declaradas en el contrato 3.1
Q_INICIAL = [0.0, -1.5708, 1.5708, -1.5708, -1.5708, 0.0]
Q_META    = [1.2, -1.0472, 1.0472, -1.5708, -1.5708, 0.0]

# Obstaculo con la MISMA geometria que el prisma del escenario 2 del contrato
# (shared_scenarios/escenarios.yaml): 0.20 x 0.20 x 0.40 m.
#
# La POSE no es la del contrato. El contrato situa el prisma en el punto medio
# entre p_pick y p_place, que son poses de la celda de E1, todavia no modelada.
# Esta verificacion usa una consulta articular propia, asi que el obstaculo se
# coloca en el punto medio REAL de su recorrido, calculado por cinematica directa
# con PyBullet: (0.422, 0.450, 0.473) en el marco base_link.
#
# Verificado: con la pose del contrato el prisma quedaba a 0.80 m del recorrido
# y no obstruia nada, lo que hacia la prueba vacia.
PRISMA_DIM  = [0.20, 0.20, 0.40]
PRISMA_POSE = [0.422, 0.450, 0.473]


class Verificador(Node):
    def __init__(self):
        super().__init__("verificador_planificadores")
        self.cli = self.create_client(GetMotionPlan, "/plan_kinematic_path")
        self.get_logger().info("esperando el servicio /plan_kinematic_path ...")
        if not self.cli.wait_for_service(timeout_sec=30.0):
            self.get_logger().error("el servicio no aparecio: move_group no esta corriendo")
            sys.exit(1)

    def _aplicar(self, objetos):
        cli = self.create_client(ApplyPlanningScene, "/apply_planning_scene")
        if not cli.wait_for_service(timeout_sec=15.0):
            self.get_logger().error("no aparecio /apply_planning_scene")
            return False
        escena = PlanningScene()
        escena.is_diff = True
        escena.world.collision_objects.extend(objetos)
        pet = ApplyPlanningScene.Request()
        pet.scene = escena
        fut = cli.call_async(pet)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=15.0)
        return fut.result() is not None and fut.result().success

    def _objetos_en_escena(self):
        cli = self.create_client(GetPlanningScene, "/get_planning_scene")
        if not cli.wait_for_service(timeout_sec=15.0):
            return []
        pet = GetPlanningScene.Request()
        pet.components.components = (PlanningSceneComponents.WORLD_OBJECT_NAMES |
                                     PlanningSceneComponents.WORLD_OBJECT_GEOMETRY)
        fut = cli.call_async(pet)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=15.0)
        if fut.result() is None:
            return []
        return fut.result().scene.world.collision_objects

    def limpiar_escena(self):
        """La escena de planificacion PERSISTE entre ejecuciones del script.
        Sin esta limpieza los obstaculos se acumulan y las medidas salen de una
        escena distinta de la declarada."""
        viejos = []
        for o in self._objetos_en_escena():
            c = CollisionObject()
            c.id = o.id
            c.header.frame_id = "base_link"
            c.operation = CollisionObject.REMOVE
            viejos.append(c)
        if viejos:
            self._aplicar(viejos)
            self.get_logger().info(f"escena limpiada: {len(viejos)} objeto(s) residual(es)")

    def cargar_obstaculo(self):
        """Inserta el prisma del escenario 2 en la escena de planificacion.

        La pose va en obj.pose, NO en primitive_poses: MoveIt interpreta las poses
        de las primitivas como RELATIVAS al marco del objeto. Fijarlas como si
        fueran absolutas deja el obstaculo en el origen, encajado en la base del
        robot, sin que nada lo advierta.
        """
        self.limpiar_escena()

        obj = CollisionObject()
        obj.header.frame_id = "base_link"
        obj.id = "escenario2_prisma"
        caja = SolidPrimitive()
        caja.type = SolidPrimitive.BOX
        caja.dimensions = PRISMA_DIM
        obj.primitives.append(caja)
        obj.primitive_poses.append(Pose(position=Point(x=0.0, y=0.0, z=0.0),
                                        orientation=Quaternion(w=1.0)))
        obj.pose = Pose(position=Point(x=PRISMA_POSE[0], y=PRISMA_POSE[1], z=PRISMA_POSE[2]),
                        orientation=Quaternion(w=1.0))
        obj.operation = CollisionObject.ADD

        ok = self._aplicar([obj])

        # Verificacion de que la pose quedo donde se pidio
        for o in self._objetos_en_escena():
            if o.id == obj.id:
                p = o.pose.position
                self.get_logger().info(
                    f"obstaculo en ({p.x:.3f}, {p.y:.3f}, {p.z:.3f}) — esperado "
                    f"({PRISMA_POSE[0]:.3f}, {PRISMA_POSE[1]:.3f}, {PRISMA_POSE[2]:.3f})")
                if abs(p.x-PRISMA_POSE[0])>1e-3 or abs(p.y-PRISMA_POSE[1])>1e-3 or abs(p.z-PRISMA_POSE[2])>1e-3:
                    self.get_logger().error("la pose NO coincide: la medicion no seria valida")
                    return False
        return ok

    def planificar(self, planner_id, tiempo_max):
        req = MotionPlanRequest()
        req.group_name = GRUPO
        req.planner_id = planner_id
        req.allowed_planning_time = tiempo_max
        req.num_planning_attempts = 1

        req.start_state.joint_state.name = ARTICULACIONES
        req.start_state.joint_state.position = Q_INICIAL
        req.start_state.is_diff = False

        metas = Constraints()
        for nombre, valor in zip(ARTICULACIONES, Q_META):
            jc = JointConstraint()
            jc.joint_name = nombre
            jc.position = valor
            jc.tolerance_above = 0.001
            jc.tolerance_below = 0.001
            jc.weight = 1.0
            metas.joint_constraints.append(jc)
        req.goal_constraints.append(metas)

        peticion = GetMotionPlan.Request()
        peticion.motion_plan_request = req

        t0 = time.perf_counter()
        fut = self.cli.call_async(peticion)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=tiempo_max + 10.0)
        t_pared = (time.perf_counter() - t0) * 1000.0

        if fut.result() is None:
            return None
        res = fut.result().motion_plan_response
        ok = res.error_code.val == 1
        puntos = res.trajectory.joint_trajectory.points
        long_art = 0.0
        for a, b in zip(puntos, puntos[1:]):
            long_art += math.dist(a.positions, b.positions)
        return {
            "ok": ok, "codigo": res.error_code.val,
            "t_planificacion_ms": res.planning_time * 1000.0,
            "t_pared_ms": t_pared,
            "puntos": len(puntos), "longitud_articular_rad": long_art,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--tiempo", type=float, default=5.0, help="presupuesto de planificacion (s)")
    ap.add_argument("--con-obstaculo", action="store_true",
                    help="carga el prisma del escenario 2 del contrato 3.1")
    args = ap.parse_args()

    rclpy.init()
    nodo = Verificador()

    escena = "escenario 2 (prisma en la trayectoria nominal)" if args.con_obstaculo else "espacio libre"
    if args.con_obstaculo:
        nodo.cargar_obstaculo()
        time.sleep(1.5)

    print(f"\n{'='*74}\nVerificacion de la configuracion de OMPL — paquete 3.9")
    print(f"escena: {escena}")
    print(f"{args.n} consultas por planificador, presupuesto {args.tiempo} s\n{'='*74}")

    resumen = {}
    for planner in ("RRTConnect", "RRTstar"):
        filas = [nodo.planificar(planner, args.tiempo) for _ in range(args.n)]
        filas = [f for f in filas if f is not None]
        exitos = [f for f in filas if f["ok"]]
        print(f"\n--- {planner} ---")
        if not filas:
            print("  sin respuesta del servicio")
            continue
        print(f"  tasa de exito        : {len(exitos)}/{len(filas)}")
        if exitos:
            tp = [f['t_planificacion_ms'] for f in exitos]
            la = [f['longitud_articular_rad'] for f in exitos]
            pt = [f['puntos'] for f in exitos]
            print(f"  t. planificacion (ms): media {statistics.mean(tp):8.2f}   "
                  f"desv {statistics.pstdev(tp):7.2f}   min {min(tp):7.2f}   max {max(tp):7.2f}")
            print(f"  longitud art. (rad)  : media {statistics.mean(la):8.4f}   "
                  f"desv {statistics.pstdev(la):7.4f}")
            print(f"  puntos de trayectoria: media {statistics.mean(pt):8.1f}")
            resumen[planner] = (statistics.mean(tp), statistics.mean(la))
        fallos = [f for f in filas if not f["ok"]]
        if fallos:
            from collections import Counter
            CODIGOS = {1:"SUCCESS", -1:"FAILURE", -2:"PLANNING_FAILED",
                       -3:"INVALID_MOTION_PLAN", -6:"TIMED_OUT",
                       -10:"START_STATE_IN_COLLISION", -11:"START_STATE_VIOLATES_PATH_CONSTRAINTS",
                       -12:"GOAL_IN_COLLISION", -13:"GOAL_VIOLATES_PATH_CONSTRAINTS",
                       -31:"NO_IK_SOLUTION"}
            c = Counter(f["codigo"] for f in fallos)
            print("  fallos por codigo   : " +
                  ", ".join(f"{CODIGOS.get(k, k)}={v}" for k, v in c.most_common()))

    if len(resumen) == 2:
        tc, lc = resumen["RRTConnect"]; ts, ls = resumen["RRTstar"]
        print(f"\n{'='*74}\nContraste esperado: RRT* invierte mas tiempo a cambio de mejor trayectoria")
        print(f"  tiempo    RRT*/RRT-Connect = {ts/tc:5.2f}x")
        print(f"  longitud  RRT*/RRT-Connect = {ls/lc:5.2f}x  (<1 indica trayectoria mas corta)")
    print()

    nodo.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
