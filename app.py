import os
import csv
import re
from datetime import datetime
from flask import Flask, redirect, url_for, session, render_template, request, jsonify
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH, override=True)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-neon-key-2026")

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
IS_GOOGLE_CONFIGURED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
                            and "apps.googleusercontent.com" in GOOGLE_CLIENT_ID)

oauth = OAuth(app)
if IS_GOOGLE_CONFIGURED:
    google = oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"}
    )
else:
    google = None

DATABASE = {}   # in-memory session tracking

# ── CSV ───────────────────────────────────────────────────────────────────────
CSV_FILE = os.path.join(os.path.dirname(__file__), "collected_data.csv")
CSV_FIELDS = [
    "timestamp",
    # Google identity
    "google_id", "name", "email", "auth_type",
    # Contact
    "phone",
    # Network (server-side)
    "ip_address", "user_agent",
    # Device / browser (parsed from UA)
    "browser", "browser_version", "os", "device_type",
    # Browser environment (from JS on page load)
    "screen_width", "screen_height",
    "viewport_width", "viewport_height",
    "color_depth", "pixel_ratio",
    "timezone", "language", "languages",
    "platform", "cpu_cores", "device_memory_gb", "touch_points",
    "connection_type", "connection_downlink",
    "cookies_enabled", "do_not_track", "online",
    # Page context
    "referrer", "page_url", "page_title",
    # Engagement
    "visit_duration_sec",
]

def parse_ua(ua: str) -> dict:
    ua_l = ua.lower()
    # Browser
    if "edg/" in ua_l or "edge/" in ua_l:        br = "Edge"
    elif "opr/" in ua_l or "opera" in ua_l:       br = "Opera"
    elif "chrome/" in ua_l:                        br = "Chrome"
    elif "firefox/" in ua_l:                       br = "Firefox"
    elif "safari/" in ua_l:                        br = "Safari"
    else:                                          br = "Other"
    # Version
    patterns = {"Chrome": r"chrome/([\d.]+)", "Firefox": r"firefox/([\d.]+)",
                "Safari": r"version/([\d.]+)", "Edge": r"edg[e]?/([\d.]+)",
                "Opera": r"(?:opr|opera)/([\d.]+)"}
    pat = patterns.get(br, "")
    m = re.search(pat, ua_l) if pat else None
    ver = m.group(1) if m else ""
    # OS
    if "windows" in ua_l:                         os_n = "Windows"
    elif "android" in ua_l:                        os_n = "Android"
    elif "iphone" in ua_l or "ipad" in ua_l:      os_n = "iOS"
    elif "mac os" in ua_l:                         os_n = "macOS"
    elif "linux" in ua_l:                          os_n = "Linux"
    else:                                          os_n = "Unknown"
    # Device
    if any(x in ua_l for x in ["mobile", "android", "iphone"]):  dev = "Mobile"
    elif "ipad" in ua_l or "tablet" in ua_l:                      dev = "Tablet"
    else:                                                           dev = "Desktop"
    return {"browser": br, "browser_version": ver, "os": os_n, "device_type": dev}

def save_to_csv(record: dict):
    exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({k: record.get(k, "") for k in CSV_FIELDS})
    try:
        email = str(record.get('email', '-')).encode('ascii', errors='replace').decode('ascii')
        phone = str(record.get('phone', '-')).encode('ascii', errors='replace').decode('ascii')
        ip = str(record.get('ip_address', '-')).encode('ascii', errors='replace').decode('ascii')
        print(f"[CSV] [+] {email} | {phone} | {ip} | {record.get('browser','?')} / {record.get('os','?')}")
    except Exception:
        pass
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    user    = session.get("user")
    user_db = DATABASE.get(user["sub"], {}) if user else {}
    return render_template("index.html", user=user, user_db=user_db,
                           is_google_configured=IS_GOOGLE_CONFIGURED)

@app.route("/auth/google")
def google_login():
    if not IS_GOOGLE_CONFIGURED:
        return jsonify({"status": "error", "message": "Google credentials not set in .env"}), 400
    return google.authorize_redirect(url_for("google_callback", _external=True))

