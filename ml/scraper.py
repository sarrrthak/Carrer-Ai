"""
CareerAI — Real-Time Job Scraper
=================================
Scrapes AI jobs from 6 FREE sources (no paid API keys needed):

  1. Remotive API         — remote tech jobs (100% free, no key)
  2. The Muse API         — company jobs (free, no key)
  3. Adzuna API           — global jobs (free key, 250 req/day)
  4. JSearch via RapidAPI — LinkedIn/Indeed/Glassdoor (free tier 500 req/month)
  5. GitHub Jobs RSS      — developer jobs via RSS feed
  6. We Work Remotely RSS — remote AI/ML jobs via RSS

Usage:
  python ml/scraper.py                        # scrape all sources
  python ml/scraper.py --source remotive      # single source
  python ml/scraper.py --query "ML Engineer"  # custom query
  python ml/scraper.py --save                 # save to CSV + JSON

Output:
  data/live_jobs.json    — latest scraped jobs (structured)
  data/live_jobs.csv     — CSV for Excel / Power BI
  data/scrape_log.txt    — log of each run

Install requirements:
  pip install requests beautifulsoup4 feedparser
"""

import requests, json, csv, time, os, re, argparse
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET  # built-in RSS parser (replaces feedparser)

# ── Config ────────────────────────────────────────────────────────
DATA_DIR     = os.path.join(os.path.dirname(__file__), "../data")
JOBS_JSON    = os.path.join(DATA_DIR, "live_jobs.json")
JOBS_CSV     = os.path.join(DATA_DIR, "live_jobs.csv")
SCRAPE_LOG   = os.path.join(DATA_DIR, "scrape_log.txt")
os.makedirs(DATA_DIR, exist_ok=True)

# ── Free API keys (sign up once, free tier is enough) ─────────────
# Get from: https://developer.adzuna.com  (free, 250/day)
ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID",  "YOUR_ADZUNA_APP_ID")
ADZUNA_API_KEY = os.getenv("ADZUNA_API_KEY", "YOUR_ADZUNA_API_KEY")

# Get from: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
#           Free tier: 500 requests/month
RAPIDAPI_KEY   = os.getenv("RAPIDAPI_KEY", "YOUR_RAPIDAPI_KEY")

AI_KEYWORDS = [
    "machine learning", "ML engineer", "data scientist", "AI engineer",
    "deep learning", "NLP engineer", "MLOps", "LLM engineer", "RAG",
    "computer vision", "data engineer", "AI researcher", "generative AI",
    "prompt engineer", "AI architect", "Python developer AI"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
}

def now_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def clean(text):
    if not text: return ""
    text = re.sub(r"<[^>]+>", " ", str(text))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]

def extract_skills(text):
    """Extract known AI skills mentioned in a job description."""
    KNOWN = [
        "Python","SQL","PyTorch","TensorFlow","Kubernetes","Docker","AWS","GCP",
        "Azure","Spark","Scala","Java","C++","R","Git","Linux","MLflow","Airflow",
        "dbt","LangChain","RAG","LLMs","Fine-tuning","CUDA","Statistics",
        "Deep Learning","Machine Learning","NLP","Computer Vision","Scikit-learn",
        "Pandas","NumPy","Tableau","Power BI","Kafka","Redis","MongoDB","FastAPI",
        "Flask","React","Node.js","CI/CD","Terraform","Agile","Communication",
        "Leadership","Research","Mathematics","Cloud","MLOps","Feature Stores",
        "Vector DBs","Hugging Face","OpenAI","LLM APIs","System Design","RLHF"
    ]
    found = []
    text_lower = text.lower()
    for skill in KNOWN:
        if skill.lower() in text_lower:
            found.append(skill)
    return ", ".join(found[:12])

def normalise_job(raw: dict) -> dict:
    """Standardise job data across all sources."""
    return {
        "id":          raw.get("id", ""),
        "title":       clean(raw.get("title", "")),
        "company":     clean(raw.get("company", "")),
        "location":    clean(raw.get("location", "")),
        "country":     raw.get("country", ""),
        "remote":      raw.get("remote", "Unknown"),
        "salary_min":  raw.get("salary_min", 0),
        "salary_max":  raw.get("salary_max", 0),
        "salary_str":  raw.get("salary_str", "Not stated"),
        "skills":      raw.get("skills", ""),
        "description": clean(raw.get("description", ""))[:300],
        "url":         raw.get("url", ""),
        "source":      raw.get("source", ""),
        "posted_date": raw.get("posted_date", now_str()),
        "scraped_at":  now_str(),
        "experience":  raw.get("experience", ""),
        "job_type":    raw.get("job_type", "Full-time"),
        "category":    raw.get("category", "AI / ML"),
    }

