"""Levanta move_group con el Magician E6 y la configuración de OMPL del paquete 3.9.

No arranca Gazebo: para verificar la PLANIFICACIÓN basta el modelo del robot,
robot_state_publisher y un publicador de estados articulares.

El URDF y el SRDF salen de rl6gdl_e6_description (fuente única, generada con
tools/gen_modelo_e6.py): la matriz de colisiones del SRDF es la misma que usa PyBullet.
Los parámetros se arman a mano, sin MoveItConfigsBuilder, porque el URDF, el SRDF y la
configuración de planificación viven en paquetes distintos.

Uso: ros2 launch rl6gdl_planning planning_e6.launch.py [ompl_config:=<ruta.yaml>]
"""
import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def leer(paquete, ruta_rel):
    with open(os.path.join(get_package_share_directory(paquete), ruta_rel)) as f:
        return f.read()


def launch_setup(context):
    robot_description = {"robot_description": leer("rl6gdl_e6_description", "urdf/magician_e6.urdf")}
    semantic = {"robot_description_semantic": leer("rl6gdl_e6_description", "config/magician_e6.srdf")}
    kinematics = {"robot_description_kinematics":
                  yaml.safe_load(leer("rl6gdl_planning", "config/e6/kinematics.yaml"))}
    planning = {"robot_description_planning":
                yaml.safe_load(leer("rl6gdl_planning", "config/e6/joint_limits.yaml"))}

    ruta = LaunchConfiguration("ompl_config").perform(context)
    if ruta:
        with open(ruta) as f:
            ompl = yaml.safe_load(f)
    else:
        ompl = yaml.safe_load(leer("rl6gdl_planning", "config/ompl_planning_e6.yaml"))

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            robot_description, semantic, kinematics, planning,
            {"ompl": ompl},
            {"planning_pipelines": ["ompl"], "default_planning_pipeline": "ompl"},
            {"publish_robot_description_semantic": True, "use_sim_time": False},
        ],
    )
    rsp = Node(package="robot_state_publisher", executable="robot_state_publisher",
               output="screen", parameters=[robot_description])
    jsp = Node(package="joint_state_publisher", executable="joint_state_publisher",
               output="screen", parameters=[robot_description])
    return [rsp, jsp, move_group]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("ompl_config", default_value="",
                              description="YAML de OMPL alternativo (vacío = el del paquete)"),
        OpaqueFunction(function=launch_setup),
    ])
