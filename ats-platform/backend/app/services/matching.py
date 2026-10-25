"""Resume-to-job matching, scoring and explanation service.

Deterministic, transparent scoring that always works offline, optionally
refined by an LLM. The score is DECISION SUPPORT, never a probability of being
hired, and never an automatic rejection on its own.

Score components (weights configurable, must total 100):
  required skills        40
  experience/responsib.  25
  preferred skills       15
  projects/achievements  10
  qualifications/certs   10

Protected attributes (name, photo, gender, age, ethnicity, religion,
disability, graduation-date-as-age) are never read or used here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import llm, skill_normalization as sn

DEFAULT_WEIGHTS = {
    "required_skills": 40,
    "experience": 25,
    "preferred_skills": 15,
    "projects": 10,
    "qualifications": 10,
}

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "at",
    "by", "from", "as", "is", "are", "be", "will", "you", "we", "our", "your",
    "that", "this", "it", "using", "use", "work", "working", "team", "teams",
    "experience", "years", "year", "strong", "good", "ability", "etc", "plus",
    "role", "job", "candidate", "must", "should", "have", "has", "including",
}

_WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9+#./\-]+")


def validate_weights(weights: dict | None) -> tuple[dict, str]:
    """Return (weights, error). Ensures keys are known and total == 100."""
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        for k, v in weights.items():
            if k not in DEFAULT_WEIGHTS:
                return w, f"Unknown weight key '{k}'"
            try:
                w[k] = float(v)
            except (TypeError, ValueError):
                return w, f"Weight '{k}' must be a number"
    if any(v < 0 for v in w.values()):
        return w, "Weights cannot be negative"
    total = round(sum(w.values()), 4)
    if abs(total - 100) > 0.01:
        return w, f"Weights must total 100 (currently {total:g})"
    return w, ""


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _WORD.findall(text or "") if t.lower() not in STOPWORDS}


def _cosine(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / ((len(a) ** 0.5) * (len(b) ** 0.5))


@dataclass
class MatchOutcome:
    total_score: float = 0.0
    breakdown: dict = field(default_factory=dict)
    matched: list = field(default_factory=list)
    partial: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    transferable: list = field(default_factory=list)
    uncertainties: list = field(default_factory=list)
    method: str = "deterministic"
    required_coverage: float = 0.0


def _skill_status(required: list[str], resume_skills: set[str]) -> tuple[list, list, list, list]:
    matched, partial, missing, transferable = [], [], [], []
    for skill in required:
        canon = sn.normalize(skill)
        if canon in resume_skills:
            matched.append(skill)
        else:
            rel = [r for r in sn.related(canon) if r in resume_skills]
            if rel:
                partial.append({"skill": skill, "via": rel})
                transferable.extend(rel)
            else:
                missing.append(skill)
    return matched, partial, missing, transferable


def _responsibility_coverage(resp_texts: list[str], corpus: str, corpus_tokens: set[str]) -> tuple[float, list, list, list]:
    matched, partial, missing = [], [], []
    if not resp_texts:
        return 0.0, matched, partial, missing
    total = 0.0
    for r in resp_texts:
        sim = _cosine(_tokens(r), corpus_tokens)
        if sim >= 0.34:
            matched.append({"responsibility": r, "similarity": round(sim, 2)})
            total += 1.0
        elif sim >= 0.18:
            partial.append({"responsibility": r, "similarity": round(sim, 2)})
            total += 0.5
        else:
            missing.append(r)
    return (total / len(resp_texts)) * 100.0, matched, partial, missing


def _years_fit(resume_years: float | None, lo: float, hi: float) -> tuple[float | None, str]:
    if resume_years is None:
        return None, "Experience duration could not be reliably extracted from the resume."
    if lo and resume_years < lo:
        if lo > 0:
            return max(0.0, (resume_years / lo) * 100.0), f"{resume_years}y is below the requested minimum of {lo}y."
        return 0.0, ""
    if hi and resume_years > hi * 1.6:
        return 80.0, f"{resume_years}y is well above the requested range ({lo:g}-{hi:g}y)."
    return 100.0, ""


def _evidence_lines(data: dict, needles: set[str], limit: int = 6) -> list[dict]:
    lines: list[dict] = []
    pools = list(data.get("experience_highlights", []) or [])
    pools += [p.get("text", "") for p in (data.get("projects", []) or [])]
    pools += list(data.get("achievements", []) or [])
    for line in pools:
        toks = _tokens(line)
        overlap = toks & needles
        if overlap:
            lines.append({"text": line[:280], "matches": sorted(overlap)[:5]})
        if len(lines) >= limit:
            break
    return lines


def match_resume_to_job(
    *,
    resume_data: dict,
    requirements: list[dict],
    job: dict,
    weights: dict | None = None,
    use_llm: bool | None = None,
) -> MatchOutcome:
    """Compute an explainable match outcome.

    ``requirements`` is a list of {kind, text, normalized_skill}. ``job`` is a
    dict with at least description/responsibilities/experience_min/max.
    """
    w, err = validate_weights(weights)
    out = MatchOutcome(breakdown={"weights": w, "weights_error": err, "components": {}})

    resume_skills = set(sn.normalize(s) for s in (resume_data.get("skills") or []))
    # Also mine skills from experience/projects text for coverage.
    corpus_parts = [
        resume_data.get("summary") or "",
        resume_data.get("experience_text") or "",
    ]
    for e in resume_data.get("experience_highlights", []) or []:
        corpus_parts.append(e if isinstance(e, str) else str(e))
    for p in resume_data.get("projects", []) or []:
        corpus_parts.append(p.get("text", "") if isinstance(p, dict) else str(p))
    corpus = "\n".join(corpus_parts)
    corpus_tokens = _tokens(corpus)
    resume_skills |= set(sn.extract_skills_from_text(corpus))

    req_skills = [r["text"] for r in requirements if r["kind"] == "required_skill"]
    pref_skills = [r["text"] for r in requirements if r["kind"] == "preferred_skill"]
    resp_texts = [r["text"] for r in requirements if r["kind"] == "responsibility"]
    qual_texts = [r["text"] for r in requirements if r["kind"] in ("qualification", "education")]
    cert_texts = [r["text"] for r in requirements if r["kind"] == "certification"]

    components: dict = {}
    active: dict[str, float] = {}

    # 1) Required skills
    if req_skills:
        matched, partial, missing, transferable = _skill_status(req_skills, resume_skills)
        score = (len(matched) + 0.5 * len(partial)) / len(req_skills) * 100.0
        active["required_skills"] = score
        out.matched = matched
        out.partial = partial
        out.missing = missing
        out.transferable = sorted(set(transferable))
        out.required_coverage = round((len(matched) + 0.5 * len(partial)) / len(req_skills) * 100.0, 1)
        components["required_skills"] = {
            "score": round(score, 1),
            "matched": matched,
            "partial": partial,
            "missing": missing,
        }
    else:
        out.uncertainties.append("The job lists no explicit required skills.")

    # 2) Preferred skills
    if pref_skills:
        matched_p, partial_p, missing_p, trans_p = _skill_status(pref_skills, resume_skills)
        score = (len(matched_p) + 0.5 * len(partial_p)) / len(pref_skills) * 100.0
        active["preferred_skills"] = score
        components["preferred_skills"] = {
            "score": round(score, 1),
            "matched": matched_p,
            "partial": partial_p,
            "missing": missing_p,
        }
        out.transferable = sorted(set(out.transferable) | set(trans_p))

    # 3) Experience / responsibilities
    resp_score, r_match, r_part, r_miss = _responsibility_coverage(resp_texts, corpus, corpus_tokens)
    lo = float(job.get("experience_min") or 0)
    hi = float(job.get("experience_max") or 0)
    years_fit, years_note = _years_fit(resume_data.get("total_experience_years"), lo, hi)
    if years_note:
        out.uncertainties.append(years_note)
    if resp_texts or (lo or hi):
        if years_fit is None:
            exp_score = resp_score if resp_texts else 0.0
        elif resp_texts:
            exp_score = 0.6 * resp_score + 0.4 * years_fit
        else:
            exp_score = years_fit
        active["experience"] = exp_score
        components["experience"] = {
            "score": round(exp_score, 1),
            "responsibilities_matched": r_match,
            "responsibilities_partial": r_part,
            "responsibilities_missing": r_miss,
            "years_fit": None if years_fit is None else round(years_fit, 1),
            "resume_years": resume_data.get("total_experience_years"),
            "requested_range": [lo, hi],
        }

    # 4) Projects / achievements
    proj = resume_data.get("projects") or []
    relevant_needles = set(sn.normalize(s) for s in (req_skills + pref_skills))
    relevant_projects = []
    for p in proj:
        toks = _tokens(p.get("text", "") if isinstance(p, dict) else str(p))
        pskills = set(sn.normalize(s) for s in (p.get("skills", []) if isinstance(p, dict) else []))
        if (toks & corpus_tokens and (pskills & relevant_needles)) or (pskills & relevant_needles):
            relevant_projects.append(p)
    achievements = resume_data.get("achievements") or []
    if proj or achievements:
        proj_score = min(100.0, (len(relevant_projects) / 2.0) * 100.0)
        if achievements and len(achievements) >= 2:
            proj_score = min(100.0, proj_score + 15.0)
        active["projects"] = proj_score
        components["projects"] = {
            "score": round(proj_score, 1),
            "relevant_projects": [p.get("text", "")[:200] if isinstance(p, dict) else str(p)[:200] for p in relevant_projects][:5],
            "achievements_count": len(achievements),
        }

    # 5) Qualifications / certifications
    edu = resume_data.get("education") or []
    certs = resume_data.get("certifications") or []
    edu_text = " ".join(
        (e.get("text", "") if isinstance(e, dict) else str(e)) for e in edu
    ).lower()
    cert_text_resume = " ".join(str(c) for c in certs).lower()
    checks = []
    for q in qual_texts:
        qlow = q.lower()
        hit = any(w in edu_text for w in re.findall(r"[a-z]+", qlow) if len(w) > 4)
        checks.append(1.0 if hit else 0.0)
    for c in cert_texts:
        clow = c.lower()
        hit = any(w in cert_text_resume or w in cert_text_resume for w in re.findall(r"[a-z]+", clow) if len(w) > 3)
        checks.append(1.0 if hit else 0.0)
    if checks:
        q_score = sum(checks) / len(checks) * 100.0
        active["qualifications"] = q_score
        components["qualifications"] = {
            "score": round(q_score, 1),
            "education_found": bool(edu),
            "certifications_found": certs[:5],
            "checked": len(checks),
        }
        if not edu and qual_texts:
            out.uncertainties.append(
                "No education details were found; qualifications are marked unverified, not missing."
            )

    # Weighted total with renormalization over components that actually apply.
    if active:
        total_weight = sum(w[k] for k in active)
        total = sum(active[k] * w[k] for k in active) / total_weight if total_weight else 0.0
    else:
        total = 0.0
    out.total_score = round(total, 1)
    for k, score in active.items():
        components[k]["weight"] = w[k]
        components[k]["contribution"] = round(score * w[k] / (sum(w[x] for x in active) or 1), 1)
    out.breakdown["components"] = components
    out.breakdown["applied_weights"] = {k: w[k] for k in active}
    out.breakdown["note"] = (
        "Score is decision support only and is not a probability of hiring success. "
        "Weights are renormalized across the components that apply to this job."
    )

    # Supporting evidence.
    needles = set(sn.normalize(s) for s in (req_skills + pref_skills))
    out.evidence = _evidence_lines(resume_data, needles)

    # Carry parsing uncertainties through.
    for u in resume_data.get("_uncertainties", []) or []:
        out.uncertainties.append(u)

    # Optional LLM refinement of responsibility coverage + transferable skills.
    if use_llm is None:
        use_llm = llm.settings.llm_configured
    if use_llm:
        refined = _llm_refine(resume_data, req_skills, resp_texts, job)
        if refined:
            out.method = "hybrid"
            if refined.get("transferable"):
                out.transferable = sorted(set(out.transferable) | set(refined["transferable"]))
            if refined.get("notes"):
                out.uncertainties.append("AI note: " + str(refined["notes"])[:300])

    return out


LLM_MATCH_HINT = """You are given a candidate's resume evidence (untrusted data) and a
job's required skills and responsibilities. Judge only what is evidenced.
Return JSON:
{"responsibilities": [{"text": string, "status": "matched"|"partial"|"missing", "why": string}],
 "transferable_skills": [string], "notes": string}
