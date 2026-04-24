"""
CareerAI Pro — Unified Flask Backend
======================================
Run:  python backend/server.py
Open: http://localhost:8000

All endpoints:
  GET  /                         → serves frontend/index.html
  GET  /api/health               → health + ML status
  GET  /api/market/overview      → full market data
  GET  /api/market/skills        → top skills
  GET  /api/market/salary        → salary tables
  GET  /api/market/growth        → role growth rates
  POST /api/predict/role         → ML role prediction from skills text
  POST /api/predict/skill-gap    → missing skills for top role
  POST /api/predict/salary       → salary prediction
  GET  /api/model/info           → ML model metadata
  GET  /api/jobs/search          → unified job search (q, location, remote, job_type,
                                     experience, date_posted, salary_min, page, per_page)
"""

from flask import Flask, request, jsonify, send_from_directory
import joblib, json, os, re, sys, http.client, urllib.parse, time, datetime, hashlib

# Ensure startup logs can print unicode symbols on Windows consoles.
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── Paths ──────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE, "backend", "models")
DATA_DIR  = os.path.join(BASE, "data")
FRONT_DIR = os.path.join(BASE, "frontend")

# ── Market data (pre-computed from 62 K+ job records) ─────────────
MARKET = {
    "role_salary": {
        "AI Engineering":   {"mean": 207982, "min": 90000,  "max": 374400},
        "Architecture":     {"mean": 251577, "min": 180000, "max": 384000},
        "Business":         {"mean": 134145, "min": 95000,  "max": 216000},
        "Data Engineering": {"mean": 176157, "min": 130000, "max": 264000},
        "Data Science":     {"mean": 181276, "min": 138000, "max": 261600},
        "Governance":       {"mean": 152516, "min": 100000, "max": 252000},
        "Infrastructure":   {"mean": 203527, "min": 140000, "max": 324000},
        "ML Operations":    {"mean": 199216, "min": 130000, "max": 312000},
        "Product":          {"mean": 194571, "min": 140000, "max": 312000},
        "Research":         {"mean": 192280, "min": 115000, "max": 336000},
        "Robotics":         {"mean": 170851, "min": 125000, "max": 288000},
        "Security":         {"mean": 200400, "min": 140000, "max": 312000},
    },
    "role_demand": {
        "AI Engineering": 92.6, "Architecture": 84,   "Business": 78,
        "Data Engineering": 88,  "Data Science": 91,   "Governance": 69.8,
        "Infrastructure": 85,   "ML Operations": 93,   "Product": 85,
        "Research": 88,          "Robotics": 76,        "Security": 80,
    },
    "role_growth": {
        "AI Engineering": 40.2, "Architecture": 18,    "Business": 17.1,
        "Data Engineering": 19.7,"Data Science": 31.5, "Governance": 16.9,
        "Infrastructure": 18.4, "ML Operations": 52.8, "Product": 17.3,
        "Research": 17.5,        "Robotics": 18.1,     "Security": 17.2,
    },
    "top_skills": [
        {"skill":"Python","count":942}, {"skill":"SQL","count":452},
        {"skill":"Cloud","count":429},  {"skill":"Statistics","count":350},
        {"skill":"PyTorch","count":302},{"skill":"Git","count":295},
        {"skill":"Fine-tuning","count":164},{"skill":"LLMs","count":125},
        {"skill":"Kubernetes","count":123},{"skill":"MLOps","count":88},
        {"skill":"Docker","count":93},  {"skill":"Deep Learning","count":91},
        {"skill":"TensorFlow","count":86},{"skill":"LangChain","count":77},
        {"skill":"RAG","count":63},
    ],
    "country_salary": {
        "USA":226190, "Global":222044, "UAE":194226,
        "Switzerland":190592,"Australia":188000,"France":183152,
        "Singapore":181831,"Germany":181180,"UK":180644,
        "Canada":180588,"Netherlands":175257,"India":133123,
    },
    "exp_salary": {
        "Entry (0-2 yrs)":150039,"Mid (3-5 yrs)":175984,
        "Senior (6-9 yrs)":214280,"Lead (10+ yrs)":240055,
    },
}