# ══════════════════════════════════════════════════════════════════
# SOURCE 1 — REMOTIVE API (100% FREE, NO KEY)
# https://remotive.com/api/remote-jobs
# ══════════════════════════════════════════════════════════════════
def scrape_remotive(query="machine learning", limit=50) -> list:
    """
    Remotive: Free remote job board API.
    No authentication needed.
    Returns up to 300 remote tech jobs per category.
    """
    print("  [Remotive] Fetching remote AI jobs...")
    jobs = []
    categories = ["software-dev", "data", "devops-sysadmin"]

    for cat in categories:
        try:
            url = f"https://remotive.com/api/remote-jobs?category={cat}&limit={limit}"
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            data = r.json()

            for j in data.get("jobs", []):
                title = j.get("title", "").lower()
                # Filter AI-relevant jobs
                if not any(kw.lower() in title for kw in [
                    "ml","machine learning","data","ai ","engineer","scientist",
                    "nlp","deep learning","python","analytics","llm","devops"
                ]):
                    continue

                desc = clean(j.get("description", ""))
                jobs.append(normalise_job({
                    "id":          f"remotive_{j.get('id','')}",
                    "title":       j.get("title",""),
                    "company":     j.get("company_name",""),
                    "location":    j.get("candidate_required_location","Remote"),
                    "country":     "Global",
                    "remote":      "Remote",
                    "salary_str":  j.get("salary","Not stated"),
                    "skills":      extract_skills(desc + " " + " ".join(j.get("tags",[]))),
                    "description": desc,
                    "url":         j.get("url",""),
                    "source":      "Remotive",
                    "posted_date": j.get("publication_date",""),
                    "job_type":    j.get("job_type","Full-time"),
                    "category":    j.get("category","AI / ML"),
                }))
            time.sleep(0.5)
        except Exception as e:
            print(f"    Remotive error ({cat}): {e}")

    print(f"    Found {len(jobs)} AI-relevant jobs from Remotive")
    return jobs


# ══════════════════════════════════════════════════════════════════
# SOURCE 2 — ADZUNA API (FREE KEY, 250 req/day)
# Sign up: https://developer.adzuna.com
# ══════════════════════════════════════════════════════════════════
def scrape_adzuna(query="machine learning engineer", country="gb", pages=2) -> list:
    """
    Adzuna: Aggregates jobs from 100s of job boards globally.
    Free developer key: 250 requests/day.
    Covers: UK, US, CA, AU, DE, FR, IN, SG, AE and more.
    """
    if ADZUNA_APP_ID == "YOUR_ADZUNA_APP_ID":
        print("  [Adzuna] Skipped — set ADZUNA_APP_ID and ADZUNA_API_KEY env vars")
        print("           Get free key at: https://developer.adzuna.com")
        return []

    print(f"  [Adzuna] Fetching '{query}' jobs from {country.upper()}...")
    jobs = []
    countries = ["gb", "us", "ca", "au", "in", "de"]

    for c in countries:
        for page in range(1, pages + 1):
            try:
                url = (
                    f"https://api.adzuna.com/v1/api/jobs/{c}/search/{page}"
                    f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_API_KEY}"
                    f"&results_per_page=20&what={query.replace(' ','+')}"
                    f"&content-type=application/json"
                )
                r = requests.get(url, headers=HEADERS, timeout=10)
                r.raise_for_status()
                data = r.json()

                COUNTRY_MAP = {
                    "gb":"UK","us":"USA","ca":"Canada","au":"Australia",
                    "in":"India","de":"Germany"
                }

                for j in data.get("results", []):
                    desc = clean(j.get("description",""))
                    sal = j.get("salary_min") or j.get("salary_max")
                    jobs.append(normalise_job({
                        "id":          f"adzuna_{j.get('id','')}",
                        "title":       j.get("title",""),
                        "company":     j.get("company",{}).get("display_name",""),
                        "location":    j.get("location",{}).get("display_name",""),
                        "country":     COUNTRY_MAP.get(c, c.upper()),
                        "remote":      "Unknown",
                        "salary_min":  j.get("salary_min",0),
                        "salary_max":  j.get("salary_max",0),
                        "salary_str":  (f"${sal:,.0f}" if sal else "Not stated"),
                        "skills":      extract_skills(desc),
                        "description": desc,
                        "url":         j.get("redirect_url",""),
                        "source":      "Adzuna",
                        "posted_date": j.get("created",""),
                        "category":    j.get("category",{}).get("label","AI / ML"),
                    }))
                time.sleep(0.3)
            except Exception as e:
                print(f"    Adzuna error ({c} p{page}): {e}")

    print(f"    Found {len(jobs)} jobs from Adzuna")
    return jobs


