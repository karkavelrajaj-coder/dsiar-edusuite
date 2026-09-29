import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePlatformAuth } from "../../context/PlatformAuthContext";
import { Button, Field, Input } from "../../components/ui";

export default function PlatformLogin() {
  const { login } = usePlatformAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!email || !password) {
      setError("Enter both email and password.");
      return;
    }
    setBusy(true);
    try {
      await login(email, password);
      navigate("/platform");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-950 px-6">
      <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-ink-900 p-8">
        <div className="mb-6 flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 font-display text-sm font-bold text-white">
            DT
          </div>
          <div>
            <div className="font-display text-base font-bold text-white">Super Admin</div>
            <div className="text-[11px] font-medium text-ink-400">Platform console — D'siar Tech only</div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Email">
            <Input type="email" autoFocus value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@dsiar.com" />
          </Field>
          <Field label="Password">
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          </Field>
          {error && <div className="rounded-lg bg-danger-50 px-3 py-2 text-sm text-danger-700">{error}</div>}
          <Button type="submit" disabled={busy} size="lg" className="w-full">
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-ink-500">
          Looking for a client login instead?{" "}
          <a href="/login" className="font-medium text-ink-300 hover:text-white">
            Go there
          </a>
        </p>
      </div>
    </div>
  );
}
