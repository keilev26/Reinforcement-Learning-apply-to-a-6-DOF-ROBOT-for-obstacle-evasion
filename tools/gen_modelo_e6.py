#!/usr/bin/env python3
"""Genera el modelo corregido del DOBOT Magician E6: fuente única para PyBullet, MoveIt y Gazebo.

Parte del URDF oficial de Dobot (repositorio DOBOT_6Axis_ROS2_V4, licencia MIT, commit fijado
abajo) y escribe el paquete ROS 2 `ros2_ws/src/rl6gdl_e6_description/` con estas correcciones:

  1. Masas: el CAD oficial calculó las masas con densidad ~1000 kg/m3 (valor por defecto sin
     material) sobre carcasas huecas, y suman 0.94 kg. Se escalan uniformemente hasta los 7.2 kg
     de la ficha técnica. El escalado uniforme conserva los centros de masa y multiplica las
     inercias por el mismo factor. Es una ESTIMACIÓN declarada.
  2. Velocidad articular: 2.0944 rad/s (120 grados/s, ficha oficial) en lugar del marcador 300.
  3. Par: el fabricante no lo publica. Se estima por dinámica inversa (gravedad, velocidad y
     aceleración máximas, con la carga útil de 0.75 kg), por un margen de 2, en lugar del
     marcador 300. Es una ESTIMACIÓN: solo la usan los controladores de simulación.
  4. Mallas visuales reducidas a ~15 000 triángulos por eslabón (las originales suman 368 000).
  5. Mallas de colisión: cada eslabón se rellena (las mallas oficiales son carcasas huecas y
     abiertas) y se descompone en <= 4 piezas convexas con V-HACD; se usa la descomposición solo
     si reduce el exceso sobre la malla real frente a la envolvente única. Cada pieza es un elemento
     <collision> propio: PyBullet usa la envolvente convexa de cada malla, y como cada pieza ya
     es convexa, PyBullet y FCL (MoveIt) ven exactamente la misma geometría.
  6. Raíz en `base_link` apoyada en z = 0 (se elimina la elevación arbitraria de 3 cm del
     `world_joint` oficial) y se añade el marco `tool0` en la cara de la brida.
  7. Se eliminan los bloques de Gazebo Classic (`gravity=false`, `gazebo_ros2_control`).
  8. Matriz de colisiones permitidas calculada sobre esta geometría, para que ambos motores
     excluyan exactamente los mismos pares. Se escribe como YAML (PyBullet) y como SRDF (MoveIt),
     con el grupo `manipulador` de base_link a tool0.

La cinemática (orígenes y ejes de las articulaciones, límites de posición) NO se modifica: el
generador verifica que la cinemática directa coincide con la oficial antes de escribir.

Uso:
    .venv/bin/python tools/gen_modelo_e6.py [--fuente RUTA_AL_REPO_DOBOT]

Dependencias (solo para regenerar; cargar el modelo solo requiere pybullet):
    pip install trimesh scipy rtree scikit-image fast-simplification
"""

import argparse
import contextlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import fast_simplification
import numpy as np
import pybullet as p
import trimesh
import yaml

REPO_DOBOT = "https://github.com/Dobot-Arm/DOBOT_6Axis_ROS2_V4.git"
COMMIT_DOBOT = "ec201c40d5db63185a3593ec9c39f80fe25aa527"  # 2026-09-03

RAIZ = Path(__file__).resolve().parents[1]
PAQUETE = "rl6gdl_e6_description"
DESTINO = RAIZ / "ros2_ws" / "src" / PAQUETE

ESLABONES = ["base_link", "Link1", "Link2", "Link3", "Link4", "Link5", "Link6"]
ARTICULACIONES = [f"joint{i}" for i in range(1, 7)]

# Ficha técnica oficial (dobot-robots.com, Magician E6)
MASA_TOTAL_KG = 7.2
VELOCIDAD_MAX_RAD_S = round(float(np.deg2rad(120.0)), 4)  # 2.0944
CARGA_UTIL_KG = 0.75
ACELERACION_MAX_RAD_S2 = 4.72  # joint_limits.yaml de me6_moveit (oficial)
MARGEN_PAR = 2.0
ESFUERZO_MIN_NM = 1.0          # piso para que ningún controlador de simulación quede sin par

