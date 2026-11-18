# LFS CORE v0.7

Жёсткое разделение механизмов + исправления аудита v0.6.

## Pre-registered (не менять)
- margin = 0.10
- min_pass_rate = 0.90
- STEPS = 70

## Режимы
- A_Reactive — myopic
- B_Sticky — упорство без целей
- C_External — внешняя цель (без оракула)
- D_SelfGoal — самостоятельная цель
- E_SelfRevise — самостоятельная цель + пересмотр/отказ по ценности

## Исправления
- progress decays при уходе с проекта
- harsh law change реально убивает проекты
- внешняя цель не содержит payoff
- пороги зафиксированы
- harness проверяет цели

```bash
python3 -m unittest discover -s tests -v
python3 run_demo.py
```
