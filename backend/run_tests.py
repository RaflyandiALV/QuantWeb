import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(name, method, url, json_data=None):
    try:
        t0 = time.time()
        if method == "GET":
            res = requests.get(url, timeout=60)
        else:
            res = requests.post(url, json=json_data, timeout=60)
        t1 = time.time()
        print(f"[{name}] HTTP {res.status_code} ({t1-t0:.2f}s)")
        print(f"    --> {dict(list(res.json().items())[:3]) if res.status_code == 200 else res.text[:200]}")
    except Exception as e:
        print(f"[{name}] FAILED: {e}")

print("=== STARTING FULL SYSTEM VERIFICATION ===")
print("Testing Phase 1 & 2: Scanner (Caching, Concurrency, Math Fixes)")
test_endpoint("Scanner BIG_CAP", "POST", f"{BASE_URL}/api/scan-market", {"sector": "BIG_CAP"})

print("\nTesting Phase 3 & 4: AI & Microstructure")
test_endpoint("AI Status", "GET", f"{BASE_URL}/api/ai/status")
test_endpoint("AI Decision (BTC-USDT)", "POST", f"{BASE_URL}/api/ai-decision/BTC-USDT")
test_endpoint("Validation Report", "GET", f"{BASE_URL}/api/validation/report")
