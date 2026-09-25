# Demo CRM

Small CRM used to demonstrate the AI incident triage platform. It contains a deliberate bug in
`validators.py`: valid IINs whose check digit needs the second weight set are rejected.

    pip install -r requirements.txt
    SENTRY_DSN=<DSN from the platform> uvicorn main:app --port 9000
