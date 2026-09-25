# Doctor Approach Growth Gap API

Backend API for the Doctor Approach landing page.

## Endpoints

- GET /health
- POST /api/submit-diagnosis

## Render

Build:
pip install -r requirements.txt

Start:
uvicorn app:app --host 0.0.0.0 --port $PORT

The landing page should POST to:
https://YOUR-RENDER-SERVICE.onrender.com/api/submit-diagnosis

## Current MVP

The API validates the lead submission and performs a lightweight public website scan. It returns the lead payload and diagnostic signals.

Persistent lead storage, email notifications, Google Places enrichment, and the full Growth Gap report generation are deliberately separate follow-on steps.
