"""Load demo data:  python -m scripts.seed

IMPORTANT: these are generated sample records for the lab, not real incident reports.
Indicators use documentation-only addresses (203.0.113.0/24, 198.51.100.0/24) and
the reserved .example domain, so nothing here points at real infrastructure.
Source names are real CTI publishers, but the threat records attributed to them are fictional.
"""
import hashlib
import random
from datetime import datetime, timedelta, timezone

from backend.config.connection import banner, ensure_indexes, get_db
from backend.labs.lab71 import build_embedded
from backend.services.classifier import SEVERITY_RANK, suggest

SOURCES = [
    ("CISA Advisories", "https://www.cisa.gov/news-events/cybersecurity-advisories", "Government", 96),
    ("Mandiant Threat Intelligence", "https://cloud.google.com/blog/topics/threat-intelligence", "Vendor", 92),
    ("Unit 42", "https://unit42.paloaltonetworks.com", "Vendor", 90),
    ("Microsoft Threat Intelligence", "https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/", "Vendor", 90),
    ("Cisco Talos", "https://blog.talosintelligence.com", "Vendor", 88),
    ("Securelist", "https://securelist.com", "Vendor", 84),
    ("ESET WeLiveSecurity", "https://www.welivesecurity.com", "Vendor", 82),
    ("SentinelLabs", "https://www.sentinelone.com/labs/", "Vendor", 80),
    ("The Hacker News", "https://thehackernews.com", "Media", 62),
    ("Reddit r/netsec", "https://www.reddit.com/r/netsec/", "Community", 45),
    ("Anonymous paste feed", "https://pastebin.com", "Community", 22),
]
SOURCE_WEIGHTS = [10, 9, 9, 9, 8, 7, 6, 6, 5, 4, 3]

ACTORS = [  # fictional names on purpose, to avoid attributing real campaigns
    ("Silent Heron", ["SH-01"], "Espionage"), ("Iron Ledger", ["IL-Crew"], "Financial"),
    ("Pale Harbor", [], "Espionage"), ("Copper Wasp", ["CW"], "Financial"),
    ("Hollow Atlas", ["HA-7"], "Disruption"), ("Velvet Tide", [], "Financial"),
]

TEMPLATES = [  # title, category, severity, description, tags
    ("Double-extortion ransomware campaign", "Ransomware", "Critical", "Operators encrypt file servers and exfiltrate data before demanding payment. Initial access comes from exposed remote services and stolen credentials.", ["ransomware", "extortion", "exfiltration"]),
    ("Ransomware affiliate abusing unpatched VPN appliances", "Ransomware", "High", "Affiliates exploit a known VPN vulnerability to gain access, then deploy ransomware after moving laterally.", ["ransomware", "vpn", "exploit"]),
    ("Phishing kit impersonating cloud-storage login pages", "Phishing", "High", "A kit hosted on short-lived domains harvests credentials and session cookies from fake sign-in pages.", ["phishing", "credential", "kit"]),
    ("Invoice-themed phishing delivering malicious attachments", "Phishing", "Medium", "Emails carry macro-enabled documents that download a loader when opened.", ["phishing", "email", "loader"]),
    ("QR-code phishing against corporate email users", "Phishing", "Medium", "Messages embed QR codes that lead to credential-harvesting pages and bypass URL scanners.", ["phishing", "qr-code", "credential"]),
    ("Spear-phishing of finance staff with payment-redirect lures", "Phishing", "High", "Targeted emails impersonate suppliers and ask staff to change bank details for pending invoices.", ["phishing", "bec", "fraud"]),
    ("State-linked intrusion set targeting telecom providers", "APT", "Critical", "Long-term access to core network systems, with a backdoor and C2 traffic hidden in normal-looking protocols.", ["apt", "espionage", "backdoor", "c2"]),
    ("Long-running espionage campaign against research institutions", "APT", "High", "Operators use spear-phishing and custom implants to collect unpublished research.", ["apt", "espionage", "implant"]),
    ("Supply-chain compromise of a popular open-source package", "Supply Chain", "Critical", "A maintainer account was hijacked and a release modified to steal credentials from build servers.", ["supply-chain", "credential", "hijack"]),
    ("Malicious browser extension harvesting session tokens", "Malware", "High", "An extension update adds code that exfiltrates cookies and tokens to a remote server.", ["malware", "browser", "exfiltration"]),
    ("Remote code execution flaw in an enterprise file-transfer product", "Vulnerability", "Critical", "A zero-day remote code execution bug is being exploited to drop web shells on internet-facing servers.", ["vulnerability", "zero-day", "remote code execution"]),
    ("Authentication bypass in a network management console", "Vulnerability", "High", "A flaw lets unauthenticated users reach administrative functions. Exploit code is public.", ["vulnerability", "exploit", "authentication"]),
    ("Privilege escalation in a widely deployed Linux utility", "Vulnerability", "Medium", "A local user can gain root through a crafted input. A patch is available from major distributions.", ["vulnerability", "linux", "patch available"]),
    ("Botnet recruiting exposed IoT cameras for DDoS", "Botnet", "High", "Devices with default credentials are enrolled in a botnet used for volumetric DDoS attacks.", ["botnet", "iot", "ddos"]),
    ("Information stealer sold on underground forums", "Malware", "High", "A stealer collects browser passwords, wallets and tokens, and sends them to a C2 panel.", ["malware", "stealer", "c2"]),
    ("Credential-stuffing wave against retail loyalty accounts", "Credential Theft", "Medium", "Automated logins using leaked passwords target loyalty and gift-card balances.", ["credential", "stuffing", "fraud"]),
    ("Wiper malware deployed against logistics firms", "Malware", "Critical", "A wiper overwrites disks after attackers gain domain admin access, causing prolonged outages.", ["malware", "wiper", "destructive"]),
    ("Cryptojacking via misconfigured container APIs", "Cryptomining", "Medium", "Exposed container APIs are used to launch miners that consume CPU on cloud workloads.", ["cryptomining", "container", "cloud"]),
    ("Fake software-update lures leading to loader malware", "Malware", "High", "Compromised websites show fake update prompts that install a loader and a trojan.", ["malware", "loader", "trojan"]),
    ("Annual threat landscape summary and detection guidance", "Informational", "Low", "A yearly summary of observed trends with detection guidance and best practice for defenders.", ["report", "guidance", "summary"]),
    ("Vendor advisory: patch available for medium-severity flaw", "Informational", "Low", "An advisory describes a fixed flaw. No exploitation has been observed and a patch available now.", ["advisory", "patch available"]),
    ("Security awareness bulletin on password hygiene", "Informational", "Low", "Informational awareness material about password managers and multi-factor authentication.", ["awareness", "informational"]),
    ("Mobile banking trojan distributed through sideloaded apps", "Malware", "High", "A trojan abuses accessibility services to overlay banking apps and steal credentials.", ["malware", "mobile", "trojan", "credential"]),
    ("DNS hijacking of registrar accounts for credential interception", "Network Attack", "High", "Attackers take over registrar accounts and redirect mail and login traffic to hijack credentials.", ["dns", "hijack", "credential"]),
]
REGIONS = ["EMEA", "APAC", "North America", "LATAM", "Global"]