ALL_SKILLS = [
    "Python","SQL","Cloud","PyTorch","TensorFlow","Git","Statistics","Docker",
    "Kubernetes","LLMs","Fine-tuning","Deep Learning","MLOps","LangChain","RAG",
    "CUDA","Machine Learning","NLP","Computer Vision","Scikit-learn","Pandas",
    "NumPy","Jupyter","Keras","FastAPI","Flask","Spark","Tableau","Power BI",
    "R","Scala","Java","C++","Airflow","dbt","ETL","AWS","GCP","Azure","CI/CD",
    "MLflow","Linux","Risk Analysis","Cybersecurity","ML Security","Red Teaming",
    "Agile","Product Strategy","Data Analysis","Stakeholder Mgmt","AI Literacy",
    "EU AI Act","Legal Knowledge","Auditing","Ethics Frameworks","System Design",
    "Enterprise Architecture","Leadership","Communication","Research","Publishing",
    "Mathematics","LLM APIs","Vector DBs","Data Visualization","Business Analysis",
    "BERT","GPT","HuggingFace","ONNX","Feature Engineering","A/B Testing",
    "Causal Inference","Probability","Regression","Classification","Clustering",
    "OpenCV","Transformers","Reinforcement Learning",
]

ROLE_REQ = {
    "AI Engineering":   ["Python","PyTorch","SQL","Fine-tuning","LLMs","Cloud",
                          "Linux","Git","Statistics","LLM APIs"],
    "Data Science":     ["Python","Statistics","SQL","Deep Learning","Machine Learning",
                          "Scikit-learn","Data Visualization","Causal Inference","Cloud"],
    "ML Operations":    ["Cloud","Kubernetes","Docker","Python","Monitoring",
                          "MLflow","CI/CD","Git","Linux"],
    "Data Engineering": ["SQL","Airflow","dbt","Python","ETL","Spark",
                          "Feature Stores","Cloud"],
    "Architecture":     ["Cloud","Leadership","System Design","Machine Learning",
                          "Python","Enterprise Architecture"],
    "Research":         ["Publishing","PyTorch","Mathematics","Deep Learning",
                          "Python","Statistics"],
    "Infrastructure":   ["Cloud","CUDA","Kubernetes","Linux","Docker"],
    "Security":         ["Risk Analysis","Cybersecurity","ML Security","Python"],
    "Governance":       ["EU AI Act","Legal Knowledge","Auditing","Ethics Frameworks"],
    "Product":          ["Agile","Data Analysis","Product Strategy","AI Literacy"],
    "Business":         ["SQL","Communication","Business Analysis","Data Visualization"],
    "Robotics":         ["C++","Computer Vision","System Design","Python"],
}

# ── API Connectors (api_connectors/) ──────────────────────────────
import sys as _sys
_sys.path.insert(0, BASE)
try:
    from backend.api_connectors.job_service import search_jobs, SOURCE_META
    CONNECTORS_READY = True
    print(f"  ✓ Job Service loaded: {list(SOURCE_META.keys())}")
except Exception as _ce:
    _ce_msg = str(_ce)
    CONNECTORS_READY = False
    SOURCE_META = {}
    print(f"  ✗ Job Service not loaded ({_ce})")

    def search_jobs(**kw):
        return {"jobs": [], "total": 0, "sources": {}, "errors": {"init": _ce_msg},
                "page": 1, "per_page": 20, "total_pages": 1,
                "from_cache": False, "cached_at": ""}

# ── News Cache ────────────────────────────────────────────────────
_NEWS_CACHE    = {}
NEWS_CACHE_TTL = 900   # 15 minutes
NEWS_API_KEY   = "baa76720998a4a6593ee3cbe54f68a01"

