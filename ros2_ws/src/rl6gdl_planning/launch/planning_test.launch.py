"""Levanta move_group con la configuracion de OMPL del paquete 3.9.

No arranca Gazebo: para verificar la PLANIFICACION basta el modelo del robot,
robot_state_publisher y un publicador de estados articulares.

Corrige ademas el desajuste de nombre entre URDF y SRDF documentado en
docs/semana-03/nota-tecnica-entorno.md: ur_sim_control.launch.py fija el URDF con
name:="ur" mientras ur_moveit.launch.py construye el SRDF con name:=ur_type.
Aqui se pasa el MISMO nombre a ambos.
"""
import os
import yaml
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder

NOMBRE_ROBOT = "ur5e"     # mismo valor para URDF y SRDF: evita el desajuste


def cargar_yaml(paquete, ruta_rel):
    ruta = os.path.join(get_package_share_directory(paquete), ruta_rel)
    with open(ruta, "r") as f:
        return yaml.safe_load(f)


def launch_setup(context):
    ur_type = LaunchConfiguration("ur_type")

    robot_description = {
        "robot_description": Command([
            PathJoinSubstitution([FindExecutable(name="xacro")]), " ",
            PathJoinSubstitution([FindPackageShare("ur_description"), "urdf", "ur.urdf.xacro"]), " ",
            "name:=", NOMBRE_ROBOT, " ",
            "ur_type:=", ur_type, " ",
            "safety_limits:=true",
        ])
    }

    moveit_config = (
        MoveItConfigsBuilder(robot_name=NOMBRE_ROBOT, package_name="ur_moveit_config")
        .robot_description_semantic(Path("srdf") / "ur.srdf.xacro", {"name": NOMBRE_ROBOT})
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .to_moveit_configs()
    )

    # Configuracion de OMPL: la del paquete por defecto, o una alternativa via
    # ompl_config:=<ruta> para experimentos sin tocar la entregada.
    ruta = LaunchConfiguration("ompl_config").perform(context)
    if ruta:
        with open(ruta, "r") as f:
            ompl_config = yaml.safe_load(f)
    else:
        ompl_config = cargar_yaml("rl6gdl_planning", "config/ompl_planning.yaml")

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            robot_description,
            {"ompl": ompl_config},
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
        DeclareLaunchArgument("ur_type", default_value="ur5e"),
        DeclareLaunchArgument("ompl_config", default_value="",
                              description="YAML de OMPL alternativo (vacio = el del paquete)"),
        OpaqueFunction(function=launch_setup),
    ])
