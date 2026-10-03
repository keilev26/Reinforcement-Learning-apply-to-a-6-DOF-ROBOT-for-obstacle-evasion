import os
import sys
import tempfile
from pathlib import Path

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction,
                            RegisterEventHandler)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

PAQUETE = "rl6gdl_e6_gazebo"


def _contrato():
    for padre in Path(__file__).resolve().parents:
        if (padre / "shared_scenarios" / "contrato.py").exists():
            sys.path.insert(0, str(padre / "shared_scenarios"))
            import contrato
            return contrato
    raise RuntimeError("no se encuentra shared_scenarios/contrato.py")


def launch_setup(context):
    arg = lambda n: context.launch_configurations[n]
    contrato = _contrato()
    C = contrato.cargar()

    mundo = Path(tempfile.gettempdir()) / f"rl6gdl_e6_escenario_{arg('escenario')}.sdf"
    mundo.write_text(contrato.mundo_sdf(C, int(arg("escenario")), arg("variante") or None)[1])

    compartido = get_package_share_directory(PAQUETE)
    descripcion = get_package_share_directory("rl6gdl_e6_description")
    urdf = xacro.process_file(
        os.path.join(compartido, "urdf", "magician_e6_gz.urdf.xacro"),
        mappings={"controladores": os.path.join(compartido, "config", "controladores.yaml"),
                  "efector_radio": str(C["efector"]["radio_m"]),
                  "efector_largo": str(C["efector"]["largo_m"])}).toxml()
    urdf = urdf.replace("package://rl6gdl_e6_description/", f"file://{descripcion}/")

    rsp = Node(package="robot_state_publisher", executable="robot_state_publisher", output="screen",
               parameters=[{"robot_description": urdf, "use_sim_time": True}])
    gz = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py")),
        launch_arguments={"gz_args": ("-r -v 2 " if arg("gui") == "true" else "-s -r -v 2 ") + str(mundo),
                          "on_exit_shutdown": "true"}.items())
    crear = Node(package="ros_gz_sim", executable="create", output="screen",
                 arguments=["-string", urdf, "-name", "magician_e6", "-allow_renaming", "true"])
    reloj = Node(package="ros_gz_bridge", executable="parameter_bridge", output="screen",
                 arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"])
    jsb = Node(package="controller_manager", executable="spawner", output="screen",
               arguments=["joint_state_broadcaster", "-c", "/controller_manager"])
    brazo = Node(package="controller_manager", executable="spawner", output="screen",
                 arguments=["brazo_controller", "-c", "/controller_manager"])
    tras_crear = RegisterEventHandler(OnProcessExit(target_action=crear, on_exit=[jsb, brazo]))

    acciones = [rsp, gz, crear, reloj, tras_crear]
    if arg("moveit") == "true":
        acciones.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                get_package_share_directory("rl6gdl_planning"), "launch", "planning_e6.launch.py")),
            launch_arguments={"gazebo": "true"}.items()))
    return acciones


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("escenario", default_value="1", description="escenario del contrato (1-8)"),
        DeclareLaunchArgument("variante", default_value="",
                              description='etiqueta de la variante, p. ej. "5 k=2.0" (vacío = la primera)'),
        DeclareLaunchArgument("gui", default_value="false"),
        DeclareLaunchArgument("moveit", default_value="true"),
        OpaqueFunction(function=launch_setup),
    ])
