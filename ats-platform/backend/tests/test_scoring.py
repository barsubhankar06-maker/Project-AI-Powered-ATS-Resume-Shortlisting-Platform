"""Match scoring: correctness, weighting, explainability and edge cases."""
import pytest

from app.services import matching


def _reqs(required, preferred=None, resp=None):
    out = [{"kind": "required_skill", "text": s, "normalized_skill": s} for s in required]
    out += [{"kind": "preferred_skill", "text": s, "normalized_skill": s} for s in (preferred or [])]
    out += [{"kind": "responsibility", "text": r, "normalized_skill": ""} for r in (resp or [])]
    return out


JOB = {"description": "", "responsibilities": "", "experience_min": 3, "experience_max": 6}


def test_full_match_scores_high():
    resume = {
        "skills": ["python", "fastapi", "postgresql", "docker", "aws", "rest"],
        "summary": "Backend engineer building REST APIs and microservices in Python.",
        "experience_highlights": ["Designed REST APIs in Python and FastAPI", "Deployed with Docker on AWS"],
        "experience_text": "Backend Engineer (Jan 2019 - Present)",
        "total_experience_years": 5.0,
        "projects": [{"text": "Built a FastAPI microservice", "skills": ["fastapi"]}],
        "education": [{"text": "B.Tech Computer Science"}],
        "certifications": [],
    }
    reqs = _reqs(
        ["python", "fastapi", "postgresql", "docker", "aws", "rest"],
        ["redis", "kubernetes"],
        ["Design and build REST APIs and microservices"],
    )
    out = matching.match_resume_to_job(resume_data=resume, requirements=reqs, job=JOB, use_llm=False)
    assert out.total_score >= 70
    assert set(out.matched) >= {"python", "fastapi", "docker"}
    assert out.breakdown["components"]["required_skills"]["score"] == 100.0


def test_missing_required_skills_are_reported():
    resume = {"skills": ["javascript", "react"], "total_experience_years": 2.0, "experience_highlights": [], "projects": [], "education": []}
    reqs = _reqs(["python", "fastapi", "postgresql", "docker", "aws", "rest"])
    out = matching.match_resume_to_job(resume_data=resume, requirements=reqs, job=JOB, use_llm=False)
    assert out.total_score < 50
    assert "python" in out.missing


def test_transferable_skill_counts_as_partial_not_match():
    # Candidate knows MySQL; job wants PostgreSQL -> partial, not full match.
    resume = {"skills": ["mysql"], "total_experience_years": 4.0, "experience_highlights": [], "projects": [], "education": []}
    reqs = _reqs(["postgresql"])
    out = matching.match_resume_to_job(resume_data=resume, requirements=reqs, job=JOB, use_llm=False)
    assert out.matched == []
    assert any(p["skill"] == "postgresql" for p in out.partial)
    assert out.breakdown["components"]["required_skills"]["score"] == 50.0


def test_weights_must_total_100():
    w, err = matching.validate_weights({"required_skills": 50, "experience": 50, "preferred_skills": 10, "projects": 10, "qualifications": 10})
    assert err  # totals 130
    w, err = matching.validate_weights({"required_skills": 40, "experience": 25, "preferred_skills": 15, "projects": 10, "qualifications": 10})
    assert err == ""


def test_unknown_weight_key_rejected():
    _, err = matching.validate_weights({"required_skills": 100, "bogus": 0})
    assert "Unknown weight key" in err


def test_custom_weights_change_the_total():
    resume = {"skills": ["python"], "total_experience_years": 5.0, "experience_highlights": [], "projects": [], "education": []}
    # "excel" is unrelated to python, so exactly one of two required skills matches.
    reqs = _reqs(["python", "excel"])
    default = matching.match_resume_to_job(resume_data=resume, requirements=reqs, job=JOB, use_llm=False)
    # Weight everything on required skills: 1 of 2 matched -> 50.
    skewed = matching.match_resume_to_job(
        resume_data=resume,
        requirements=reqs,
        job=JOB,
        weights={"required_skills": 100, "experience": 0, "preferred_skills": 0, "projects": 0, "qualifications": 0},
        use_llm=False,
    )
    assert skewed.total_score == 50.0
    assert default.total_score != skewed.total_score


def test_uncertain_experience_is_flagged_not_penalised_hard():
    resume = {"skills": ["python"], "total_experience_years": None, "experience_highlights": [], "projects": [], "education": []}
    reqs = _reqs(["python"], resp=["Build things"])
    out = matching.match_resume_to_job(resume_data=resume, requirements=reqs, job=JOB, use_llm=False)
    assert any("experience" in u.lower() for u in out.uncertainties)


def test_protected_attributes_are_not_used():
    """Two identical candidates differing only by name/gender must score the same."""
    base = {"skills": ["python", "fastapi"], "total_experience_years": 5.0, "experience_highlights": ["Built APIs"], "projects": [], "education": []}
    a = {**base, "name": "Alice", "gender": "female", "age": 45}
    b = {**base, "name": "Bob", "gender": "male", "age": 24}
    reqs = _reqs(["python", "fastapi"])
    assert matching.match_resume_to_job(resume_data=a, requirements=reqs, job=JOB, use_llm=False).total_score == \
           matching.match_resume_to_job(resume_data=b, requirements=reqs, job=JOB, use_llm=False).total_score
