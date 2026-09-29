import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { platformApi } from "../../api/client";
import { usePlatformAuth } from "../../context/PlatformAuthContext";
import { Badge, Button, Card, Field, Input, Modal, PageHeader, Select } from "../../components/ui";

const emptyForm = {
  company_code: "",
  company_name: "",
  plan: "starter",
  max_users: 100,
  live_sessions: false,
  admin_name: "",
  admin_email: "",
  admin_password: "",
};

const PLANS = ["starter", "advanced", "custom"];

export default function PlatformConsole() {
  const { admin, logout } = usePlatformAuth();
  const navigate = useNavigate();
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    try {
      const res = await platformApi.get("/platform/tenants");
      setTenants(res.data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleLogout() {
    await logout();
    navigate("/platform/login");
  }

  async function updateTenant(code, patch) {
    setError("");
    try {
      await platformApi.patch(`/platform/tenants/${code}`, patch);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="min-h-screen bg-ink-50">
      <header className="flex items-center justify-between border-b border-ink-200 bg-white px-6 py-4">
        <div>
          <div className="font-display text-sm font-bold text-ink-900">D'siar Tech LMS — Platform Console</div>
          <div className="text-xs text-ink-500">Signed in as {admin?.name} ({admin?.email})</div>
        </div>
        <Button variant="secondary" onClick={handleLogout}>
          Log out
        </Button>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <PageHeader
          eyebrow="Clients"
          title="Client companies"
          description="Every company running on this deployment, each fully isolated in its own database. Onboard a new one, adjust a plan/seat limit, switch add-on features, or suspend access — nothing here touches another client's data."
          actions={<Button onClick={() => setAddOpen(true)}>+ Add client</Button>}
        />

        {error && <div className="mt-4 rounded-lg bg-danger-50 px-3.5 py-2.5 text-sm text-danger-700">{error}</div>}

        {loading ? (
          <div className="mt-8 text-center text-sm text-ink-400">Loading…</div>
        ) : (
          <div className="mt-6 space-y-3">
            {tenants.map((t) => (
              <TenantRow key={t.company_code} tenant={t} onUpdate={(patch) => updateTenant(t.company_code, patch)} />
            ))}
            {tenants.length === 0 && (
              <div className="rounded-lg border border-dashed border-ink-200 px-4 py-10 text-center text-sm text-ink-400">
                No clients yet — add your first one above.
              </div>
            )}
          </div>
        )}
      </main>

      <AddTenantModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onCreated={() => {
          setAddOpen(false);
          load();
        }}
      />
    </div>
  );
}

function TenantRow({ tenant, onUpdate }) {
  const [plan, setPlan] = useState(tenant.plan);
  const [maxUsers, setMaxUsers] = useState(tenant.max_users ?? "");
  const [liveSessions, setLiveSessions] = useState(!!tenant.features?.live_sessions);
  const dirty = plan !== tenant.plan || Number(maxUsers) !== tenant.max_users || liveSessions !== !!tenant.features?.live_sessions;

  const atLimit = tenant.max_users && tenant.active_users >= tenant.max_users;

  return (
    <Card className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-display text-base font-bold text-ink-900">{tenant.company_name}</h3>
            <Badge variant={tenant.active ? "success" : "danger"}>{tenant.active ? "Active" : "Suspended"}</Badge>
          </div>
          <div className="mt-0.5 text-xs text-ink-500">
            Company code <code className="rounded bg-ink-100 px-1 py-0.5">{tenant.company_code}</code> · database{" "}
            <code className="rounded bg-ink-100 px-1 py-0.5">{tenant.db_name}</code>
          </div>
        </div>
        <div className="text-right">
          <div className={`text-sm font-semibold ${atLimit ? "text-danger-600" : "text-ink-800"}`}>
            {tenant.active_users} / {tenant.max_users ?? "∞"} seats used
          </div>
          {atLimit && <div className="text-xs text-danger-600">At limit — new users are blocked until raised</div>}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 border-t border-ink-100 pt-3 sm:grid-cols-4">
        <Field label="Plan">
          <Select value={plan} onChange={(e) => setPlan(e.target.value)}>
            {PLANS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Max users (seats)">
          <Input type="number" min="1" value={maxUsers} onChange={(e) => setMaxUsers(e.target.value)} />
        </Field>
        <Field label="Live Sessions add-on">
          <label className="mt-2 flex items-center gap-2 text-sm text-ink-700">
            <input type="checkbox" checked={liveSessions} onChange={(e) => setLiveSessions(e.target.checked)} />
            Enabled
          </label>
        </Field>
        <div className="flex items-end justify-end gap-2">
          <Button
            size="sm"
            variant={tenant.active ? "danger" : "secondary"}
            onClick={() => onUpdate({ active: !tenant.active })}
          >
            {tenant.active ? "Suspend" : "Reinstate"}
          </Button>
          <Button
            size="sm"
            disabled={!dirty}
            onClick={() => onUpdate({ plan, max_users: Number(maxUsers) || null, features: { live_sessions: liveSessions } })}
          >
            Save
          </Button>
        </div>
      </div>
    </Card>
  );
}

function AddTenantModal({ open, onClose, onCreated }) {
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setForm(emptyForm);
      setError("");
    }
  }, [open]);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await platformApi.post("/platform/tenants", {
        company_code: form.company_code,
        company_name: form.company_name,
        plan: form.plan,
        max_users: Number(form.max_users) || null,
        features: { live_sessions: form.live_sessions },
        admin_name: form.admin_name,
        admin_email: form.admin_email,
        admin_password: form.admin_password,
      });
      onCreated();
    } catch (e2) {
      setError(e2.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add a new client company" wide>
      <form className="space-y-3" onSubmit={submit}>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Company code" hint="What they type at login — short, no spaces (e.g. acme)">
            <Input value={form.company_code} onChange={(e) => setForm({ ...form, company_code: e.target.value })} />
          </Field>
          <Field label="Company name">
            <Input value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
          </Field>
          <Field label="Plan">
            <Select value={form.plan} onChange={(e) => setForm({ ...form, plan: e.target.value })}>
              {PLANS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Max users (seats)">
            <Input type="number" min="1" value={form.max_users} onChange={(e) => setForm({ ...form, max_users: e.target.value })} />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm text-ink-700">
          <input
            type="checkbox"
            checked={form.live_sessions}
            onChange={(e) => setForm({ ...form, live_sessions: e.target.checked })}
          />
          Enable the Live Sessions add-on for this client
        </label>

        <div className="border-t border-ink-100 pt-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">Their first Admin login</h3>
          <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Admin name">
              <Input value={form.admin_name} onChange={(e) => setForm({ ...form, admin_name: e.target.value })} />
            </Field>
            <Field label="Admin email">
              <Input type="email" value={form.admin_email} onChange={(e) => setForm({ ...form, admin_email: e.target.value })} />
            </Field>
            <Field label="Temporary password" hint="At least 8 characters">
              <Input
                type="password"
                value={form.admin_password}
                onChange={(e) => setForm({ ...form, admin_password: e.target.value })}
              />
            </Field>
          </div>
        </div>

        {error && <div className="rounded-lg bg-danger-50 px-3.5 py-2.5 text-sm text-danger-700">{error}</div>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? "Creating…" : "Create client"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
