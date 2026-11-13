"""
RAWbreach - check if an email address appeared in known data breaches.

Backend (this file) does the email lookup so API keys stay on the server
and browser CORS limits don't apply. Data sources:

  * Have I Been Pwned API v3  - used when HIBP_API_KEY is set (paid key,
    or the free test key 00000000000000000000000000000000 which only works
    for @hibp-integration-tests.com demo addresses).
  * XposedOrNot API           - free, no key, used otherwise.

Password checks happen in the BROWSER using k-anonymity, so passwords
never reach this server at all.
"""

import os
import re
import html
from urllib.parse import quote

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

HIBP_API_KEY = os.environ.get("HIBP_API_KEY", "").strip()
USER_AGENT = "RAWbreach-student-project"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TIMEOUT = 15


def clean_text(text):
    """Strip HTML tags from breach descriptions (prevents XSS in the UI)."""
    if not text:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


# ---------------------------------------------------------------- sources
def lookup_hibp(email):
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(email)}"
    r = requests.get(
        url,
        params={"truncateResponse": "false"},
        headers={"hibp-api-key": HIBP_API_KEY, "user-agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    if r.status_code == 404:
        return []
    if r.status_code == 401:
        raise LookupError("HIBP rejected the API key (check HIBP_API_KEY).")
    if r.status_code == 429:
        raise LookupError("Rate limited by HIBP. Wait a few seconds and try again.")
    r.raise_for_status()

    return [
        {
            "name": b.get("Title") or b.get("Name"),
            "domain": b.get("Domain") or "",
            "date": b.get("BreachDate") or "",
            "records": b.get("PwnCount") or 0,
            "data": b.get("DataClasses") or [],
            "description": clean_text(b.get("Description")),
            "verified": bool(b.get("IsVerified")),
        }
        for b in r.json()
    ]


def lookup_xposedornot(email):
    r = requests.get(
        "https://api.xposedornot.com/v1/breach-analytics",
        params={"email": email},
        headers={"user-agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    if r.status_code == 404:
        return []
    if r.status_code == 429:
        raise LookupError("Too many checks right now (free API limit). Try again in a minute.")
    r.raise_for_status()

    exposed = (r.json() or {}).get("ExposedBreaches") or {}
    breaches = []
    for b in exposed.get("breaches_details") or []:
        data = [d.strip() for d in (b.get("xposed_data") or "").split(";") if d.strip()]
        breaches.append(
            {
                "name": b.get("breach") or "Unknown",
                "domain": b.get("domain") or "",
                "date": str(b.get("xposed_date") or ""),
                "records": int(b.get("xposed_records") or 0),
                "data": data,
                "description": clean_text(b.get("details")),
                "verified": (b.get("verified") or "").lower() == "yes",
            }
        )
    return breaches


# ---------------------------------------------------------------- routes
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/email")
def check_email():
    email = (request.args.get("email") or "").strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        return jsonify(error="Please enter a valid email address."), 400

    source = "Have I Been Pwned" if HIBP_API_KEY else "XposedOrNot"
    try:
        breaches = lookup_hibp(email) if HIBP_API_KEY else lookup_xposedornot(email)
    except LookupError as e:
        return jsonify(error=str(e)), 502
    except requests.RequestException:
        return jsonify(error="Couldn't reach the breach database. Check your internet connection."), 502

    breaches.sort(key=lambda b: b["date"], reverse=True)
    return jsonify(
        email=email,
        source=source,
        found=bool(breaches),
        count=len(breaches),
        total_records=sum(b["records"] for b in breaches),
        breaches=breaches,
    )


if __name__ == "__main__":
    # Port 5000 is taken by AirPlay Receiver on macOS, so default to 5001.
    port = int(os.environ.get("PORT", "5001"))
    print(f"RAWbreach running -> http://127.0.0.1:{port}   (source: {'HIBP' if HIBP_API_KEY else 'XposedOrNot'})")
    app.run(host="127.0.0.1", port=port, debug=False)
