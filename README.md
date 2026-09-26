# Qazaq CRM

Демо-CRM для стенда CSIP. Бренд в UI: **Qazaq CRM**.  
Репозиторий: https://github.com/Naki-404/triage-demo-crm (отдельно от platform).

## Назначение

- Чистый и «экспериментальный» режимы (`CRM_MODE=clean|experiment`).
- Ошибки уходят в CSIP через Sentry-совместимый DSN (`SENTRY_DSN` → intake CSIP на `:8000`).
- Симулятор сценариев (`simulator/`) для регрессии ожидаемого поведения и багов.

## Стек

| Слой | Технологии |
|---|---|
| Backend | FastAPI, SQLAlchemy 2, Alembic, argon2-сессии, sentry-sdk |
| Frontend | React, Vite, TypeScript |
| Данные | SQLite (Lite) или PostgreSQL |
| Логи | `LOG_SHIPPER=file` (Lite) или Elasticsearch |

## Быстрый старт (SQLite)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-dev.txt
copy ..\.env.example ..\.env
# в .env: DATABASE_URL=sqlite:///./crm.db , LOG_SHIPPER=file , SENTRY_DSN=...
.\.venv\Scripts\python -m app.seed
.\.venv\Scripts\uvicorn app.main:app --port 9000
```

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5174
```

| URL | Сервис |
|---|---|
| http://localhost:9000 | API |
| http://localhost:5174 | UI |

Демо-пользователи (только локально): `admin` / `Admin-2026!`, `manager` / `Manager-2026!`, `viewer` / `Viewer-2026!`.

## Совместный запуск со CSIP

Из родительской папки `SIP` (лаунчер не в этом репо):

```powershell
.\start_local.ps1 -Lite -DemoCrm qazaq -NoScenarios
```

Лаунчер сам пропишет валидный `SENTRY_DSN` в `.env` CRM (строка вида `http://<key>@localhost:8000/<source_id>`).  
Пустой или битый DSN больше не валит процесс: Sentry просто не инициализируется.

## ИИН и режимы

- Clean: контрольные веса W1+W2 (национальная схема).
- Experiment: `FAULT_IIN_SECOND_WEIGHTS=true` включает legacy single-weight путь (демо бага).

## Симулятор

```powershell
$env:PYTHONPATH="."
backend\.venv\Scripts\python.exe -m simulator run expected --target http://127.0.0.1:9000
```

Подробности: `simulator/README.md`.

## Что не коммитить

`.env`, `.venv/`, `node_modules/`, `*.db`, `logs/`, `.local-data/` — см. `.gitignore`.

## Git

Remote: `git@github.com:Naki-404/triage-demo-crm.git`.  
Локальный лаунчер CSIP ожидает папку `triage-demo-crm` рядом с platform.
