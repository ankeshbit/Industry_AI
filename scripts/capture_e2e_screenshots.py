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
        self.ws = websocket.create_connection(ws_url, timeout=30)
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
    print("Generating auth session for E2E capture...")
    token, refresh_token = get_auth_tokens()

    port = 9260
    temp_dir = f"C:\\temp\\edge_cdp_{int(time.time())}"
    cmd = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "--headless=new",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={temp_dir}",
        "--no-first-run",
        "--disable-gpu",
        "--window-size=1440,960",
        "http://localhost:3000"
    ]
    proc = subprocess.Popen(cmd)
    time.sleep(3)

    try:
        tabs = requests.get(f"http://127.0.0.1:{port}/json/list", timeout=10).json()
        app_tab = next(t for t in tabs if "3000" in t.get("url", ""))
        client = CDPClient(app_tab["webSocketDebuggerUrl"])

        client.send("Page.enable")
        client.send("Runtime.enable")
        client.send("DOM.enable")

        # Inject auth credentials into localStorage
        script = f"""
            localStorage.setItem('access_token', '{token}');
            localStorage.setItem('refresh_token', '{refresh_token}');
            localStorage.removeItem('industria_onboarding_dismissed');
            location.reload();
        """
        client.evaluate(script)
        time.sleep(4)

        # Helper to click sidebar nav items
        def click_nav(name):
            res = client.evaluate(f"""
                (() => {{
                    const btns = Array.from(document.querySelectorAll('aside button'));
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

        # 1. Overview Page
        print("Screen 1: Overview")
        click_nav("Overview")
        time.sleep(2)
        client.capture("01_overview.png")

        # 2. My Datasets Page
        print("Screen 2: My Datasets")
        click_nav("My Datasets")
        time.sleep(2)
        client.capture("02_my_datasets.png")

        # 3. Dataset Preview Modal
        print("Screen 3: Dataset Preview Modal")
        preview_clicked = client.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const previewBtn = btns.find(b => b.textContent.trim().startsWith('Preview'));
                if (previewBtn) {
                    previewBtn.click();
                    return true;
                }
                return false;
            })()
        """)
        print(f"Preview clicked: {preview_clicked}")
        time.sleep(2)
        client.capture("03_dataset_preview.png")

        # Close Preview Modal
        client.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('.fixed button'));
                const closeBtn = btns.find(b => b.textContent.includes('Close Preview') || b.querySelector('svg'));
                if (closeBtn) closeBtn.click();
            })()
        """)
        time.sleep(1)

        # 4. Analysis Stage 1: Prepare
        print("Screen 4: Analysis Stage 1 (Prepare)")
        click_nav("Analysis")
        time.sleep(2)
        client.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const stage1Btn = btns.find(b => b.textContent.includes('1. Prepare Dataset'));
                if (stage1Btn) stage1Btn.click();
            })()
        """)
        time.sleep(1.5)
        client.capture("04_analysis_prepare.png")

        # 5. Analysis Stage 2: Analyze
        print("Screen 5: Analysis Stage 2 (Analyze)")
        client.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const stage2Btn = btns.find(b => b.textContent.includes('2. Run Analysis'));
                if (stage2Btn) stage2Btn.click();
            })()
        """)
        time.sleep(1.5)
        client.capture("05_analysis_analyze.png")

        # 6. Analysis Stage 3: Results
        print("Screen 6: Analysis Stage 3 (Results)")
        # Ensure results stage is loaded or switch to stage 3
        client.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const stage3Btn = btns.find(b => b.textContent.includes('3. Results & Insights') && !b.disabled);
                if (stage3Btn) {
                    stage3Btn.click();
                } else {
                    const runBtn = btns.find(b => b.textContent.includes('Run Analysis Now'));
                    if (runBtn) runBtn.click();
                }
            })()
        """)
        time.sleep(4)
        client.capture("06_analysis_results.png")

        # 7. Factors Influencing Prediction Modal
        print("Screen 7: Factors Influencing Prediction Modal")
        factor_clicked = client.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const factorBtn = btns.find(b => b.textContent.includes('Inspect Factors'));
                if (factorBtn) {
                    factorBtn.click();
                    return true;
                }
                return false;
            })()
        """)
        print(f"Factors modal clicked: {factor_clicked}")
        time.sleep(2)
        client.capture("07_factors_inspection.png")

        # Close Factors Modal
        client.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('.fixed button'));
                const closeBtn = btns.find(b => b.textContent.includes('Close') || b.querySelector('svg'));
                if (closeBtn) closeBtn.click();
            })()
        """)
        time.sleep(1)

        # 8. Technical Details Expanded View
        print("Screen 8: Technical Details & Model Provenance (Expanded)")
        client.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const techBtn = btns.find(b => b.textContent.includes('Technical Details'));
                if (techBtn) {
                    techBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    techBtn.click();
                }
            })()
        """)
        time.sleep(2)
        client.capture("08_technical_details_expanded.png")

        # 9. Reports Library Page
        print("Screen 9: Reports Library")
        click_nav("Reports")
        time.sleep(2)
        client.capture("09_reports_library.png")

        # 10. Mobile Simplified Navigation
        print("Screen 10: Mobile Viewport (375x812)")
        client.send("Emulation.setDeviceMetricsOverride", {
            "width": 375,
            "height": 812,
            "deviceScaleFactor": 2,
            "mobile": True
        })
        time.sleep(1)
        client.evaluate("""
            (() => {
                const mobileBtn = document.querySelector('button[aria-label="Open Navigation"]');
                if (mobileBtn) mobileBtn.click();
            })()
        """)
        time.sleep(1.5)
        client.capture("10_mobile_simplified_navigation.png")

        client.close()
        print("SUCCESS: ALL 10 REDESIGNED E2E SCREENSHOTS CAPTURED!")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            pass

if __name__ == "__main__":
    run()