@app.route("/auth/callback")
def google_callback():
    if not IS_GOOGLE_CONFIGURED:
        return redirect(url_for("index"))
    try:
        token    = google.authorize_access_token()
        userinfo = token.get("userinfo")
        if userinfo:
            sub = userinfo["sub"]
            session["user"] = {
                "sub":       sub,
                "name":      userinfo.get("name", ""),
                "email":     userinfo.get("email", ""),
                "picture":   userinfo.get("picture", ""),
                "locale":    userinfo.get("locale", "en"),
                "auth_type": "Google OAuth 2.0"
            }
            DATABASE.setdefault(sub, {"phone": None})
    except Exception as e:
        session["oauth_error"] = str(e)
    return redirect(url_for("index"))

# ── Sandbox login ─────────────────────────────────────────────────────────────
@app.route("/api/test-oauth-login", methods=["POST"])
def test_oauth_login():
    data    = request.get_json() or {}
    sub     = data.get("sub", "sandbox_" + datetime.now().strftime("%f"))
    payload = {
        "sub":       sub,
        "name":      data.get("name", "Test User"),
        "email":     data.get("email", "test@gmail.com"),
        "picture":   data.get("picture", ""),
        "locale":    "en_US",
        "auth_type": "Simulated Google OAuth 2.0"
    }
    session["user"] = payload
    DATABASE.setdefault(sub, {"phone": None})
    return jsonify({"status": "success", "user": payload, "user_db": DATABASE[sub]})

# ── Browser fingerprint – called by JS silently on page load ──────────────────
@app.route("/api/fingerprint", methods=["POST"])
def fingerprint():
    js  = request.get_json() or {}
    ua  = request.headers.get("User-Agent", "")
    ip  = request.headers.get("X-Forwarded-For",
          request.remote_addr or "").split(",")[0].strip()
    click_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    fp = {
        "ip_address":          ip,
        "user_agent":          ua,
        **parse_ua(ua),
        "screen_width":        js.get("sw", ""),
        "screen_height":       js.get("sh", ""),
        "viewport_width":      js.get("vw", ""),
        "viewport_height":     js.get("vh", ""),
        "color_depth":         js.get("cd", ""),
        "pixel_ratio":         js.get("pr", ""),
        "timezone":            js.get("tz", ""),
        "language":            js.get("lang", ""),
        "languages":           js.get("langs", ""),
        "platform":            js.get("plat", ""),
        "cpu_cores":           js.get("cpu", ""),
        "device_memory_gb":    js.get("mem", ""),
        "touch_points":        js.get("touch", ""),
        "connection_type":     js.get("connType", ""),
        "connection_downlink": js.get("connDl", ""),
        "cookies_enabled":     js.get("cookies", ""),
        "do_not_track":        js.get("dnt", ""),
        "online":              js.get("online", ""),
        "referrer":            js.get("ref", ""),
        "page_url":            js.get("url", ""),
        "page_title":          js.get("title", ""),
    }
    session["fingerprint"] = fp
    session["click_timestamp"] = click_time

    # Record every URL click / visit immediately in CSV
    visit_record = {
        "timestamp":          click_time,
        "google_id":          "-",
        "name":               "-",
        "email":              "-",
        "auth_type":          "URL Clicked",
        "phone":              "-",
        "visit_duration_sec": "0",
        **fp,
    }
    try:
        save_to_csv(visit_record)
    except Exception as e:
        print(f"[WARN] visit log failed: {e}")

    return jsonify({"status": "ok", "click_time": click_time})

# ── Save phone → write full enriched row to CSV ───────────────────────────────
@app.route("/api/save-phone", methods=["POST"])
def save_phone():
    user = session.get("user")
    if not user:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    data         = request.get_json() or {}
    phone        = data.get("phone", "").strip()
    country_code = data.get("country_code", "+1").strip()
    duration     = data.get("duration_sec", "")

    if not phone or len(phone) < 6:
        return jsonify({"status": "error", "message": "Invalid phone number"}), 400

    full_phone = f"{country_code} {phone}"
    sub        = user["sub"]
    DATABASE.setdefault(sub, {})
    DATABASE[sub]["phone"] = full_phone

    fp         = session.get("fingerprint", {})
    ua         = request.headers.get("User-Agent", "")
    ip         = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    ua_info    = parse_ua(ua)

    record = {
        "timestamp":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "google_id":          user.get("sub", ""),
        "name":               user.get("name", ""),
        "email":              user.get("email", ""),
        "auth_type":          user.get("auth_type", ""),
        "phone":              full_phone,
        "ip_address":         fp.get("ip_address") or ip,
        "user_agent":         fp.get("user_agent") or ua,
        "browser":            fp.get("browser") or ua_info.get("browser", ""),
        "browser_version":    fp.get("browser_version") or ua_info.get("browser_version", ""),
        "os":                 fp.get("os") or ua_info.get("os", ""),
        "device_type":        fp.get("device_type") or ua_info.get("device_type", ""),
        "visit_duration_sec": duration,
        **fp,
    }
    save_to_csv(record)

    return jsonify({"status": "success", "phone": full_phone, "message": "Saved"})

