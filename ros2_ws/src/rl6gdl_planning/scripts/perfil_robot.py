"""Robot activo para los scripts de la línea base: grupo de MoveIt, articulaciones y TCP.

Se elige con la variable de entorno RL6GDL_ROBOT (por defecto 'e6'). 'ur5e' reproduce las
mediciones de la semana 4, hechas con planning_test.launch.py.
"""
import os

PERFILES = {
    "e6": {
        "launch": "planning_e6.launch.py",
        "grupo": "manipulador",
        "articulaciones": [f"joint{i}" for i in range(1, 7)],
        "tcp": "tool0",
    },
    "ur5e": {
        "launch": "planning_test.launch.py",
        "grupo": "ur_manipulator",
        "articulaciones": ["shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
                           "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"],
        "tcp": "tool0",
    },
}

ROBOT = os.environ.get("RL6GDL_ROBOT", "e6")
if ROBOT not in PERFILES:
    raise SystemExit(f"RL6GDL_ROBOT={ROBOT!r} desconocido; opciones: {', '.join(PERFILES)}")
PERFIL = PERFILES[ROBOT]
