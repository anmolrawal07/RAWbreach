# RAWbreach

Breach checker website. Enter an email to see which known data breaches it appears in, or test a password against leaked-password lists. Results include a risk score, the types of data that leaked, a breach timeline, a personalised action checklist and a downloadable PDF report.

---

## Architecture

RAWbreach is a **single Python Flask application**. The same server delivers the website (frontend) and answers the API request it makes (backend). Because both come from the same origin, they communicate in production with no extra setup: the page calls the relative URL `/api/email`, and there is no CORS configuration or second deployment to manage.

```
Browser ──GET /──────────────► Flask (app.py) ──► templates/index.html + static/*
        ──GET /api/email?email=…► Flask ──► XposedOrNot API  (or Have I Been Pwned if HIBP_API_KEY is set)
        ──GET api.pwnedpasswords.com/range/XXXXX (directly from the browser; password never leaves the device)
```

| Area | Files | What it contains |
|---|---|---|
| **Frontend** | `templates/index.html` | The whole UI: layout, CSS (design tokens, animations, responsive rules), and JavaScript (email/password scans, password strength meter, results rendering, PDF report generator). |
| | `static/logo.png`, `static/favicon.png`, `static/apple-touch-icon.png` | Brand logo and browser/home-screen icons |
| | `static/worldmap.svg` | Animated dotted world map in the hero section |
| | `static/logo-watermark.png` | Single-colour logo used as the PDF watermark |
| **Backend** | `app.py` | Flask server: serves the page, the `/api/email` route, email validation, Have I Been Pwned and XposedOrNot integrations, error and rate-limit handling, and HTML sanitising of breach descriptions. |
| **Configuration** | `requirements.txt`, `requirements.lock.txt`, `render.yaml`, `.env.example`, `.gitignore`, `RAWbreach.code-workspace` | Dependencies, exact version lock, Render deployment config, environment variable template, and the VS Code workspace file. |
| **Docs** | `README.md`, `docs/DEPLOYMENT.md` | This file, plus step-by-step deployment and domain setup. |
| **Tools** (optional) | `tools/build_assets.py`, `tools/source/logo-original.png` | Script that produced the coral logo, favicons, watermark and world map from the original logo. Only needed if you want to change the brand images. |

**Not present, by design:** there is no database, no user accounts or authentication, and no build step (no Node.js, `package.json` or bundler). Searches are never stored.

### External services used at runtime

| Service | Used by | Purpose | Key needed |
|---|---|---|---|
| XposedOrNot API | Backend | Email breach lookup (default) | No. Rate-limited (about 25 checks/hour, shared by all visitors) |
| Have I Been Pwned API v3 | Backend | Email breach lookup, when `HIBP_API_KEY` is set | Yes (paid subscription) |
| Pwned Passwords range API | Browser | Password check using k-anonymity | No |
| cdnjs.cloudflare.com (jsPDF 2.5.1) | Browser | Builds the PDF report, loaded on first click | No |
| Google Fonts (Figtree, DM Serif Display, Geist Mono) | Browser | Typography | No |

---

## Run it locally

Requirements: **Python 3.10 or newer**.

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
#    or, for the exact versions this project was built and tested with:
#    pip install -r requirements.lock.txt

# 3. Start the server
python app.py
```

Open **http://127.0.0.1:5001**.

On macOS, port 5000 is taken by AirPlay Receiver, so the app uses 5001 by default. To use another port, run `PORT=8000 python app.py`.

### Optional: try the Have I Been Pwned integration for free

```bash
export HIBP_API_KEY=00000000000000000000000000000000      # Windows PowerShell: $env:HIBP_API_KEY="0000…"
python app.py
```

Then search `account-exists@hibp-integration-tests.com` or `multiple-breaches@hibp-integration-tests.com`. The test key works only for these demo addresses.

### Run it the production way (locally)

```bash
gunicorn app:app --bind 127.0.0.1:5001 --workers 2 --timeout 30
```

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `HIBP_API_KEY` | No | *(empty)* | Have I Been Pwned API key. If it's set, email lookups use HIBP. If it's empty, they use XposedOrNot. |
| `PORT` | No | `5001` | Port used by `python app.py`. Render sets this automatically. |
| `PYTHON_VERSION` | Render only | `3.12.7` | Python version on Render. Already set in `render.yaml`. |

`.env.example` lists these variables. The app reads **real environment variables** and does not auto-load a `.env` file. Locally, use `export` as shown above. In production, set them in the Render dashboard. **Never commit a real `.env` file or API key**; `.gitignore` already excludes `.env`.

---

## Deploy to production

Full instructions: **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**

1. Push this folder to a GitHub repository.
2. On [render.com](https://render.com), go to **New → Blueprint**, select the repo, then click **Apply**. Render reads `render.yaml`, installs `requirements.txt`, and starts gunicorn.
3. Optionally, add `HIBP_API_KEY` under **Environment** in the Render dashboard.
4. Connect **rawbreach.com**. See [docs/DEPLOYMENT.md#connect-rawbreachcom](docs/DEPLOYMENT.md#connect-rawbreachcom).

Every `git push` to the connected branch redeploys the site automatically.

---

## Security and privacy

- **Passwords never leave the browser.** The page SHA-1 hashes the password locally and sends only the first 5 hex characters (k-anonymity). The match is checked in the browser.
- **API keys stay on the server.** The browser only talks to `/api/email`.
- **No XSS from breach data.** Breach descriptions are stripped of HTML on the server and rendered with `textContent` in the browser.
- **No storage.** Searches aren't logged or saved, and PDF reports are generated entirely in the visitor's browser.
- `debug=False` is used, and production runs under gunicorn, not the Flask development server.

## Known limitations

- **No database has every breach.** XposedOrNot (the default) can miss breaches that HIBP knows about. Set `HIBP_API_KEY` for the most complete coverage.
- **Shared rate limit.** The free XposedOrNot limit is shared by every visitor. Heavy traffic will show a "Too many checks" message.
- **Free-plan sleep.** On Render's free plan, the site sleeps after 15 minutes of inactivity. The first visit after that takes about 30–50 seconds.
- **Cosmetic map dots.** The pulsing dots on the world map are decoration. They don't represent live breach locations.
