"""Skill normalization and a small transferability graph.

Maps surface forms ("JS", "node.js", "React.js") to a canonical key so that
required-skill matching is not defeated by spelling. Also exposes related-skill
lookups used to flag *potentially transferable* skills rather than silently
counting them as matches.
"""
from __future__ import annotations

import re

# canonical -> aliases
_ALIASES: dict[str, list[str]] = {
    "javascript": ["js", "ecmascript", "es6"],
    "typescript": ["ts"],
    "python": ["py", "python3"],
    "java": ["java se", "java 8", "jdk"],
    "c++": ["cpp", "c plus plus"],
    "c#": ["csharp", "dotnet c#"],
    "golang": ["go"],
    "react": ["react.js", "reactjs"],
    "next.js": ["nextjs", "next js"],
    "vue": ["vue.js", "vuejs"],
    "angular": ["angularjs", "angular.js"],
    "node.js": ["nodejs", "node js", "node"],
    "express": ["express.js", "expressjs"],
    "fastapi": ["fast api"],
    "django": [],
    "flask": [],
    "spring": ["spring boot", "springboot"],
    "rest": ["rest api", "restful", "rest apis"],
    "graphql": ["gql"],
    "sql": ["ansi sql"],
    "postgresql": ["postgres", "psql"],
    "mysql": ["mariadb"],
    "mongodb": ["mongo"],
    "redis": [],
    "sqlite": [],
    "html": ["html5"],
    "css": ["css3"],
    "tailwind": ["tailwindcss", "tailwind css"],
    "sass": ["scss"],
    "docker": ["containerization", "containers"],
    "kubernetes": ["k8s"],
    "aws": ["amazon web services"],
    "azure": ["microsoft azure"],
    "gcp": ["google cloud", "google cloud platform"],
    "terraform": ["iac", "infrastructure as code"],
    "ci/cd": ["cicd", "ci cd", "continuous integration"],
    "git": ["github", "gitlab", "version control"],
    "linux": ["unix", "bash", "shell"],
    "pandas": [],
    "numpy": [],
    "pytorch": ["torch"],
    "tensorflow": ["tf"],
    "scikit-learn": ["sklearn", "scikit learn"],
    "machine learning": ["ml", "statistical learning"],
    "deep learning": ["neural networks", "dl"],
    "nlp": ["natural language processing"],
    "llm": ["large language models", "gpt", "genai", "generative ai"],
    "data analysis": ["analytics", "data analytics"],
    "data engineering": ["etl", "elt", "data pipelines"],
    "airflow": ["apache airflow"],
    "spark": ["apache spark", "pyspark"],
    "kafka": ["apache kafka"],
    "tableau": [],
    "power bi": ["powerbi"],
    "excel": ["microsoft excel", "spreadsheets"],
    "product management": ["product owner", "pm"],
    "project management": ["pmp", "program management"],
    "agile": ["scrum", "kanban", "safe"],
    "communication": ["verbal communication", "written communication"],
    "leadership": ["team leadership", "people management"],
    "stakeholder management": ["stakeholder engagement"],
    "figma": [],
    "ui/ux": ["ui design", "ux design", "user experience", "user interface"],
    "salesforce": ["sfdc"],
    "hubspot": [],
    "seo": ["search engine optimization"],
    "content marketing": ["content strategy"],
    "accounting": ["bookkeeping"],
    "financial modeling": ["financial analysis"],
    "recruiting": ["talent acquisition", "sourcing"],
    "customer success": ["customer support", "customer service"],
    "testing": ["qa", "quality assurance", "unit testing", "pytest", "jest"],
    "microservices": ["service oriented architecture", "soa"],
    "graphql api": [],
    "webpack": ["bundler", "vite"],
    "celery": ["task queue", "background jobs"],
    "ceramics": ["ceramic engineering", "materials science", "refractories"],
    "materials science": ["materials engineering", "metallurgy"],
    "quality control": ["qc", "six sigma", "lean"],
    "cad": ["solidworks", "autocad", "fusion 360"],
    "process engineering": ["process design", "manufacturing processes"],
    "heat treatment": ["sintering", "kiln", "furnace operation"],
}

