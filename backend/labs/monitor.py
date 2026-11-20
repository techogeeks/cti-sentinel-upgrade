"""Monitoring script (Activity 7.2).

Every 10 seconds it prints the WiredTiger cache hit ratio. Periodically it also
browses the awesome-annual-security-reports list and ctidigest.com for report
links that are not yet in the `report_catalog` collection.

It also reads the GCVE Vulnerability-Lookup "recent" Atom feed (https://db.gcve.eu/recent)
and can add vulnerabilities that are not in the `threats` collection yet.

Run:  python -m labs.monitor                 # report every 10 s, scan every 5 min
      python -m labs.monitor --once          # one reading + one scan, then exit
      python -m labs.monitor --ingest        # also save newly found reports
"""
import argparse
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urldefrag, urlparse

from backend.config.connection import banner, ensure_indexes, get_db
from backend.labs.lab72 import cache_snapshot, hit_ratio
from backend.labs.lab71 import build_embedded
from backend.services.classifier import SEVERITY_RANK, suggest

README_URLS = [
    "https://raw.githubusercontent.com/jacobdjwilson/awesome-annual-security-reports/main/README.md",
    "https://raw.githubusercontent.com/jacobdjwilson/awesome-annual-security-reports/master/README.md",
]
CTI_DIGEST_URL = "https://ctidigest.com/"
SKIP_HOSTS = ("github.com", "shields.io", "img.shields.io", "githubusercontent.com", "twitter.com", "x.com", "linkedin.com")
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "cti-sentinel-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


class _Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._text = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.links.append((" ".join("".join(self._text).split()), self._href))
            self._href = None


def _clean(url):
    return urldefrag(url.strip())[0].rstrip("/")


def _record(title, url, origin):
    year = re.search(r"(20\d\d)", title + " " + url)
    return {"title": title or url, "url": _clean(url), "origin": origin, "host": urlparse(url).netloc,
            "year": int(year.group(1)) if year else None}


def fetch_report_links():
    """Return (links, errors). Never raises: a failing site is reported, not fatal."""
    links, errors = [], []
    for url in README_URLS:
        try:
            text = _get(url)
            links += [_record(t, u, "awesome-annual-security-reports") for t, u in LINK_RE.findall(text)]
            break
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    try:
        parser = _Anchors()
        parser.feed(_get(CTI_DIGEST_URL))
        links += [_record(t, h, "ctidigest.com") for t, h in parser.links if h.startswith("http")]
    except Exception as exc:
        errors.append(f"{CTI_DIGEST_URL}: {exc}")

    seen, unique = set(), []
    for item in links:
        host = item["host"].lower()
        if item["url"] in seen or any(host == h or host.endswith("." + h) for h in SKIP_HOSTS):
            continue
        seen.add(item["url"])
        unique.append(item)
    return unique, errors


def find_new_reports(db):
    known = set(db.report_catalog.distinct("url"))
    links, errors = fetch_report_links()
    return [l for l in links if l["url"] not in known], len(links), errors


def ingest(db, reports):
    ensure_indexes(db)
    saved = 0
    for r in reports:
        res = db.report_catalog.update_one({"url": r["url"]}, {"$setOnInsert": {**r, "found_at": time.time()}}, upsert=True)
        saved += 1 if res.upserted_id else 0
    return saved


# --------------------------------------------------------------------------
# GCVE Vulnerability-Lookup feed (https://db.gcve.eu/recent)
# --------------------------------------------------------------------------
# The site publishes an Atom feed of its most recent entries (about 10 per feed).
# Other sources can be added here: pick one in the site's dropdown and copy its feed link.
GCVE_FEEDS = ["https://db.gcve.eu/recent/cvelistv5.atom?date_sort=updated&sort_order=desc"]
GCVE_SOURCE = {"name": "GCVE Vulnerability-Lookup", "website": "https://db.gcve.eu", "type": "Aggregator", "reliability": 85, "tier": "A"}
ATOM = "{http://www.w3.org/2005/Atom}"
XHTML = "{http://www.w3.org/1999/xhtml}"

CRITICAL_WORDS = ["remote code execution", "arbitrary code execution", "unauthenticated remote"]
HIGH_WORDS = ["sql injection", "authentication bypass", "account takeover", "command injection", "privilege escalation",
              "deserialization", "exploit has been", "exploit has been published", "arbitrary file"]
LOW_WORDS = ["denial of service", "information disclosure"]


def estimate_severity(text):
    """The Atom feed carries no CVSS score, so severity is estimated from the wording. Analysts can still reclassify."""
    t = text.lower()
    if any(w in t for w in CRITICAL_WORDS):
        return "Critical"
    if any(w in t for w in HIGH_WORDS):
        return "High"
    if any(w in t for w in LOW_WORDS):
        return "Low"
    return "Medium"


