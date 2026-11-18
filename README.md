# LFS CORE v0.6 — Goal Necessity & Causal Value

Проверяем не наличие целей, а **нужны ли они**.

## Четыре режима (ablation)

| Режим | Описание |
|-------|----------|
| A_NoGoal | Нет механизма целей |
| B_ExternalGoal | Цели задаются извне |
| C_SelfGoal | Агент сам формирует и держит цели |
| D_SelfGoalRevise | Формирует + пересматривает + отказывается по ценности |

## Pre-registered

- margin = 0.08
- min_pass_rate = 0.80
- STEPS = 60

## Мир

Проекты требуют commitment. Myopic поведение наказывается. Есть junk, probes, смена законов, которая портит часть проектов.

## Запуск

```bash
python3 -m unittest discover -s tests -v
python3 run_demo.py
```
