import { Badge, Field, Input, Select } from "./ui";

export interface Requirement {
  kind: string;
  text: string;
  normalized_skill?: string;
  is_hard?: boolean;
  source?: string;
}

export const REQUIREMENT_KINDS = [
  ["required_skill", "Required skill"],
  ["preferred_skill", "Preferred skill"],
  ["responsibility", "Responsibility"],
  ["qualification", "Qualification"],
  ["certification", "Certification"],
  ["education", "Education"],
  ["tool", "Tool / technology"],
] as const;

const KIND_TONE: Record<string, any> = {
  required_skill: "brand",
  preferred_skill: "blue",
  responsibility: "slate",
  qualification: "amber",
  certification: "green",
  education: "amber",
  tool: "slate",
};

export function RequirementsEditor({
  requirements,
  onChange,
}: {
  requirements: Requirement[];
  onChange: (r: Requirement[]) => void;
}) {
  function update(i: number, patch: Partial<Requirement>) {
    onChange(requirements.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }
  function remove(i: number) {
    onChange(requirements.filter((_, idx) => idx !== i));
  }
  function add() {
    onChange([...requirements, { kind: "required_skill", text: "", is_hard: false, source: "manual" }]);
  }

  const grouped = requirements.reduce<Record<string, number>>((acc, r) => {
    acc[r.kind] = (acc[r.kind] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-2">
          {Object.entries(grouped).map(([k, n]) => (
            <Badge key={k} tone={KIND_TONE[k] || "slate"}>
              {REQUIREMENT_KINDS.find((x) => x[0] === k)?.[1] || k}: {n}
            </Badge>
          ))}
          {requirements.length === 0 && <span className="text-sm text-slate-400">No requirements yet.</span>}
        </div>
        <button type="button" className="btn-secondary" onClick={add}>+ Add requirement</button>
      </div>

      <div className="space-y-2">
        {requirements.map((r, i) => (
          <div key={i} className="flex flex-col gap-2 rounded-lg border border-slate-200 p-3 sm:flex-row sm:items-center">
            <Select className="sm:w-48" value={r.kind} onChange={(e) => update(i, { kind: e.target.value })}>
              {REQUIREMENT_KINDS.map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </Select>
            <Input
              className="flex-1"
              value={r.text}
              placeholder="Describe the requirement"
              onChange={(e) => update(i, { text: e.target.value })}
            />
            <label className="flex items-center gap-2 whitespace-nowrap text-xs text-slate-600">
              <input
                type="checkbox"
                checked={!!r.is_hard}
                onChange={(e) => update(i, { is_hard: e.target.checked })}
              />
              Hard requirement
            </label>
            <button type="button" className="text-sm text-rose-600 hover:underline" onClick={() => remove(i)}>
              Remove
            </button>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400">
        Hard requirements are still reviewable — they are flagged for the recruiter and never auto-reject on their own.
      </p>
    </div>
  );
}

export const DEFAULT_WEIGHTS = {
  required_skills: 40,
  experience: 25,
  preferred_skills: 15,
  projects: 10,
  qualifications: 10,
};

export function WeightsEditor({
  weights,
  onChange,
}: {
  weights: Record<string, number>;
  onChange: (w: Record<string, number>) => void;
}) {
  const total = Object.values(weights).reduce((a, b) => a + (Number(b) || 0), 0);
  const valid = Math.abs(total - 100) < 0.01;
  const labels: Record<string, string> = {
    required_skills: "Required skills",
    experience: "Experience & responsibilities",
    preferred_skills: "Preferred skills",
    projects: "Projects & achievements",
    qualifications: "Qualifications & certifications",
  };
  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(weights).map(([k, v]) => (
          <Field key={k} label={labels[k] || k}>
            <Input
              type="number"
              min={0}
              max={100}
              value={v}
              onChange={(e) => onChange({ ...weights, [k]: Number(e.target.value) })}
            />
          </Field>
        ))}
      </div>
      <div className={`text-sm ${valid ? "text-emerald-600" : "text-rose-600"}`}>
        Total: {total}% {valid ? "✓" : "— must equal 100%"}
      </div>
    </div>
  );
}
