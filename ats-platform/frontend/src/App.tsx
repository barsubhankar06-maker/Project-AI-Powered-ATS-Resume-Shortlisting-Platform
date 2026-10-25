import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import MarketingLayout from "./components/MarketingLayout";
import DashboardLayout from "./components/DashboardLayout";
import { Spinner } from "./components/ui";
import { useAuth } from "./lib/auth";

import Home from "./pages/marketing/Home";
import Features from "./pages/marketing/Features";
import HowItWorks from "./pages/marketing/HowItWorks";
import Pricing from "./pages/marketing/Pricing";
import Contact from "./pages/marketing/Contact";
import Legal from "./pages/marketing/Legal";
import PublicJobs from "./pages/marketing/PublicJobs";
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";

import Dashboard from "./pages/recruiter/Dashboard";
import Jobs from "./pages/recruiter/Jobs";
import JobNew from "./pages/recruiter/JobNew";
import JobDetail from "./pages/recruiter/JobDetail";
import Candidates from "./pages/recruiter/Candidates";
import CandidateDetail from "./pages/recruiter/CandidateDetail";
import Screening from "./pages/recruiter/Screening";
import Pipeline from "./pages/recruiter/Pipeline";
import Reports from "./pages/recruiter/Reports";
import Settings from "./pages/recruiter/Settings";
import Profile from "./pages/recruiter/Profile";
import Admin from "./pages/admin/Admin";

import CandidateHome from "./pages/candidate/CandidateHome";
import CandidateProfile from "./pages/candidate/CandidateProfile";

function FullScreenLoader() {
  return (
    <div className="flex h-96 items-center justify-center">
      <Spinner className="h-8 w-8" />
    </div>
  );
}

function RequireAuth({ children, role }: { children: JSX.Element; role?: "recruiter" | "candidate" }) {
  const { me, loading, isRecruiter, isCandidate } = useAuth();
  const location = useLocation();
  if (loading) return <FullScreenLoader />;
  if (!me) return <Navigate to="/login" state={{ from: location }} replace />;
  if (role === "recruiter" && !isRecruiter) return <Navigate to="/candidate" replace />;
  if (role === "candidate" && !isCandidate) return <Navigate to="/app/dashboard" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      {/* Public marketing site */}
      <Route element={<MarketingLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/features" element={<Features />} />
        <Route path="/how-it-works" element={<HowItWorks />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/jobs" element={<PublicJobs />} />
        <Route path="/privacy" element={<Legal kind="privacy" />} />
        <Route path="/terms" element={<Legal kind="terms" />} />
        <Route path="/ai-disclosure" element={<Legal kind="ai" />} />
      </Route>

      {/* Auth */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Recruiter dashboard */}
      <Route
        path="/app"
        element={
          <RequireAuth role="recruiter">
            <DashboardLayout variant="recruiter" />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/app/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="jobs/new" element={<JobNew />} />
        <Route path="jobs/:jobId" element={<JobDetail />} />
        <Route path="jobs/:jobId/pipeline" element={<Pipeline />} />
        <Route path="candidates" element={<Candidates />} />
        <Route path="candidates/:candidateId" element={<CandidateDetail />} />
        <Route path="screening" element={<Screening />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings" element={<Settings />} />
        <Route path="profile" element={<Profile />} />
        <Route path="admin" element={<Admin />} />
      </Route>

      {/* Candidate dashboard */}
      <Route
        path="/candidate"
        element={
          <RequireAuth role="candidate">
            <DashboardLayout variant="candidate" />
          </RequireAuth>
        }
      >
        <Route index element={<CandidateHome />} />
        <Route path="profile" element={<CandidateProfile />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
