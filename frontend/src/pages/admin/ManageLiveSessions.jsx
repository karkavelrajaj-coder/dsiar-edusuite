import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useConfirm } from "../../context/ConfirmContext";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  IconButton,
  Input,
  Modal,
  PageHeader,
  RichText,
  Select,
  Textarea,
} from "../../components/ui";

const statusBadge = { upcoming: { variant: "brand", label: "Upcoming" }, live: { variant: "live", label: "● Live now" }, ended: { variant: "neutral", label: "Ended" } };

const emptyForm = {
  course_id: "",
  title: "",
  description: "",
  date: "",
  time: "18:00",
  timezone: "Asia/Kolkata",
  duration_minutes: 60,
};

function isoToLocalDateTime(iso, tz) {
  try {
    const d = new Date(iso);
    const date = new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
    const time = new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(d);
    return { date, time };
  } catch {
    return { date: "", time: "18:00" };
  }
}

export default function ManageLiveSessions() {
  const confirm = useConfirm();
  const [courses, setCourses] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [timezones, setTimezones] = useState([]);
  const [hostView, setHostView] = useState({}); // sessionId -> join_link
  const [modal, setModal] = useState(null); // null | "new" | session

  async function load() {
    const [cRes, sRes, tzRes] = await Promise.all([
      api.get("/courses/manage"),
      api.get("/live-sessions/manage"),
      api.get("/timezones"),
    ]);
    setCourses(cRes.data);
    setSessions(sRes.data);
    setTimezones(tzRes.data.options);
  }

  useEffect(() => {
    load();
  }, []);

  const courseTitle = (id) => courses.find((c) => c.id === id)?.title || "Unknown";

  async function saveSession(form) {
    const ok = await confirm({
      title: form.id ? "Save changes to this session?" : "Schedule this session?",
      message: form.id
        ? `"${form.title}" will update immediately for every enrolled student.`
        : `"${form.title}" will be scheduled on "${courseTitle(form.course_id)}" for ${form.date} ${form.time} (${form.timezone}) — visible to every enrolled student.`,
      confirmLabel: form.id ? "Save changes" : "Schedule session",
      variant: "brand",
    });
    if (!ok) return;
    const payload = { ...form, time: form.time.length === 5 ? `${form.time}:00` : form.time };
    if (form.id) {
      const { id, ...body } = payload;
      await api.patch(`/live-sessions/${id}`, body);
    } else {
      await api.post("/live-sessions", payload);
    }
    setModal(null);
    load();
  }

  async function deleteSession(session) {
    const ok = await confirm({
      title: "Delete this session?",
      message: `"${session.title}" will be permanently removed from the schedule. Students will no longer see it.`,
      confirmLabel: "Delete session",
    });
    if (!ok) return;
    await api.delete(`/live-sessions/${session.id}`);
    load();
  }

  async function startSession(id) {
    try {
      const res = await api.post(`/live-sessions/${id}/start`);
      setHostView({ ...hostView, [id]: res.data.join_link });
      load();
    } catch (err) {
      alert(err.message);
    }
  }

  async function endSession(session) {
    const ok = await confirm({
      title: "End this session for everyone?",
      message: `"${session.title}" will be closed immediately and every participant currently on the call will be disconnected. This can't be undone.`,
      confirmLabel: "End session",
    });
    if (!ok) return;
    await api.post(`/live-sessions/${session.id}/end`);
    const next = { ...hostView };
    delete next[session.id];
    setHostView(next);
    load();
  }

  function formatUtc(iso) {
    return new Date(iso).toLocaleString();
  }

  return (
    <div>
      <PageHeader
        eyebrow="Live"
        title="Manage live sessions"
        description="Admins schedule for every course. Instructors only schedule for courses assigned to them."
        actions={<Button onClick={() => setModal("new")}>+ Schedule session</Button>}
      />

      {sessions.length === 0 && (
        <div className="mt-8">
          <EmptyState icon="🎥" title="No live sessions scheduled" />
        </div>
      )}

      <div className="mt-6 space-y-4">
        {sessions.map((s) => {
          const status = statusBadge[s.status] || statusBadge.upcoming;
          return (
            <Card key={s.id}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <div className="font-display text-base font-bold text-ink-900">{s.title}</div>
                    <Badge variant={status.variant} dot={s.status === "live"}>{status.label}</Badge>
                  </div>
                  <div className="mt-1 text-xs text-ink-500">
                    {courseTitle(s.course_id)} · Host {s.host_name} · {formatUtc(s.scheduled_at)} ({s.scheduled_tz}) · {s.duration_minutes} min
                  </div>
                </div>
                <div className="flex flex-shrink-0 items-center gap-1">
                  <IconButton onClick={() => setModal(s)} aria-label="Edit session">
                    ✎
                  </IconButton>
                  <IconButton onClick={() => deleteSession(s)} className="hover:bg-danger-50 hover:text-danger-600" aria-label="Delete session">
                    🗑
                  </IconButton>
                </div>
              </div>
              {s.description && <RichText text={s.description} className="mt-2 text-sm text-ink-600" />}

              <div className="mt-2 text-xs text-ink-500">
                {s.ended_at && `✅ Ended at ${formatUtc(s.ended_at)}.`}
                {!s.ended_at && s.started_at && `🟢 Started at ${formatUtc(s.started_at)} — students can now join.`}
                {!s.ended_at && !s.started_at && "⏳ Not started yet — students won't see an active Join button until you start it."}
              </div>

              {!hostView[s.id] ? (
                <Button variant="success" className="mt-3" onClick={() => startSession(s.id)}>
                  {s.ended_at ? "↻ Start a new session" : "▶ Start / rejoin session"}
                </Button>
              ) : (
                <div className="mt-3">
                  <div className="aspect-video w-full max-w-3xl overflow-hidden rounded-xl bg-black">
                    <iframe
                      src={hostView[s.id]}
                      title={s.title}
                      className="h-full w-full"
                      allow="camera; microphone; fullscreen; display-capture"
                    />
                  </div>
                  <div className="mt-2 flex gap-2">
                    <Button
                      variant="secondary"
                      onClick={() => {
                        const next = { ...hostView };
                        delete next[s.id];
                        setHostView(next);
                      }}
                    >
                      Leave (keep session open)
                    </Button>
                    <Button variant="dangerSolid" onClick={() => endSession(s)}>
                      ● End session for everyone
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>

      <SessionModal
        open={!!modal}
        session={modal === "new" ? null : modal}
        courses={courses}
        timezones={timezones}
        onClose={() => setModal(null)}
        onSave={saveSession}
      />
    </div>
  );
}

function SessionModal({ open, session, courses, timezones, onClose, onSave }) {
  const [form, setForm] = useState(emptyForm);

  useEffect(() => {
    if (!open) return;
    if (session) {
      const { date, time } = isoToLocalDateTime(session.scheduled_at, session.scheduled_tz);
      setForm({
        id: session.id,
        course_id: session.course_id,
        title: session.title || "",
        description: session.description || "",
        date,
        time,
        timezone: session.scheduled_tz || "Asia/Kolkata",
        duration_minutes: session.duration_minutes || 60,
      });
    } else {
      setForm(emptyForm);
    }
  }, [open, session]);

  return (
    <Modal open={open} onClose={onClose} title={session ? "Edit live session" : "Schedule a new live session"}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!form.course_id || !form.title || !form.date) return;
          onSave(form);
        }}
      >
        <Field label="Course">
          <Select value={form.course_id} onChange={(e) => setForm({ ...form, course_id: e.target.value })} disabled={!!session}>
            <option value="">Select course</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Session title">
          <Input
            placeholder="e.g. Live Q&A: Neural Networks"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
        </Field>
        <Field label="Description (optional)">
          <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="Timezone">
          <Select value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })}>
            {timezones.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </Select>
        </Field>
        <div className="grid grid-cols-3 gap-2">
          <Field label="Date">
            <Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
          </Field>
          <Field label="Time">
            <Input type="time" value={form.time} onChange={(e) => setForm({ ...form, time: e.target.value })} />
          </Field>
          <Field label="Minutes">
            <Input
              type="number"
              min={15}
              max={300}
              step={15}
              value={form.duration_minutes}
              onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })}
            />
          </Field>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit">{session ? "Save changes" : "Schedule session"}</Button>
        </div>
      </form>
    </Modal>
  );
}