TRIANGULOS_VISUAL = 15000
PASO_VOXEL_M = 0.002       # relleno de las carcasas huecas
VHACD_PROFUNDIDAD = 2      # 2 etapas de corte -> <= 4 piezas convexas por eslabón
VHACD_RESOLUCION = 400000
MEJORA_MIN_MM = 3.0        # la descomposición se usa solo si reduce el exceso al menos esto
MUESTRAS_ACM = 5000
SEMILLA = 0


# --------------------------------------------------------------------------- fuente oficial

def obtener_fuente(ruta: Path | None) -> Path:
    if ruta:
        return ruta
    cache = Path.home() / ".cache" / "rl6gdl" / "DOBOT_6Axis_ROS2_V4"
    if not (cache / ".git").exists():
        cache.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", str(cache)], check=True)
        subprocess.run(["git", "-C", str(cache), "remote", "add", "origin", REPO_DOBOT], check=True)
    subprocess.run(["git", "-C", str(cache), "fetch", "-q", "--depth", "1", "origin", COMMIT_DOBOT],
                   check=True)
    subprocess.run(["git", "-C", str(cache), "checkout", "-q", COMMIT_DOBOT], check=True)
    return cache


def leer_urdf_oficial(fuente: Path) -> ET.Element:
    texto = (fuente / "cra_description" / "urdf" / "me6_robot.xacro").read_text()
    texto = re.sub(r"<ros2_control.*?</ros2_control>|<gazebo.*?</gazebo>", "", texto, flags=re.S)
    return ET.fromstring(texto)


def urdf_oficial_plano(raiz: ET.Element, dir_mallas: Path) -> str:
    """URDF oficial sin tocar, con rutas absolutas, para comparar la cinemática."""
    texto = ET.tostring(raiz, encoding="unicode")
    return texto.replace("file://$(find cra_description)/meshes/me6/", f"{dir_mallas}/")


# --------------------------------------------------------------------------- mallas

@contextlib.contextmanager
def silenciar_stdout():
    """V-HACD imprime su progreso desde C: hay que redirigir el descriptor, no sys.stdout."""
    sys.stdout.flush()
    copia = os.dup(1)
    with open(os.devnull, "w") as nulo:
        os.dup2(nulo.fileno(), 1)
        try:
            yield
        finally:
            os.dup2(copia, 1)
            os.close(copia)


def malla_visual(src: Path, dst: Path) -> int:
    m = trimesh.load(src)
    if len(m.faces) > TRIANGULOS_VISUAL:
        v, f = fast_simplification.simplify(m.vertices, m.faces,
                                            target_reduction=1 - TRIANGULOS_VISUAL / len(m.faces))
        m = trimesh.Trimesh(v, f)
    m.export(dst)
    return len(m.faces)


def piezas_colision(src: Path, tmp: Path) -> list[trimesh.Trimesh]:
    m = trimesh.load(src)
    vox = m.voxelized(PASO_VOXEL_M).fill()
    solido = vox.marching_cubes
    solido.apply_transform(vox.transform)
    v, f = fast_simplification.simplify(solido.vertices, solido.faces, target_reduction=0.9)
    entrada, salida = tmp / f"{src.stem}.obj", tmp / f"{src.stem}_vhacd.obj"
    trimesh.Trimesh(v, f).export(entrada)
    with silenciar_stdout():
        p.vhacd(str(entrada), str(salida), str(tmp / "vhacd.log"), resolution=VHACD_RESOLUCION,
                depth=VHACD_PROFUNDIDAD, concavity=0.0, maxNumVerticesPerCH=64)
    # El OBJ de V-HACD trae una pieza convexa por cada 'o'
    vertices, piezas, caras = [], [], None
    for linea in salida.read_text().splitlines():
        if linea.startswith("o "):
            caras = []
            piezas.append(caras)
        elif linea.startswith("v "):
            vertices.append([float(x) for x in linea.split()[1:4]])
        elif linea.startswith("f "):
            caras.append([int(x.split("/")[0]) - 1 for x in linea.split()[1:4]])
    vertices = np.array(vertices)
    return [trimesh.Trimesh(vertices, np.array(c)).convex_hull for c in piezas if c]


