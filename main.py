import asyncio
import os
import secrets
import re
import json
import logging
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fake_useragent import UserAgent
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API-Proxy-Runner")

ua = UserAgent()

# Lifecycle Manager to handle TLSProxy.exe
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Path to the executable in the same directory
    proxy_exe = os.path.join(os.path.dirname(__file__), "TLSProxy.exe")
    proxy_process = None

    if os.path.exists(proxy_exe):
        try:
            logger.info("Starting TLSProxy.exe backend...")
            # Launch the executable in the background
            proxy_process = await asyncio.create_subprocess_exec(
                proxy_exe,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            logger.info(f"TLSProxy.exe started with PID: {proxy_process.pid}")
        except Exception as e:
            logger.error(f"Failed to start TLSProxy.exe: {e}")
    else:
        logger.warning("TLSProxy.exe not found in the current directory. Expecting external process on port 9000.")

    yield  # The API runs while suspended here

    # Shutdown logic
    if proxy_process:
        logger.info("Terminating TLSProxy.exe...")
        try:
            proxy_process.terminate()
            await proxy_process.wait()
            logger.info("TLSProxy.exe terminated successfully.")
        except Exception as e:
            logger.error(f"Error terminating TLSProxy.exe: {e}")

app = FastAPI(title="Auth Orchestrator API", lifespan=lifespan)

class AuthRequest(BaseModel):
    username: str
    password: str
    proxy: Optional[str] = None


def format_proxy(raw_proxy: str) -> Optional[str]:
    """Parses standard proxy formats into clean connection strings."""
    if not raw_proxy:
        return None
    match_userpass = re.match(r"^[^:]+:[^:]+:([^:]+:[^_]+(?:_.+)?)$", raw_proxy)
    match_ipport = re.match(r"^([^:]+:[^:]+)", raw_proxy)
    
    if match_userpass and match_ipport:
        return f"http://{match_userpass.group(1)}@{match_ipport.group(1)}"
    if not raw_proxy.startswith("http"):
        return f"http://{raw_proxy}"
    return raw_proxy


async def make_request_with_retry(session: aiohttp.ClientSession, url: str, method: str, data: dict, headers: dict, proxy: Optional[str]):
    """Routes requests to the local TLSProxy binary forwarding pool."""
    while True:
        try:
            if method == "POST":
                async with session.post(url, data=data, headers=headers, proxy=proxy, timeout=120) as resp:
                    if resp.status in [500, 403, 406]:
                        await asyncio.sleep(1)
                        continue
                    return resp.status, await resp.text()
            else:
                async with session.get(url, headers=headers, proxy=proxy, timeout=120) as resp:
                    if resp.status in [500, 403, 406]:
                        await asyncio.sleep(1)
                        continue
                    return resp.status, await resp.text()
        except Exception:
            await asyncio.sleep(1)
            continue


@app.post("/auth")
async def authenticate(payload: AuthRequest):
    formatted_proxy = format_proxy(payload.proxy) if payload.proxy else ""
    device_id = secrets.token_hex(8).lower()
    user_agent = ua.random

    # Default TLS Fingerprint context map targeting the loopback listener
    tls_config = {
        "x-tp-h1order": "sec-ch-ua,sec-ch-ua-mobile,sec-ch-ua-platform,upgrade-insecure-requests,user-agent,accept,sec-fetch-site,sec-fetch-mode,sec-fetch-user,sec-fetch-dest,accept-encoding,accept-language",
        "x-tp-h2order": "auto",
        "x-tp-method": "POST",
        "x-tp-h2settings": json.dumps({"mode": "auto"}),
        "x-tp-chid": "HelloIOS_16",
        "x-tp-proxy": formatted_proxy,
        "Host": "api.example.com",
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate, br"
    }

    # Pipeline Step 1: Initial Handshake/Auth
    auth_headers = tls_config.copy()
    auth_headers["x-tp-url"] = "https://api.example.com/v2/auth/login.json"
    auth_headers["Content-Type"] = "application/x-www-form-urlencoded"

    body_data = {
        "username": payload.username,
        "password": payload.password,
        "deviceId": device_id
    }

    async with aiohttp.ClientSession() as session:
        # Request passes directly into the managed binary listener on 9000
        status, source = await make_request_with_retry(
            session, "http://127.0.0.1:9000", "POST", body_data, auth_headers, formatted_proxy
        )

        if "invalid" in source.lower():
            raise HTTPException(status_code=401, detail="Authentication Failure")
        
        # Pipeline Step 2: Session Extraction
        status_headers = tls_config.copy()
        status_headers["x-tp-method"] = "GET"
        status_headers["x-tp-url"] = "https://api.example.com/v3/user/status.json"

        status_code, status_source = await make_request_with_retry(
            session, "http://127.0.0.1:9000", "GET", {}, status_headers, formatted_proxy
        )

        return {
            "status": "Session Processed",
            "raw_payload_length": len(status_source)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