@app.route("/api/session-user")
def session_user():
    user = session.get("user")
    if not user:
        return jsonify({"user": None, "user_db": None})
    return jsonify({"user": user, "user_db": DATABASE.get(user["sub"], {})})

@app.route("/auth/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ── Data viewer ───────────────────────────────────────────────────────────────
@app.route("/data/view")
def view_data():
    rows = []
    if os.path.isfile(CSV_FILE):
        with open(CSV_FILE, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

    total = len(rows)
    clicks_count = sum(1 for r in rows if r.get("auth_type") == "URL Clicked")
    claims_count = sum(1 for r in rows if r.get("auth_type") != "URL Clicked" and r.get("phone") and r.get("phone") != "—")
    mobile_count = sum(1 for r in rows if "mobile" in r.get("device_type", "").lower())
    desktop_count = sum(1 for r in rows if "desktop" in r.get("device_type", "").lower())

    # Build priority columns first: timestamp, auth_type, name, email, phone, then rest
    PRIORITY = ["timestamp", "auth_type", "name", "email", "phone", "device_type", "browser", "os", "ip_address"]
    OTHER_COLS = [c for c in CSV_FIELDS if c not in PRIORITY]
    DISPLAY_COLS = PRIORITY + OTHER_COLS

    th = "".join(
        f"<th class='col-ts'>{c}</th>" if c == "timestamp"
        else f"<th>{c}</th>"
        for c in DISPLAY_COLS
    )

    def render_cell(c, val):
        if c == "timestamp":
            return f"<td class='col-ts'><span class='ts-val'>🕐 {val}</span></td>"
        if c == "auth_type":
            if val == "URL Clicked":
                return "<td><span class='badge-click'>🔗 URL Clicked</span></td>"
            else:
                return "<td><span class='badge-claim'>✓ " + (val or "Claimed") + "</span></td>"
        return f"<td>{val}</td>"

    trs = "".join(
        "<tr>" + "".join(render_cell(c, r.get(c, '')) for c in DISPLAY_COLS) + "</tr>"
        for r in rows
    ) or "<tr><td colspan='99' style='color:#777;text-align:center;padding:24px'>No records yet.</td></tr>"

    return f"""<!DOCTYPE html><html><head><meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>Collected Data Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Nunito:wght@700;900&display=swap" rel="stylesheet">
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#080714;color:#e2e8f0;font-family:'Inter',sans-serif;padding:clamp(16px,3vw,32px);min-height:100vh}}
  .top-bar{{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;margin-bottom:24px}}
  h2{{font-family:'Nunito',sans-serif;font-size:clamp(20px,4vw,28px);font-weight:900;color:#f0e6ff;display:flex;align-items:center;gap:10px}}
  h2 span{{background:linear-gradient(135deg,#a855f7,#38bdf8);-webkit-background-clip:text;background-clip:text;color:transparent}}
  .sub{{color:#64748b;font-size:12px;margin-top:4px;word-break:break-all}}
  .btn-back{{display:inline-flex;align-items:center;gap:6px;background:rgba(168,85,247,.15);color:#c084fc;border:1px solid rgba(168,85,247,.3);padding:9px 18px;border-radius:12px;text-decoration:none;font-weight:700;font-size:13px;transition:all .2s}}
  .btn-back:hover{{background:rgba(168,85,247,.28);color:#fff}}
  
  /* Stat cards */
  .stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-bottom:24px}}
  .stat-card{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);padding:14px 18px;border-radius:14px}}
  .stat-label{{font-size:11px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.6px}}
  .stat-val{{font-size:clamp(20px,3.5vw,26px);font-weight:800;color:#f8fafc;margin-top:4px}}
  
  /* Badges */
  .badge-click{{background:rgba(168,85,247,.18);color:#c084fc;border:1px solid rgba(168,85,247,.35);padding:3px 8px;border-radius:6px;font-size:11px;font-weight:700;white-space:nowrap}}
  .badge-claim{{background:rgba(52,211,153,.18);color:#34d399;border:1px solid rgba(52,211,153,.35);padding:3px 8px;border-radius:6px;font-size:11px;font-weight:700;white-space:nowrap}}

  /* Table container */
  .wrap{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:16px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,.4)}}
  .table-scroll{{overflow-x:auto;max-height:70vh;-webkit-overflow-scrolling:touch}}
  table{{border-collapse:collapse;width:100%;font-size:12px;text-align:left}}
  th{{background:#120726;color:#a855f7;padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.1);white-space:nowrap;position:sticky;top:0;z-index:2;font-weight:700;letter-spacing:.5px}}
  td{{padding:10px 14px;border-bottom:1px solid rgba(255,255,255,.05);white-space:nowrap;color:#cbd5e1}}
  tr:nth-child(even){{background:rgba(255,255,255,.015)}}
  tr:hover{{background:rgba(168,85,247,.06)}}
  
  /* Scrollbar */
  .table-scroll::-webkit-scrollbar{{height:8px;width:8px}}
  .table-scroll::-webkit-scrollbar-track{{background:rgba(255,255,255,.02)}}
  .table-scroll::-webkit-scrollbar-thumb{{background:rgba(168,85,247,.3);border-radius:4px}}
  .table-scroll::-webkit-scrollbar-thumb:hover{{background:rgba(168,85,247,.5)}}

  /* Pinned timestamp column */
  th.col-ts{{position:sticky;left:0;z-index:3;background:#0e0722;color:#38bdf8;min-width:175px}}
  td.col-ts{{position:sticky;left:0;z-index:1;background:#080714;border-right:1px solid rgba(56,189,248,.2)}}
  tr:nth-child(even) td.col-ts{{background:#0a0916}}
  tr:hover td.col-ts{{background:#0f0d22}}
  .ts-val{{color:#38bdf8;font-weight:700;font-size:12px;white-space:nowrap;display:flex;align-items:center;gap:5px}}
</style></head><body>

<div class='top-bar'>
  <div>
    <h2>📊 <span>Collected Data</span></h2>
    <p class='sub'>Storage: {CSV_FILE}</p>
  </div>
  <a href='/' class='btn-back'>← Back to App</a>
</div>

<div class='stats-grid'>
  <div class='stat-card'>
    <div class='stat-label'>Total Events</div>
    <div class='stat-val'>{total}</div>
  </div>
  <div class='stat-card'>
    <div class='stat-label'>URL Clicks</div>
    <div class='stat-val' style='color:#a855f7'>{clicks_count}</div>
  </div>
  <div class='stat-card'>
    <div class='stat-label'>Completed Claims</div>
    <div class='stat-val' style='color:#34d399'>{claims_count}</div>
  </div>
  <div class='stat-card'>
    <div class='stat-label'>Mobile Users</div>
    <div class='stat-val' style='color:#38bdf8'>{mobile_count}</div>
  </div>
  <div class='stat-card'>
    <div class='stat-label'>Desktop Users</div>
    <div class='stat-val' style='color:#fde047'>{desktop_count}</div>
  </div>
</div>

<div class='wrap'>
  <div class='table-scroll'>
    <table>
      <thead><tr>{th}</tr></thead>
      <tbody>{trs}</tbody>
    </table>
  </div>
</div>

</body></html>"""

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n[+] App            -> http://127.0.0.1:{port}")
    print(f"[+] Google OAuth   -> {'ENABLED (Live)' if IS_GOOGLE_CONFIGURED else 'DISABLED (Sandbox)'}")
    print(f"[+] Data View      -> http://127.0.0.1:{port}/data/view")
    print(f"[+] CSV            -> {CSV_FILE}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
