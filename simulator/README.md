# CRM Simulator (Phase 2)

Safe HTTP simulator against **Qazaq CRM** for the CSIP diploma experiment.

## Safety

- Default whitelist: `localhost`, `127.0.0.1`, `::1`, `crm.csip.dev`, `*.local`
- Other hosts require `--i-own-this-target`
- Rate limit: `--rate-ms` (default 50)

**Do not** point this tool at systems you do not operate.

## Seed bands (train ≠ test)

| Band | Range | Use |
|------|-------|-----|
| train | `1_000_000–1_999_999` | background / train generators |
| test / main | `2_000_000–2_999_999` | evaluation scenarios |
| injection | `2_800_000–2_899_999` | prompt-injection set |

Defined in `simulator/seeds.py`.

## Run

CRM must be up (`CRM_MODE` can start clean; bug/data_infra scenarios switch stand via admin API).

```powershell
cd triage-demo-crm
# use CRM venv (has httpx) or any env with httpx
..\triage-demo-crm\backend\.venv\Scripts\python.exe -m simulator list
..\triage-demo-crm\backend\.venv\Scripts\python.exe -m simulator run expected --target http://127.0.0.1:9000 --journal ..\..\SIP\.local-data\simulator\runs\out.jsonl
..\triage-demo-crm\backend\.venv\Scripts\python.exe -m simulator run all --count 1 --seed 2000001 --with-background --journal runs\demo.jsonl
..\triage-demo-crm\backend\.venv\Scripts\python.exe -m simulator generate contrast_iin_pair --seed 2000100
```

From `triage-demo-crm` with `PYTHONPATH=.`:

```powershell
$env:PYTHONPATH="."
backend\.venv\Scripts\python.exe -m simulator run bug --target http://127.0.0.1:9000
```

## Groups

| Group | Scenarios |
|-------|-----------|
| bug | `valid_iin_rejected`, `name_search_raw_sql` |
| expected | `wrong_check_digit`, `wrong_password` |
| data_infra | `tax_timeout`, `notes_down`, `corrupt_record`, `export_empty_field` |
| security | `brute_force`, `iin_enumeration`, `sql_injection` |
| injection | `prompt_injection_note`, `prompt_injection_header` |
| background | `background_manager` |

## Journal JSONL

Each line:

```json
{"request_id":"...","scenario":"wrong_password","label":"expected","set":"main","seed":2000001,"http_status":401,"detail":null,"time":"...","target":"http://127.0.0.1:9000"}
```

## E2E checklist (sim → Sentry → CSIP)

1. Start stack with Qazaq CRM and CSIP DSN (`start_local.ps1 -DemoCrm qazaq`).
2. Confirm CRM `.env` has `SENTRY_DSN` pointing at CSIP ingest.
3. `python -m simulator run expected,bug --journal runs/e2e.jsonl --seed 2000001`
4. In CSIP UI, incidents appear; `X-Request-ID` / `trace.id` matches journal `request_id`.
5. Optional: `python -c "from research.collect import collect; ..."` in CSIP repo.

## Collect stub

`cybersecurity-incident-platform/research/collect.py` — normalize + mask + match by `request_id`.
