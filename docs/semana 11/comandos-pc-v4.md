# Comandos en la PC para la tanda v4

```
git clone git@github.com:keilev26/Reinforcement-Learning-apply-to-a-6-DOF-ROBOT-for-obstacle-evasion.git
cd Reinforcement-Learning-apply-to-a-6-DOF-ROBOT-for-obstacle-evasion
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-entrenamiento.txt && pip install torch==2.14.1
.venv/bin/python -m pytest -q
.venv/bin/python -m training.lanzar_barrido training/barridos/v4_ablacion.yaml --simular
nohup systemd-inhibit --what=sleep:idle .venv/bin/python -m training.lanzar_barrido training/barridos/v4_ablacion.yaml > barrido_v4.log 2>&1 &
```

Si el repositorio ya está clonado, en lugar de `git clone`:

```
git pull
```

Ver avance:

```
.venv/bin/python -m training.lanzar_barrido training/barridos/v4_ablacion.yaml --resumen
tail -f barrido_v4.log
```

Evaluar al terminar:

```
for m in training/runs/sac_v4*_s*_2*/mejor.zip; do
  .venv/bin/python -m evaluation.evaluar_politica $m --archivo shared_scenarios/kit_evaluacion.yaml
  .venv/bin/python -m evaluation.evaluar_politica $m --conjunto evaluacion
  .venv/bin/python -m evaluation.evaluar_politica $m --conjunto contrato
done
.venv/bin/python -m tools.resumen_kit training/runs/sac_v4*_s*_2*/mejor_metricas_kit_evaluacion.csv
```
