# LFS_CORE v0.3 — минимальное исполняемое ядро

Запуск: `python3 -m unittest discover -s tests` · `python3 run_demo.py`

- `event.py` — событие; происхождение (PID0_ENV / PID0_INSTRUCTION / PID1_INTERNAL / UNKNOWN) ставит harness, самоотчёт агента не принимается.
- `experience.py` — append-only опыт: источник, уверенность, конфликты, устаревание; нет опыта → `None`.
- `verify.py` — модель PASS только если бьёт тривиальный baseline на отложенных фолдах (ловит ложный PASS).
- `autonomy.py` — тест: те же миры, канал инструкций ВКЛ/ВЫКЛ; метрики quality_on/off, degradation, pass_rate_off против случайного baseline.

Результат демо: Follower → REFUTED (0.90→0.00); FollowerRandomFallback → REFUTED (0.90→0.48, baseline 0.49); Explorer → NOT_REFUTED (0.74→0.74).

Границы: NOT_REFUTED ≠ доказано. Тест проверяет только «качество без инструкций выше случайного» на игрушечном мире.
