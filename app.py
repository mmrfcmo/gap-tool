import os
import re
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator

app = FastAPI(title="Doctor Approach Growth Gap API", version="1.0.0")

ALLOWED_ORIGINS = [
    "https://doctor-approach-landing.onrender.com",
    "https://doctorapproach.com",
]
extra_origin = os.getenv("FRONTEND_ORIGIN")
if extra_origin:
    ALLOWED_ORIGINS.append(extra_origin.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

class DiagnosisRequest(BaseModel):
    name: str
    practice: str
    email: EmailStr
    phone: str
    website: str
    patient_trend: str = ""

    @field_validator("name", "practice", "phone")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field is required")
        return value

    @field_validator("website")
    @classmethod
    def normalise_website(cls, value: str) -> str:
        value = value.strip().lower()
        if not value:
            raise ValueError("Website is required")
        if not value.startswith(("http://", "https://")):
            value = "https://" + value
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("Invalid website URL")
        if parsed.username or parsed.password:
            raise ValueError("Credentials are not permitted in website URLs")
        return value.rstrip("/")

def is_public_hostname(hostname: str) -> bool:
    try:
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            ip = info[4][0]
            parts = ip.split(".")
            if ":" in ip:
                # Reject IPv6 loopback/private/link-local ranges conservatively.
                if ip == "::1" or ip.lower().startswith(("fc", "fd", "fe80")):
                    return False
            elif len(parts) == 4:
                a, b = int(parts[0]), int(parts[1])
                if a == 10 or a == 127 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168) or a == 0:
                    return False
        return True
    except socket.gaierror:
        return False

def scan_website(url: str) -> dict:
    parsed = urlparse(url)
    if not is_public_hostname(parsed.hostname):
        raise HTTPException(status_code=400, detail="Website could not be reached safely.")

    headers = {"User-Agent": "DoctorApproach-GrowthGap/1.0"}
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=12.0,
            headers=headers,
        ) as client:
            response = client.get(url)
    except Exception as exc:
        return {
            "status": "unavailable",
            "url": url,
            "error": str(exc)[:160],
        }

    if response.status_code >= 400:
        return {
            "status": "error",
            "url": str(response.url),
            "http_status": response.status_code,
        }

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    description = description_tag.get("content", "").strip() if description_tag else ""
    h1s = [x.get_text(" ", strip=True) for x in soup.find_all("h1")]
    text = soup.get_text(" ", strip=True)
    lower = text.lower()

    signals = []
    score = 100

    if not title:
        signals.append("Missing page title")
        score -= 15
    elif len(title) < 20 or len(title) > 65:
        signals.append("Page title may need optimisation")
        score -= 5

    if not description:
        signals.append("Missing meta description")
        score -= 10

    if not h1s:
        signals.append("No H1 heading detected")
        score -= 10
    elif len(h1s) > 1:
        signals.append("Multiple H1 headings detected")
        score -= 3

    if not any(k in lower for k in ("book", "appointment", "contact", "call us", "request")):
        signals.append("No obvious booking/contact call-to-action detected")
        score -= 15

    if not any(k in lower for k in ("review", "testimonial", "case study", "google")):
        signals.append("Limited visible trust/review evidence detected")
        score -= 10

    if len(text.split()) < 250:
        signals.append("Low visible page content")
        score -= 10

    if parsed.scheme != "https":
        signals.append("Website is not using HTTPS")
        score -= 20

    return {
        "status": "success",
        "url": str(response.url),
        "http_status": response.status_code,
        "title": title,
        "description": description,
        "h1_count": len(h1s),
        "word_count": len(text.split()),
        "https": str(response.url).startswith("https://"),
        "website_score": max(0, min(100, score)),
        "signals": signals,
    }

@app.get("/")
def root():
    return {"service": "Doctor Approach Growth Gap API", "status": "ok"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/submit-diagnosis")
def submit_diagnosis(request: DiagnosisRequest):
    website = request.website
    scan = scan_website(website)

    # MVP: return the lead + scan result. Persistent lead storage/email delivery
    # will be added once the API is deployed and tested end-to-end.
    return {
        "success": True,
        "message": "Diagnosis request received.",
        "lead": {
            "name": request.name,
            "practice": request.practice,
            "email": request.email,
            "phone": request.phone,
            "website": website,
            "patient_trend": request.patient_trend,
        },
        "diagnosis": scan,
    }
