"""
CONNECTOR 4 — Jobs API v2
Host    : jobs-api14.p.rapidapi.com
Endpoint: /v2/salary/range  (salary data)
          /list              (job listings)
"""
import http.client, json, urllib.parse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_keys import RAPIDAPI_KEY

HOST    = "jobs-api14.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-key':  RAPIDAPI_KEY,
    'x-rapidapi-host': HOST,
    'Content-Type':    "application/json"
}

# ── RAW CALL (your exact snippet) ────────────────────────────────
def raw_call():
    conn = http.client.HTTPSConnection(HOST)
    conn.request("GET",
        "/v2/salary/range?query=developer&countryCode=de",
        headers=HEADERS)
    res  = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")

# ── SALARY LOOKUP ─────────────────────────────────────────────────
def fetch_salary(query="AI engineer", country_code="us"):
    params = urllib.parse.urlencode({"query": query, "countryCode": country_code})
    conn   = http.client.HTTPSConnection(HOST)
    conn.request("GET", f"/v2/salary/range?{params}", headers=HEADERS)
    res    = conn.getresponse()
    return json.loads(res.read().decode("utf-8"))

# ── JOB LISTINGS ──────────────────────────────────────────────────
def fetch_indeed_jobs(query="AI engineer", location="remote",
                      employment_types="FULLTIME", date_posted="week"):
    params = urllib.parse.urlencode({
        "query": query, "location": location,
        "employment_types": employment_types, "date_posted": date_posted,
    })
    conn = http.client.HTTPSConnection(HOST)
    conn.request("GET", f"/list?{params}", headers=HEADERS)
    res  = conn.getresponse()
    raw = res.read().decode("utf-8")
    try:
        resp = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(resp, dict) and resp.get("message"):
        return []
    jobs = resp.get("jobs") or resp.get("data") or (resp if isinstance(resp, list) else [])
    return [_normalize(j) for j in jobs if isinstance(j, dict)]

def _normalize(j):
    sal_min = j.get("salaryMin") or j.get("salary_min") or 0
    sal_max = j.get("salaryMax") or j.get("salary_max") or 0
    sal_str = (f"${int(sal_min):,}–${int(sal_max):,}" if sal_min and sal_max
               else f"${int(sal_min):,}+" if sal_min
               else j.get("salary") or "Not stated")
    loc    = j.get("location") or j.get("city") or ""
    remote = ("Remote"  if "remote" in str(loc).lower() or str(j.get("remote","")).lower() in ("true","1","yes")
              else "Hybrid" if "hybrid" in str(loc).lower() else "On-site")
    desc   = j.get("description") or j.get("jobDescription") or ""
    providers = j.get("jobProviders") or []
    url = providers[0].get("url") if providers else j.get("url") or "#"
    return {
        "title":       j.get("title") or j.get("jobTitle") or "",
        "company":     j.get("company") or j.get("employer") or "Unknown",
        "location":    str(loc),
        "remote":      remote,
        "salary_str":  sal_str,
        "url":         url,
        "source":      "Jobs API",
        "color":       "#F5C842",
        "date_posted": (j.get("datePosted") or j.get("date_posted") or "")[:10],
        "description": desc[:300] + "…" if len(desc) > 300 else desc,
    }

# ── STANDALONE TEST → python indeed_connector.py ─────────────────
if __name__ == "__main__":
    print("="*56)
    print("  CONNECTOR 4 — Jobs API v2")
    print("  Host:", HOST)
    print("="*56)
    out = raw_call()
    print(out[:600] + ("…" if len(out) > 600 else ""))