# ══════════════════════════════════════════════════════════════════
# SOURCE 3 — JSEARCH via RapidAPI (FREE tier 500 req/month)
# Aggregates: LinkedIn, Indeed, Glassdoor, ZipRecruiter
# Sign up: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
# ══════════════════════════════════════════════════════════════════
def scrape_jsearch(query="AI engineer", location="United States", pages=2) -> list:
    """
    JSearch: Searches LinkedIn, Indeed, Glassdoor simultaneously.
    Free RapidAPI tier: 500 requests/month.
    Best source for company-level job details.
    """
    if RAPIDAPI_KEY == "YOUR_RAPIDAPI_KEY":
        print("  [JSearch] Skipped — set RAPIDAPI_KEY env var")
        print("            Get free key at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch")
        return []

    print(f"  [JSearch] Searching '{query}' on LinkedIn/Indeed/Glassdoor...")
    jobs = []
    queries = [
        "Machine Learning Engineer",
        "Data Scientist AI",
        "MLOps Engineer",
        "LLM Engineer",
        "AI Research Scientist"
    ]

    for q in queries[:pages]:
        try:
            url = "https://jsearch.p.rapidapi.com/search"
            headers = {
                **HEADERS,
                "X-RapidAPI-Key":  RAPIDAPI_KEY,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
            }
            params = {
                "query":         f"{q} {location}",
                "page":          "1",
                "num_pages":     "1",
                "date_posted":   "week",
                "employment_types": "FULLTIME"
            }
            r = requests.get(url, headers=headers, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()

            for j in data.get("data", []):
                desc = clean(j.get("job_description",""))
                sal_min = j.get("job_min_salary") or 0
                sal_max = j.get("job_max_salary") or 0
                sal_str = ""
                if sal_min and sal_max:
                    sal_str = f"${sal_min:,.0f} – ${sal_max:,.0f}"
                elif sal_min:
                    sal_str = f"From ${sal_min:,.0f}"
                else:
                    sal_str = "Not stated"

                jobs.append(normalise_job({
                    "id":          f"jsearch_{j.get('job_id','')}",
                    "title":       j.get("job_title",""),
                    "company":     j.get("employer_name",""),
                    "location":    j.get("job_city","") + ", " + j.get("job_country",""),
                    "country":     j.get("job_country",""),
                    "remote":      ("Remote" if j.get("job_is_remote") else "On-site"),
                    "salary_min":  sal_min,
                    "salary_max":  sal_max,
                    "salary_str":  sal_str,
                    "skills":      extract_skills(desc),
                    "description": desc,
                    "url":         j.get("job_apply_link","") or j.get("job_google_link",""),
                    "source":      f"JSearch/{j.get('job_publisher','Indeed')}",
                    "posted_date": j.get("job_posted_at_datetime_utc",""),
                    "experience":  j.get("job_required_experience",{}).get("required_experience_in_months",""),
                    "job_type":    j.get("job_employment_type","Full-time"),
                }))
            time.sleep(1)  # respect rate limit
        except Exception as e:
            print(f"    JSearch error ({q}): {e}")

    print(f"    Found {len(jobs)} jobs from JSearch (LinkedIn/Indeed/Glassdoor)")
    return jobs


# ══════════════════════════════════════════════════════════════════
# SOURCE 4 — WE WORK REMOTELY RSS (100% FREE, NO KEY)
# https://weworkremotely.com/categories/remote-programming-jobs.rss
# ══════════════════════════════════════════════════════════════════
def scrape_wwr() -> list:
    """
    We Work Remotely: RSS feeds for remote jobs.
    Completely free, no authentication.
    Covers: programming, design, data, DevOps categories.
    """
    print("  [WeWorkRemotely] Fetching RSS feeds...")
    jobs = []
    feeds = [
        ("https://weworkremotely.com/categories/remote-programming-jobs.rss",   "Programming"),
        ("https://weworkremotely.com/categories/remote-data-science-jobs.rss",  "Data Science"),
        ("https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss","DevOps"),
    ]

    NS = {"atom": "http://www.w3.org/2005/Atom"}
    AI_KWS = ["machine learning","data","ml","ai ","engineer","scientist",
              "python","llm","nlp","analytics","devops","deep learning","backend"]

    for feed_url, cat in feeds:
        try:
            r = requests.get(feed_url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            items = root.findall(".//item")[:25]
            for item in items:
                title   = (item.findtext("title") or "").strip()
                link    = (item.findtext("link")  or "").strip()
                summary = clean(item.findtext("description") or "")
                pubdate = (item.findtext("pubDate") or "").strip()

                if not any(kw in title.lower() for kw in AI_KWS):
                    continue

                company = ""
                if ":" in title:
                    parts   = title.split(":", 1)
                    company = parts[0].strip()
                    title   = parts[1].strip()

                jobs.append(normalise_job({
                    "id":          f"wwr_{abs(hash(link)) % 9999999}",
                    "title":       title,
                    "company":     company,
                    "location":    "Remote",
                    "country":     "Global",
                    "remote":      "Remote",
                    "skills":      extract_skills(summary),
                    "description": summary,
                    "url":         link,
                    "source":      "WeWorkRemotely",
                    "posted_date": pubdate,
                    "category":    cat,
                }))
        except Exception as e:
            print(f"    WWR error ({cat}): {e}")

    print(f"    Found {len(jobs)} AI jobs from We Work Remotely")
    return jobs


# ══════════════════════════════════════════════════════════════════
# SOURCE 5 — THE MUSE API (FREE, NO KEY)
# https://www.themuse.com/api/public/jobs
# ══════════════════════════════════════════════════════════════════
def scrape_muse(pages=3) -> list:
    """
    The Muse: Free public jobs API, no key needed.
    Good for US-based tech company jobs with culture data.
    """
    print("  [TheMuse] Fetching tech jobs...")
    jobs = []
    categories = ["Data Science","Software Engineer","Data Analytics","IT","DevOps & Sysadmin"]
    AI_KWS = ["data","ml","machine learning","ai","engineer","scientist",
              "analytics","python","devops","nlp","llm","deep learning","cloud","platform"]

    for cat in categories:
        for page in range(1, pages + 1):
            try:
                r = requests.get(
                    "https://www.themuse.com/api/public/jobs",
                    headers=HEADERS,
                    params={"category": cat, "page": page},
                    timeout=12
                )
                r.raise_for_status()
                data = r.json()

                for j in data.get("results", []):
                    title = j.get("name", "")
                    if not any(kw in title.lower() for kw in AI_KWS):
                        continue
                    contents = " ".join([c.get("body","") for c in j.get("contents",[])])
                    desc = clean(contents)
                    locs = j.get("locations", [])
                    loc  = locs[0].get("name","USA") if locs else "USA"
                    jobs.append(normalise_job({
                        "id":          f"muse_{j.get('id','')}",
                        "title":       title,
                        "company":     j.get("company",{}).get("name",""),
                        "location":    loc,
                        "country":     "USA",
                        "remote":      "Remote" if "remote" in loc.lower() else "On-site",
                        "skills":      extract_skills(desc),
                        "description": desc,
                        "url":         j.get("refs",{}).get("landing_page",""),
                        "source":      "TheMuse",
                        "posted_date": j.get("publication_date",""),
                        "job_type":    "Full-time",
                        "category":    cat,
                    }))
                time.sleep(0.4)
            except Exception as e:
                print(f"    Muse error ({cat} p{page}): {e}")

    print(f"    Found {len(jobs)} AI jobs from The Muse")
    return jobs


# ══════════════════════════════════════════════════════════════════
# SOURCE 6 — ARBEITNOW RSS (FREE, EUROPE FOCUSED)
# https://www.arbeitnow.com/api/job-board-api
# ══════════════════════════════════════════════════════════════════
def scrape_arbeitnow() -> list:
    """
    Arbeitnow: Free job board API focused on Europe + Visa sponsorship.
    No key needed. Great for German, Dutch, French AI jobs.
    """
    print("  [Arbeitnow] Fetching European AI jobs...")
    jobs = []
    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()

        for j in data.get("data", []):
            title = j.get("title","")
            if not any(kw.lower() in title.lower() for kw in [
                "data","ml","machine learning","ai","engineer","scientist",
                "python","devops","analytics","llm","nlp","backend"
            ]):
                continue

            desc = clean(j.get("description",""))
            jobs.append(normalise_job({
                "id":          f"arb_{j.get('slug','')}",
                "title":       title,
                "company":     j.get("company_name",""),
                "location":    j.get("location","Europe"),
                "country":     "Europe",
                "remote":      ("Remote" if j.get("remote") else "On-site"),
                "skills":      extract_skills(desc),
                "description": desc,
                "url":         j.get("url",""),
                "source":      "Arbeitnow",
                "posted_date": j.get("created_at",""),
                "job_type":    "Full-time",
            }))
    except Exception as e:
        print(f"    Arbeitnow error: {e}")

    print(f"    Found {len(jobs)} AI jobs from Arbeitnow")
    return jobs


# ══════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════
def scrape_all(sources=None, save=True) -> list:
    """Run all scrapers and merge results."""
    start = time.time()
    print(f"\n{'='*60}")
    print(f"CareerAI Job Scraper — {now_str()}")
    print(f"{'='*60}\n")

    all_jobs = []
    source_fns = {
        "remotive":   scrape_remotive,
        "muse":       scrape_muse,
        "adzuna":     scrape_adzuna,
        "jsearch":    scrape_jsearch,
        "wwr":        scrape_wwr,
        "arbeitnow":  scrape_arbeitnow,
    }

    run_sources = sources if sources else list(source_fns.keys())
    for src in run_sources:
        if src in source_fns:
            try:
                jobs = source_fns[src]()
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"  [{src}] FAILED: {e}")
        print()

    # Deduplicate by title + company
    seen = set()
    unique_jobs = []
    for j in all_jobs:
        key = (j["title"].lower().strip(), j["company"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique_jobs.append(j)

    # Sort by posted date (newest first)
    unique_jobs.sort(key=lambda x: str(x.get("posted_date","") or ""), reverse=True)

    elapsed = round(time.time()-start, 1)
    print(f"{'='*60}")
    print(f"TOTAL JOBS SCRAPED : {len(all_jobs)}")
    print(f"AFTER DEDUP        : {len(unique_jobs)}")
    print(f"TIME TAKEN         : {elapsed}s")
    print(f"{'='*60}\n")

    # Source breakdown
    src_counts = {}
    for j in unique_jobs:
        src = j["source"].split("/")[0]
        src_counts[src] = src_counts.get(src, 0) + 1
    print("Source breakdown:")
    for src, cnt in sorted(src_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {src:<20} {cnt:>4} jobs")

    if save:
        save_jobs(unique_jobs)

    return unique_jobs


def save_jobs(jobs: list):
    """Save jobs to JSON and CSV."""
    # JSON
    with open(JOBS_JSON, "w") as f:
        json.dump({
            "scraped_at": now_str(),
            "total":      len(jobs),
            "jobs":       jobs
        }, f, indent=2)
    print(f"\n  Saved JSON  : {JOBS_JSON}")

    # CSV
    if jobs:
        fields = list(jobs[0].keys())
        with open(JOBS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(jobs)
        print(f"  Saved CSV   : {JOBS_CSV}")

    # Log
    log_entry = (
        f"[{now_str()}] Scraped {len(jobs)} jobs\n"
        + "\n".join(f"  {j['title']} @ {j['company']} ({j['source']})"
                    for j in jobs[:10])
        + f"\n  ... and {max(0,len(jobs)-10)} more\n"
        + "-"*60 + "\n"
    )
    with open(SCRAPE_LOG, "a") as f:
        f.write(log_entry)
    print(f"  Saved log   : {SCRAPE_LOG}")


def load_cached_jobs() -> list:
    """Load previously scraped jobs from cache."""
    if os.path.exists(JOBS_JSON):
        with open(JOBS_JSON) as f:
            data = json.load(f)
        return data.get("jobs", [])
    return []


# ── CLI ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CareerAI Job Scraper")
    parser.add_argument("--source", nargs="+",
                        choices=["remotive","muse","adzuna","jsearch","wwr","arbeitnow"],
                        help="Sources to scrape (default: all)")
    parser.add_argument("--query", default="machine learning",
                        help="Search query (used where applicable)")
    parser.add_argument("--save", action="store_true", default=True,
                        help="Save results to CSV + JSON")
    parser.add_argument("--show", type=int, default=10,
                        help="Print N sample jobs after scraping")
    args = parser.parse_args()

    jobs = scrape_all(sources=args.source, save=args.save)

    if jobs and args.show:
        print(f"\nSample jobs (first {args.show}):")
        print("-"*60)
        for j in jobs[:args.show]:
            sal = j["salary_str"] if j["salary_str"] != "Not stated" else "—"
            print(f"  {j['title']:<35} {j['company']:<25} {j['location']:<20} {sal}")
            if j["skills"]:
                print(f"    Skills: {j['skills'][:70]}")
            print(f"    URL: {j['url'][:70]}")
            print()
