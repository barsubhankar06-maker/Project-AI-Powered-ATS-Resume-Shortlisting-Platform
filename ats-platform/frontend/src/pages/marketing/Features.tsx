import { Link } from "react-router-dom";
import { Badge } from "../../components/ui";

const groups = [
  {
    heading: "Screening & matching",
    items: [
      ["AI job-description analyzer", "Extract required skills, responsibilities, qualifications and certifications from a pasted JD, then edit before screening."],
      ["Bulk resume upload", "Drag-and-drop PDF/DOCX upload with progress, validation, duplicate detection and per-file processing status."],
      ["Explainable match score", "A configurable 0–100 score with a full breakdown of matched, partial and missing requirements."],
      ["Transferable-skill detection", "Related technologies are flagged as potentially transferable rather than silently ignored."],
    ],
  },
  {
    heading: "Hiring workflow",
    items: [
      ["Ranked candidate tables", "Filter by score, coverage, experience, skills, stage and parsing status; sort and paginate instantly."],
      ["Visual pipeline", "Move candidates through Applied → Review → Shortlisted → Interview → Assessment → Offer → Hired / Rejected."],
      ["Notes & interview feedback", "Capture recruiter notes and structured interview feedback on every application."],
      ["Corrections & re-runs", "Edit any parsed field and re-run matching so scores reflect the corrected data."],
    ],
  },
  {
    heading: "Governance",
    items: [
      ["Role-based access", "Recruiter, candidate and administrator roles enforced on the server, not just the UI."],
      ["Organization isolation", "Every query is scoped to your organization; one tenant can never read another's records."],
      ["Audit logging", "Logins, stage changes, uploads and admin actions are recorded for review."],
      ["Fairness & privacy", "Protected attributes are excluded from scoring, with optional blind screening and data-deletion requests."],
    ],
  },
];

export default function Features() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
      <div className="max-w-2xl">
        <Badge tone="brand">Features</Badge>
        <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-900">Built for teams that have to justify decisions</h1>
        <p className="mt-4 text-lg text-slate-600">
          Every capability below is wired to real backend behaviour — not a mockup. Figures you see in the app are
          computed from your own database records.
        </p>
      </div>

      <div className="mt-12 space-y-14">
        {groups.map((g) => (
          <div key={g.heading}>
            <h2 className="text-xl font-semibold text-slate-900">{g.heading}</h2>
            <div className="mt-5 grid gap-6 sm:grid-cols-2">
              {g.items.map(([t, d]) => (
                <div key={t} className="card p-6">
                  <h3 className="font-semibold text-slate-900">{t}</h3>
                  <p className="mt-2 text-sm text-slate-600">{d}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-16 rounded-2xl border border-slate-200 bg-white p-8 text-center">
        <h2 className="text-2xl font-bold text-slate-900">See it on your own roles</h2>
        <p className="mt-2 text-slate-600">Create a free workspace in under a minute.</p>
        <Link to="/register" className="btn-primary mt-6 px-6 py-3">Get started</Link>
      </div>
    </div>
  );
}
