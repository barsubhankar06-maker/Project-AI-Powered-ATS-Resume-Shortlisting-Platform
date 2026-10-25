import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

const navItems = [
  { to: "/features", label: "Features" },
  { to: "/how-it-works", label: "How it works" },
  { to: "/pricing", label: "Pricing" },
  { to: "/jobs", label: "Careers" },
  { to: "/contact", label: "Contact" },
];

export function Logo({ dark = false }: { dark?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2 font-bold tracking-tight">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm text-white">TL</span>
      <span className={dark ? "text-white" : "text-slate-900"}>TalentLens</span>
    </Link>
  );
}

export default function MarketingLayout() {
  const { me, logout, isRecruiter, isCandidate } = useAuth();
  const navigate = useNavigate();
  const dashPath = isRecruiter ? "/app/dashboard" : isCandidate ? "/candidate" : "/app/dashboard";

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <Logo />
          <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
            {navItems.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm font-medium transition ${
                    isActive ? "bg-slate-100 text-slate-900" : "text-slate-600 hover:text-slate-900"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            {me ? (
              <>
                <button className="btn-secondary" onClick={() => navigate(dashPath)}>
                  Go to dashboard
                </button>
                <button
                  className="btn-ghost"
                  onClick={() => {
                    logout();
                    navigate("/");
                  }}
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="btn-ghost">
                  Log in
                </Link>
                <Link to="/register" className="btn-primary">
                  Get started
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 sm:px-6 md:grid-cols-4">
          <div>
            <Logo />
            <p className="mt-3 max-w-xs text-sm text-slate-500">
              Explainable AI screening that helps hiring teams shortlist fairly and faster.
            </p>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-800">Product</h4>
            <ul className="mt-3 space-y-2 text-sm text-slate-500">
              <li><Link to="/features" className="hover:text-slate-800">Features</Link></li>
              <li><Link to="/how-it-works" className="hover:text-slate-800">How it works</Link></li>
              <li><Link to="/pricing" className="hover:text-slate-800">Pricing</Link></li>
              <li><Link to="/jobs" className="hover:text-slate-800">Open roles</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-800">Company</h4>
            <ul className="mt-3 space-y-2 text-sm text-slate-500">
              <li><Link to="/contact" className="hover:text-slate-800">Contact</Link></li>
              <li><Link to="/ai-disclosure" className="hover:text-slate-800">AI use disclosure</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-800">Legal</h4>
            <ul className="mt-3 space-y-2 text-sm text-slate-500">
              <li><Link to="/privacy" className="hover:text-slate-800">Privacy policy</Link></li>
              <li><Link to="/terms" className="hover:text-slate-800">Terms of service</Link></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-slate-100 py-4 text-center text-xs text-slate-400">
          © {new Date().getFullYear()} TalentLens. Demo project — sample plans and fictional data.
        </div>
      </footer>
    </div>
  );
}