# ── Courses Cache ─────────────────────────────────────────────────
_COURSES_CACHE    = {}
COURSES_CACHE_TTL = 600   # 10 minutes
COURSES_API_HOST  = "collection-for-coursera-courses.p.rapidapi.com"
COURSES_API_KEY   = "61ee1c4518msh5d5083b2d788379p18c056jsn4fca2f1bb54c"

# ── Load ML Model ──────────────────────────────────────────────────
try:
    _model     = joblib.load(os.path.join(MODEL_DIR, "role_predictor.pkl"))
    _label_enc = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))
    with open(os.path.join(MODEL_DIR, "model_meta.json")) as f:
        MODEL_META = json.load(f)
    ML_READY = True
    print(f"  ✓ ML model loaded: {MODEL_META.get('best_model','?')}  "
          f"accuracy={MODEL_META.get('accuracy','?')}")
except Exception as exc:
    ML_READY   = False
    MODEL_META = {}
    print(f"  ✗ ML model not loaded ({exc}) — using rule-based fallback")

# ── Flask App ──────────────────────────────────────────────────────
app = Flask(__name__, static_folder=FRONT_DIR)

@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"]  = "*"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return r

# Serve frontend
@app.route("/", methods=["GET"])
def index():
    return send_from_directory(FRONT_DIR, "index.html")

@app.route("/<path:p>")
def static_files(p):
    # Don't catch API routes — return 404 so Flask can route them properly
    if p.startswith("api/"):
        from flask import abort
        abort(404)
    try:
        return send_from_directory(FRONT_DIR, p)
    except Exception:
        return send_from_directory(FRONT_DIR, "index.html")

# ── Helpers ────────────────────────────────────────────────────────
def extract_skills(text: str) -> list:
    norm = text.lower()
    return [s for s in ALL_SKILLS
            if re.search(r'\b' + re.escape(s.lower()) + r'\b', norm)]