def parse_gcve_feed(xml_text):
    out = []
    for entry in ET.fromstring(xml_text.encode("utf-8")).findall(ATOM + "entry"):
        raw_title = (entry.findtext(ATOM + "title") or "").strip()
        cve = raw_title.split(" ")[0].upper()
        title_part = raw_title.split("\u2014", 1)[1].strip() if "\u2014" in raw_title else ""
        link_el = entry.find(ATOM + "link")
        url = link_el.get("href") if link_el is not None else f"https://db.gcve.eu/vuln/{cve.lower()}"
        affected, description = "", ""
        content = entry.find(ATOM + "content")
        if content is not None and len(content):
            for p in content[0].findall(XHTML + "p"):
                text = " ".join("".join(p.itertext()).split())
                if text.startswith("Affected:"):
                    affected = text[len("Affected:"):].strip()
                elif text:
                    description = (description + " " + text).strip()
        published = entry.findtext(ATOM + "published") or entry.findtext(ATOM + "updated")
        try:
            created = datetime.fromisoformat(published).astimezone(timezone.utc)
        except (TypeError, ValueError):
            created = datetime.now(timezone.utc)
        severity = estimate_severity(title_part + " " + description)
        out.append({"external_id": cve, "title": f"{cve}: {title_part or description[:80]}", "description": description or title_part,
                    "severity": severity, "severity_rank": SEVERITY_RANK[severity], "category": "Vulnerability",
                    "tags": ["vulnerability", "cve", "gcve"], "affected": affected[:300], "reference_url": url,
                    "indicators": [{"type": "cve", "value": cve}, {"type": "url", "value": url}], "created_at": created})
    return out


def find_new_gcve(db):
    """Return (new_threat_documents, errors): entries whose CVE id is not in `threats` yet."""
    known = set(db.threats.distinct("external_id"))
    found, errors = [], []
    for url in GCVE_FEEDS:
        try:
            found += parse_gcve_feed(_get(url))
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    seen, new = set(), []
    for t in found:
        if t["external_id"] not in known and t["external_id"] not in seen:
            seen.add(t["external_id"])
            new.append(t)
    return new, errors


def ingest_gcve(db, threats):
    """Save new vulnerabilities as threats, with an automatic (unreviewed) classification."""
    if not threats:
        return 0
    ensure_indexes(db)
    from pymongo import ReturnDocument
    source = db.sources.find_one_and_update({"name": GCVE_SOURCE["name"]}, {"$setOnInsert": GCVE_SOURCE},
                                            upsert=True, return_document=ReturnDocument.AFTER)
    saved = 0
    for t in threats:
        doc = {**t, "source_id": source["_id"], "actor_id": None}
        s = suggest(doc, source.get("reliability", 50))
        doc["classification"] = {"verdict": s["verdict"], "confidence": s["confidence"], "reviewed": False,
                                 "updated_at": datetime.now(timezone.utc), "history": []}
        res = db.threats.update_one({"external_id": doc["external_id"]}, {"$setOnInsert": doc}, upsert=True)
        saved += 1 if res.upserted_id else 0
    build_embedded(db)  # keep the Lab 7.1 embedded copy in step
    return saved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=10, help="seconds between cache readings")
    ap.add_argument("--scan-every", type=int, default=300, help="seconds between scans for new reports")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--ingest", action="store_true", help="save new reports to report_catalog and new GCVE vulnerabilities to threats")
    args = ap.parse_args()

    db = get_db()
    banner(f"Cache monitor - every {args.interval}s (Ctrl+C to stop)")
    prev, last_scan = cache_snapshot(db), 0.0
    while True:
        now = time.time()
        if now - last_scan >= args.scan_every or args.once:
            new, total, errors = find_new_reports(db)
            print(f"[scan] {total} links found, {len(new)} not in the database yet")
            for r in new[:10]:
                print(f"   + {r['title'][:70]}  {r['url']}")
            if args.ingest and new:
                print(f"[scan] saved {ingest(db, new)} new report(s)")
            for e in errors:
                print(f"[scan] could not read {e}")
            new_t, gerrors = find_new_gcve(db)
            print(f"[gcve] {len(new_t)} vulnerability entries not in the database yet")
            for t in new_t[:10]:
                print(f"   + {t['external_id']} [{t['severity']}] {t['title'][:70]}")
            if args.ingest and new_t:
                print(f"[gcve] saved {ingest_gcve(db, new_t)} new threat(s)")
            for e in gerrors:
                print(f"[gcve] could not read {e}")
            last_scan = now
        if args.once:
            cur = cache_snapshot(db)
            print(f"[cache] cumulative hit ratio {cur['hitRatio']}%  used {cur['usedPercent']}% of cache")
            return
        time.sleep(args.interval)
        cur = cache_snapshot(db)
        print(f"[cache] {time.strftime('%H:%M:%S')}  interval hit ratio {hit_ratio(prev, cur)}%  "
              f"cumulative {cur['hitRatio']}%  used {cur['usedPercent']}% ({cur['usedBytes'] / 1048576:,.1f} MB)")
        prev = cur


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped")
