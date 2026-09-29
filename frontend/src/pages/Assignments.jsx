import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Badge, Button, Card, EmptyState, LoadingScreen, PageHeader, RichText, Textarea } from "../components/ui";
import { useConfirm } from "../context/ConfirmContext";

const statusBadge = {
  approved: { variant: "success", label: "✓ Approved" },
  rejected: { variant: "danger", label: "✕ Needs revision" },
  pending: { variant: "warning", label: "⏳ Pending review" },
};

export default function Assignments() {
  const confirm = useConfirm();
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [drafts, setDrafts] = useState({});

  async function load() {
    setLoading(true);
    const res = await api.get("/my/assignments");
    setAssignments(res.data);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function submit(assignmentId) {
    const text = (drafts[assignmentId] || "").trim();
    if (!text) return;
    const ok = await confirm({
      title: "Submit this assignment?",
      message: "Once submitted you won't be able to edit it — your instructor will review it and it's what gets graded.",
      confirmLabel: "Submit assignment",
      variant: "brand",
    });
    if (!ok) return;
    await api.post(`/assignments/${assignmentId}/submit`, { link_or_text: text });
    load();
  }

  if (loading) return <LoadingScreen label="Loading assignments…" />;

  return (
    <div>
      <PageHeader eyebrow="Coursework" title="Assignments" description="Submit your work and track review status per course." />

      {assignments.length === 0 && (
        <div className="mt-8">
          <EmptyState icon="📝" title="No assignments yet" description="Enroll in a course to see its assignments here." />
        </div>
      )}

      <div className="mt-6 space-y-4">
        {assignments.map((a) => {
          const status = a.submission ? statusBadge[a.submission.status] || statusBadge.pending : null;
          return (
            <Card key={a.id}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h2 className="font-display text-base font-bold text-ink-900">{a.title}</h2>
                  <div className="mt-0.5 text-xs text-ink-500">
                    {a.course_title} · Due {a.due_date || "no deadline"}
                  </div>
                </div>
                {status && <Badge variant={status.variant}>{status.label}</Badge>}
              </div>

              {a.locked ? (
                <div className="mt-3 rounded-lg bg-warning-50 px-3 py-2 text-sm text-warning-700">
                  🔒 Locked — finish every module in <strong>{a.course_title}</strong> (lessons + module quiz,
                  passed) to unlock this assignment ({a.lessons_completed}/{a.lessons_total} lessons completed
                  {a.quizzes_total > 0 && <>, {a.quizzes_completed}/{a.quizzes_total} quizzes passed</>}).
                </div>
              ) : (
                <>
                  <RichText text={a.description} className="mt-2 text-sm text-ink-600" />

                  {a.submission ? (
                    <div className="mt-3 rounded-lg bg-ink-50 px-3.5 py-3 text-sm">
                      <div className="text-ink-700">
                        <span className="font-semibold text-ink-500">Your submission: </span>
                        <RichText as="span" text={a.submission.link_or_text} />
                      </div>
                      {a.submission.status !== "pending" && (
                        <div className="mt-1.5 text-ink-700">
                          <span className="font-semibold text-ink-500">Grade: </span>
                          {a.submission.grade ?? "—"}
                          <span className="mx-1.5 text-ink-300">·</span>
                          <span className="font-semibold text-ink-500">Feedback: </span>
                          <RichText as="span" text={a.submission.feedback || "—"} />
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="mt-3 space-y-2">
                      <Textarea
                        placeholder="Paste your project link (GitHub/Colab/Drive) or answer"
                        value={drafts[a.id] || ""}
                        onChange={(e) => setDrafts({ ...drafts, [a.id]: e.target.value })}
                      />
                      <Button size="sm" onClick={() => submit(a.id)}>
                        Submit assignment
                      </Button>
                    </div>
                  )}
                </>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
