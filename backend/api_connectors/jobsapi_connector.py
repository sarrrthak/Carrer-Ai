"""
CONNECTOR 6 — Indeed12
Host    : indeed12.p.rapidapi.com
Endpoint: /company/{company}/jobs  (jobs by company)
          /jobs/search              (keyword search)
"""
import http.client, json, urllib.parse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_keys import RAPIDAPI_KEY

HOST    = "indeed12.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-key':  RAPIDAPI_KEY,
    'x-rapidapi-host': HOST,
    'Content-Type':    "application/json"
}

# ── RAW CALL (your exact snippet) ────────────────────────────────
def raw_call():
    conn = http.client.HTTPSConnection(HOST)
    conn.request("GET",
        "/company/Ubisoft/jobs?locality=us&start=1",
        headers=HEADERS)
    res  = conn.getresponse()
    data = res.read()
    return data.decode("utf-8")

# ── JOBS BY COMPANY ───────────────────────────────────────────────
def fetch_company_jobs(company="Google", locality="us", start=1):
    params = urllib.parse.urlencode({"locality": locality, "start": start})
    conn   = http.client.HTTPSConnection(HOST)
    conn.request("GET", f"/company/{urllib.parse.quote(company)}/jobs?{params}", headers=HEADERS)
    res    = conn.getresponse()
    resp   = json.loads(res.read().decode("utf-8"))
    jobs   = resp.get("jobs") or resp.get("data") or (resp if isinstance(resp, list) else [])
    return [_normalize(j, company) for j in jobs if isinstance(j, dict)]

# ── KEYWORD SEARCH ────────────────────────────────────────────────
def fetch_indeed_jobs(query="AI engineer", locality="us", start=1):
    params = urllib.parse.urlencode({"query": query, "locality": locality, "start": start})
    conn   = http.client.HTTPSConnection(HOST)
    conn.request("GET", f"/jobs/search?{params}", headers=HEADERS)
    res    = conn.getresponse()
    raw    = res.read().decode("utf-8")
    try:
        resp = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(resp, dict) and resp.get("message"):
        return []
    jobs   = resp.get("jobs") or resp.get("hits") or resp.get("data") or (resp if isinstance(resp, list) else [])
    return [_normalize(j) for j in jobs if isinstance(j, dict)]

def _normalize(j, default_company="Unknown"):
    loc    = j.get("location") or j.get("city") or ""
    if isinstance(loc, dict): loc = loc.get("city") or loc.get("country") or ""
    remote = "Remote" if (j.get("remote") or "remote" in str(loc).lower()) else "On-site"
    salary = j.get("salary") or {}
    sal_min = (salary.get("min") if isinstance(salary, dict) else 0) or 0
    sal_max = (salary.get("max") if isinstance(salary, dict) else 0) or 0
    sal_str = (f"${int(sal_min):,}–${int(sal_max):,}" if sal_min and sal_max
               else f"${int(sal_min):,}+" if sal_min else "Not stated")
    desc = j.get("description") or j.get("snippet") or ""
    return {
        "title":       j.get("title") or j.get("job_title") or "",
        "company":     j.get("company") or j.get("employer") or default_company,
        "location":    str(loc),
        "remote":      remote,
        "salary_str":  sal_str,
        "url":         j.get("url") or j.get("apply_url") or "#",
        "source":      "Indeed",
        "color":       "#003A9B",
        "date_posted": (j.get("date") or j.get("posted_at") or "")[:10],
        "description": desc[:300] + "…" if len(desc) > 300 else desc,
    }

# ── STANDALONE TEST → python jobsapi_connector.py ────────────────
if __name__ == "__main__":
    print("="*56)
    print("  CONNECTOR 6 — Indeed12")
    print("  Host:", HOST)
    print("="*56)
    out = raw_call()
    print(out[:600] + ("…" if len(out) > 600 else ""))
