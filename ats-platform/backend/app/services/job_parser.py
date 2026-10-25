"""Job-description parsing service.

Turns a free-text job description into structured requirements (required
skills, preferred skills, responsibilities, qualifications, certifications,
education) plus suggested experience range. Heuristic first; optional LLM
enrichment. Recruiters review and edit the result before screening.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import llm, skill_normalization as sn

REQUIRED_HEADS = ["required", "requirements", "must have", "must-have", "essential", "minimum qualifications"]
PREFERRED_HEADS = ["preferred", "nice to have", "nice-to-have", "good to have", "bonus", "desirable"]
RESP_HEADS = ["responsibilities", "what you will do", "what you'll do", "the role", "duties", "key responsibilities"]
QUAL_HEADS = ["qualifications", "education", "experience"]
CERT_HEADS = ["certifications", "certificates", "licenses"]
EXP_RE = re.compile(r"(\d{1,2})\s*(?:\+|-|to|–|—)?\s*(\d{1,2})?\s*\+?\s*years?", re.IGNORECASE)
DEGREE_RE = re.compile(
    r"\b(b\.?tech|b\.?e\.?|bachelor'?s?|m\.?tech|master'?s?|mba|m\.?sc|b\.?sc|ph\.?d|diploma|graduate|degree)\b",
    re.IGNORECASE,
)
CERT_RE = re.compile(
    r"\b(aws certified|azure|gcp|pmp|cissp|cpa|scrum master|certified|certification|six sigma|ccna)\b",
    re.IGNORECASE,
)


@dataclass
class JdResult:
    requirements: list = field(default_factory=list)
    suggested: dict = field(default_factory=dict)
    method: str = "heuristic"


def _lines(text: str) -> list[str]:
    return [l.strip(" •-–—\t*") for l in (text or "").splitlines() if l.strip()]


def _sectionize(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"_all": []}
    current = "_all"
    for raw in (text or "").splitlines():
        s = raw.strip()
        low = s.lower().strip(":•-– ")
        matched = None
        if 0 < len(s) <= 50:
            for key, heads in (
                ("required", REQUIRED_HEADS),
                ("preferred", PREFERRED_HEADS),
                ("responsibilities", RESP_HEADS),
                ("qualifications", QUAL_HEADS),
                ("certifications", CERT_HEADS),
            ):
                if any(h in low for h in heads):
                    matched = key
                    break
        if matched:
            current = matched
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(s)
            sections["_all"].append(s)
    return sections


def parse_heuristic(description: str, title: str = "") -> JdResult:
    sections = _sectionize(description)
    req_text = "\n".join(sections.get("required", []))
    pref_text = "\n".join(sections.get("preferred", []))
    resp_text = "\n".join(sections.get("responsibilities", []))
    qual_text = "\n".join(sections.get("qualifications", []))
    cert_text = "\n".join(sections.get("certifications", []))

    # If no explicit "required" section, treat the whole text as the source.
    required_source = req_text or "\n".join(sections["_all"])
    preferred_source = pref_text

    req_skills = sn.extract_skills_from_text(required_source)
    pref_skills = [s for s in sn.extract_skills_from_text(preferred_source) if s not in req_skills]

    requirements: list[dict] = []
    for s in req_skills:
        requirements.append(
            {"kind": "required_skill", "text": s, "normalized_skill": s, "is_hard": False, "source": "ai"}
        )
    for s in pref_skills:
        requirements.append(
            {"kind": "preferred_skill", "text": s, "normalized_skill": s, "is_hard": False, "source": "ai"}
        )

    for b in _lines(resp_text)[:12]:
        if len(b) > 12:
            requirements.append(
                {"kind": "responsibility", "text": b[:300], "normalized_skill": "", "is_hard": False, "source": "ai"}
            )
    for b in _lines(qual_text)[:8]:
        if DEGREE_RE.search(b) or len(b) > 20:
            requirements.append(
                {"kind": "qualification", "text": b[:300], "normalized_skill": "", "is_hard": False, "source": "ai"}
            )
    for b in _lines(cert_text)[:8]:
        if CERT_RE.search(b) or len(b) > 3:
            requirements.append(
                {"kind": "certification", "text": b[:200], "normalized_skill": "", "is_hard": False, "source": "ai"}
            )
    # Education line from the whole description if present.
    for line in _lines(description):
        if DEGREE_RE.search(line) and len(line) < 200:
            requirements.append(
                {"kind": "education", "text": line.strip(), "normalized_skill": "", "is_hard": False, "source": "ai"}
            )
            break

    # Suggested experience range.
    exp_min = exp_max = None
    for m in EXP_RE.finditer(description):
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else None
        if exp_min is None or lo < exp_min:
            exp_min = lo
        if hi and (exp_max is None or hi > exp_max):
            exp_max = hi
    suggested = {
        "title": title,
        "experience_min": exp_min,
        "experience_max": exp_max,
        "required_skills": req_skills,
        "preferred_skills": pref_skills,
    }
    return JdResult(requirements=requirements, suggested=suggested, method="heuristic")


JD_SCHEMA_HINT = """Return JSON with this shape:
{
 "required_skills": [string], "preferred_skills": [string],
 "responsibilities": [string], "qualifications": [string],
 "certifications": [string], "education": [string],
 "experience_min": number|null, "experience_max": number|null
}
Only include skills explicitly evidenced by the description. Do not invent
requirements. Return valid JSON only."""


def analyze_jd(description: str, title: str = "", use_llm: bool | None = None) -> JdResult:
    base = parse_heuristic(description, title)
    if use_llm is None:
        use_llm = llm.settings.llm_configured
    if not use_llm or not description.strip():
        return base

    user = llm.wrap_document(description) + "\n\n" + JD_SCHEMA_HINT
    res = llm.complete_json(llm.SAFETY_PREAMBLE, user, max_tokens=2000)
    if not res.ok or not res.data:
        base.suggested["ai_error"] = res.error
        return base

    d = res.data
    requirements: list[dict] = []
    for s in d.get("required_skills", []):
        requirements.append({"kind": "required_skill", "text": s, "normalized_skill": sn.normalize(s), "is_hard": False, "source": "ai"})
    for s in d.get("preferred_skills", []):
        requirements.append({"kind": "preferred_skill", "text": s, "normalized_skill": sn.normalize(s), "is_hard": False, "source": "ai"})
    for s in d.get("responsibilities", []):
        requirements.append({"kind": "responsibility", "text": s, "normalized_skill": "", "is_hard": False, "source": "ai"})
    for s in d.get("qualifications", []):
        requirements.append({"kind": "qualification", "text": s, "normalized_skill": "", "is_hard": False, "source": "ai"})
    for s in d.get("certifications", []):
        requirements.append({"kind": "certification", "text": s, "normalized_skill": "", "is_hard": False, "source": "ai"})
    for s in d.get("education", []):
        requirements.append({"kind": "education", "text": s, "normalized_skill": "", "is_hard": False, "source": "ai"})

    suggested = dict(base.suggested)
    suggested["experience_min"] = d.get("experience_min", base.suggested.get("experience_min"))
    suggested["experience_max"] = d.get("experience_max", base.suggested.get("experience_max"))
    suggested["required_skills"] = d.get("required_skills", base.suggested.get("required_skills"))
    suggested["preferred_skills"] = d.get("preferred_skills", base.suggested.get("preferred_skills"))
    return JdResult(requirements=requirements or base.requirements, suggested=suggested, method="ai")
