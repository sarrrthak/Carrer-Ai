"""
CONNECTOR 5 — Glassdoor Real-Time
Host    : glassdoor-real-time.p.rapidapi.com
Endpoint: /companies/interview-details  (interview info)
          /jobs/search                  (job listings)
"""
import http.client, json, urllib.parse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_keys import RAPIDAPI_KEY

HOST    = "glassdoor-real-time.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-key':  RAPIDAPI_KEY,
    'x-rapidapi-host': HOST,
    'Content-Type':    "application/json"
}
SOCKET_TIMEOUT = 6   # seconds — hard cap per request

# ── RAW CALL (your exact snippet) ────────────────────────────────
def raw_call():
    conn = http.client.HTTPSConnection(HOST, timeout=SOCKET_TIMEOUT)
    conn.request("GET",
        "/companies/interview-details?interviewId=19018219",
        headers=HEADERS)
    res  = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")

# ── JOB LISTINGS ──────────────────────────────────────────────────
def fetch_glassdoor_jobs(keyword="AI engineer", location="", page=1):
    params = {"keyword": keyword, "page": page}
    if location: params["location"] = location
    qs   = urllib.parse.urlencode(params)
    try:
        conn = http.client.HTTPSConnection(HOST, timeout=SOCKET_TIMEOUT)
        conn.request("GET", f"/jobs/search?{qs}", headers=HEADERS)
        res  = conn.getresponse()
        if res.status != 200:
            return []
        raw = res.read().decode("utf-8")
    except Exception:
        return []
    try:
        resp = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(resp, dict) and resp.get("message"):
        return []
    jobs = resp.get("jobs") or resp.get("data") or (resp if isinstance(resp, list) else [])
    return [_normalize(j) for j in jobs if isinstance(j, dict)]

def _normalize(j):
    pay     = j.get("payPeriod") or j.get("salary") or {}
    sal_min = (pay.get("min") if isinstance(pay, dict) else 0) or 0
    sal_max = (pay.get("max") if isinstance(pay, dict) else 0) or 0
    sal_str = (f"${int(sal_min):,}–${int(sal_max):,}" if sal_min and sal_max
               else f"${int(sal_min):,}+" if sal_min else "Not stated")
    employer = j.get("employer") or j.get("company") or {}
    company  = (employer.get("name") if isinstance(employer, dict) else str(employer)) or "Unknown"
    loc  = j.get("location") or j.get("locationName") or ""
    if isinstance(loc, dict): loc = loc.get("cityName") or loc.get("countryName") or ""
    remote = "Remote" if str(j.get("isRemote","")).lower() in ("true","1","yes") else "On-site"
    desc   = j.get("description") or j.get("jobDescription") or ""
    return {
        "title":       j.get("jobTitleText") or j.get("title") or "",
        "company":     company,
        "location":    str(loc),
        "remote":      remote,
        "salary_str":  sal_str,
        "url":         j.get("jobViewUrl") or j.get("url") or j.get("applyUrl") or "#",
        "source":      "Glassdoor",
        "color":       "#0CAA41",
        "date_posted": (j.get("discoverDate") or j.get("postingDateText") or "")[:10],
        "description": desc[:300] + "…" if len(desc) > 300 else desc,
        "rating":      (employer.get("rating") if isinstance(employer, dict) else None),
    }

# ── STANDALONE TEST → python glassdoor_connector.py ──────────────
if __name__ == "__main__":
    print("="*56)
    print("  CONNECTOR 5 — Glassdoor Real-Time")
    print("  Host:", HOST)
    print("="*56)
    out = raw_call()
    print(out[:600] + ("…" if len(out) > 600 else ""))
