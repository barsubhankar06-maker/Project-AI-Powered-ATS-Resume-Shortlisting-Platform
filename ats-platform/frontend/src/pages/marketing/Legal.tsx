const content: Record<string, { title: string; updated: string; sections: [string, string][] }> = {
  privacy: {
    title: "Privacy Policy",
    updated: "Last updated: 25 October 2026",
    sections: [
      ["What we collect", "Account details (name, email), job and organization data you enter, and the resumes you upload. Resume files are stored in private object storage, separate from database records."],
      ["How resumes are used", "Resumes are parsed into structured fields and matched against job requirements to produce an explainable match score. Protected characteristics (name, photo, gender, age, ethnicity, religion, disability) are excluded from scoring."],
      ["Third-party AI services", "If an AI provider is configured, we minimize the personal data sent: scoring excludes identifiers, and document text is treated strictly as untrusted data. No AI provider is configured by default."],
      ["Retention", "Organizations configure a resume retention window. Candidates can request deletion of their data; requests are recorded and actioned by the organization."],
      ["Your rights", "You can access, correct, export or request deletion of your data. Candidates can submit a deletion request from their dashboard."],
      ["Contact", "privacy@talentlens.example"],
    ],
  },
  terms: {
    title: "Terms of Service",
    updated: "Last updated: 25 October 2026",
    sections: [
      ["Acceptable use", "You agree to use TalentLens only for lawful hiring activities and to upload only resumes you are permitted to process."],
      ["Decision support only", "Match scores are decision-support outputs. They are not a probability of hiring success, and you remain responsible for all hiring decisions. Do not use the platform to make fully automated rejection decisions."],
      ["Accounts & access", "You are responsible for keeping credentials secure. Role-based access is enforced on the server; do not attempt to access records belonging to other organizations."],
      ["Demo data", "Sample jobs and fictional resumes are clearly labelled and isolated in a demo organization. Do not treat demo data as real customer records."],
      ["Availability", "This is a demonstration build provided as-is, without warranty. Sample pricing does not constitute a commercial offer."],
    ],
  },
  ai: {
    title: "AI Use Disclosure",
    updated: "Last updated: 25 October 2026",
    sections: [
      ["Where AI is used", "AI (an OpenAI-compatible LLM, when configured) may be used to extract structured fields from job descriptions and resumes and to refine responsibility-coverage judgements. All other scoring is deterministic and auditable."],
      ["Matching method is always labelled", "Each match result records whether it came from the deterministic engine or a hybrid AI method, and this label is shown in the interface."],
      ["Graceful degradation", "If the AI provider is unavailable, times out, is rate-limited or returns invalid output, the deterministic engine runs instead and the result is labelled accordingly."],
      ["Untrusted input handling", "Resume and job-description text is treated as data, never as instructions. Embedded attempts to change scoring rules, reveal secrets or access other candidates' data are ignored."],
      ["What AI does not do", "AI does not make hiring decisions, does not auto-reject candidates, and does not use protected attributes. Graduation dates are never used to infer age, and no personality or culture-fit inference is performed."],
      ["Limitations", "Score explanations and fairness practices reduce risk but do not guarantee unbiased outcomes. Keep a human in the loop for all consequential decisions."],
    ],
  },
};

export default function Legal({ kind }: { kind: "privacy" | "terms" | "ai" }) {
  const doc = content[kind];
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">{doc.title}</h1>
      <p className="mt-2 text-sm text-slate-500">{doc.updated}</p>
      <div className="mt-10 space-y-8">
        {doc.sections.map(([h, b]) => (
          <section key={h}>
            <h2 className="text-lg font-semibold text-slate-900">{h}</h2>
            <p className="mt-2 text-slate-600">{b}</p>
          </section>
        ))}
      </div>
      <p className="mt-12 rounded-lg bg-slate-100 p-4 text-xs text-slate-500">
        This document is a template provided for a demonstration build and is not legal advice. Have counsel review it
        before any production use.
      </p>
    </div>
  );
}