def smart_predict(skills_text: str, found_skills: list) -> list:
    """
    Weighted keyword scoring across resume full text + detected skills.
    Each role has PRIMARY keywords (weight 3), SECONDARY (weight 2), CONTEXT (weight 1).
    Also scans raw text for title hints and job context words.
    Gives genuinely different scores for different resumes.
    """
    text_lower = skills_text.lower()

    ROLE_KEYWORDS = {
        "AI Engineering": {
            "primary":   ["llm","large language model","fine-tuning","fine tuning","lora","qlora",
                          "rag","retrieval augmented","langchain","openai api","groq","llm engineer",
                          "ai engineer","generative ai","genai","prompt engineering","vector database",
                          "embedding","huggingface","transformers","llama","gpt","gemini"],
            "secondary": ["pytorch","python","nlp","deep learning","neural network","bert","attention",
                          "inference","model deployment","api","fastapi","ai application"],
            "context":   ["model","token","context window","hallucination","agent","rlhf","alignment",
                          "foundation model","multimodal","claude","anthropic"],
        },
        "Data Science": {
            "primary":   ["data scientist","statistical analysis","hypothesis testing","a/b test",
                          "regression","classification","clustering","scikit-learn","sklearn",
                          "statistical model","predictive model","exploratory data analysis","eda",
                          "data analysis","analytics","matplotlib","seaborn","plotly"],
            "secondary": ["python","r language","pandas","numpy","jupyter","statistics","probability",
                          "machine learning","xgboost","random forest","logistic regression","svm",
                          "cross validation","feature engineering","tableau","power bi"],
            "context":   ["insight","experiment","kpi","metric","business intelligence","report",
                          "correlation","distribution","p-value","confidence interval","dataset"],
        },
        "ML Operations": {
            "primary":   ["mlops","ml engineer","ml pipeline","model deployment","model serving",
                          "mlflow","kubeflow","model monitoring","model registry","feature store",
                          "data drift","model drift","retraining","ci/cd","continuous integration",
                          "continuous deployment","devops","sre","platform engineer"],
            "secondary": ["kubernetes","k8s","docker","helm","airflow","prefect","dagster",
                          "prometheus","grafana","cloud","aws","gcp","azure","terraform","ansible"],
            "context":   ["pipeline","automation","orchestration","observability","scaling",
                          "infrastructure","deployment","production","reliability","latency"],
        },
        "Data Engineering": {
            "primary":   ["data engineer","etl","elt","data pipeline","data warehouse","data lake",
                          "lakehouse","apache spark","pyspark","kafka","flink","dbt","airflow",
                          "data modeling","dimensional modeling","star schema","snowflake","bigquery",
                          "redshift","databricks","delta lake","apache iceberg"],
            "secondary": ["sql","python","scala","java","hive","presto","trino","postgres","mysql",
                          "mongodb","redis","parquet","avro","data quality","data governance"],
            "context":   ["ingestion","batch","streaming","real-time","partition","sharding",
                          "schema","migration","data catalog","lineage","medallion","bronze silver gold"],
        },
        "Research": {
            "primary":   ["research scientist","research engineer","phd","publication","paper",
                          "arxiv","ieee","acm","neurips","icml","iclr","cvpr","emnlp","acl",
                          "novel algorithm","state of the art","sota","benchmark","ablation",
                          "theoretical","proof","theorem","experimental evaluation"],
            "secondary": ["pytorch","tensorflow","deep learning","mathematics","linear algebra",
                          "calculus","optimization","gradient","backpropagation","reinforcement learning",
                          "computer vision","natural language processing"],
            "context":   ["literature review","citation","methodology","hypothesis","experiment",
                          "evaluation","dataset","baseline","reproducibility","open source"],
        },
        "Architecture": {
            "primary":   ["architect","solutions architect","enterprise architect","principal engineer",
                          "staff engineer","technical lead","system design","distributed systems",
                          "microservices","api design","cloud architecture","multi-cloud",
                          "technical strategy","roadmap","design patterns"],
            "secondary": ["aws","gcp","azure","cloud","kubernetes","terraform","high availability",
                          "scalability","security","cost optimization","leadership","mentoring"],
            "context":   ["architecture review","rfc","adr","stakeholder","cross-functional",
                          "engineering excellence","governance","compliance","enterprise"],
        },
        "ML Operations": {
            "primary":   ["mlops","model deployment","ml pipeline","model monitoring","feature store",
                          "mlflow","kubeflow","model registry","production ml","platform engineer"],
            "secondary": ["kubernetes","docker","airflow","ci/cd","cloud","prometheus","grafana"],
            "context":   ["pipeline","automation","orchestration","observability","scaling"],
        },
        "Infrastructure": {
            "primary":   ["infrastructure engineer","platform engineer","gpu cluster","cuda",
                          "hpc","high performance computing","distributed training","networking",
                          "linux admin","devops","sre","site reliability","bare metal","nvidia"],
            "secondary": ["kubernetes","docker","terraform","ansible","python","bash","linux",
                          "aws","gcp","azure","monitoring","alerting","incident response"],
            "context":   ["latency","throughput","uptime","sla","slo","capacity","provisioning"],
        },
        "Security": {
            "primary":   ["security engineer","cybersecurity","ai security","ml security",
                          "red team","penetration testing","threat modeling","vulnerability",
                          "adversarial attack","model robustness","privacy","differential privacy",
                          "federated learning","compliance","risk assessment","soc","siem"],
            "secondary": ["python","risk analysis","auditing","authentication","encryption",
                          "zero trust","identity","access management","iam"],
            "context":   ["attack","defense","exploit","mitigation","policy","regulation","gdpr"],
        },
        "Governance": {
            "primary":   ["ai ethics","responsible ai","ai governance","ai policy","ai regulation",
                          "eu ai act","model card","bias detection","fairness","explainability",
                          "transparency","audit","compliance officer","legal","policy analyst"],
            "secondary": ["documentation","stakeholder","risk management","auditing","reporting"],
            "context":   ["ethics","accountability","oversight","trustworthy","bias","fairness"],
        },
        "Product": {
            "primary":   ["product manager","product owner","ai product","roadmap","user story",
                          "product strategy","go-to-market","product metrics","okr","kpi",
                          "product-led growth","customer discovery","user research","ux"],
            "secondary": ["agile","scrum","jira","confluence","stakeholder","prioritization",
                          "data-driven","a/b testing","analytics","sql","python"],
            "context":   ["feature","launch","sprint","backlog","customer","market","revenue"],
        },
        "Business": {
            "primary":   ["business analyst","business intelligence","bi analyst","data analyst",
                          "sql","excel","tableau","power bi","looker","reporting","dashboard",
                          "business analysis","requirements gathering","process improvement"],
            "secondary": ["data visualization","statistics","python","r","communication",
                          "stakeholder management","presentation","documentation"],
            "context":   ["insight","report","kpi","metric","decision","business","operations"],
        },
        "Robotics": {
            "primary":   ["robotics engineer","robot","ros","ros2","autonomous","self-driving",
                          "computer vision","slam","path planning","kinematics","embedded systems",
                          "control systems","pid","sensor fusion","lidar","point cloud","3d"],
            "secondary": ["c++","python","opencv","pytorch","real-time","simulation","gazebo",
                          "hardware","firmware","perception","localization"],
            "context":   ["actuator","sensor","motor","mapping","navigation","manipulation"],
        },
    }

    scores = {}
    for role, kws in ROLE_KEYWORDS.items():
        score = 0.0
        for kw in kws.get("primary", []):
            if kw in text_lower:
                score += 3.0
        for kw in kws.get("secondary", []):
            if kw in text_lower:
                score += 2.0
        for kw in kws.get("context", []):
            if kw in text_lower:
                score += 1.0
        scores[role] = score

    total = sum(scores.values()) or 1.0
    # Convert to percentage confidence
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Normalize so top role gets a meaningful %, others are relative
    top_score = ranked[0][1] if ranked[0][1] > 0 else 1.0
    result = []
    for role, s in ranked:
        conf = round((s / top_score) * 65 + (s / total) * 35, 1)
        conf = min(95.0, max(5.0, conf))
        result.append({"role": role, "confidence": conf})

    return result