def sobresale_mm(piezas: list[trimesh.Trimesh], original: trimesh.Trimesh) -> float:
    """Percentil 95 de cuánto sobresale la superficie EXTERIOR de colisión respecto de la malla real.

    Las caras de corte entre piezas quedan dentro del cuerpo y no cuentan: se descartan los puntos
    que caen dentro de otra pieza.
    """
    pts = []
    for i, pz in enumerate(piezas):
        muestra = pz.sample(max(500, 4000 // len(piezas)), seed=SEMILLA)
        for j, otra in enumerate(piezas):
            if j != i:
                muestra = muestra[trimesh.proximity.signed_distance(otra, muestra) < -5e-4]
        pts.append(muestra)
    pts = np.vstack(pts)
    return float(np.percentile(trimesh.proximity.closest_point(original, pts)[1], 95) * 1000)


# --------------------------------------------------------------------------- URDF

def escribir_urdf(raiz_oficial: ET.Element, factor_masa: float, colisiones: dict[str, int],
                  z_brida: float, esfuerzo: dict[str, float]) -> str:
    uri = f"package://{PAQUETE}/meshes"
    out = ['<?xml version="1.0"?>',
           "<!-- GENERADO por tools/gen_modelo_e6.py. No editar a mano: regenerar. -->",
           f"<!-- Fuente: {REPO_DOBOT} @ {COMMIT_DOBOT} (MIT). Correcciones: ver README.md -->",
           '<robot name="magician_e6">']
    links = {l.get("name"): l for l in raiz_oficial.findall("link")}
    for nombre in ESLABONES:
        ine = links[nombre].find("inertial")
        o, m, i = ine.find("origin"), float(ine.find("mass").get("value")), ine.find("inertia")
        inercia = " ".join(f'{k}="{float(i.get(k)) * factor_masa:.6e}"'
                           for k in ["ixx", "ixy", "ixz", "iyy", "iyz", "izz"])
        out += [f'  <link name="{nombre}">',
                "    <inertial>",
                f'      <origin xyz="{o.get("xyz")}" rpy="{o.get("rpy")}"/>',
                f'      <mass value="{m * factor_masa:.6f}"/>',
                f"      <inertia {inercia}/>",
                "    </inertial>",
                "    <visual>",
                f'      <geometry><mesh filename="{uri}/visual/{nombre}.stl"/></geometry>',
                '      <material name="gris"><color rgba="0.75 0.75 0.75 1"/></material>',
                "    </visual>"]
        for k in range(colisiones[nombre]):
            out.append(f'    <collision name="{nombre}_{k}"><geometry>'
                       f'<mesh filename="{uri}/collision/{nombre}_{k}.stl"/></geometry></collision>')
        out.append("  </link>")
    joints = {j.get("name"): j for j in raiz_oficial.findall("joint")}
    for nombre in ARTICULACIONES:
        j = joints[nombre]
        o, lim = j.find("origin"), j.find("limit")
        out += [f'  <joint name="{nombre}" type="revolute">',
                f'    <origin xyz="{o.get("xyz")}" rpy="{o.get("rpy")}"/>',
                f'    <parent link="{j.find("parent").get("link")}"/>',
                f'    <child link="{j.find("child").get("link")}"/>',
                f'    <axis xyz="{j.find("axis").get("xyz")}"/>',
                f'    <limit lower="{lim.get("lower")}" upper="{lim.get("upper")}" '
                f'effort="{esfuerzo[nombre]:.1f}" velocity="{VELOCIDAD_MAX_RAD_S}"/>',
                "  </joint>"]
    # tool0 lleva una inercia despreciable: sin <inertial>, PyBullet le asigna 1 kg por defecto
    out += ['  <link name="tool0">',
            '    <inertial><mass value="1e-6"/>'
            '<inertia ixx="1e-9" ixy="0" ixz="0" iyy="1e-9" iyz="0" izz="1e-9"/></inertial>',
            '  </link>',
            '  <joint name="tool0_joint" type="fixed">',
            f'    <origin xyz="0 0 {z_brida:.4f}" rpy="0 0 0"/>',
            '    <parent link="Link6"/>',
            '    <child link="tool0"/>',
            "  </joint>",
            "</robot>", ""]
    return "\n".join(out)


def urdf_resuelto(texto: str, tmp: Path) -> Path:
    ruta = tmp / "resuelto.urdf"
    ruta.write_text(texto.replace(f"package://{PAQUETE}/", f"{DESTINO}/"))
    return ruta


def indices(cuerpo: int) -> tuple[list[int], dict[str, int]]:
    art, links = [], {"base_link": -1}
    for j in range(p.getNumJoints(cuerpo)):
        info = p.getJointInfo(cuerpo, j)
        links[info[12].decode()] = j
        if info[2] == p.JOINT_REVOLUTE:
            art.append(j)
    return art, links


# --------------------------------------------------------------------------- verificaciones

def verificar_cinematica(urdf_oficial: Path, urdf_nuevo: Path, rng) -> float:
    a = p.loadURDF(str(urdf_oficial), useFixedBase=True)
    b = p.loadURDF(str(urdf_nuevo), useFixedBase=True)
    art_a, links_a = indices(a)
    art_b, links_b = indices(b)
    lo = np.array([p.getJointInfo(b, j)[8] for j in art_b])
    hi = np.array([p.getJointInfo(b, j)[9] for j in art_b])
    peor = 0.0
    for _ in range(200):
        q = rng.uniform(lo, hi)
        for ja, jb, v in zip(art_a, art_b, q):
            p.resetJointState(a, ja, v)
            p.resetJointState(b, jb, v)
        # El oficial cuelga base_link de world a 3 cm de altura: se compara respecto de base_link
        base_a = np.array(p.getLinkState(a, links_a["base_link"], computeForwardKinematics=True)[4])
        pa = np.array(p.getLinkState(a, links_a["Link6"], computeForwardKinematics=True)[4])
        pb = np.array(p.getLinkState(b, links_b["Link6"], computeForwardKinematics=True)[4])
        qa = p.getLinkState(a, links_a["Link6"])[5]
        qb = p.getLinkState(b, links_b["Link6"])[5]
        d = p.getDifferenceQuaternion(qa, qb)
        giro = 2 * np.arctan2(np.linalg.norm(d[:3]), abs(d[3]))  # error angular, en rad
        peor = max(peor, np.linalg.norm((pa - base_a) - pb), giro)
    p.removeBody(a)
    p.removeBody(b)
    return peor


def estimar_esfuerzo(urdf: Path, rng) -> dict[str, float]:
    """Par máximo por articulación por dinámica inversa: gravedad + velocidad + aceleración.

    La carga útil se suma a la masa de Link6 (su centro de masa está a 8 mm de la brida). Las
    posturas, velocidades y aceleraciones se muestrean dentro de los límites: velocidad de la ficha
    técnica y aceleración de `joint_limits.yaml` de `me6_moveit` (el fabricante no publica otra).
    """
    cuerpo = p.loadURDF(str(urdf), useFixedBase=True)
    art, links = indices(cuerpo)
    masa6 = p.getDynamicsInfo(cuerpo, links["Link6"])[0]
    p.changeDynamics(cuerpo, links["Link6"], mass=masa6 + CARGA_UTIL_KG)
    p.setGravity(0, 0, -9.81)
    lo = np.array([p.getJointInfo(cuerpo, j)[8] for j in art])
    hi = np.array([p.getJointInfo(cuerpo, j)[9] for j in art])
    peor = np.zeros(6)
    for _ in range(5000):
        q = list(rng.uniform(lo, hi))
        qd = list(rng.uniform(-VELOCIDAD_MAX_RAD_S, VELOCIDAD_MAX_RAD_S, 6))
        qdd = list(rng.choice([-1.0, 1.0], 6) * ACELERACION_MAX_RAD_S2)
        tau = np.array(p.calculateInverseDynamics(cuerpo, q, qd, qdd))
        peor = np.maximum(peor, np.abs(tau))
    p.removeBody(cuerpo)
    p.setGravity(0, 0, 0)
    return {n: max(ESFUERZO_MIN_NM, float(np.ceil(t * MARGEN_PAR * 10) / 10))
            for n, t in zip(ARTICULACIONES, peor)}


def matriz_colisiones(urdf: Path, rng) -> list[dict]:
    """Pares que nunca deben evaluarse: adyacentes y los que están en contacto en toda postura."""
    cuerpo = p.loadURDF(str(urdf), useFixedBase=True, flags=p.URDF_USE_SELF_COLLISION)
    art, links = indices(cuerpo)
    lo = np.array([p.getJointInfo(cuerpo, j)[8] for j in art])
    hi = np.array([p.getJointInfo(cuerpo, j)[9] for j in art])
    nombres = ESLABONES
    adyacentes = {(nombres[k], nombres[k + 1]) for k in range(len(nombres) - 1)}
    contactos = {}
    for k in range(MUESTRAS_ACM):
        q = np.zeros(6) if k == 0 else rng.uniform(lo, hi)
        for j, v in zip(art, q):
            p.resetJointState(cuerpo, j, v)
        p.performCollisionDetection()
        for i1, a in enumerate(nombres):
            for b in nombres[i1 + 1:]:
                if (a, b) in adyacentes:
                    continue
                toca = bool(p.getClosestPoints(cuerpo, cuerpo, 0.0, links[a], links[b]))
                contactos.setdefault((a, b), []).append(toca)
    p.removeBody(cuerpo)
    pares = [{"par": [a, b], "motivo": "adyacentes"} for a, b in sorted(adyacentes)]
    for (a, b), v in sorted(contactos.items()):
        if all(v):
            pares.append({"par": [a, b], "motivo": "en contacto en toda postura"})
    en_reposo = [list(par) for par, v in contactos.items() if v[0]]
    frecuencia = {f"{a}-{b}": round(float(np.mean(v)), 4) for (a, b), v in contactos.items()}
    return pares, en_reposo, frecuencia


def escribir_srdf(pares: list[dict]) -> str:
    """SRDF de MoveIt: grupo, postura de reposo y la MISMA matriz de colisiones que el YAML."""
    out = ['<?xml version="1.0"?>',
           "<!-- GENERADO por tools/gen_modelo_e6.py desde colisiones_permitidas.yaml. No editar. -->",
           '<robot name="magician_e6">',
           '  <group name="manipulador">',
           '    <chain base_link="base_link" tip_link="tool0"/>',
           "  </group>",
           '  <group_state name="reposo" group="manipulador">']
    out += [f'    <joint name="{j}" value="0"/>' for j in ARTICULACIONES]
    out.append("  </group_state>")
    for x in pares:
        a, b = x["par"]
        motivo = "Adjacent" if x["motivo"] == "adyacentes" else "Default"
        out.append(f'  <disable_collisions link1="{a}" link2="{b}" reason="{motivo}"/>')
    out += ["</robot>", ""]
    return "\n".join(out)


# --------------------------------------------------------------------------- principal

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fuente", type=Path, help="clon local de DOBOT_6Axis_ROS2_V4")
    args = ap.parse_args()

    fuente = obtener_fuente(args.fuente)
    dir_mallas = fuente / "cra_description" / "meshes" / "me6"
    oficial = leer_urdf_oficial(fuente)
    rng = np.random.default_rng(SEMILLA)
    p.connect(p.DIRECT)

    masa_oficial = sum(float(l.find("inertial/mass").get("value"))
                       for l in oficial.findall("link") if l.get("name") in ESLABONES)
    factor = MASA_TOTAL_KG / masa_oficial

    for sub in ["urdf", "meshes/visual", "meshes/collision", "config"]:
        shutil.rmtree(DESTINO / sub, ignore_errors=True)
        (DESTINO / sub).mkdir(parents=True)

    informe = {"fuente": {"repositorio": REPO_DOBOT, "commit": COMMIT_DOBOT, "licencia": "MIT"},
               "masa": {"oficial_kg": round(masa_oficial, 4), "factor_escala": round(factor, 4),
                        "total_kg": MASA_TOTAL_KG},
               "eslabones": {}}
    colisiones = {}
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for nombre in ESLABONES:
            src = dir_mallas / f"{nombre}.STL"
            tri = malla_visual(src, DESTINO / "meshes" / "visual" / f"{nombre}.stl")
            original = trimesh.load(src)
            envolvente = [original.convex_hull]
            descompuesta = piezas_colision(src, tmp)
            s_env = sobresale_mm(envolvente, original)
            s_desc = sobresale_mm(descompuesta, original)
            # Más piezas cuestan tiempo de cálculo: solo se usan si reducen el exceso de verdad
            piezas = descompuesta if s_desc <= s_env - MEJORA_MIN_MM else envolvente
            for k, pz in enumerate(piezas):
                pz.export(DESTINO / "meshes" / "collision" / f"{nombre}_{k}.stl")
            colisiones[nombre] = len(piezas)
            informe["eslabones"][nombre] = {
                "triangulos_visual": tri, "triangulos_original": len(original.faces),
                "piezas_colision": len(piezas),
                "sobresale_p95_mm_envolvente_unica": round(s_env, 1),
                "sobresale_p95_mm_descompuesta": round(s_desc, 1)}
            print(f"{nombre:9s} visual {tri:6d} tri · sobresale p95: envolvente {s_env:4.1f} mm, "
                  f"{len(descompuesta)} piezas {s_desc:4.1f} mm -> usa {len(piezas)}")

        # tool0 en la cara de la brida: el punto más alto de Link6 sobre su eje z
        z_brida = float(trimesh.load(dir_mallas / "Link6.STL").bounds[1][2])

        # Primera pasada con par provisional, para poder calcular el par por dinámica inversa
        provisional = {n: 1.0 for n in ARTICULACIONES}
        texto = escribir_urdf(oficial, factor, colisiones, z_brida, provisional)
        esfuerzo = estimar_esfuerzo(urdf_resuelto(texto, tmp), rng)
        texto = escribir_urdf(oficial, factor, colisiones, z_brida, esfuerzo)
        (DESTINO / "urdf" / "magician_e6.urdf").write_text(texto)
        nuevo = urdf_resuelto(texto, tmp)

        ruta_oficial = tmp / "oficial.urdf"
        ruta_oficial.write_text(urdf_oficial_plano(oficial, dir_mallas))
        error = verificar_cinematica(ruta_oficial, nuevo, rng)
        if error > 1e-6:
            raise SystemExit(f"La cinemática difiere de la oficial: {error:.2e} (m o rad)")
        print(f"cinemática idéntica a la oficial (error máx. {error:.1e} m o rad, 200 posturas)")

        pares, en_reposo, frecuencia = matriz_colisiones(nuevo, rng)

    informe.update({"velocidad_max_rad_s": VELOCIDAD_MAX_RAD_S,
                    "esfuerzo_estimado_Nm": esfuerzo,
                    "tool0_z_sobre_Link6_m": round(z_brida, 4),
                    "error_cinematica_vs_oficial_m": float(error),
                    "autocolision_en_reposo": en_reposo,
                    "frecuencia_autocolision": frecuencia})
    acm = {"descripcion": "Pares de eslabones que NO se evalúan en colisión. PyBullet y MoveIt "
                          "deben leer esta misma lista.",
           "muestras": MUESTRAS_ACM, "semilla": SEMILLA, "pares_excluidos": pares}
    (DESTINO / "config" / "colisiones_permitidas.yaml").write_text(
        yaml.safe_dump(acm, allow_unicode=True, sort_keys=False))
    (DESTINO / "config" / "magician_e6.srdf").write_text(escribir_srdf(pares))
    (DESTINO / "config" / "informe_generacion.yaml").write_text(
        yaml.safe_dump(informe, allow_unicode=True, sort_keys=False))
    shutil.copy(fuente / "LICENSE", DESTINO / "LICENSE.dobot")
    print(f"esfuerzo estimado (N·m): {esfuerzo}")
    print(f"pares excluidos: {[x['par'] for x in pares]}")
    print(f"autocolisión en reposo (debe estar vacío): {en_reposo}")
    print(f"escrito en {DESTINO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
