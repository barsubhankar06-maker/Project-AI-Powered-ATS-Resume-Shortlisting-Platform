import { useState } from "react";
import { Field, Input, Textarea, useToast } from "../../components/ui";

export default function Contact() {
  const { push } = useToast();
  const [form, setForm] = useState({ name: "", email: "", company: "", message: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!form.name.trim()) errs.name = "Please enter your name";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) errs.email = "Please enter a valid email";
    if (form.message.trim().length < 10) errs.message = "Please add a little more detail";
    setErrors(errs);
    if (Object.keys(errs).length) return;
    // This marketing form is not wired to a backend in this build; it validates
    // and confirms locally and points to the support inbox.
    push("success", "Thanks! This demo form validated your message. Email hello@talentlens.example to reach a human.");
    setForm({ name: "", email: "", company: "", message: "" });
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2">
      <div>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900">Talk to us</h1>
        <p className="mt-4 text-lg text-slate-600">
          Questions about deployment, fairness, or fitting TalentLens into your hiring process? We'd love to hear from you.
        </p>
        <dl className="mt-8 space-y-4 text-sm">
          <div>
            <dt className="font-medium text-slate-800">Sales & support</dt>
            <dd className="text-slate-600">hello@talentlens.example</dd>
          </div>
          <div>
            <dt className="font-medium text-slate-800">Security & privacy</dt>
            <dd className="text-slate-600">privacy@talentlens.example</dd>
          </div>
          <div>
            <dt className="font-medium text-slate-800">Office</dt>
            <dd className="text-slate-600">Bengaluru, India</dd>
          </div>
        </dl>
      </div>

      <form onSubmit={submit} className="card space-y-4 p-6" noValidate>
        <Field label="Full name" error={errors.name}>
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} autoComplete="name" />
        </Field>
        <Field label="Work email" error={errors.email}>
          <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" />
        </Field>
        <Field label="Company (optional)">
          <Input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} autoComplete="organization" />
        </Field>
        <Field label="How can we help?" error={errors.message}>
          <Textarea rows={5} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
        </Field>
        <button type="submit" className="btn-primary w-full">Send message</button>
        <p className="text-xs text-slate-400">
          This is a demo contact form; submissions are validated in the browser and are not stored.
        </p>
      </form>
    </div>
  );
}