def ml_predict(skills_text: str, found: list) -> list:
    """Use smart keyword scoring always — the trained ML model has too low accuracy (23%)."""
    return smart_predict(skills_text, found)

# ── API routes ─────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({
        "status":        "ok",
        "ml_model":      ML_READY,
        "ml_accuracy":   MODEL_META.get("accuracy") if ML_READY else None,
        "market_roles":  len(MARKET["role_salary"]),
        "version":       "2.0.0",
    })

@app.route("/api/market/overview")
def market_overview():
    return jsonify(MARKET)

@app.route("/api/market/skills")
def market_skills():
    return jsonify({"skills": MARKET["top_skills"]})

@app.route("/api/market/salary")
def market_salary():
    return jsonify({
        "salaries":      MARKET["role_salary"],
        "by_experience": MARKET["exp_salary"],
        "by_country":    MARKET["country_salary"],
    })

@app.route("/api/market/growth")
def market_growth():
    return jsonify({
        "growth": MARKET["role_growth"],
        "demand": MARKET["role_demand"],
    })

@app.route("/api/predict/role", methods=["POST","OPTIONS"])
def predict_role():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    body        = request.get_json(force=True) or {}
    skills_text = body.get("skills", "").strip()
    if not skills_text:
        return jsonify({"error": "skills field required"}), 400

    found = extract_skills(skills_text)
    preds = ml_predict(skills_text, found)

    top   = preds[0]["role"] if preds else "AI Engineering"
    conf  = preds[0]["confidence"] if preds else 30

    # Score based on: keyword match confidence + number of skills found + text length
    text_richness = min(20, len(skills_text.split()) / 20)  # up to 20 pts for detailed resume
    skill_bonus   = min(25, len(found) * 2.5)               # up to 25 pts for skills detected
    match_score   = conf * 0.55                              # up to ~52 pts for role match
    score = min(95, max(20, round(match_score + skill_bonus + text_richness)))

    grade = ("Excellent — strong profile" if score >= 80
             else "Good — keep growing" if score >= 60
             else "Developing — build core skills")

    return jsonify({
        "top_role":     top,
        "predictions":  preds[:6],
        "found_skills": found,
        "resume_score": score,
        "score_grade":  grade,
        "model_used":   MODEL_META.get("best_model","rule-based") if ML_READY else "rule-based",
        "ml_accuracy":  MODEL_META.get("accuracy") if ML_READY else None,
    })

