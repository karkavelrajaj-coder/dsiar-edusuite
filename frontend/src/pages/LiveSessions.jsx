import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Badge, Button, Card, EmptyState, Field, LoadingScreen, PageHeader, RichText, Select } from "../components/ui";

const statusBadge = {
  upcoming: { variant: "brand", label: "Upcoming" },
  live: { variant: "live", label: "● Live now" },
  ended: { variant: "neutral", label: "Ended" },
};

export default function LiveSessions() {
  const [sessions, setSessions] = useState([]);
  const [timezones, setTimezones] = useState([]);
  const [viewTz, setViewTz] = useState("Asia/Kolkata");
  const [joined, setJoined] = useState({}); // sessionId -> join_link
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    const [sessRes, tzRes, meRes] = await Promise.all([
      api.get("/my/live-sessions"),
      api.get("/timezones"),
      api.get("/auth/me"),
    ]);
    setSessions(sessRes.data);
    setTimezones(tzRes.data.options);
    setViewTz(meRes.data.timezone || "Asia/Kolkata");
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function handleTzChange(tz) {
    setViewTz(tz);
    await api.patch("/users/me/timezone", { timezone: tz });
  }

  async function handleJoin(sessionId) {
    const res = await api.post(`/live-sessions/${sessionId}/join`);
    setJoined({ ...joined, [sessionId]: res.data.join_link });
  }

  function formatInTz(iso, tz) {
    try {
      return new Date(iso).toLocaleString("en-US", { timeZone: tz, dateStyle: "medium", timeStyle: "short" });
    } catch {
      return iso;
    }
  }

  if (loading) return <LoadingScreen label="Loading live sessions…" />;

  return (
    <div>
      <PageHeader
        eyebrow="Live"
        title="Live sessions"
        description="Cohort sessions hosted by your instructors."
        actions={
          <Button variant="secondary" onClick={load}>
            ↻ Refresh
          </Button>
        }
      />

      <Card className="mt-6 max-w-md">
        <Field label="🌐 View times in">
          <Select value={viewTz} onChange={(e) => handleTzChange(e.target.value)}>
            {timezones.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </Select>
        </Field>
      </Card>

      {sessions.length === 0 && (
        <div className="mt-8">
          <EmptyState icon="🎥" title="No live sessions scheduled" description="Nothing scheduled yet for your courses." />
        </div>
      )}

      <div className="mt-6 space-y-4">
        {sessions.map((s) => {
          const status = statusBadge[s.status] || statusBadge.upcoming;
          return (
            <Card key={s.id}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-display text-base font-bold text-ink-900">{s.title}</h2>
                    <Badge variant={status.variant} dot={s.status === "live"}>{status.label}</Badge>
                  </div>
                  <div className="mt-1 text-xs text-ink-500">
                    {s.course_title} · Host {s.host_name} · {formatInTz(s.scheduled_at, viewTz)} · {s.duration_minutes} min
                  </div>
                </div>
              </div>
              {s.description && <RichText text={s.description} className="mt-2 text-sm text-ink-600" />}

              {!joined[s.id] ? (
                s.can_join ? (
                  <Button variant="dangerSolid" className="mt-3" onClick={() => handleJoin(s.id)}>
                    ● Join session
                  </Button>
                ) : (
                  <div className="mt-2 text-xs text-ink-500">{s.join_blocked_reason}</div>
                )
              ) : (
                <div className="mt-3">
                  <div className="aspect-video w-full max-w-3xl overflow-hidden rounded-xl bg-black">
                    <iframe
                      src={joined[s.id]}
                      title={s.title}
                      className="h-full w-full"
                      allow="camera; microphone; fullscreen; display-capture"
                    />
                  </div>
                  <Button
                    variant="secondary"
                    className="mt-2"
                    onClick={() => {
                      const next = { ...joined };
                      delete next[s.id];
                      setJoined(next);
                    }}
                  >
                    Leave session
                  </Button>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