def indicators(rng, informational):
    out = []
    for _ in range(rng.randint(0, 1) if informational else rng.randint(2, 6)):
        kind = rng.choice(["ip", "domain", "sha256", "url", "email"])
        word = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(8))
        value = {
            "ip": f"{rng.choice(['203.0.113', '198.51.100'])}.{rng.randint(1, 254)}",
            "domain": f"{word}.example",
            "sha256": hashlib.sha256(word.encode()).hexdigest(),
            "url": f"https://{word}.example/{rng.choice(['login', 'update', 'invoice', 'download'])}",
            "email": f"{word[:5]}@{word[5:]}.example",
        }[kind]
        out.append({"type": kind, "value": value})
    return out


def main():
    db = get_db()
    banner("Seeding CTI Sentinel demo data")
    for name in ["threats", "sources", "threat_actors", "threats_embedded"]:
        db.drop_collection(name)
    rng = random.Random(42)
    now = datetime.now(timezone.utc)

    source_docs = [{"name": n, "website": w, "type": t, "reliability": r,
                    "tier": "A" if r >= 85 else "B" if r >= 70 else "C" if r >= 50 else "D"} for n, w, t, r in SOURCES]
    sources = db.sources.insert_many(source_docs).inserted_ids
    source_by_id = {s_id: d for s_id, d in zip(sources, source_docs)}
    actors = db.threat_actors.insert_many([{"name": n, "aliases": a, "motivation": m, "origin": "Unknown"} for n, a, m in ACTORS]).inserted_ids

    threats = []
    for title, category, severity, desc, tags in TEMPLATES:
        for region in REGIONS:
            src_id = rng.choices(sources, weights=SOURCE_WEIGHTS)[0]
            doc = {"title": f"{title} ({region})", "description": desc, "severity": severity,
                   "severity_rank": SEVERITY_RANK[severity], "category": category, "tags": tags + [region.lower()],
                   "indicators": indicators(rng, category == "Informational"), "source_id": src_id,
                   "actor_id": rng.choice(actors) if category in ("APT", "Ransomware", "Phishing", "Malware") and rng.random() < 0.5 else None,
                   "created_at": now - timedelta(days=rng.randint(0, 180), hours=rng.randint(0, 23), minutes=rng.randint(0, 59))}
            s = suggest(doc, source_by_id[src_id]["reliability"])
            reviewed = rng.random() < 0.25
            doc["classification"] = {"verdict": s["verdict"], "confidence": s["confidence"], "reviewed": reviewed,
                                     "updated_at": doc["created_at"], "history": []}
            threats.append(doc)
    db.threats.insert_many(threats)
    ensure_indexes(db)
    n = build_embedded(db)
    print(f"sources: {len(sources)}  actors: {len(actors)}  threats: {len(threats)}  threats_embedded: {n}")
    print("Done. Start the API with:  python app.py")


if __name__ == "__main__":
    main()
