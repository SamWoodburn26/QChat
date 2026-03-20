import random
import re
from urllib.parse import quote

import requests
import xml.etree.ElementTree as ET

LIVEWHALE_RSS_BASE = "https://calendar.qu.edu/live/rss/events/"


# keywords for more specific search
SPORT_KEYWORDS = {
    "basketball": ["basketball", "mbb", "wbb"],
    "hockey": ["hockey", "mhoc", "whoc"],
    "soccer": ["soccer"],
    "baseball": ["baseball"],
    "softball": ["softball"],
}

def extract_sport_terms(q: str) -> list[str]:
    ql = q.lower()
    terms = []
    for sport, keys in SPORT_KEYWORDS.items():
        if any(k in ql for k in [sport] + keys):
            terms.extend([sport] + keys)
    # generic “game” but no sport → still try athletics-y words
    if not terms and any(w in ql for w in ["game", "match", "vs", "versus"]):
        terms = ["vs", "versus", "game"]
    return list(dict.fromkeys(terms))  # dedupe preserve order


def parse_date_range_from_query(query: str | None) -> tuple[str, str]:
    """
    Infer start_date and end_date for LiveWhale from the user's question.
    Returns (start_date, end_date) as API-ready strings (e.g. "today", "tomorrow", "+1 week").
    """
    if not query or not query.strip():
        return "today", "today"

    ql = query.lower().strip()

    # tomorrow / next day
    if re.search(r"\btomorrow\b", ql):
        return "tomorrow", "tomorrow"

    # next week (next 7 days from today)
    if re.search(r"\bnext\s+week\b", ql):
        return "today", "+1 week"

    # this week
    if re.search(r"\bthis\s+week\b", ql):
        return "today", "+1 week"

    # next few days / next 3 days / next 5 days
    m = re.search(r"\bnext\s+(\d+)\s+days?\b", ql)
    if m:
        n = min(int(m.group(1)), 31)
        return "today", f"+{n} days"

    # next weekend
    if re.search(r"\b(next\s+)?weekend\b", ql):
        return "this Saturday", "this Sunday"

    # next month
    if re.search(r"\bnext\s+month\b", ql):
        return "today", "+1 month"

    # today / today's
    if re.search(r"\b(tonight|todays?)\b", ql):
        return "today", "today"

    # default: today only
    return "today", "today"


# clean file to avoid errors
_ILLEGAL_XML_CHARS = re.compile(
    r"[\x00-\x08\x0B\x0C\x0E-\x1F]"  # invalid control chars in XML 1.0
)
_AMP_FIX = re.compile(r"&(?!(amp|lt|gt|apos|quot|#\d+|#x[0-9A-Fa-f]+);)")

def _strip_xml_prefixes(xml_text: str) -> str:
    # Tag prefixes: <a:b> -> <a_b>
    xml_text = re.sub(r'(<\/?)([A-Za-z_][\w.\-]*):', r'\1\2_', xml_text)
    # Attribute prefixes: xlink:href= -> xlink_href=
    xml_text = re.sub(r'(\s)([A-Za-z_][\w.\-]*):([A-Za-z_][\w.\-]*)=', r'\1\2_\3=', xml_text)
    return xml_text
def _sanitize_xml(xml_text: str) -> str:
    # 1) remove illegal control characters
    xml_text = _ILLEGAL_XML_CHARS.sub("", xml_text)
    # 2) fix bare ampersands (most common invalid token)
    xml_text = _AMP_FIX.sub("&amp;", xml_text)
    return xml_text

def _build_events_url(start_date: str, end_date: str) -> str:
    """Build LiveWhale RSS URL with start_date and end_date path segments (URL-encoded)."""
    start_enc = quote(start_date, safe="")
    end_enc = quote(end_date, safe="")
    return f"{LIVEWHALE_RSS_BASE}start_date/{start_enc}/end_date/{end_enc}/"


def _fetch_and_parse_feed(url: str) -> list:
    """Fetch RSS from url and return list of item elements. Returns [] on error."""
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        xml_text = _strip_xml_prefixes(r.text)
        xml_text = _sanitize_xml(xml_text)
        root = ET.fromstring(xml_text)
        return list(root.findall(".//item"))
    except Exception as e:
        print("Livewhale fetch error:", e)
        return []


def _items_to_events(items: list, terms: list[str], limit: int) -> list[dict]:
    """Convert item elements to event dicts, optionally filter by sport terms, cap at limit."""
    filtered = []
    for item in items:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if terms:
            hay = (title + " " + link).lower()
            if not any(t in hay for t in terms):
                continue
        filtered.append({"title": title, "link": link, "date": pub_date})
        if len(filtered) >= limit:
            break
    return filtered


# get events
def get_upcoming_events(limit=10, query: str | None = None):
    try:
        start_date, end_date = parse_date_range_from_query(query)
        # Request a wide window so the feed returns more events (server often limits by date range)
        wide_end = "+1 month"
        url = _build_events_url(start_date, wide_end)
        items = _fetch_and_parse_feed(url)

        # If date-filtered feed returns very few, also pull from base feed (no date params)
        # which often returns a larger default "upcoming" list
        if len(items) < 10:
            base_items = _fetch_and_parse_feed(LIVEWHALE_RSS_BASE)
            seen_links = {(item.findtext("link") or "").strip() for item in items}
            for node in base_items:
                link = (node.findtext("link") or "").strip()
                if link and link not in seen_links:
                    items.append(node)
                    seen_links.add(link)

        random.shuffle(items)  # vary which events are shown each time
        terms = extract_sport_terms(query or "")
        return _items_to_events(items, terms, limit)

    except Exception as e:
        print("Livewhale error:", e)
        return []
