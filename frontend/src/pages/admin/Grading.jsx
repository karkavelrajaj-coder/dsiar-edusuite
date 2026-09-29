import { useEffect, useState } from "react";
import { api } from "../../api/client";
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
import { useConfirm } from "../../context/ConfirmContext";
import { BulkImportButton } from "../../components/BulkImport";

const emptyAssignment = { course_id: "", title: "", description: "", due_date: "" };

const statusVariant = { pending: "warning", approved: "success", rejected: "danger" };

export default function Grading() {
  const confirm = useConfirm();
  const [courses, setCourses] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [submissionsByAssignment, setSubmissionsByAssignment] = useState({});
  const [assignmentModal, setAssignmentModal] = useState(null); // null | "new" | assignment
  const [drafts, setDrafts] = useState({});

  async function load() {
    const [cRes, aRes] = await Promise.all([api.get("/courses/manage"), api.get("/assignments/manage")]);
    setCourses(cRes.data);
    setAssignments(aRes.data);
    for (const a of aRes.data) loadSubmissions(a.id);
  }

  async function loadSubmissions(assignmentId) {
    const res = await api.get(`/assignments/${assignmentId}/submissions`);
    setSubmissionsByAssignment((prev) => ({ ...prev, [assignmentId]: res.data }));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const courseTitle = (id) => courses.find((c) => c.id === id)?.title || "Unknown";

  async function saveAssignment(form) {
    if (form.id) {
      await api.patch(`/assignments/${form.id}`, {
        title: form.title,
        description: form.description,
        due_date: form.due_date || null,
      });
    } else {
      await api.post("/assignments", form);
    }
    setAssignmentModal(null);
    load();
  }

  async function deleteAssignment(assignment) {
    const ok = await confirm({
      title: "Delete this assignment?",
      message: `"${assignment.title}" and every student submission against it will be permanently removed.`,
      confirmLabel: "Delete assignment",
    });
    if (!ok) return;
    await api.delete(`/assignments/${assignment.id}`);
    load();
  }

  function updateDraft(subId, field, value) {
    setDrafts((prev) => ({ ...prev, [subId]: { ...prev[subId], [field]: value } }));
  }

  async function saveGrade(assignmentId, sub) {
    const draft = drafts[sub.id] || {};
    const status = draft.status ?? sub.status;
    const grade = draft.grade ?? sub.grade ?? 0;
    const ok = await confirm({
      title: "Save this grade?",
      message:
        status === "approved"
          ? `${sub.student_name} will be marked "approved" with a grade of ${grade}. If they've also finished every lesson, this issues their certificate immediately.`
          : `${sub.student_name}'s submission will be marked "${status}" with a grade of ${grade}, visible to them right away.`,
      confirmLabel: "Save grade",
      variant: "brand",
    });
    if (!ok) return;
    await api.patch(`/submissions/${sub.id}`, {
      grade,
      status,
      feedback: draft.feedback ?? sub.feedback ?? "",
    });
    loadSubmissions(assignmentId);
  }

  return (
    <div>
      <PageHeader
        eyebrow="Coursework"
        title="Assignments & grading"
        description="Post assignments and review student submissions."
        actions={
          <div className="flex flex-wrap gap-2">
            <BulkImportButton kind="assignments" label="Bulk import assignments" onDone={load} />
            <Button onClick={() => setAssignmentModal("new")}>+ New assignment</Button>
          </div>
        }
      />

      {assignments.length === 0 && (
        <div className="mt-8">
          <EmptyState icon="📥" title="No assignments posted yet" />
        </div>
      )}

      <div className="mt-6 space-y-4">
        {assignments.map((a) => (
          <Card key={a.id}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <h2 className="font-display text-base font-bold text-ink-900">{a.title}</h2>
                <div className="mt-0.5 text-xs text-ink-500">
                  {courseTitle(a.course_id)} · Due {a.due_date || "no deadline"}
                </div>
              </div>
              <div className="flex flex-shrink-0 items-center gap-1">
                <IconButton onClick={() => setAssignmentModal(a)} aria-label="Edit assignment">
                  ✎
                </IconButton>
                <IconButton onClick={() => deleteAssignment(a)} className="hover:bg-danger-50 hover:text-danger-600" aria-label="Delete assignment">
                  🗑
                </IconButton>
              </div>
            </div>
            <RichText text={a.description} className="mt-2 text-sm text-ink-600" />

            <div className="mt-4 space-y-3">
              {(submissionsByAssignment[a.id] || []).length === 0 && (
                <div className="text-xs text-ink-400">No submissions yet.</div>
              )}
              {(submissionsByAssignment[a.id] || []).map((s) => (
                <div key={s.id} className="rounded-xl border border-ink-100 bg-ink-50 p-3.5">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm text-ink-800">
                      {s.student_name} <span className="text-ink-400">({s.student_email})</span>
                    </div>
                    <Badge variant={statusVariant[s.status] || "warning"}>{s.status}</Badge>
                  </div>
                  <div className="mt-1 text-sm text-ink-600">
                    Submission: <RichText as="span" text={s.link_or_text} />
                  </div>
                  <div className="mt-2.5 grid grid-cols-1 gap-2 sm:grid-cols-3">
                    <Input
                      type="number"
                      min={0}
                      max={100}
                      placeholder="Grade"
                      defaultValue={s.grade ?? ""}
                      onChange={(e) => updateDraft(s.id, "grade", Number(e.target.value))}
                    />
                    <Select defaultValue={s.status} onChange={(e) => updateDraft(s.id, "status", e.target.value)}>
                      <option value="pending">pending</option>
                      <option value="approved">approved</option>
                      <option value="rejected">rejected</option>
                    </Select>
                    <Button size="sm" onClick={() => saveGrade(a.id, s)}>
                      Save grade
                    </Button>
                  </div>
                  <Input
                    className="mt-2"
                    placeholder="Feedback"
                    defaultValue={s.feedback}
                    onChange={(e) => updateDraft(s.id, "feedback", e.target.value)}
                  />
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      <AssignmentModal
        open={!!assignmentModal}
        assignment={assignmentModal === "new" ? null : assignmentModal}
        courses={courses}
        onClose={() => setAssignmentModal(null)}
        onSave={saveAssignment}
      />
    </div>
  );
}

function AssignmentModal({ open, assignment, courses, onClose, onSave }) {
  const [form, setForm] = useState(emptyAssignment);

  useEffect(() => {
    if (open) {
      setForm(
        assignment
          ? {
              id: assignment.id,
              course_id: assignment.course_id,
              title: assignment.title || "",
              description: assignment.description || "",
              due_date: assignment.due_date || "",
            }
          : emptyAssignment
      );
    }
  }, [open, assignment]);

  return (
    <Modal open={open} onClose={onClose} title={assignment ? "Edit assignment" : "Post a new assignment"}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!form.course_id || !form.title) return;
          onSave(form);
        }}
      >
        <Field label="Course">
          <Select value={form.course_id} onChange={(e) => setForm({ ...form, course_id: e.target.value })} disabled={!!assignment}>
            <option value="">Select course</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Title">
          <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <Field label="Description / instructions">
          <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="Due date">
          <Input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit">{assignment ? "Save changes" : "Post assignment"}</Button>
        </div>
      </form>
    </Modal>
  );
}