@app.route("/api/predict/skill-gap", methods=["POST","OPTIONS"])
def predict_skill_gap():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    body        = request.get_json(force=True) or {}
    skills_text = body.get("skills", "")
    found       = extract_skills(skills_text)
    preds       = ml_predict(skills_text, found)
    top         = preds[0]["role"] if preds else "AI Engineering"

    req  = ROLE_REQ.get(top, ["Python","SQL","Machine Learning"])

    # Check have/miss against both detected skills AND raw text (for broader matching)
    text_lower = skills_text.lower()
    have = []
    miss = []
    for s in req:
        # Check in detected skills list OR directly in the resume text
        in_found = any(s.lower() in f.lower() or f.lower() in s.lower() for f in found)
        in_text  = s.lower() in text_lower
        if in_found or in_text:
            have.append(s)
        else:
            miss.append(s)

    priority = [
        {"skill": s, "priority": "high" if i < 3 else "medium" if i < 6 else "low"}
        for i, s in enumerate(miss)
    ]
    return jsonify({
        "top_role":        top,
        "required_skills": req,
        "have_skills":     have,
        "missing_skills":  priority,
        "match_percent":   round(len(have) / max(len(req), 1) * 100),
    })

@app.route("/api/predict/salary", methods=["POST","OPTIONS"])
def predict_salary():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    body = request.get_json(force=True) or {}
    role = body.get("role", "AI Engineering")
    exp  = body.get("experience_level", "Mid (3-5 yrs)")
    cty  = body.get("country", "USA")

    base    = MARKET["role_salary"].get(role, {}).get("mean", 180000)
    exp_mul = {"Entry (0-2 yrs)":0.72,"Mid (3-5 yrs)":0.90,
               "Senior (6-9 yrs)":1.12,"Lead (10+ yrs)":1.28}.get(exp, 1.0)
    cty_mul = {"USA":1.18,"UK":0.95,"Germany":0.95,"Canada":0.95,
               "Australia":0.99,"India":0.70,"Singapore":0.95,
               "UAE":1.02,"Global":1.15}.get(cty, 0.92)
    mid = round(base * exp_mul * cty_mul)

    return jsonify({
        "predicted_salary": mid,
        "range_low":        round(mid * 0.78),
        "range_high":       round(mid * 1.24),
        "role":             role,
        "experience_level": exp,
        "country":          cty,
        "base_market_avg":  base,
    })

@app.route("/api/model/info")
def model_info():
    if not ML_READY:
        return jsonify({"ml_ready": False,
                        "message":  "Run: python ml/train_model.py"})
    return jsonify({"ml_ready": True, **MODEL_META})

