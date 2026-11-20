"""Rule-based threat classifier.

It is deliberately simple and explainable: every point of the score comes from
a stated reason, so an analyst can see why a verdict was suggested and override it.
"""

SEVERITY_WEIGHT = {"Critical": 40, "High": 30, "Medium": 15, "Low": 5}
SEVERITY_RANK = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}

THREAT_WORDS = [
    "ransomware", "exploit", "zero-day", "c2", "backdoor", "credential", "exfiltrat",
    "wiper", "botnet", "remote code execution", "stealer", "hijack", "trojan",
]
BENIGN_WORDS = ["advisory", "patch available", "informational", "best practice", "awareness", "guidance", "summary"]


def suggest(threat, reliability=50):
    """Return {verdict, confidence, score, reasons} for a threat document."""
    severity = threat.get("severity", "Medium")
    base = SEVERITY_WEIGHT.get(severity, 15)
    reasons = [f"Severity is {severity}: +{base}"]

    n_ind = len(threat.get("indicators", []))
    ind_pts = min(n_ind * 5, 20)
    reasons.append(f"{n_ind} indicator(s) of compromise: +{ind_pts}")

    rel_pts = round(reliability * 0.2)
    reasons.append(f"Source reliability {reliability}/100: +{rel_pts}")

    text = " ".join([threat.get("title", ""), threat.get("description", ""), " ".join(threat.get("tags", []))]).lower()
    hits = [w for w in THREAT_WORDS if w in text]
    kw_pts = min(len(hits) * 4, 20)
    if hits:
        reasons.append(f"Threat keywords ({', '.join(hits[:5])}): +{kw_pts}")

    soft = [w for w in BENIGN_WORDS if w in text]
    pen = min(len(soft) * 10, 20)
    if soft:
        reasons.append(f"Advisory-style wording ({', '.join(soft[:3])}): -{pen}")

    score = base + ind_pts + rel_pts + kw_pts - pen

    if score >= 70:
        verdict, confidence = "Malicious", 60 + min(35, (score - 70) * 1.5)
    elif score >= 40:
        verdict, confidence = "Suspicious", 50 + max(0, 15 - abs(score - 55))
    else:
        verdict, confidence = "Benign", 60 + min(35, (40 - score) * 1.5)

    return {"verdict": verdict, "confidence": int(confidence), "score": score, "reasons": reasons}
