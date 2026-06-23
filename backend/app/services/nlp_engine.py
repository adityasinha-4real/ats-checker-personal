"""
NLP engine singleton – loads spaCy and sentence-transformers once.
Heavy models are loaded lazily on first use so startup is fast.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from loguru import logger
import numpy as np

_spacy_nlp = None
_st_model = None
_st_load_attempted = False


_spacy_available = None   # None = not yet tried; False = failed; True = loaded


def get_spacy():
    global _spacy_nlp, _spacy_available
    if _spacy_available is False:
        return None
    if _spacy_nlp is not None:
        return _spacy_nlp
    try:
        import spacy
        try:
            _spacy_nlp = spacy.load("en_core_web_sm")
        except OSError:
            _spacy_nlp = spacy.blank("en")
        _spacy_available = True
        logger.info("spaCy model loaded")
    except Exception as e:
        logger.warning(f"spaCy unavailable (will use regex fallback): {e}")
        _spacy_available = False
    return _spacy_nlp


def get_sentence_transformer():
    global _st_model, _st_load_attempted
    if _st_model is not None:
        return _st_model
    if _st_load_attempted:
        return None
    _st_load_attempted = True
    try:
        import threading
        from sentence_transformers import SentenceTransformer
        result: list = []
        error: list = []

        def _load():
            try:
                result.append(SentenceTransformer("all-MiniLM-L6-v2"))
            except Exception as e:
                error.append(e)

        thread = threading.Thread(target=_load, daemon=True)
        thread.start()
        thread.join(timeout=30)  # 30s wait; model already cached after first download

        if result:
            _st_model = result[0]
            _st_load_attempted = False  # allow retry if we got the model
            logger.info("SentenceTransformer model loaded")
        elif error:
            logger.error(f"Failed to load SentenceTransformer: {error[0]}")
        else:
            logger.warning("SentenceTransformer timed out — semantic scoring disabled until restart")
    except Exception as e:
        logger.error(f"SentenceTransformer init error: {e}")
    return _st_model


TECH_SKILLS: dict[str, list[str]] = {
    "languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "c", "go", "golang",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
        "haskell", "lua", "dart", "elixir", "clojure", "f#", "vb.net", "cobol",
        "fortran", "assembly", "bash", "shell", "powershell",
    ],
    "frontend": [
        "react", "react.js", "reactjs", "next.js", "nextjs", "vue", "vue.js", "vuejs",
        "angular", "svelte", "html", "css", "sass", "scss", "less", "tailwind",
        "tailwindcss", "bootstrap", "material ui", "mui", "chakra ui", "antd",
        "styled-components", "emotion", "webpack", "vite", "parcel", "rollup",
        "jquery", "backbone", "ember",
    ],
    "backend": [
        "node.js", "nodejs", "express", "django", "flask", "fastapi", "spring",
        "spring boot", "rails", "ruby on rails", "laravel", "asp.net", "nestjs",
        "hapi", "koa", "gin", "echo", "actix", "rocket", "phoenix", "fiber",
    ],
    "mobile": [
        "react native", "flutter", "ios", "android", "swift", "kotlin", "xamarin",
        "ionic", "capacitor", "expo",
    ],
    "databases": [
        "sql", "mysql", "postgresql", "postgres", "sqlite", "mongodb", "redis",
        "elasticsearch", "cassandra", "dynamodb", "oracle", "sql server", "mssql",
        "mariadb", "neo4j", "firebase", "supabase", "couchdb", "influxdb",
        "clickhouse", "snowflake", "bigquery", "redshift",
    ],
    "cloud": [
        "aws", "amazon web services", "azure", "gcp", "google cloud", "heroku",
        "digital ocean", "vercel", "netlify", "cloudflare", "linode", "fly.io",
        "lambda", "ec2", "s3", "rds", "eks", "ecs", "fargate", "sagemaker",
    ],
    "devops": [
        "docker", "kubernetes", "k8s", "jenkins", "github actions", "gitlab ci",
        "circleci", "travis ci", "terraform", "ansible", "puppet", "chef",
        "nginx", "apache", "caddy", "prometheus", "grafana", "datadog", "splunk",
        "elk stack", "logstash", "kibana", "helm", "istio",
    ],
    "ml_ai": [
        "machine learning", "deep learning", "neural networks", "nlp",
        "natural language processing", "computer vision", "tensorflow", "pytorch",
        "keras", "scikit-learn", "sklearn", "xgboost", "lightgbm", "catboost",
        "hugging face", "transformers", "bert", "gpt", "llm", "langchain",
        "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
        "jupyter", "opencv", "pillow",
    ],
    "tools": [
        "git", "github", "gitlab", "bitbucket", "jira", "confluence", "slack",
        "postman", "swagger", "openapi", "vs code", "intellij", "vim", "neovim",
        "linux", "unix", "macos", "windows", "bash", "zsh",
    ],
    "concepts": [
        "rest", "restful", "graphql", "grpc", "websocket", "microservices",
        "api", "ci/cd", "devops", "agile", "scrum", "kanban", "tdd",
        "bdd", "oop", "functional programming", "design patterns", "solid",
        "system design", "distributed systems", "concurrency", "multithreading",
        "data structures", "algorithms", "version control", "testing",
    ],
    "data_engineering": [
        "apache spark", "spark", "hadoop", "kafka", "airflow", "dbt",
        "etl", "data pipeline", "data warehouse", "data lake", "flink",
        "beam", "databricks",
    ],
    "security": [
        "cybersecurity", "penetration testing", "oauth", "jwt", "ssl", "tls",
        "encryption", "authentication", "authorization", "owasp",
    ],
}

ALL_SKILLS: list[str] = []
for skills_list in TECH_SKILLS.values():
    ALL_SKILLS.extend(skills_list)
ALL_SKILLS = list(set(ALL_SKILLS))

SKILL_ALIASES: dict[str, str] = {
    # Language shorthands
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "rb": "ruby",
    "cs": "c#",
    "cpp": "c++",
    "golang": "go",
    # Framework / lib shorthands
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "nextjs": "next.js",
    "nestjs": "nestjs",
    "node": "node.js",
    "nodejs": "node.js",
    "express.js": "express",
    "expressjs": "express",
    "ng": "angular",
    "rb on rails": "ruby on rails",
    "ror": "ruby on rails",
    # Database shorthands / variants
    "pg": "postgresql",
    "psql": "postgresql",
    "postgres": "postgresql",
    "mdb": "mongodb",
    "mongo": "mongodb",
    "mssql": "sql server",
    "ms sql": "sql server",
    "elastic": "elasticsearch",
    "dynamo": "dynamodb",
    # Cloud shorthands
    "aws": "aws",
    "gcp": "gcp",
    "azure": "azure",
    "google cloud": "gcp",
    "amazon web services": "aws",
    # DevOps / infra
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "tf": "terraform",
    "gh actions": "github actions",
    "ci cd": "ci/cd",
    "cicd": "ci/cd",
    # ML / AI
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "ai": "machine learning",
    "llms": "llm",
    "hf": "hugging face",
    "sklearn": "scikit-learn",
    "xgb": "xgboost",
    "lgbm": "lightgbm",
    "tf": "tensorflow",
    "pt": "pytorch",
    # Concepts
    "oop": "object oriented programming",
    "fp": "functional programming",
    "api": "api",
    "rest api": "rest",
    "restful": "rest",
    "restful api": "rest",
    "microservice": "microservices",
    "micro-services": "microservices",
    "ui": "user interface",
    "ux": "user experience",
    "db": "databases",
    "dbs": "databases",
    "vcs": "version control",
}

EDUCATION_LEVELS = {
    "phd": 5, "ph.d": 5, "doctorate": 5, "doctoral": 5,
    "master": 4, "masters": 4, "msc": 4, "ms": 4, "mba": 4, "m.s": 4, "m.e": 4,
    "bachelor": 3, "bachelors": 3, "bsc": 3, "bs": 3, "be": 3, "b.s": 3, "b.e": 3, "b.tech": 3,
    "associate": 2, "diploma": 1,
}


def normalize_skill(skill: str) -> str:
    s = skill.lower().strip()
    return SKILL_ALIASES.get(s, s)


def extract_skills_from_text(text: str) -> list[str]:
    text_lower = text.lower()
    found_skills: set[str] = set()

    for skill in ALL_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found_skills.add(skill)

    for alias, canonical in SKILL_ALIASES.items():
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, text_lower):
            found_skills.add(canonical)

    return sorted(found_skills)


_ENGLISH_STOPWORDS = frozenset(
    "a an the and or but in on at to for of is are was were be been being "
    "have has had do does did will would could should may might shall can "
    "not no nor so yet both either neither than though although because "
    "since when where while who which what that this these those it its "
    "he she we they i you me him her us them my your his our their "
    "with by from up about into through during before after above below "
    "between out over under again further then once here there all any "
    "each few more most other some such only own same than very just "
    "experience work team company position role year strong good skills "
    "ability knowledge understanding working familiarity using".split()
)


def _tokenize(text: str) -> list[str]:
    """Simple tokeniser: lowercase alphanum tokens of length >= 2."""
    return [t for t in re.findall(r"[a-z0-9][a-z0-9\+\#\.]*", text.lower())
            if len(t) >= 2 and t not in _ENGLISH_STOPWORDS]


def _build_ngrams(tokens: list[str], max_n: int = 3) -> list[str]:
    ngrams: list[str] = list(tokens)
    for n in range(2, max_n + 1):
        ngrams += [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
    return ngrams


def extract_keywords_tfidf(text: str, top_n: int = 50) -> list[str]:
    """Extract important keywords from text using a pure-Python TF-IDF."""
    try:
        sentences = [s.strip() for s in re.split(r"[.\n]", text) if len(s.strip()) > 10]
        if not sentences:
            sentences = [text]

        # Build document-term matrix using ngrams (1-3)
        docs: list[list[str]] = [_build_ngrams(_tokenize(s)) for s in sentences]
        all_terms_set: set[str] = set(t for d in docs for t in d)

        N = len(docs)
        idf: dict[str, float] = {}
        for term in all_terms_set:
            df = sum(1 for d in docs if term in d)
            idf[term] = math.log((N + 1) / (df + 1)) + 1.0

        scores: Counter = Counter()
        for doc in docs:
            tf = Counter(doc)
            total = max(len(doc), 1)
            for term, cnt in tf.items():
                scores[term] += (cnt / total) * idf.get(term, 1.0)

        return [t for t, _ in scores.most_common(top_n)]
    except Exception as e:
        logger.warning(f"TF-IDF extraction failed: {e}")
        return []


def extract_keywords_spacy(text: str) -> list[str]:
    """Extract keywords using spaCy NLP. Returns [] gracefully if spaCy unavailable."""
    nlp = get_spacy()
    if nlp is None:
        # Regex fallback: extract capitalized / CamelCase words as proxy for nouns
        tokens = re.findall(r"\b[A-Z][a-z]{2,}\b|\b[a-z]{4,}\b", text)
        return list({t.lower() for t in tokens if t.lower() not in _ENGLISH_STOPWORDS})[:40]

    doc = nlp(text[:100000])
    keywords: list[str] = []

    for token in doc:
        if (
            not token.is_stop
            and not token.is_punct
            and not token.is_space
            and len(token.text) > 2
            and token.pos_ in ("NOUN", "PROPN", "ADJ")
        ):
            keywords.append(token.lemma_.lower())

    for chunk in doc.noun_chunks:
        if len(chunk.text.split()) <= 3:
            keywords.append(chunk.text.lower().strip())

    return list(set(keywords))


def extract_jd_keywords(jd_text: str) -> list[str]:
    """Combined keyword extraction from job description."""
    skills = extract_skills_from_text(jd_text)
    tfidf_kws = extract_keywords_tfidf(jd_text, top_n=60)
    spacy_kws = extract_keywords_spacy(jd_text)

    combined: set[str] = set()
    combined.update(skills)
    combined.update(tfidf_kws[:40])
    combined.update(spacy_kws[:30])

    stop_words = {"experience", "work", "team", "company", "position", "role", "year", "strong", "good"}
    combined = {kw for kw in combined if kw not in stop_words and len(kw) > 2}

    return sorted(combined)


def extract_education_level(text: str) -> int:
    """Return numeric education level (0-5)."""
    text_lower = text.lower()
    max_level = 0
    for degree, level in EDUCATION_LEVELS.items():
        if degree in text_lower:
            max_level = max(max_level, level)
    return max_level


def compute_semantic_similarity(text1: str, text2: str) -> float:
    """Compute cosine similarity between two texts using sentence-transformers."""
    model = get_sentence_transformer()
    if model is None:
        return 50.0

    def chunk_text(text: str, max_chars: int = 2000) -> list[str]:
        chunks = []
        for i in range(0, len(text), max_chars):
            chunk = text[i:i + max_chars].strip()
            if chunk:
                chunks.append(chunk)
        return chunks or [text[:max_chars]]

    try:
        chunks1 = chunk_text(text1)
        chunks2 = chunk_text(text2)

        embs1 = model.encode(chunks1, show_progress_bar=False)
        embs2 = model.encode(chunks2, show_progress_bar=False)

        avg1 = np.mean(embs1, axis=0)
        avg2 = np.mean(embs2, axis=0)

        # Pure-numpy cosine similarity (avoids sklearn/scipy dependency)
        denom = float(np.linalg.norm(avg1) * np.linalg.norm(avg2))
        sim = float(np.dot(avg1, avg2)) / (denom + 1e-10)
        return float(sim * 100)
    except Exception as e:
        logger.error(f"Semantic similarity failed: {e}")
        return 50.0
