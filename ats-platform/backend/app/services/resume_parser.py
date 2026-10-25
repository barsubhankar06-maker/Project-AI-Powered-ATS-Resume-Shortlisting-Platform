"""Resume parsing service.

Two layers:
1. A deterministic heuristic parser that always runs (offline, no API needed).
2. Optional LLM enrichment that fills/refines fields and is used only when
   configured. Any field we cannot determine is marked unknown — a missing
   field is NEVER treated as evidence that a candidate lacks a qualification.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from . import llm, skill_normalization as sn

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s\-.]?)?(?:\(?\d{2,4}\)?[\s\-.]?)\d{3,4}[\s\-.]?\d{3,4})")
YEAR_RE = re.compile(r"(19|20)\d{2}")
DATE_RANGE_RE = re.compile(
    r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}|\d{4})"
    r"\s*(?:-|–|—|to)\s*"
    r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}|\d{4}|present|current|now)",
    re.IGNORECASE,
)
DEGREE_RE = re.compile(
    r"\b(b\.?tech|b\.?e\.?|bachelor|m\.?tech|m\.?e\.?|master|mba|m\.?sc|b\.?sc|"
    r"ph\.?d|doctorate|diploma|b\.?com|b\.?a\.?|bca|mca)\b",
    re.IGNORECASE,
)

SECTION_HEADINGS = {
    "summary": ["summary", "professional summary", "profile", "objective", "about"],
    "experience": ["experience", "work experience", "employment", "professional experience", "work history"],
    "education": ["education", "academics", "academic background", "qualifications"],
    "skills": ["skills", "technical skills", "core competencies", "technologies", "skill set"],
    "projects": ["projects", "personal projects", "selected projects", "academic projects"],
    "certifications": ["certifications", "certificates", "licenses", "courses"],
    "achievements": ["achievements", "awards", "honors", "accomplishments"],
    "tools": ["tools", "tools & technologies", "tooling"],
}

_MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
)}


@dataclass
class ParseResult:
    data: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
    uncertainties: list = field(default_factory=list)
    parser: str = "heuristic"


def _split_sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    sections: dict[str, list[str]] = {"_header": []}
    current = "_header"
    for line in lines:
        stripped = line.strip()
        low = stripped.lower().strip(":•-– ")
        matched = None
        if 0 < len(stripped) <= 40:
            for key, heads in SECTION_HEADINGS.items():
                if low in heads:
                    matched = key
                    break
        if matched:
            current = matched
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _parse_date(token: str) -> tuple[int, int] | None:
    token = token.strip().lower()
    if token in ("present", "current", "now"):
        now = datetime.utcnow()
        return now.year, now.month
    m = re.match(r"([a-z]+)\.?\s*(\d{4})", token)
    if m and m.group(1)[:3] in _MONTHS:
        return int(m.group(2)), _MONTHS[m.group(1)[:3]]
    m = re.match(r"(\d{4})", token)
    if m:
        return int(m.group(1)), 1
    return None


def _years_from_ranges(text: str) -> tuple[float | None, int]:
    total = 0.0
    count = 0
    for m in DATE_RANGE_RE.finditer(text):
        start = _parse_date(m.group(1))
        end = _parse_date(m.group(2))
        if start and end:
            months = (end[0] - start[0]) * 12 + (end[1] - start[1])
            if 0 < months < 600:
                total += months / 12.0
                count += 1
    if count == 0:
        return None, 0
    return round(total, 1), count


def _guess_name(header: str) -> str | None:
    for line in header.splitlines():
        s = line.strip()
        if not s or len(s) > 60:
            continue
        if EMAIL_RE.search(s) or PHONE_RE.search(s) or any(ch.isdigit() for ch in s):
            continue
        words = s.split()
        if 1 < len(words) <= 5 and all(w[0].isupper() for w in words if w):
            return s
    return None


def _bullets(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        s = line.strip(" •-–—\t*")
        if len(s) > 2:
            out.append(s)
    return out


def parse_heuristic(text: str) -> ParseResult:
    sections = _split_sections(text or "")
    header = sections.get("_header", "")
    whole = text or ""

    data: dict = {}
    conf: dict = {}
    unc: list[str] = []

    name = _guess_name(header)
    data["name"] = name
    conf["name"] = 0.8 if name else 0.0
    if not name:
        unc.append("Candidate name could not be reliably identified.")

    email_m = EMAIL_RE.search(whole)
    data["email"] = email_m.group(0) if email_m else None
    conf["email"] = 0.95 if email_m else 0.0

    phone_m = PHONE_RE.search(header or whole)
    data["phone"] = phone_m.group(0).strip() if phone_m else None
    conf["phone"] = 0.7 if phone_m else 0.0

    # Location: look for "City, ST/Country" pattern near the top.
    loc = None
    for line in (header or "").splitlines():
        m = re.search(r"\b([A-Z][a-zA-Z]+(?:[\s\-][A-Z][a-zA-Z]+)*),\s*([A-Za-z\.\s]{2,40})$", line.strip())
        if m:
            loc = m.group(0).strip()
            break
    data["location"] = loc
    conf["location"] = 0.5 if loc else 0.0
    if not loc:
        unc.append("Location not found.")

    summary = sections.get("summary", "").strip() or None
    data["summary"] = summary[:1200] if summary else None
    conf["summary"] = 0.7 if summary else 0.0

    # Skills: prefer the skills section, but mine the whole document too.
    skills_section = sections.get("skills", "")
    skills = set(sn.extract_skills_from_text(skills_section))
    skills |= set(sn.extract_skills_from_text(whole))
    data["skills"] = sorted(skills)
    conf["skills"] = 0.7 if skills else 0.0
    if not skills:
        unc.append("No recognizable skills found in the resume.")

    # Experience entries.
    exp_text = sections.get("experience", "")
    experience = []
    for m in DATE_RANGE_RE.finditer(exp_text):
        experience.append({"dates": m.group(0).strip()})
    years, ranges = _years_from_ranges(exp_text or whole)
    data["total_experience_years"] = years
    conf["total_experience_years"] = 0.6 if years is not None else 0.0
    if years is None:
        unc.append("Total years of experience could not be reliably determined.")
    else:
        data["experience_ranges_found"] = ranges

    # Experience bullets (evidence lines).
    exp_lines = [b for b in _bullets(exp_text) if len(b) > 25][:15]
    data["experience_highlights"] = exp_lines
    data["experience_text"] = exp_text[:4000]

    # Education.
    edu_text = sections.get("education", "")
    education = []
    for line in edu_text.splitlines():
        if DEGREE_RE.search(line):
            year = YEAR_RE.search(line)
            education.append({"text": line.strip()[:200], "year": year.group(0) if year else None})
    data["education"] = education
    conf["education"] = 0.7 if education else 0.0
    if not education:
        unc.append("Education details not found.")

    # Projects.
    proj_text = sections.get("projects", "")
    projects = []
    for b in _bullets(proj_text):
        if len(b) > 10:
            projects.append({"text": b[:300], "skills": sn.extract_skills_from_text(b)})
    data["projects"] = projects[:15]
    conf["projects"] = 0.6 if projects else 0.0

    # Certifications / achievements / tools.
    certs = [b for b in _bullets(sections.get("certifications", "")) if len(b) > 3][:15]
    data["certifications"] = certs
    conf["certifications"] = 0.7 if certs else 0.0
    achievements = [b for b in _bullets(sections.get("achievements", "")) if len(b) > 5][:15]
    data["achievements"] = achievements
    tools_section = sections.get("tools", "")
    data["tools"] = sorted(set(sn.extract_skills_from_text(tools_section))) if tools_section else []
    conf["tools"] = 0.6 if data["tools"] else 0.0

    # Compliance: we deliberately do NOT extract or infer age, gender, photo,
    # ethnicity, religion, disability or graduation-date-as-age proxies here.
    data["_privacy_note"] = (
        "Protected attributes (age, gender, photo, ethnicity, religion, "
        "disability) are intentionally not extracted or used in scoring."
    )

    return ParseResult(data=data, confidence=conf, uncertainties=unc, parser="heuristic")


LLM_SCHEMA_HINT = """Return JSON with exactly these keys:
{
 "name": string|null, "email": string|null, "phone": string|null, "location": string|null,
 "summary": string|null, "skills": [string],
 "experience": [{"title": string, "company": string, "start": string|null, "end": string|null, "description": string}],
 "total_experience_years": number|null,
 "education": [{"degree": string, "institution": string, "year": string|null}],
 "projects": [{"name": string, "description": string}],
 "certifications": [string], "achievements": [string], "tools": [string]
}
Use null when a field is not present. Do NOT guess. Do NOT include age, gender,
photo, ethnicity, religion or disability."""


def parse_resume(text: str, use_llm: bool | None = None) -> ParseResult:
    """Parse a resume. Deterministic first; LLM enrichment when configured."""
    base = parse_heuristic(text)
    if use_llm is None:
        use_llm = llm.settings.llm_configured
    if not use_llm or not text.strip():
        if llm.looks_like_injection(text):
            base.uncertainties.append(
                "The resume text contains phrases resembling embedded instructions; "
                "these were ignored and treated as untrusted data."
            )
        return base

    user = llm.wrap_document(text) + "\n\n" + LLM_SCHEMA_HINT
    res = llm.complete_json(llm.SAFETY_PREAMBLE, user, max_tokens=2500)
    if not res.ok or not res.data:
        base.uncertainties.append(
            f"AI enrichment unavailable ({res.error}); used the deterministic parser."
        )
        return base

    merged = dict(base.data)
    d = res.data
    for key in ["name", "email", "phone", "location", "summary", "total_experience_years"]:
        if d.get(key):
            merged[key] = d[key]
            base.confidence[key] = max(base.confidence.get(key, 0.0), 0.85)
    if d.get("skills"):
        merged["skills"] = sorted(set(base.data.get("skills", [])) | set(d["skills"]))
    for key in ["experience", "education", "projects", "certifications", "achievements", "tools"]:
        if d.get(key):
            merged[key] = d[key]
    base.data = merged
    base.parser = "hybrid"
    return base