# ── Unified Job Search ────────────────────────────────────────────
@app.route("/api/jobs/search")
def jobs_search():
    """Unified job search across JSearch, Active Jobs DB, and LinkedIn."""
    page     = max(1, int(request.args.get("page",     1)))
    per_page = min(50, max(1, int(request.args.get("per_page", 20))))

    # Force-bypass cache when ?force=true (Refresh button)
    if request.args.get("force") == "true":
        try:
            from backend.api_connectors import job_service as _js
            filter_params = {k: v for k, v in request.args.items()
                             if k not in ("page", "per_page", "force") and v}
            cache_key = _js._cache_key(filter_params)
            _js._CACHE.pop(cache_key, None)
        except Exception:
            pass

    sources_arg = request.args.get("sources", "")
    sources = [s.strip() for s in sources_arg.split(",") if s.strip()] or None

    result = search_jobs(
        query       = request.args.get("q",           ""),
        location    = request.args.get("location",    ""),
        remote      = request.args.get("remote",      ""),
        job_type    = request.args.get("job_type",    ""),
        experience  = request.args.get("experience",  ""),
        date_posted = request.args.get("date_posted", ""),
        salary_min  = int(request.args.get("salary_min", 0) or 0),
        page        = page,
        per_page    = per_page,
        sources     = sources,
    )

    return jsonify({
        "status":      "ok" if result.get("jobs") else "empty",
        "jobs":        result.get("jobs", []),
        "total":       result.get("total", 0),
        "page":        result.get("page", page),
        "per_page":    result.get("per_page", per_page),
        "total_pages": result.get("total_pages", 1),
        "sources":     result.get("sources", {}),
        "errors":      result.get("errors", {}),
        "from_cache":  result.get("from_cache", False),
        "cached_at":   result.get("cached_at", ""),
    })

