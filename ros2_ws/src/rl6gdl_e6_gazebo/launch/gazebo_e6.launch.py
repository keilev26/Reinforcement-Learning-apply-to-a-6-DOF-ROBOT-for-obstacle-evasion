"""Magician E6 en Gazebo Harmonic con gz_ros2_control y, opcionalmente, MoveIt (paquete 3.8).

El mundo se genera desde el contrato de escenarios con shared_scenarios/contrato.py, la MISMA
expansión que usan PyBullet y MoveIt: celda base + obstáculos de la variante elegida.

Uso:
  ros2 launch rl6gdl_e6_gazebo gazebo_e6.launch.py                       # escenario 1, sin GUI
  ros2 launch rl6gdl_e6_gazebo gazebo_e6.launch.py escenario:=2 gui:=true
  ros2 launch rl6gdl_e6_gazebo gazebo_e6.launch.py escenario:=5 variante:="5 k=2.0"
"""
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
    """shared_scenarios/contrato.py desde la raíz del repositorio (el launch se instala por symlink)."""
    for padre in Path(__file__).resolve().parents:
        if (padre / "shared_scenarios" / "contrato.py").exists():
            sys.path.insert(0, str(padre / "shared_scenarios"))
            import contrato
            return contrato
    raise RuntimeError("no se encuentra shared_scenarios/contrato.py")


def _geometria(o):
    if o["forma"] == "caja":
        return f"<box><size>{' '.join(map(str, o['dims']))}</size></box>"
    if o["forma"] == "cilindro":
        altura, radio = o["dims"]
        return f"<cylinder><radius>{radio}</radius><length>{altura}</length></cylinder>"
    return f"<sphere><radius>{o['dims'][0]}</radius></sphere>"


def _modelo_sdf(o, color):
    x, y, z, r, p, yaw = o["pose"]
    g = _geometria(o)
    return (f"<model name='{o['id']}'><static>true</static>"
            f"<pose>{x} {y} {z} {r} {p} {yaw}</pose><link name='link'>"
            f"<collision name='c'><geometry>{g}</geometry></collision>"
            f"<visual name='v'><geometry>{g}</geometry><material><ambient>{color}</ambient>"
            f"<diffuse>{color}</diffuse></material></visual></link></model>")


def mundo_sdf(C, contrato, escenario: int, variante: str) -> str:
    variantes = contrato.variantes(C, escenario)
    elegida = next((v for v in variantes if v[0] == variante), variantes[0]) if variante else variantes[0]
    modelos = [_modelo_sdf(o, "0.7 0.7 0.7 1") for o in contrato.celda(C)]
    modelos += [_modelo_sdf(o, "0.8 0.3 0.2 1") for o in elegida[1]]
    return f"""<?xml version="1.0"?>
<sdf version="1.9">
  <world name="celda">
    <!-- Generado desde el contrato {C['version']}, variante "{elegida[0]}" -->
    <physics name="1ms" type="ignored"><max_step_size>0.001</max_step_size><real_time_factor>1.0</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <light type="directional" name="sol"><pose>0 0 3 0 0 0</pose><direction>-0.5 0.1 -0.9</direction>
      <diffuse>0.8 0.8 0.8 1</diffuse><cast_shadows>true</cast_shadows></light>
    {''.join(modelos)}
  </world>
</sdf>"""


def launch_setup(context):
    arg = lambda n: context.launch_configurations[n]
    contrato = _contrato()
    C = contrato.cargar()

    # Mundo desde el contrato
    mundo = Path(tempfile.gettempdir()) / f"rl6gdl_e6_escenario_{arg('escenario')}.sdf"
    mundo.write_text(mundo_sdf(C, contrato, int(arg("escenario")), arg("variante")))

    # Robot: xacro con el efector del contrato; mallas con rutas absolutas (como ur_simulation_gz)
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
    # Los controladores se cargan cuando el robot ya existe en Gazebo
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
