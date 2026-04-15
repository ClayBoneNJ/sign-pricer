"""Harbor Sales live pricing sync utilities (no external dependencies)."""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Dict, List, Tuple


LOGIN_URL = "https://harborsales.net/login.aspx?ReturnUrl=%2fHome.aspx"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
DEFAULT_PRICE_REGEX = r"\$?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
FREQUENTS_URL = "https://harborsales.net/Frequents.aspx"


@dataclass
class MappingItem:
    category: str
    key: str
    url: str
    field_index: int
    regex: str
    divide_by: float


@dataclass
class FrequentItem:
    key: str
    label: str
    product_type: str
    code: str
    price: float


def _extract_hidden(html: str, name: str) -> str:
    match = re.search(
        rf"name=['\"]{re.escape(name)}['\"][^>]*value=['\"]([^'\"]*)",
        html,
        flags=re.IGNORECASE,
    )
    return match.group(1) if match else ""


def _new_opener() -> urllib.request.OpenerDirector:
    cookie_jar = CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def harbor_login(username: str, password: str) -> urllib.request.OpenerDirector:
    opener = _new_opener()
    initial_req = urllib.request.Request(LOGIN_URL, headers={"User-Agent": DEFAULT_USER_AGENT})
    login_html = opener.open(initial_req, timeout=30).read().decode("utf-8", "ignore")

    payload = {
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": _extract_hidden(login_html, "__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": _extract_hidden(login_html, "__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": _extract_hidden(login_html, "__EVENTVALIDATION"),
        "dnn$ctr$Login$Login_DNN$txtUsername": username,
        "dnn$ctr$Login$Login_DNN$txtPassword": password,
        "dnn$ctr$Login$Login_DNN$chkCookie": "on",
        "dnn$ctr$Login$Login_DNN$cmdLogin": "Log In",
    }
    post_data = urllib.parse.urlencode(payload).encode("utf-8")
    login_req = urllib.request.Request(
        LOGIN_URL,
        data=post_data,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    response = opener.open(login_req, timeout=30)
    body = response.read().decode("utf-8", "ignore")
    if "User Log In" in body and "Log Off" not in body and "Logout" not in body:
        raise RuntimeError("Harbor login failed. Verify credentials.")
    return opener


def extract_price(text: str, pattern: str) -> float:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError("No price matched.")
    raw = match.group(1 if match.lastindex else 0)
    cleaned = raw.replace("$", "").replace(",", "").strip()
    return float(cleaned)


def fetch_price(opener: urllib.request.OpenerDirector, url: str, regex: str) -> float:
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    html = opener.open(req, timeout=30).read().decode("utf-8", "ignore")
    return extract_price(html, regex or DEFAULT_PRICE_REGEX)


def fetch_harbor_frequents(opener: urllib.request.OpenerDirector) -> List[FrequentItem]:
    req = urllib.request.Request(FREQUENTS_URL, headers={"User-Agent": DEFAULT_USER_AGENT})
    html = opener.open(req, timeout=30).read().decode("utf-8", "ignore")
    items: List[FrequentItem] = []

    code_matches = list(
        re.finditer(
            r'id="[^"]*_Detail10_(ctl\d+)_hspttProduct_lblProComProductCode"[^>]*>(.*?)<',
            html,
            re.IGNORECASE | re.DOTALL,
        )
    )
    for match in code_matches:
        ctl = match.group(1)
        code = re.sub(r"<[^>]+>", " ", match.group(2)).strip()
        name_m = re.search(
            rf'id="[^"]*_Detail10_{ctl}_hspttProduct_lblProductName"[^>]*>(.*?)<',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        type_m = re.search(
            rf'id="[^"]*_Detail10_{ctl}_hspttProduct_lblProductType"[^>]*>(.*?)<',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        price_m = re.search(
            rf'id="[^"]*_Detail10_{ctl}_lblListPriceWithDiscount"[^>]*>\$?\s*([0-9][0-9,]*(?:\.[0-9]{{2}})?)\s*<',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        if not name_m or not type_m or not price_m:
            continue
        name = re.sub(r"<[^>]+>", " ", name_m.group(1)).strip()
        product_type = re.sub(r"<[^>]+>", " ", type_m.group(1)).strip()
        price = float(price_m.group(1).replace(",", ""))
        key = _slug(f"{code}_{name}")[:64]
        items.append(
            FrequentItem(
                key=key,
                label=name,
                product_type=product_type,
                code=code,
                price=price,
            )
        )
    return items


def _default_field_index_for_category(category: str) -> int:
    category = category.upper()
    if category in {"MATERIAL", "PRINT", "PLOT"}:
        return 3
    if category == "GARMENT":
        return 5
    if category == "LED_MODS":
        return 6
    if category == "LED_RIBBON":
        return 7
    if category == "CONTROLLER":
        return 3
    raise ValueError(f"No default field index for category {category}")


def load_mapping(path: str) -> List[MappingItem]:
    mapping_path = Path(path)
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {path}")
    content = json.loads(mapping_path.read_text(encoding="utf-8"))
    items_raw = content.get("items", [])
    if not isinstance(items_raw, list):
        raise ValueError("Mapping file must contain an 'items' list.")
    items: List[MappingItem] = []
    for raw in items_raw:
        if not isinstance(raw, dict):
            continue
        category = str(raw.get("category", "")).upper().strip()
        key = str(raw.get("key", "")).strip()
        url = str(raw.get("url", "")).strip()
        regex = str(raw.get("regex", DEFAULT_PRICE_REGEX))
        divide_by = float(raw.get("divide_by", 1.0))
        field_index = int(raw["field_index"]) if "field_index" in raw else _default_field_index_for_category(category)
        if category and key and url:
            items.append(
                MappingItem(
                    category=category,
                    key=key,
                    url=url,
                    field_index=field_index,
                    regex=regex,
                    divide_by=divide_by,
                )
            )
    if not items:
        raise ValueError("No valid mapping items found.")
    return items


def _update_prices_lines(lines: List[str], updates: Dict[Tuple[str, str], Tuple[int, float]]) -> List[str]:
    updated_lines: List[str] = []
    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            updated_lines.append(line)
            continue

        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            updated_lines.append(line)
            continue
        category = parts[0].upper()
        key = parts[1]
        update = updates.get((category, key))
        if not update:
            updated_lines.append(line)
            continue

        field_index, value = update
        if field_index >= len(parts):
            updated_lines.append(line)
            continue
        parts[field_index] = f"{value:.2f}"
        updated_lines.append(",".join(parts))
    return updated_lines


def _upsert_frequents(lines: List[str], frequents: List[FrequentItem]) -> List[str]:
    kept: List[str] = []
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("HARBOR_FREQUENT,"):
            continue
        kept.append(raw)

    if kept and kept[-1].strip() != "":
        kept.append("")
    kept.append("# Harbor frequents (auto-generated by sync)")
    for item in sorted(frequents, key=lambda x: x.key):
        label = item.label.replace(",", " ")
        ptype = item.product_type.replace(",", " ")
        code = item.code.replace(",", " ")
        kept.append(
            f"HARBOR_FREQUENT,{item.key},{label},{ptype},{code},{item.price:.2f}"
        )
    return kept


def sync_harbor_to_prices(
    mapping_path: str = "harbor_mapping.json",
    prices_path: str = "prices.txt",
    username: str | None = None,
    password: str | None = None,
) -> Dict[str, Any]:
    username = username or os.getenv("HARBOR_USERNAME")
    password = password or os.getenv("HARBOR_PASSWORD")
    if not username or not password:
        raise RuntimeError("Missing credentials. Set HARBOR_USERNAME and HARBOR_PASSWORD.")

    mappings = load_mapping(mapping_path)
    opener = harbor_login(username, password)

    updates: Dict[Tuple[str, str], Tuple[int, float]] = {}
    errors: List[str] = []
    for item in mappings:
        try:
            raw_price = fetch_price(opener, item.url, item.regex)
            normalized_price = raw_price / item.divide_by if item.divide_by else raw_price
            updates[(item.category, item.key)] = (item.field_index, normalized_price)
        except Exception as exc:  # pylint: disable=broad-except
            errors.append(f"{item.category}/{item.key}: {exc}")

    frequent_items: List[FrequentItem] = []
    try:
        frequent_items = fetch_harbor_frequents(opener)
    except Exception as exc:  # pylint: disable=broad-except
        errors.append(f"HARBOR_FREQUENT: {exc}")

    prices_file = Path(prices_path)
    lines = prices_file.read_text(encoding="utf-8").splitlines()
    updated = _update_prices_lines(lines, updates)
    if frequent_items:
        updated = _upsert_frequents(updated, frequent_items)
    prices_file.write_text("\n".join(updated) + "\n", encoding="utf-8")

    return {
        "updated_count": len(updates),
        "frequents_count": len(frequent_items),
        "error_count": len(errors),
        "errors": errors,
    }
