import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button, Field, Input } from "../components/ui";

const highlights = [
  { icon: "🧠", title: "Industry-built curriculum", text: "AI, ML and emerging-tech tracks designed with hiring partners." },
  { icon: "🎥", title: "Live + on-demand", text: "Cohort live sessions alongside a full self-paced video library." },
  { icon: "🏆", title: "Verified certification", text: "Certificates issued automatically once work is reviewed and approved." },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [companyCode, setCompanyCode] = useState(() => {
    try {
      return localStorage.getItem("lms_last_company_code") || "";
    } catch {
      return "";
    }
  });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!companyCode || !email || !password) {
      setError("Enter your company code, email and password.");
      return;
    }
    setBusy(true);
    try {
      await login(companyCode, email, password);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen bg-ink-50">
      {/* Brand panel */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-ink-900 p-12 text-white lg:flex">
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -left-24 -top-24 h-96 w-96 rounded-full bg-brand-600/30 blur-3xl" />
          <div className="absolute -right-16 bottom-0 h-80 w-80 rounded-full bg-brand-500/20 blur-3xl" />
        </div>

        <div className="relative flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 font-display text-base font-bold">
            DT
          </div>
          <div className="font-display text-lg font-bold">D'siar Tech</div>
        </div>

        <div className="relative">
          <h1 className="font-display text-4xl font-extrabold leading-tight">
            Bridging academia<br />and industry.
          </h1>
          <p className="mt-4 max-w-md text-sm text-ink-300">
            The enterprise learning platform behind D'siar Tech's AI, ML and
            emerging-technology programs — courses, live sessions, assignments
            and certification, all in one place.
          </p>

          <div className="mt-10 space-y-5">
            {highlights.map((h) => (
              <div key={h.title} className="flex gap-3">
                <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-white/10 text-lg">
                  {h.icon}
                </div>
                <div>
                  <div className="text-sm font-semibold text-white">{h.title}</div>
                  <div className="text-xs text-ink-400">{h.text}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative text-xs text-ink-500">© {new Date().getFullYear()} D'siar Tech. All rights reserved.</div>
      </div>

      {/* Form panel */}
      <div className="flex w-full flex-1 items-center justify-center px-6 py-12 lg:w-1/2">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 font-display text-sm font-bold text-white">
              DT
            </div>
            <div className="font-display text-base font-bold text-ink-900">D'siar Tech LMS</div>
          </div>

          <h2 className="font-display text-2xl font-bold text-ink-900">Welcome back</h2>
          <p className="mt-1 text-sm text-ink-500">Sign in to continue to your learning workspace.</p>

          <div className="mt-5 rounded-xl bg-brand-50 px-3.5 py-2.5 text-xs text-brand-700">
            Accounts are provisioned by the D'siar Tech team once enrollment is
            confirmed. If you've paid for a course but don't have login
            details yet, contact us.
          </div>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Field label="Company code">
              <Input
                autoFocus
                value={companyCode}
                onChange={(e) => setCompanyCode(e.target.value)}
                placeholder="e.g. dsiar"
              />
            </Field>
            <Field label="Email">
              <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
            </Field>
            <Field label="Password">
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            </Field>
            {error && (
              <div className="rounded-lg bg-danger-50 px-3 py-2 text-sm text-danger-700">{error}</div>
            )}
            <Button type="submit" disabled={busy} size="lg" className="w-full">
              {busy ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