# canonical -> related canonical skills (transferable, not equivalent)
_TRANSFERABLE: dict[str, list[str]] = {
    "react": ["vue", "angular", "javascript", "typescript"],
    "vue": ["react", "angular", "javascript"],
    "angular": ["react", "vue", "typescript"],
    "next.js": ["react", "node.js"],
    "node.js": ["javascript", "express", "deno"],
    "express": ["node.js", "fastapi", "flask", "django"],
    "fastapi": ["flask", "django", "express", "python"],
    "django": ["flask", "fastapi", "python"],
    "flask": ["django", "fastapi", "python"],
    "postgresql": ["mysql", "sql", "sqlite"],
    "mysql": ["postgresql", "sql", "sqlite"],
    "mongodb": ["redis", "postgresql"],
    "docker": ["kubernetes", "containers"],
    "kubernetes": ["docker"],
    "aws": ["gcp", "azure"],
    "gcp": ["aws", "azure"],
    "azure": ["aws", "gcp"],
    "pytorch": ["tensorflow", "machine learning"],
    "tensorflow": ["pytorch", "machine learning"],
    "spark": ["data engineering", "kafka"],
    "kafka": ["spark", "data engineering"],
    "tableau": ["power bi", "data analysis"],
    "power bi": ["tableau", "data analysis"],
    "javascript": ["typescript"],
    "typescript": ["javascript"],
    "machine learning": ["deep learning", "data analysis"],
    "ceramics": ["materials science", "process engineering"],
    "materials science": ["ceramics", "process engineering"],
    "process engineering": ["quality control", "materials science"],
}

_ALIAS_TO_CANON: dict[str, str] = {}
for canon, aliases in _ALIASES.items():
    _ALIAS_TO_CANON[canon] = canon
    for a in aliases:
        _ALIAS_TO_CANON[a] = canon

_TOKEN = re.compile(r"[a-zA-Z][a-zA-Z0-9+#./\- ]{1,40}")

# A compact canonical vocabulary used to mine free text for skills.
KNOWN_SKILLS = sorted(_ALIASES.keys())


def normalize(skill: str) -> str:
    """Return a canonical skill key for a surface form."""
    if not skill:
        return ""
    s = skill.strip().lower()
    s = re.sub(r"\s+", " ", s)
    if s in _ALIAS_TO_CANON:
        return _ALIAS_TO_CANON[s]
    # try trimming trailing punctuation / common suffixes
    s2 = s.strip(" .,;:")
    if s2 in _ALIAS_TO_CANON:
        return _ALIAS_TO_CANON[s2]
    return s


def related(skill: str) -> list[str]:
    canon = normalize(skill)
    return _TRANSFERABLE.get(canon, [])


def is_related(a: str, b: str) -> bool:
    ca, cb = normalize(a), normalize(b)
    if ca == cb:
        return True
    return cb in _TRANSFERABLE.get(ca, []) or ca in _TRANSFERABLE.get(cb, [])


def extract_skills_from_text(text: str, vocabulary: list[str] | None = None) -> list[str]:
    """Mine canonical skills present in free text.

    Word-boundary aware so "go" does not match inside "algorithm" and "react"
    does not match inside "reaction".
    """
    if not text:
        return []
    low = " " + text.lower() + " "
    found: set[str] = set()
    vocab = vocabulary or KNOWN_SKILLS
    for canon in vocab:
        forms = [canon] + _ALIASES.get(canon, [])
        for form in forms:
            pattern = r"(?<![a-z0-9])" + re.escape(form) + r"(?![a-z0-9])"
            if re.search(pattern, low):
                found.add(canon)
                break
    return sorted(found)
