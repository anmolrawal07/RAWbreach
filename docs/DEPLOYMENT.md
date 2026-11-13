# Deploying RAWbreach

RAWbreach is one Flask service that delivers both the website and its API, so you deploy it once. The recommended host is **Render**, and the project already includes the `render.yaml` Blueprint for it.

> **Why not Vercel?** Vercel is built for static frontends and short-lived serverless functions. RAWbreach is a single always-on Python web server running under gunicorn, which is exactly what a Render Web Service runs. Splitting it across two platforms would add CORS configuration and a second deployment for no benefit. Any other host that can run `gunicorn app:app` also works, for example Railway, Fly.io or a VPS.

---

## 1. Put the code on GitHub

### Option A: VS Code (easiest, no token needed)

1. Open the project folder in VS Code.
2. Go to **Source Control** (`Ctrl/Cmd+Shift+G`) → **Initialize Repository**. Skip this if the folder is already a git repository.
3. Commit all files.
4. Click **Publish Branch**, sign in to GitHub in the browser, and choose a public or private repo.

### Option B: Command line

```bash
git init -b main
git add -A
git commit -m "RAWbreach"
# Create an empty repo at https://github.com/new (leave every box unticked), then:
git remote add origin https://github.com/YOUR-USERNAME/rawbreach.git
git push -u origin main
```

When git asks for a password, paste a GitHub **personal access token** (GitHub → Settings → Developer settings → Personal access tokens), not your GitHub password.

---

## 2. Deploy on Render

1. Sign in at [render.com](https://render.com) with **Sign in with GitHub**.
2. Click **New → Blueprint** and select your repository.
3. Render reads `render.yaml`:
   ```yaml
   buildCommand: pip install -r requirements.txt
   startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 30
   envVars:
     - key: PYTHON_VERSION
       value: 3.12.7
   ```
4. Click **Apply**. After the build finishes, you get a URL like `https://rawbreach.onrender.com`.
5. **Optional, for better breach coverage:** go to your service → **Environment** → **Add Environment Variable**, add `HIBP_API_KEY` with your key, then save. Render redeploys automatically.

**Updates:** every push to the connected branch triggers a new deploy.

**Checking it works:**
- `https://<your-app>.onrender.com/` should show the site.
- `https://<your-app>.onrender.com/api/email?email=test` should return `{"error":"Please enter a valid email address."}` with HTTP 400. That response means the backend is running.

---

## Connect rawbreach.com

`rawbreach.com` was **unregistered** when this project was packaged. Register it before someone else does.

1. **Buy the domain** at a registrar such as Cloudflare Registrar, Porkbun or Namecheap. Expect roughly $10–15 a year for a `.com`.
2. **Add it in Render:** your service → **Settings → Custom Domains → Add Custom Domain**.
   - Add `rawbreach.com`.
   - Add `www.rawbreach.com`.
3. **Create the DNS records Render shows you** in your registrar's DNS settings. They're typically:

   | Type | Name / Host | Value |
   |---|---|---|
   | `A` | `@` (the root domain) | *the IP address Render displays* |
   | `CNAME` | `www` | `<your-app>.onrender.com` |

   Use the exact values from the Render dashboard, because they can change.
4. **If your DNS is on Cloudflare,** set both records to **DNS only** (grey cloud) until Render shows the domain as verified and the certificate as issued. You can turn on the proxy (orange cloud) afterwards if you want it.
5. **Wait for verification.** It usually takes minutes, occasionally a few hours. Render then issues a free HTTPS certificate automatically, and **https://rawbreach.com** goes live.
6. **Optional:** in Render, choose whether `www` redirects to the root domain or the other way round.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Browser shows **403** at `127.0.0.1:5000` | macOS AirPlay Receiver uses port 5000. Use `http://127.0.0.1:5001`, which is the app's default. |
| `ModuleNotFoundError: No module named 'flask'` | Dependencies aren't installed in the active environment. Activate `.venv` and run `pip install -r requirements.txt`. |
| "Too many checks right now" | The free XposedOrNot limit has been reached. Wait, or set `HIBP_API_KEY`. |
| "HIBP rejected the API key" | `HIBP_API_KEY` is wrong or expired. Check it in Render → Environment. |
| First load takes 30–50 seconds | The Render free plan sleeps when idle. Upgrade the plan to keep it always on. |
| Custom domain stuck on "Verifying" | The DNS records don't match yet, or Cloudflare proxy is on. Re-check the values and use **DNS only**. |
| PDF button shows "Couldn't load the PDF generator" | The browser couldn't reach `cdnjs.cloudflare.com`, often because of an ad blocker or offline mode. |
