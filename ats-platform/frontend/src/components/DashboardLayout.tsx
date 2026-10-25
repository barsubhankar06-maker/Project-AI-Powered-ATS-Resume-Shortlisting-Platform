import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../lib/auth";
import { Logo } from "./MarketingLayout";
import { Badge } from "./ui";

const recruiterNav = [
  { to: "/app/dashboard", label: "Dashboard", icon: "▦" },
  { to: "/app/jobs", label: "Jobs", icon: "🧳" },
  { to: "/app/candidates", label: "Candidates", icon: "👥" },
  { to: "/app/screening", label: "Resume Screening", icon: "🔎" },
  { to: "/app/reports", label: "Reports", icon: "📈" },
  { to: "/app/settings", label: "Settings", icon: "⚙️" },
  { to: "/app/profile", label: "Profile", icon: "🙂" },
];

const candidateNav = [
  { to: "/candidate", label: "My applications", icon: "📄" },
  { to: "/candidate/profile", label: "My profile", icon: "🙂" },
  { to: "/jobs", label: "Browse jobs", icon: "🧳" },
];

const adminNav = [
  { to: "/app/admin", label: "Platform admin", icon: "🛡️" },
];

export default function DashboardLayout({ variant = "recruiter" }: { variant?: "recruiter" | "candidate" | "admin" }) {
  const { me, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const nav = variant === "candidate" ? candidateNav : recruiterNav;

  return (
    <div className="flex min-h-full bg-slate-50">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform border-r border-slate-200 bg-white transition-transform lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 items-center border-b border-slate-200 px-5">
          <Logo />
        </div>
        <nav className="space-y-1 p-3" aria-label="Dashboard">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/app/dashboard" || n.to === "/candidate"}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              <span aria-hidden className="text-base">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
          {variant === "recruiter" && isAdmin && (
            <div className="pt-2">
              {adminNav.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                      isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
                    }`
                  }
                >
                  <span aria-hidden className="text-base">{n.icon}</span>
                  {n.label}
                </NavLink>
              ))}
            </div>
          )}
        </nav>
      </aside>

      {open && <div className="fixed inset-0 z-30 bg-slate-900/30 lg:hidden" onClick={() => setOpen(false)} />}

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
          <button className="btn-ghost lg:hidden" aria-label="Toggle navigation" onClick={() => setOpen((o) => !o)}>
            ☰
          </button>
          <div className="hidden text-sm text-slate-500 sm:block">
            {me?.memberships?.[0]?.org_name || "Workspace"}
          </div>
          <div className="flex items-center gap-3">
            {me?.active_role && <Badge tone="brand">{me.active_role}</Badge>}
            <span className="hidden text-sm text-slate-600 sm:block">{me?.user.full_name}</span>
            <button
              className="btn-secondary"
              onClick={() => {
                logout();
                navigate("/");
              }}
            >
              Sign out
            </button>
          </div>
        </header>
        <div className="flex-1 p-4 sm:p-6">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
