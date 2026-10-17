# Qazaq CRM

CRM отдела продаж учебного центра **Bilim Academy** и тестовый стенд для платформы CSIP
([cybersecurity-incident-platform](https://github.com/Naki-404/cybersecurity-incident-platform)).
Ведёт клиентов, записи на курсы, договоры с рассрочкой и оплаты; ошибки и журнал запросов отдаёт в CSIP.

## Что умеет

| Экран | Содержание |
|---|---|
| Обзор | клиенты и новые за 30 дней, активные договоры, выручка за месяц и сравнение с прошлым, просрочка, выручка за 6 месяцев, популярные курсы, последние оплаты, ближайшие платежи |
| Клиенты | поиск по имени / ИИН, создание клиента (проверка ИИН), экспорт CSV / XLSX |
| Карточка клиента | профиль, налоговый статус (ЭСФ), вкладки «Договоры», «Записи на курсы», «Заметки»; запись на курс, оформление договора одним платежом или в рассрочку 3 / 6 / 12 мес. |
| Договоры | фильтры по статусу и «С просрочкой», доля оплаты; карточка: график платежей, оплаты, курсы, подписание черновика, приём оплаты (Kaspi, карта, наличные), выгрузка в 1С |
| Оплаты | журнал операций с итоговой суммой и фильтрами |
| Курсы | каталог курсов и пакетов |
| Стенд | переключатели режимов `experiment` / `vuln` (только администратор, только вне production) |

Роли: **admin** видит всё; **manager** — только своих клиентов, их договоры и оплаты (чужое отвечает 404);
**viewer** — только чтение.

## Стек

| Слой | Технологии |
|---|---|
| Backend | FastAPI, SQLAlchemy 2, Alembic, argon2, сессии в cookie, sentry-sdk |
| Frontend | React 19, Vite, TypeScript |
| Данные | SQLite (быстрый старт) или PostgreSQL 16 |
| Логи | ECS JSON: файл или Elasticsearch (отправка пакетами в фоне) |

## Быстрый старт (SQLite)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-dev.txt
copy ..\.env.example ..\.env
# в .env: DATABASE_URL=sqlite:///./crm.db , LOG_SHIPPER=file , SENTRY_DSN=<DSN источника в CSIP или пусто>
.\.venv\Scripts\python -m app.seed --demo
.\.venv\Scripts\uvicorn app.main:app --port 9000
```

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5174
```

| URL | Сервис |
|---|---|
| http://localhost:9000 | API (`/health`, `/docs` вне production) |
| http://localhost:5174 | интерфейс |

Пользователи локального стенда: `admin`, менеджеры `manager`, `aliya`, `daniyar`, наблюдатель `viewer`.
Их лабораторные пароли заданы в `backend/app/seed.py` и действуют **только** при `BASE_URL` на localhost; на
стенде, доступном снаружи, сид генерирует пароли сам (или берёт `SEED_<USER>_PASSWORD`).

## Демо-база

`python -m app.seed` создаёт минимум для тестов: трёх пользователей, курсы и 10 клиентов.
`--demo` добавляет год работы учебного центра: ~320 клиентов с корректными ИИН, 3 менеджера, 10 курсов и
3 пакета, ~190 договоров в разных статусах, графики рассрочки, ~470 оплат (есть просрочки и отклонённые
платежи), заметки. Данные детерминированы (фиксированный seed), повторный запуск ничего не дублирует,
`--demo-reset` пересоздаёт демо-часть. Тесты и сборщик обучающих данных CSIP демо-базу не используют.

## Совместный запуск с CSIP

Из родительской папки `SIP` (лаунчер не входит в этот репозиторий):

```powershell
.\start_local.ps1 -NoScenarios          # CSIP + Qazaq CRM с демо-базой
.\start_local.ps1 -WithEs -NoScenarios  # плюс Elasticsearch: журнал запросов CRM → индекс crm-logs → CSIP
.\start_local.ps1 -Stop
```

Лаунчер сам прописывает `SENTRY_DSN` источника CSIP в `.env` CRM.

Что получает CSIP:
- **Sentry**: необработанные исключения и ответы 5xx, плюс бизнес-предупреждения уровня warning/error
  (`observe.emit`: неудачный вход, отказ проверки и т. п.).
- **Elasticsearch** (`LOG_SHIPPER=elasticsearch`): строка ECS на каждый запрос с `log.level`
  (error для 5xx, warning для 4xx, иначе info), `message`, `service.name`, маскированным телом неудачного запроса.
  CSIP со `scan_requests` замечает в этом журнале и атаки, которым приложение ответило 200.

## Режимы стенда

| `CRM_MODE` | Что включается |
|---|---|
| `clean` | обычная работа (по умолчанию, единственный режим в production) |
| `experiment` | переключатели `FAULT_*` — настоящие дефекты и сбои (неверная проверка ИИН, падение экспорта, таймаут налогового сервиса…) |
| `vuln` | переключатели `VULN_*` — учебные уязвимости (SQLi, IDOR, XSS в заметках, path traversal, SSRF…), см. [docs/VULN_FLAGS.md](docs/VULN_FLAGS.md) |

Защита от случайного включения: в production приложение не стартует с режимом не `clean`, со стандартными
секретами или с `STAND_CONTROL_ENABLED=true`; Docker-образ по умолчанию собран как production. Стенд с
`BASE_URL` не на localhost (например, лабораторный `crm.csip.dev`) может работать в режиме `vuln`, но не с
секретами из репозитория.

## Симулятор

```powershell
$env:PYTHONPATH="."
backend\.venv\Scripts\python.exe -m simulator run expected --target http://127.0.0.1:9000
```

Генерирует сценарии ожидаемого поведения, дефектов и атак против **своего** стенда; чужие хосты отклоняет.
Подробности — [simulator/README.md](simulator/README.md).

## Тесты

```powershell
backend\.venv\Scripts\python -m pytest backend/tests simulator/tests -q
backend\.venv\Scripts\python -m ruff check backend simulator
cd frontend; npx tsc -b; npm test; npm run build
```

Каждой учебной уязвимости соответствует пара тестов clean / vuln (`backend/tests/test_vuln_pairs.py`).

## Что не коммитить

`.env`, `.venv/`, `node_modules/`, `*.db`, `logs/`, `exports/` — см. `.gitignore`.

Remote: `git@github.com:Naki-404/triage-demo-crm.git`. Лаунчер CSIP ожидает папку `triage-demo-crm` рядом
с `cybersecurity-incident-platform`.