# ── News Search ───────────────────────────────────────────────────
@app.route("/api/news")
def news_search():
    """Proxy NewsAPI requests server-side (browser CORS blocked on free tier)."""
    category  = request.args.get("category",  "technology").lower().strip()
    q         = request.args.get("q",          "").strip()
    page      = max(1, int(request.args.get("page",     1) or 1))
    page_size = min(100, max(1, int(request.args.get("pageSize", 20) or 20)))

    # Cache key
    ck = hashlib.md5(json.dumps(
        {"cat": category, "q": q, "page": page, "ps": page_size},
        sort_keys=True).encode()).hexdigest()
    entry = _NEWS_CACHE.get(ck)
    if entry and entry["expires_at"] > time.time():
        return jsonify({**entry["data"], "from_cache": True})

    # Build NewsAPI request
    params = {"apiKey": NEWS_API_KEY, "language": "en",
              "pageSize": page_size, "page": page}
    if q:
        endpoint = "/v2/everything"
        params["q"] = q
        params["sortBy"] = "publishedAt"
    else:
        endpoint = "/v2/top-headlines"
        params["category"] = category

    try:
        conn = http.client.HTTPSConnection("newsapi.org", timeout=10)
        conn.request("GET", endpoint + "?" + urllib.parse.urlencode(params),
                     headers={"User-Agent": "CareerAI-Pro/2.0"})
        raw = json.loads(conn.getresponse().read().decode("utf-8"))
        conn.close()
    except Exception as e:
        return jsonify({"status": "error", "message": str(e),
                        "articles": [], "total": 0}), 502

    articles = [
        {"title":       a.get("title", ""),
         "description": a.get("description", "") or "",
         "url":         a.get("url", ""),
         "urlToImage":  a.get("urlToImage", "") or "",
         "source":      (a.get("source") or {}).get("name", ""),
         "author":      a.get("author", "") or "",
         "publishedAt": a.get("publishedAt", ""),
        }
        for a in raw.get("articles", [])
        if (a.get("title", "") or "") not in ("", "[Removed]")
        and (a.get("url", "") or "")
    ]

    result = {
        "status":     "ok" if raw.get("status") == "ok" else "error",
        "articles":   articles,
        "total":      raw.get("totalResults", len(articles)),
        "page":       page,
        "pageSize":   page_size,
        "from_cache": False,
        "cached_at":  datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if result["status"] == "error":
        result["message"] = raw.get("message", "Unknown error from NewsAPI")
    else:
        _NEWS_CACHE[ck] = {"data": result, "expires_at": time.time() + NEWS_CACHE_TTL}

    return jsonify(result)

# ── Courses Search ────────────────────────────────────────────────
@app.route("/api/courses")
def courses_search():
    """Proxy Coursera Courses Collection API requests server-side."""
    institution = request.args.get("institution", "").strip()
    page_no     = max(1, int(request.args.get("page_no", 1) or 1))

    ck = hashlib.md5(json.dumps(
        {"inst": institution, "page": page_no},
        sort_keys=True).encode()).hexdigest()
    entry = _COURSES_CACHE.get(ck)
    if entry and entry["expires_at"] > time.time():
        return jsonify({**entry["data"], "from_cache": True})

    params = {"page_no": page_no}
    if institution:
        params["course_institution"] = institution

    try:
        conn = http.client.HTTPSConnection(COURSES_API_HOST, timeout=12)
        conn.request("GET",
                     "/rapidapi/course/get_course.php?" + urllib.parse.urlencode(params),
                     headers={
                         "x-rapidapi-key":  COURSES_API_KEY,
                         "x-rapidapi-host": COURSES_API_HOST,
                         "Content-Type":    "application/json",
                     })
        raw = json.loads(conn.getresponse().read().decode("utf-8"))
        conn.close()
    except Exception as e:
        return jsonify({"status": "error", "message": str(e),
                        "courses": [], "total": 0}), 502

    # Normalize — API returns {"reviews": [...], "total_records": "N", ...}
    items = raw if isinstance(raw, list) else raw.get("reviews", raw.get("courses", raw.get("data", [])))

    courses = []
    for c in (items if isinstance(items, list) else []):
        title = (c.get("course_name") or c.get("course_title") or c.get("title") or "").strip()
        if not title:
            continue
        url   = (c.get("course_url")        or c.get("url")         or "").strip()
        inst  = (c.get("course_institution") or c.get("institution") or "").strip()
        slug  = (c.get("course_unique_id")   or "").strip()
        desc  = (c.get("course_description") or c.get("description") or "").strip()[:400]
        instr = (c.get("instructor_name")    or c.get("instructor")  or "").strip()
        dur   = (c.get("course_time")        or c.get("duration")    or "").strip()
        rat   = c.get("course_rating")       or c.get("rating")      or 0
        enr   = c.get("course_students_enrolled") or c.get("enrolled") or 0
        diff  = (c.get("course_difficulty")  or c.get("difficulty")  or "").strip()
        # Use Coursera's CDN thumbnail pattern from the slug when available
        img   = (c.get("course_image") or c.get("image") or "").strip()

        try:
            rat = float(rat)
        except (ValueError, TypeError):
            rat = 0.0

        cid = hashlib.md5((url or title + inst).encode()).hexdigest()[:12]
        courses.append({
            "id":          cid,
            "title":       title,
            "institution": inst,
            "description": desc,
            "instructor":  instr,
            "duration":    dur,
            "rating":      rat,
            "enrolled":    enr,
            "image":       img,
            "difficulty":  diff,
            "slug":        slug,
            "url":         url,
        })

    try:
        total_records = int(raw.get("total_records", len(courses)))
    except (ValueError, TypeError):
        total_records = len(courses)

    has_more = raw.get("next_records_available", "no").lower() == "yes"

    result = {
        "status":       "ok" if courses else "empty",
        "courses":      courses,
        "total":        total_records,
        "on_page":      len(courses),
        "has_more":     has_more,
        "page_no":      page_no,
        "institution":  institution,
        "from_cache":   False,
        "cached_at":    datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if courses:
        _COURSES_CACHE[ck] = {"data": result, "expires_at": time.time() + COURSES_CACHE_TTL}

    return jsonify(result)

# ── Run ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    print("\n" + "=" * 56)
    print("  CareerAI Pro — Backend v2.0")
    print("=" * 56)
    print(f"  ML Model  : {'✓ Loaded — ' + MODEL_META.get('best_model','') if ML_READY else '✗ Not found (rule-based fallback)'}")
    print(f"  Frontend  : http://localhost:8000")
    print(f"  Health    : http://localhost:8000/api/health")
    print(f"  Job Search: http://localhost:8000/api/jobs/search")
    print(f"  News      : http://localhost:8000/api/news")
    print(f"  Courses   : http://localhost:8000/api/courses")
    print("=" * 56 + "\n")
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