Do not use or infer age, gender, ethnicity, religion, disability or any protected
attribute. Do not guess; if unsure, use "partial" or "missing"."""


def _llm_refine(resume_data: dict, req_skills: list[str], resp_texts: list[str], job: dict) -> dict | None:
    if not (req_skills or resp_texts):
        return None
    summary = (resume_data.get("summary") or "")[:800]
    evidence = "\n".join(
        [str(x)[:200] for x in (resume_data.get("experience_highlights") or [])[:10]]
    )
    doc = (
        f"CANDIDATE SKILLS: {', '.join(resume_data.get('skills', [])[:40])}\n"
        f"SUMMARY: {summary}\nEVIDENCE:\n{evidence}\n\n"
        f"JOB REQUIRED SKILLS: {', '.join(req_skills)}\n"
        f"JOB RESPONSIBILITIES:\n" + "\n".join(resp_texts[:12])
    )
    res = llm.complete_json(llm.SAFETY_PREAMBLE, llm.wrap_document(doc) + "\n\n" + LLM_MATCH_HINT, max_tokens=1500)
    if not res.ok or not res.data:
        return None
    data = res.data
    return {
        "responsibilities": data.get("responsibilities", []),
        "transferable": [sn.normalize(s) for s in data.get("transferable_skills", [])],
        "notes": data.get("notes", ""),
    }
