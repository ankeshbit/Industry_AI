import subprocess
import time
import json
import base64
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import websocket

from backend.app.database import SessionLocal
from backend.app.models.auth import User, Organisation
from backend.app.services.auth_service import create_access_token, create_refresh_token

SCREENSHOTS_DIR = Path("docs/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

def get_auth_tokens():
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email.like("lead-engineer%")).first()
        if not u:
            u = db.query(User).first()
        token, _ = create_access_token(u.id, u.organisation_id, u.role)
        refresh_token = create_refresh_token(db, u)
        return token, refresh_token
    finally:
        db.close()

class CDPClient:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=20)
        self.msg_id = 0

    def send(self, method, params=None):
        self.msg_id += 1
        payload = {"id": self.msg_id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(payload))
        while True:
            resp = json.loads(self.ws.recv())
            if resp.get("id") == self.msg_id:
                return resp.get("result", {})

    def evaluate(self, expression):
        res = self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        })
        return res.get("result", {}).get("value")

    def capture(self, filename):
        res = self.send("Page.captureScreenshot", {"format": "png"})
        data = base64.b64decode(res["data"])
        out_path = SCREENSHOTS_DIR / filename
        out_path.write_bytes(data)
        print(f"Captured: {out_path} ({len(data)} bytes)")
        return out_path

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass

def run():
    print("Generating auth session...")
    token, refresh_token = get_auth_tokens()

    port = 9255
    temp_dir = f"C:\\temp\\edge_cdp_{int(time.time())}"
    cmd = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "--headless=new",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={temp_dir}",
        "--no-first-run",
        "--disable-gpu",
        "--window-size=1440,900",
        "http://localhost:3000"
    ]
    proc = subprocess.Popen(cmd)
    time.sleep(3)

    try:
        tabs = requests.get(f"http://127.0.0.1:{port}/json/list", timeout=5).json()
        app_tab = next(t for t in tabs if "3000" in t.get("url", ""))
        client = CDPClient(app_tab["webSocketDebuggerUrl"])

        client.send("Page.enable")
        client.send("Runtime.enable")
        client.send("DOM.enable")

        # Inject auth credentials into localStorage
        script = f"""
            localStorage.setItem('access_token', '{token}');
            localStorage.setItem('refresh_token', '{refresh_token}');
            localStorage.setItem('industria_onboarding_dismissed', 'true');
            location.reload();
        """
        client.evaluate(script)
        time.sleep(4)

        # Helper to click sidebar nav items
        def click_nav(name):
            res = client.evaluate(f"""
                (() => {{
                    const btns = Array.from(document.querySelectorAll('aside nav button'));
                    const target = btns.find(b => b.textContent.includes('{name}'));
                    if (target) {{ 
                        target.click(); 
                        return target.textContent.trim().split('\\n')[0]; 
                    }}
                    return 'NOT_FOUND';
                }})()
            """)
            print(f"Clicked nav '{name}': {res}")
            time.sleep(2)

        # 1. Dashboard View
        print("Screen 1: Dashboard")
        click_nav("Dashboard")
        client.capture("01_dashboard.png")

        # 2. Datasets View
        print("Screen 2: Datasets View")
        click_nav("Datasets")
        client.capture("04_datasets_view.png")

        # 3. Pipeline View
        print("Screen 3: Pipeline View")
        click_nav("Pipeline")
        client.capture("05_pipeline_status.png")

        # 4. Predictions View
        print("Screen 4: Predictions View")
        click_nav("Predictions")
        client.capture("06_predictions_analytics.png")

        # 5. Explainability View
        print("Screen 5: Explainability View")
        click_nav("Explainability")
        client.capture("07_explainability_treeshap.png")

        # 6. Reports View
        print("Screen 6: Reports View")
        click_nav("Reports")
        client.capture("08_reports_governance.png")

        # 7. Settings View
        print("Screen 7: Settings View")
        click_nav("Settings")
        client.capture("09_settings_machinery.png")

        # 8. How It Works Modal
        print("Screen 8: How It Works Modal")
        click_nav("Dashboard")
        res = client.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('header button')).find(b => b.textContent.includes('How It Works'));
                if (btn) { btn.click(); return true; }
                return false;
            })()
        """)
        print(f"Clicked How It Works button: {res}")
        time.sleep(1.5)
        client.capture("02_onboarding_howitworks.png")

        # Close How It Works Modal
        client.evaluate("""
            (() => {
                const closeBtn = document.querySelector('.fixed button[title="Close"]') ||
                                 document.querySelector('.fixed button[class*="hover:text-slate-600"]') ||
                                 document.querySelector('.fixed button');
                if (closeBtn) closeBtn.click();
            })()
        """)
        time.sleep(1)

        # 9. CSV Upload Wizard Modal
        print("Screen 9: Upload Wizard")
        res = client.evaluate("""
            (() => {
                const btn = Array.from(document.querySelectorAll('header button')).find(b => b.textContent.includes('Upload Dataset'));
                if (btn) { btn.click(); return true; }
                return false;
            })()
        """)
        print(f"Clicked Upload Dataset button: {res}")
        time.sleep(1.5)
        # Select first machine from picker modal
        client.evaluate("""
            (() => {
                const modalBtns = Array.from(document.querySelectorAll('.fixed button'));
                const machBtn = modalBtns.find(b => b.textContent.includes('CNC') || b.textContent.includes('Milling') || b.textContent.includes('Lathe') || b.textContent.includes('VMC'));
                if (machBtn) { machBtn.click(); return 'FOUND_MACH'; }
                if (modalBtns[1]) { modalBtns[1].click(); return 'FALLBACK_MACH'; }
                return 'NO_BTN';
            })()
        """)
        time.sleep(2)
        client.capture("03_upload_wizard.png")

        # Close Wizard
        client.evaluate("""
            (() => {
                const cancelBtn = Array.from(document.querySelectorAll('.fixed button')).find(b => b.textContent.includes('Cancel') || b.textContent.includes('Close'));
                if (cancelBtn) cancelBtn.click();
            })()
        """)
        time.sleep(1)

        # 10. Mobile Viewport Navigation
        print("Screen 10: Mobile Viewport (375x812)")
        client.send("Emulation.setDeviceMetricsOverride", {
            "width": 375,
            "height": 812,
            "deviceScaleFactor": 2,
            "mobile": True
        })
        time.sleep(1)
        client.evaluate("document.querySelector('button[aria-label=\"Open Navigation\"]')?.click()")
        time.sleep(1.5)
        client.capture("10_mobile_navigation.png")

        client.close()
        print("ALL 10 SCREENSHOTS CAPTURED WITH AUTHENTICATED REAL STATE!")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            pass

if __name__ == "__main__":
    run()
