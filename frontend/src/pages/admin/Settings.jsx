import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { Badge, Button, Card, Field, Input, PageHeader } from "../../components/ui";
import { useConfirm } from "../../context/ConfirmContext";

const sourceBadge = {
  database: { variant: "success", label: "Saved here" },
  env: { variant: "neutral", label: "Render default" },
  default: { variant: "neutral", label: "Default" },
};

export default function Settings() {
  const confirm = useConfirm();
  const [data, setData] = useState(null);
  const [form, setForm] = useState({
    digitalsamba_developer_key: "",
    digitalsamba_team_id: "",
    jwt_expire_minutes: "",
  });
  const [reveal, setReveal] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [quizForm, setQuizForm] = useState({
    quiz_pass_percent: "",
    quiz_max_attempts: "",
    quiz_shuffle_questions: true,
    quiz_shuffle_options: true,
  });
  const [savingQuiz, setSavingQuiz] = useState(false);

  async function load(withReveal = reveal) {
    const res = await api.get("/settings", { params: { reveal: withReveal } });
    setData(res.data);
    setForm({
      digitalsamba_developer_key: "",
      digitalsamba_team_id: "",
      jwt_expire_minutes: String(res.data.jwt_expire_minutes),
    });
    setQuizForm({
      quiz_pass_percent: String(res.data.quiz_pass_percent),
      quiz_max_attempts: String(res.data.quiz_max_attempts),
      quiz_shuffle_questions: res.data.quiz_shuffle_questions,
      quiz_shuffle_options: res.data.quiz_shuffle_options,
    });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function toggleReveal() {
    const next = !reveal;
    if (next) {
      const ok = await confirm({
        title: "Show the full credentials?",
        message: "The Digital Samba developer key and team ID will be displayed in full on this screen.",
        confirmLabel: "Show credentials",
        variant: "brand",
      });
      if (!ok) return;
    }
    setReveal(next);
    await load(next);
  }

  async function save(e) {
    e.preventDefault();
    setError("");
    setNotice("");

    const minutes = Number(form.jwt_expire_minutes);
    if (!minutes || minutes < 5 || minutes > 43200) {
      setError("Session length must be between 5 minutes and 30 days (43200 minutes).");
      return;
    }

    const changingSecrets = form.digitalsamba_developer_key || form.digitalsamba_team_id;
    const ok = await confirm({
      title: "Save these settings?",
      message: changingSecrets
        ? "This updates the live Digital Samba credentials and/or session length used across the whole app immediately — existing live-session links created with the old credentials may stop working."
        : `Login sessions will now stay valid for ${minutes} minutes across the whole app, effective immediately for new logins.`,
      confirmLabel: "Save settings",
      variant: "brand",
    });
    if (!ok) return;

    setSaving(true);
    try {
      const body = { jwt_expire_minutes: minutes };
      if (form.digitalsamba_developer_key) body.digitalsamba_developer_key = form.digitalsamba_developer_key;
      if (form.digitalsamba_team_id) body.digitalsamba_team_id = form.digitalsamba_team_id;
      const res = await api.patch("/settings", body);
      setData(res.data);
      setForm({
        digitalsamba_developer_key: "",
        digitalsamba_team_id: "",
        jwt_expire_minutes: String(res.data.jwt_expire_minutes),
      });
      setNotice("Settings saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function saveQuizSettings(e) {
    e.preventDefault();
    setError("");
    setNotice("");

    const passPct = Number(quizForm.quiz_pass_percent);
    const maxAttempts = Number(quizForm.quiz_max_attempts);
    if (Number.isNaN(passPct) || passPct < 0 || passPct > 100) {
      setError("Pass percentage must be between 0 and 100.");
      return;
    }
    if (Number.isNaN(maxAttempts) || maxAttempts < 0 || maxAttempts > 50) {
      setError("Max attempts must be between 0 (unlimited) and 50.");
      return;
    }

    const ok = await confirm({
      title: "Save quiz settings?",
      message: `Every module quiz across every course will now require ${passPct}% to pass, with ${
        maxAttempts === 0 ? "unlimited retakes" : `up to ${maxAttempts} attempt${maxAttempts === 1 ? "" : "s"}`
      } — effective immediately, including for quizzes already in progress.`,
      confirmLabel: "Save quiz settings",
      variant: "brand",
    });
    if (!ok) return;

    setSavingQuiz(true);
    try {
      const res = await api.patch("/settings", {
        quiz_pass_percent: passPct,
        quiz_max_attempts: maxAttempts,
        quiz_shuffle_questions: quizForm.quiz_shuffle_questions,
        quiz_shuffle_options: quizForm.quiz_shuffle_options,
      });
      setData(res.data);
      setNotice("Quiz settings saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingQuiz(false);
    }
  }

  async function resetToRenderDefault(field, label) {
    const ok = await confirm({
      title: `Reset ${label} to the Render default?`,
      message: "This clears the saved override in the database — the app goes back to using the value from Render's environment variables.",
      confirmLabel: "Reset",
    });
    if (!ok) return;
    setError("");
    setNotice("");
    try {
      // null (not "") so this works for numeric/boolean fields too — an
      // empty string fails FastAPI's int/bool validation.
      const res = await api.patch("/settings", { [field]: null });
      setData(res.data);
      setForm((prev) => ({ ...prev, jwt_expire_minutes: String(res.data.jwt_expire_minutes) }));
      setQuizForm({
        quiz_pass_percent: String(res.data.quiz_pass_percent),
        quiz_max_attempts: String(res.data.quiz_max_attempts),
        quiz_shuffle_questions: res.data.quiz_shuffle_questions,
        quiz_shuffle_options: res.data.quiz_shuffle_options,
      });
      setNotice(`${label} reset to the default.`);
    } catch (err) {
      setError(err.message);
    }
  }

  if (!data) return null;

  return (
    <div>
      <PageHeader
        eyebrow="Admin"
        title="Settings"
        description="Change Digital Samba credentials and session length without touching Render or redeploying. Everything else (database connection, JWT signing secret, CORS, etc.) stays managed in Render on purpose."
      />

      {error && <div className="mt-4 rounded-lg bg-danger-50 px-3.5 py-2.5 text-sm text-danger-700">{error}</div>}
      {notice && <div className="mt-4 rounded-lg bg-success-50 px-3.5 py-2.5 text-sm text-success-700">{notice}</div>}

      <Card as="form" onSubmit={save} className="mt-6 max-w-xl space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-sm font-bold text-ink-900">🎥 Digital Samba (live sessions)</h2>
          <button type="button" onClick={toggleReveal} className="text-xs font-medium text-brand-600 hover:underline">
            {reveal ? "Hide values" : "Show values"}
          </button>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-600">Developer key</span>
            <SourceTag source={data.digitalsamba_developer_key_source} onReset={() => resetToRenderDefault("digitalsamba_developer_key", "Developer key")} />
          </div>
          <Input
            type={reveal ? "text" : "password"}
            placeholder={data.digitalsamba_developer_key_set ? data.digitalsamba_developer_key : "Not set"}
            value={form.digitalsamba_developer_key}
            onChange={(e) => setForm({ ...form, digitalsamba_developer_key: e.target.value })}
          />
          <p className="mt-1 text-xs text-ink-400">Leave blank to keep the current value.</p>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-600">Team ID</span>
            <SourceTag source={data.digitalsamba_team_id_source} onReset={() => resetToRenderDefault("digitalsamba_team_id", "Team ID")} />
          </div>
          <Input
            type={reveal ? "text" : "password"}
            placeholder={data.digitalsamba_team_id_set ? data.digitalsamba_team_id : "Not set"}
            value={form.digitalsamba_team_id}
            onChange={(e) => setForm({ ...form, digitalsamba_team_id: e.target.value })}
          />
          <p className="mt-1 text-xs text-ink-400">Leave blank to keep the current value.</p>
        </div>

        <div className="border-t border-ink-100 pt-4">
          <div className="mb-1 flex items-center justify-between">
            <h2 className="font-display text-sm font-bold text-ink-900">🔐 Login session length</h2>
            <SourceTag source={data.jwt_expire_minutes_source} onReset={() => resetToRenderDefault("jwt_expire_minutes", "Session length")} />
          </div>
          <Field label="Minutes before a login expires" hint="5 – 43200 (30 days). Applies to new logins immediately.">
            <Input
              type="number"
              min={5}
              max={43200}
              value={form.jwt_expire_minutes}
              onChange={(e) => setForm({ ...form, jwt_expire_minutes: e.target.value })}
            />
          </Field>
        </div>

        <Button type="submit" disabled={saving} className="w-full">
          {saving ? "Saving…" : "Save settings"}
        </Button>
      </Card>

      <Card as="form" onSubmit={saveQuizSettings} className="mt-6 max-w-xl space-y-4">
        <h2 className="font-display text-sm font-bold text-ink-900">🧩 Module quizzes</h2>
        <p className="text-xs text-ink-500">
          Applies to every module quiz across every course — the pass mark, retake limit, and shuffle behavior
          students see.
        </p>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-600">Pass percentage</span>
            <SourceTag
              source={data.quiz_pass_percent_source}
              onReset={() => resetToRenderDefault("quiz_pass_percent", "Pass percentage")}
            />
          </div>
          <Input
            type="number"
            min={0}
            max={100}
            value={quizForm.quiz_pass_percent}
            onChange={(e) => setQuizForm({ ...quizForm, quiz_pass_percent: e.target.value })}
          />
          <p className="mt-1 text-xs text-ink-400">Score needed (out of 100) to pass a module's quiz.</p>
        </div>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-semibold text-ink-600">Max attempts</span>
            <SourceTag
              source={data.quiz_max_attempts_source}
              onReset={() => resetToRenderDefault("quiz_max_attempts", "Max attempts")}
            />
          </div>
          <Input
            type="number"
            min={0}
            max={50}
            value={quizForm.quiz_max_attempts}
            onChange={(e) => setQuizForm({ ...quizForm, quiz_max_attempts: e.target.value })}
          />
          <p className="mt-1 text-xs text-ink-400">0 = unlimited retakes until a student passes.</p>
        </div>

        <div className="space-y-2 border-t border-ink-100 pt-4">
          <label className="flex items-center justify-between gap-2 text-sm text-ink-700">
            <span>Shuffle question order per attempt</span>
            <input
              type="checkbox"
              checked={quizForm.quiz_shuffle_questions}
              onChange={(e) => setQuizForm({ ...quizForm, quiz_shuffle_questions: e.target.checked })}
            />
          </label>
          <label className="flex items-center justify-between gap-2 text-sm text-ink-700">
            <span>Shuffle answer options per attempt</span>
            <input
              type="checkbox"
              checked={quizForm.quiz_shuffle_options}
              onChange={(e) => setQuizForm({ ...quizForm, quiz_shuffle_options: e.target.checked })}
            />
          </label>
        </div>

        <Button type="submit" disabled={savingQuiz} className="w-full">
          {savingQuiz ? "Saving…" : "Save quiz settings"}
        </Button>
      </Card>
    </div>
  );
}

function SourceTag({ source, onReset }) {
  const tag = sourceBadge[source] || sourceBadge.env;
  return (
    <div className="flex items-center gap-2">
      <Badge variant={tag.variant}>{tag.label}</Badge>
      {source === "database" && (
        <button type="button" onClick={onReset} className="text-xs font-medium text-ink-400 hover:text-danger-600 hover:underline">
          Reset
        </button>
      )}
    </div>
  );
}
