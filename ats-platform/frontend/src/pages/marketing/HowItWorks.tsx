import { Link } from "react-router-dom";
import { Badge } from "../../components/ui";

const weights = [
  ["Required skills", 40, "Explicit must-have skills matched against parsed resume skills (with transferable-skill credit)."],
  ["Experience & responsibilities", 25, "Semantic overlap between the job's responsibilities and the candidate's experience, plus an experience-duration fit check."],
  ["Preferred skills", 15, "Nice-to-have skills, scored the same transparent way as required skills."],
  ["Projects & achievements", 10, "Evidence of relevant project work and achievements drawn from the resume."],
  ["Qualifications & certifications", 10, "Education and certifications checked against the job's stated requirements."],
];

export default function HowItWorks() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
      <Badge tone="brand">How it works</Badge>
      <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-900">Transparent from resume to shortlist</h1>
      <p className="mt-4 text-lg text-slate-600">
        TalentLens combines deterministic rules with optional AI enrichment. When no AI provider is configured, the
        deterministic engine runs on its own and the interface clearly labels which method produced each score.
      </p>

      <ol className="mt-12 space-y-8">
        {[
          ["Parse the job description", "Paste a JD. The analyzer proposes required skills, preferred skills, responsibilities, qualifications and an experience range. You review and edit — nothing is screened until you confirm."],
          ["Upload and parse resumes", "PDF and DOCX resumes are text-extracted (with OCR available if configured for scanned files), then parsed into structured fields. Missing or unclear fields are marked unknown, never treated as a gap in ability."],
          ["Match and score", "Each resume is compared to the job using the weighted model below. The result lists matched requirements, partial matches, missing/unverified items, supporting evidence and parsing uncertainties."],
          ["Review, shortlist, report", "Use ranked tables, filters and the pipeline to shortlist and progress candidates. AI is decision support only — recruiters make and record the calls, and every stage change is audited."],
        ].map(([t, d], i) => (
          <li key={t} className="flex gap-5">
            <span className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-brand-600 font-semibold text-white">{i + 1}</span>
            <div>
              <h3 className="text-lg font-semibold text-slate-900">{t}</h3>
              <p className="mt-1 text-slate-600">{d}</p>
            </div>
          </li>
        ))}
      </ol>

      <div className="mt-16">
        <h2 className="text-2xl font-bold text-slate-900">The scoring model</h2>
        <p className="mt-2 text-slate-600">
          The default weights below are configurable per job and validated to total 100%. The score is decision support —
          it is not a probability of hiring success, and it never rejects a candidate by itself.
        </p>
        <div className="mt-6 overflow-hidden rounded-xl border border-slate-200">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-3 font-medium">Component</th>
                <th className="px-4 py-3 font-medium">Weight</th>
                <th className="px-4 py-3 font-medium">What it measures</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {weights.map(([name, w, d]) => (
                <tr key={name as string}>
                  <td className="px-4 py-3 font-medium text-slate-800">{name}</td>
                  <td className="px-4 py-3 text-slate-600">{w}%</td>
                  <td className="px-4 py-3 text-slate-600">{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-14 rounded-2xl bg-slate-900 p-8 text-slate-100">
        <h2 className="text-xl font-bold text-white">Fairness, honestly stated</h2>
        <p className="mt-2 text-slate-300">
          Protected and irrelevant personal characteristics are excluded from scoring, and blind screening is available.
          That said, no automated screening system can guarantee unbiased outcomes — fairness testing and clear score
          explanations reduce risk, they do not eliminate it. Always keep a human in the loop.
        </p>
        <Link to="/ai-disclosure" className="mt-4 inline-block text-brand-300 underline">Read the AI-use disclosure</Link>
      </div>
    </div>
  );
}
