import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useConfirm } from "../../context/ConfirmContext";
import { BulkImportButton } from "../../components/BulkImport";
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
  Select,
  Textarea,
} from "../../components/ui";

const TRACKS = [
  { value: "course", label: "Course" },
  { value: "internship", label: "Internship" },
  { value: "diploma", label: "Diploma" },
  { value: "nano_degree", label: "Nano Degree" },
];
const trackLabel = (t) => TRACKS.find((x) => x.value === t)?.label || "Course";
const trackVariant = { course: "brand", internship: "success", diploma: "warning", nano_degree: "neutral" };

const emptyCourse = { title: "", category: "", description: "", thumbnail_url: "", is_free: true, instructor_id: "", track: "course" };
const emptyLesson = { title: "", youtube_id: "", ppt_link: "", colab_link: "", dataset_link: "" };

const QUESTION_TYPES = [
  { value: "single", label: "Single answer (MCQ)" },
  { value: "multi", label: "Multi-select" },
  { value: "true_false", label: "True / False" },
];

function emptyQuestion(n) {
  return {
    id: `q${n}`,
    type: "single",
    text: "",
    options: [
      { id: "o1", text: "" },
      { id: "o2", text: "" },
      { id: "o3", text: "" },
      { id: "o4", text: "" },
    ],
    correct_option_ids: [],
  };
}

function emptyQuizQuestions() {
  return [1, 2, 3, 4, 5].map(emptyQuestion);
}

export default function ManageCourses() {
  const { user } = useAuth();
  const confirm = useConfirm();
  const [courses, setCourses] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [expanded, setExpanded] = useState(null);
  const [modulesByCourse, setModulesByCourse] = useState({});
  const [courseModal, setCourseModal] = useState(null); // null | "new" | course object being edited
  const [quizModal, setQuizModal] = useState(null); // null | { moduleId, moduleTitle }

  async function load() {
    const res = await api.get("/courses/manage");
    setCourses(res.data);
    if (user.role === "admin") {
      const ires = await api.get("/users/instructors");
      setInstructors(ires.data);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadModules(courseId) {
    const res = await api.get(`/courses/${courseId}`);
    setModulesByCourse((prev) => ({ ...prev, [courseId]: res.data.modules }));
  }

  async function toggleExpand(courseId) {
    if (expanded === courseId) {
      setExpanded(null);
      return;
    }
    setExpanded(courseId);
    if (!modulesByCourse[courseId]) await loadModules(courseId);
  }

  async function saveCourse(form) {
    const ok = await confirm({
      title: form.id ? "Save changes to this course?" : "Create this course?",
      message: form.id
        ? `"${form.title}" will update everywhere students and instructors see it, immediately.`
        : `"${form.title}" will be created and visible to admins right away — add modules/lessons next before enrolling students.`,
      confirmLabel: form.id ? "Save changes" : "Create course",
      variant: "brand",
    });
    if (!ok) return;
    if (form.id) {
      await api.patch(`/courses/${form.id}`, {
        title: form.title,
        category: form.category,
        description: form.description,
        thumbnail_url: form.thumbnail_url,
        is_free: form.is_free,
        instructor_id: form.instructor_id || null,
        track: form.track,
      });
    } else {
      await api.post("/courses", { ...form, instructor_id: form.instructor_id || null });
    }
    setCourseModal(null);
    load();
  }

  async function deleteCourse(course) {
    const ok = await confirm({
      title: "Delete this course?",
      message: `"${course.title}" and every module, lesson, enrollment, assignment, and certificate tied to it will be permanently removed. This can't be undone.`,
      confirmLabel: "Delete course",
    });
    if (!ok) return;
    await api.delete(`/courses/${course.id}`);
    load();
  }

  async function addModule(courseId, title) {
    if (!title) return;
    const ok = await confirm({
      title: "Add this module?",
      message: `"${title}" will be added to this course, visible to admins right away.`,
      confirmLabel: "Add module",
      variant: "brand",
    });
    if (!ok) return;
    await api.post(`/courses/${courseId}/modules`, { title });
    loadModules(courseId);
  }

  async function renameModule(courseId, moduleId, title) {
    const ok = await confirm({
      title: "Rename this module?",
      message: `It will be renamed to "${title}" everywhere students see it.`,
      confirmLabel: "Save",
      variant: "brand",
    });
    if (!ok) return;
    await api.patch(`/modules/${moduleId}`, { title });
    loadModules(courseId);
  }

  async function deleteModule(courseId, module) {
    const ok = await confirm({
      title: "Delete this module?",
      message: `"${module.title}" and all ${module.lessons.length} lesson${module.lessons.length === 1 ? "" : "s"} in it will be permanently removed.`,
      confirmLabel: "Delete module",
    });
    if (!ok) return;
    await api.delete(`/modules/${module.id}`);
    loadModules(courseId);
  }

  async function addLesson(courseId, moduleId, lesson) {
    if (!lesson.title) return;
    const ok = await confirm({
      title: "Add this lesson?",
      message: `"${lesson.title}" will be added and visible to every student enrolled once they reach this module.`,
      confirmLabel: "Add lesson",
      variant: "brand",
    });
    if (!ok) return;
    await api.post(`/modules/${moduleId}/lessons`, lesson);
    loadModules(courseId);
  }

  async function updateLesson(courseId, lessonId, lesson) {
    const ok = await confirm({
      title: "Save changes to this lesson?",
      message: `"${lesson.title}" will update immediately for every student, including anyone partway through it.`,
      confirmLabel: "Save changes",
      variant: "brand",
    });
    if (!ok) return;
    await api.patch(`/lessons/${lessonId}`, lesson);
    loadModules(courseId);
  }

  async function deleteLesson(courseId, lesson) {
    const ok = await confirm({
      title: "Delete this lesson?",
      message: `"${lesson.title}" and its video/resource links will be permanently removed. Any student progress on it will also be lost.`,
      confirmLabel: "Delete lesson",
    });
    if (!ok) return;
    await api.delete(`/lessons/${lesson.id}`);
    loadModules(courseId);
  }

  const instructorName = (id) => instructors.find((i) => i.id === id)?.name;

  return (
    <div>
      <PageHeader
        eyebrow="Content"
        title="Manage courses & content"
        description="Admins manage every course. Instructors only manage courses assigned to them."
        actions={
          <div className="flex flex-wrap gap-2">
            <BulkImportButton kind="courses" label="Bulk import courses" onDone={load} />
            <BulkImportButton kind="quizzes" label="Bulk import quizzes" onDone={load} />
            <Button onClick={() => setCourseModal("new")}>+ New course</Button>
          </div>
        }
      />

      {courses.length === 0 && (
        <div className="mt-8">
          <EmptyState icon="📘" title="No courses yet" description="Create your first course to get started." />
        </div>
      )}

      <div className="mt-6 space-y-4">
        {courses.map((c) => (
          <Card key={c.id} padded={false}>
            <div className="flex items-center justify-between gap-3 p-5">
              <button onClick={() => toggleExpand(c.id)} className="flex min-w-0 flex-1 items-center gap-3 text-left">
                <span className={`flex-shrink-0 text-xs text-ink-400 transition-transform ${expanded === c.id ? "rotate-90" : ""}`}>▶</span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="truncate font-display text-base font-bold text-ink-900">{c.title}</h2>
                    {c.category && <Badge variant="brand">{c.category}</Badge>}
                    {c.is_free && <Badge variant="success">Free</Badge>}
                    <Badge variant={trackVariant[c.track] || "neutral"}>{trackLabel(c.track)}</Badge>
                  </div>
                  {/* The instructor roster is only ever fetched for admins (the
                      /users/instructors endpoint is admin-only) — an instructor
                      only ever sees their OWN assigned courses here anyway, so
                      this line would just show "—" for them. Show it for admin
                      only, where the lookup actually has data. */}
                  {user.role === "admin" && c.instructor_id && (
                    <div className="mt-0.5 text-xs text-ink-500">Instructor: {instructorName(c.instructor_id) || "—"}</div>
                  )}
                </div>
              </button>
              <div className="flex flex-shrink-0 items-center gap-1.5">
                <IconButton onClick={() => setCourseModal(c)} aria-label="Edit course">
                  ✎
                </IconButton>
                <IconButton onClick={() => deleteCourse(c)} className="hover:bg-danger-50 hover:text-danger-600" aria-label="Delete course">
                  🗑
                </IconButton>
              </div>
            </div>

            {expanded === c.id && (
              <div className="border-t border-ink-100 bg-ink-50/50 p-5">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">Modules & lessons</h3>
                <div className="mt-3">
                  <NewModuleForm onAdd={(title) => addModule(c.id, title)} />
                </div>
                <div className="mt-3 space-y-3">
                  {(modulesByCourse[c.id] || []).map((m) => (
                    <ModuleCard
                      key={m.id}
                      module={m}
                      onRename={(title) => renameModule(c.id, m.id, title)}
                      onDelete={() => deleteModule(c.id, m)}
                      onAddLesson={(lesson) => addLesson(c.id, m.id, lesson)}
                      onUpdateLesson={(lessonId, lesson) => updateLesson(c.id, lessonId, lesson)}
                      onDeleteLesson={(lesson) => deleteLesson(c.id, lesson)}
                      onManageQuiz={() => setQuizModal({ moduleId: m.id, moduleTitle: m.title })}
                    />
                  ))}
                  {(modulesByCourse[c.id] || []).length === 0 && (
                    <div className="rounded-lg border border-dashed border-ink-200 px-4 py-6 text-center text-sm text-ink-400">
                      No modules yet — add one above.
                    </div>
                  )}
                </div>
              </div>
            )}
          </Card>
        ))}
      </div>

      <CourseModal
        open={!!courseModal}
        course={courseModal === "new" ? null : courseModal}
        instructors={instructors}
        isAdmin={user.role === "admin"}
        onClose={() => setCourseModal(null)}
        onSave={saveCourse}
      />

      <QuizModal
        open={!!quizModal}
        moduleId={quizModal?.moduleId}
        moduleTitle={quizModal?.moduleTitle}
        onClose={() => setQuizModal(null)}
      />
    </div>
  );
}

function CourseModal({ open, course, instructors, isAdmin, onClose, onSave }) {
  const confirm = useConfirm();
  const [form, setForm] = useState(emptyCourse);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  async function uploadThumbnail(file) {
    if (!file) return;
    setUploadError("");
    const ok = await confirm({
      title: "Replace this course's thumbnail?",
      message: "The new image takes effect everywhere this course is shown — catalog, course page — as soon as it's uploaded.",
      confirmLabel: "Upload",
      variant: "brand",
    });
    if (!ok) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post(`/courses/${form.id}/thumbnail`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setForm((prev) => ({ ...prev, thumbnail_url: res.data.thumbnail_url }));
    } catch (e) {
      setUploadError(e.message);
    } finally {
      setUploading(false);
    }
  }

  useEffect(() => {
    if (open) {
      setForm(
        course
          ? {
              id: course.id,
              title: course.title || "",
              category: course.category || "",
              description: course.description || "",
              thumbnail_url: course.thumbnail_url || "",
              is_free: !!course.is_free,
              instructor_id: course.instructor_id || "",
              track: course.track || "course",
            }
          : emptyCourse
      );
    }
  }, [open, course]);

  return (
    <Modal open={open} onClose={onClose} title={course ? "Edit course" : "Add a new course"} wide>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!form.title) return;
          onSave(form);
        }}
      >
        <Field label="Title">
          <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        </Field>
        <Field label="Category">
          <Input
            placeholder="e.g. Artificial Intelligence"
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
          />
        </Field>
        <Field label="Description">
          <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field
          label="Thumbnail"
          hint={
            form.id
              ? "Upload an image below, or paste a URL instead."
              : "Paste a URL for now — image upload is available once the course is created (save it, then reopen Edit)."
          }
        >
          <Input
            placeholder="https://… (or leave blank and upload an image below)"
            value={form.thumbnail_url?.startsWith("data:") ? "" : form.thumbnail_url}
            onChange={(e) => setForm({ ...form, thumbnail_url: e.target.value })}
          />
          {form.thumbnail_url?.startsWith("data:") && (
            <div className="mt-2 flex items-center gap-2">
              <img src={form.thumbnail_url} alt="Current thumbnail" className="h-12 w-20 rounded-md object-cover" />
              <span className="text-xs text-ink-500">Current uploaded thumbnail</span>
            </div>
          )}
          {form.id && (
            <div className="mt-2">
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                disabled={uploading}
                onChange={(e) => uploadThumbnail(e.target.files?.[0])}
                className="w-full rounded-lg border border-ink-200 px-3 py-2 text-sm"
              />
              <p className="mt-1 text-[11px] text-ink-400">PNG, JPEG, or WEBP, up to 2MB.</p>
              {uploading && <p className="mt-1 text-xs text-ink-500">Uploading…</p>}
              {uploadError && <p className="mt-1 text-xs text-danger-600">{uploadError}</p>}
            </div>
          )}
        </Field>
        <Field label="Track" hint="Labels this course everywhere a student sees it (title, certificate) — the same for every student enrolled. Content and completion requirements never differ by track.">
          <Select value={form.track} onChange={(e) => setForm({ ...form, track: e.target.value })}>
            {TRACKS.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </Select>
        </Field>
        {isAdmin && (
          <Field label="Instructor">
            <Select value={form.instructor_id} onChange={(e) => setForm({ ...form, instructor_id: e.target.value })}>
              <option value="">— Unassigned (admin managed) —</option>
              {instructors.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name}
                </option>
              ))}
            </Select>
          </Field>
        )}
        <label className="flex items-center gap-2 text-sm text-ink-700">
          <input
            type="checkbox"
            checked={form.is_free}
            onChange={(e) => setForm({ ...form, is_free: e.target.checked })}
          />
          Free course
        </label>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit">{course ? "Save changes" : "Create course"}</Button>
        </div>
      </form>
    </Modal>
  );
}

function NewModuleForm({ onAdd }) {
  const [title, setTitle] = useState("");
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        onAdd(title);
        setTitle("");
      }}
    >
      <Input placeholder="New module title" value={title} onChange={(e) => setTitle(e.target.value)} />
      <Button type="submit" variant="secondary" className="flex-shrink-0">
        + Add module
      </Button>
    </form>
  );
}

function ModuleCard({ module: m, onRename, onDelete, onAddLesson, onUpdateLesson, onDeleteLesson, onManageQuiz }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(m.title);
  const [addingLesson, setAddingLesson] = useState(false);

  return (
    <div className="rounded-xl border border-ink-200 bg-white">
      <div className="flex items-center justify-between gap-2 px-4 py-3">
        {editing ? (
          <form
            className="flex flex-1 gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              onRename(title);
              setEditing(false);
            }}
          >
            <Input autoFocus value={title} onChange={(e) => setTitle(e.target.value)} />
            <Button size="sm" type="submit">Save</Button>
            <Button size="sm" type="button" variant="secondary" onClick={() => { setEditing(false); setTitle(m.title); }}>
              Cancel
            </Button>
          </form>
        ) : (
          <>
            <div className="font-semibold text-ink-800">{m.title}</div>
            <div className="flex flex-shrink-0 items-center gap-1">
              <Button size="sm" variant="secondary" onClick={() => setAddingLesson((v) => !v)}>
                + Lesson
              </Button>
              <Button size="sm" variant="secondary" onClick={onManageQuiz}>
                🧩 Quiz
              </Button>
              <IconButton onClick={() => setEditing(true)} aria-label="Rename module">
                ✎
              </IconButton>
              <IconButton onClick={onDelete} className="hover:bg-danger-50 hover:text-danger-600" aria-label="Delete module">
                🗑
              </IconButton>
            </div>
          </>
        )}
      </div>

      {m.lessons.length > 0 && (
        <ul className="divide-y divide-ink-100 border-t border-ink-100">
          {m.lessons.map((l) => (
            <LessonRow key={l.id} lesson={l} onUpdate={(data) => onUpdateLesson(l.id, data)} onDelete={() => onDeleteLesson(l)} />
          ))}
        </ul>
      )}

      {addingLesson && (
        <div className="border-t border-ink-100 p-3">
          <LessonForm
            onSubmit={(lesson) => {
              onAddLesson(lesson);
              setAddingLesson(false);
            }}
            onCancel={() => setAddingLesson(false)}
            submitLabel="Add lesson"
          />
        </div>
      )}
    </div>
  );
}

function LessonRow({ lesson, onUpdate, onDelete }) {
  const [editing, setEditing] = useState(false);

  if (editing) {
    return (
      <li className="p-3">
        <LessonForm
          initial={lesson}
          onSubmit={(data) => {
            onUpdate(data);
            setEditing(false);
          }}
          onCancel={() => setEditing(false)}
          submitLabel="Save lesson"
        />
      </li>
    );
  }

  return (
    <li className="flex items-center justify-between gap-2 px-4 py-2.5 text-sm">
      <div className="min-w-0 flex-1">
        <div className="truncate text-ink-800">{lesson.title}</div>
        <div className="mt-0.5 flex flex-wrap gap-1.5 text-[11px] text-ink-400">
          {lesson.youtube_id ? <Badge variant="brand">▶ video</Badge> : <span>no video</span>}
          {lesson.ppt_link && <Badge variant="neutral">slides</Badge>}
          {lesson.colab_link && <Badge variant="neutral">practice link</Badge>}
          {lesson.dataset_link && <Badge variant="neutral">resource</Badge>}
        </div>
      </div>
      <div className="flex flex-shrink-0 items-center gap-1">
        <IconButton onClick={() => setEditing(true)} aria-label="Edit lesson">
          ✎
        </IconButton>
        <IconButton onClick={onDelete} className="hover:bg-danger-50 hover:text-danger-600" aria-label="Delete lesson">
          🗑
        </IconButton>
      </div>
    </li>
  );
}

function LessonForm({ initial, onSubmit, onCancel, submitLabel }) {
  const [lesson, setLesson] = useState(initial ? { ...emptyLesson, ...initial } : emptyLesson);

  return (
    <form
      className="grid grid-cols-1 gap-2 sm:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (!lesson.title) return;
        onSubmit(lesson);
      }}
    >
      <Input
        className="sm:col-span-2"
        placeholder="Lesson title"
        value={lesson.title}
        onChange={(e) => setLesson({ ...lesson, title: e.target.value })}
      />
      <Input
        placeholder="YouTube video ID"
        value={lesson.youtube_id}
        onChange={(e) => setLesson({ ...lesson, youtube_id: e.target.value })}
      />
      <Input
        placeholder="Slides link"
        value={lesson.ppt_link}
        onChange={(e) => setLesson({ ...lesson, ppt_link: e.target.value })}
      />
      <Input
        placeholder="Practice link (GitHub, Colab, CodeSandbox, Figma…)"
        value={lesson.colab_link}
        onChange={(e) => setLesson({ ...lesson, colab_link: e.target.value })}
      />
      <Input
        placeholder="Resource link (dataset, template, reading material…)"
        value={lesson.dataset_link}
        onChange={(e) => setLesson({ ...lesson, dataset_link: e.target.value })}
      />
      <div className="flex gap-2 sm:col-span-2">
        <Button type="submit" size="sm">{submitLabel}</Button>
        <Button type="button" size="sm" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

/**
 * Module quiz builder — exactly 5 questions, each single-answer MCQ,
 * multi-select, or true/false. Loads the existing quiz (if any) when
 * opened, lets the admin/instructor edit every question inline, and saves
 * the whole set in one PUT. A separate "Results" view shows every
 * student's attempts for this module's quiz.
 */
function QuizModal({ open, moduleId, moduleTitle, onClose }) {
  const confirm = useConfirm();
  const [questions, setQuestions] = useState(emptyQuizQuestions());
  const [hasQuiz, setHasQuiz] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("edit"); // "edit" | "results"
  const [attempts, setAttempts] = useState([]);

  useEffect(() => {
    if (!open || !moduleId) return;
    setError("");
    setTab("edit");
    setLoading(true);
    api
      .get(`/modules/${moduleId}/quiz/manage`)
      .then((res) => {
        if (res.data) {
          setQuestions(res.data.questions);
          setHasQuiz(true);
        } else {
          setQuestions(emptyQuizQuestions());
          setHasQuiz(false);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [open, moduleId]);

  function updateQuestion(qIndex, patch) {
    setQuestions((prev) => prev.map((q, i) => (i === qIndex ? { ...q, ...patch } : q)));
  }

  function updateOption(qIndex, oIndex, text) {
    setQuestions((prev) =>
      prev.map((q, i) => {
        if (i !== qIndex) return q;
        const options = q.options.map((o, j) => (j === oIndex ? { ...o, text } : o));
        return { ...q, options };
      })
    );
  }

  function toggleCorrect(qIndex, optionId) {
    setQuestions((prev) =>
      prev.map((q, i) => {
        if (i !== qIndex) return q;
        if (q.type === "multi") {
          const already = q.correct_option_ids.includes(optionId);
          const correct_option_ids = already
            ? q.correct_option_ids.filter((id) => id !== optionId)
            : [...q.correct_option_ids, optionId];
          return { ...q, correct_option_ids };
        }
        // single / true_false: exactly one correct option
        return { ...q, correct_option_ids: [optionId] };
      })
    );
  }

  function changeType(qIndex, type) {
    setQuestions((prev) =>
      prev.map((q, i) => {
        if (i !== qIndex) return q;
        if (type === "true_false") {
          return {
            ...q,
            type,
            options: [
              { id: "o1", text: "True" },
              { id: "o2", text: "False" },
            ],
            correct_option_ids: [],
          };
        }
        // switching away from true_false (or between single/multi) —
        // restore 4 option slots if it currently only has 2.
        const options =
          q.options.length < 4
            ? [...q.options, { id: "o3", text: "" }, { id: "o4", text: "" }]
            : q.options;
        return { ...q, type, options, correct_option_ids: [] };
      })
    );
  }

  function validate() {
    for (let i = 0; i < questions.length; i++) {
      const q = questions[i];
      if (!q.text.trim()) return `Question ${i + 1} needs text.`;
      const filledOptions = q.options.filter((o) => o.text.trim());
      if (filledOptions.length < 2) return `Question ${i + 1} needs at least 2 options.`;
      if (q.correct_option_ids.length === 0) return `Question ${i + 1}: mark the correct answer.`;
      const filledIds = new Set(filledOptions.map((o) => o.id));
      if (q.correct_option_ids.some((id) => !filledIds.has(id))) {
        return `Question ${i + 1}: the correct answer is marked on a blank option — fill it in or re-select.`;
      }
    }
    return null;
  }

  async function save() {
    const err = validate();
    if (err) {
      setError(err);
      return;
    }
    setError("");
    const ok = await confirm({
      title: hasQuiz ? "Save changes to this quiz?" : "Create this module's quiz?",
      message: "Students will see these exact 5 questions the next time they open this module's quiz.",
      confirmLabel: "Save quiz",
      variant: "brand",
    });
    if (!ok) return;

    setSaving(true);
    try {
      const payload = {
        questions: questions.map((q) => ({
          ...q,
          options: q.options.filter((o) => o.text.trim()),
        })),
      };
      await api.put(`/modules/${moduleId}/quiz`, payload);
      setHasQuiz(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function deleteQuiz() {
    const ok = await confirm({
      title: "Delete this module's quiz?",
      message: "All 5 questions and every student's attempt history for this quiz will be permanently removed.",
      confirmLabel: "Delete quiz",
    });
    if (!ok) return;
    await api.delete(`/modules/${moduleId}/quiz`);
    setHasQuiz(false);
    setQuestions(emptyQuizQuestions());
  }

  async function loadResults() {
    setTab("results");
    const res = await api.get(`/modules/${moduleId}/quiz/attempts`);
    setAttempts(res.data);
  }

  return (
    <Modal open={open} onClose={onClose} title={`Quiz — ${moduleTitle || ""}`} wide>
      {loading ? (
        <div className="py-8 text-center text-sm text-ink-400">Loading…</div>
      ) : (
        <>
          <div className="mb-4 flex gap-2 border-b border-ink-100 pb-3">
            <Button size="sm" variant={tab === "edit" ? "primary" : "secondary"} onClick={() => setTab("edit")}>
              Edit questions
            </Button>
            {hasQuiz && (
              <Button size="sm" variant={tab === "results" ? "primary" : "secondary"} onClick={loadResults}>
                Results
              </Button>
            )}
          </div>

          {error && <div className="mb-3 rounded-lg bg-danger-50 px-3.5 py-2.5 text-sm text-danger-700">{error}</div>}

          {tab === "edit" ? (
            <div className="max-h-[60vh] space-y-5 overflow-y-auto pr-1">
              {questions.map((q, qIndex) => (
                <div key={q.id} className="rounded-xl border border-ink-200 p-3.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wide text-ink-400">
                      Question {qIndex + 1}
                    </span>
                    <Select
                      className="w-auto py-1 text-xs"
                      value={q.type}
                      onChange={(e) => changeType(qIndex, e.target.value)}
                    >
                      {QUESTION_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </Select>
                  </div>
                  <Input
                    className="mt-2"
                    placeholder="Question text"
                    value={q.text}
                    onChange={(e) => updateQuestion(qIndex, { text: e.target.value })}
                  />
                  <div className="mt-2 space-y-1.5">
                    {q.options.map((o, oIndex) => (
                      <div key={o.id} className="flex items-center gap-2">
                        <input
                          type={q.type === "multi" ? "checkbox" : "radio"}
                          name={`correct-${q.id}`}
                          checked={q.correct_option_ids.includes(o.id)}
                          onChange={() => toggleCorrect(qIndex, o.id)}
                        />
                        {q.type === "true_false" ? (
                          <span className="flex-1 text-sm text-ink-700">{o.text}</span>
                        ) : (
                          <Input
                            className="flex-1"
                            placeholder={`Option ${oIndex + 1}`}
                            value={o.text}
                            onChange={(e) => updateOption(qIndex, oIndex, e.target.value)}
                          />
                        )}
                      </div>
                    ))}
                  </div>
                  <p className="mt-1.5 text-[11px] text-ink-400">
                    {q.type === "multi" ? "Check every correct option." : "Select the one correct option."}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="max-h-[60vh] overflow-y-auto">
              {attempts.length === 0 ? (
                <div className="py-8 text-center text-sm text-ink-400">No attempts yet.</div>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs font-semibold uppercase tracking-wide text-ink-400">
                      <th className="py-1.5">Student</th>
                      <th className="py-1.5">Attempt</th>
                      <th className="py-1.5">Score</th>
                      <th className="py-1.5">Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attempts.map((a) => (
                      <tr key={a.id} className="border-t border-ink-100">
                        <td className="py-2">
                          <div className="text-ink-800">{a.student_name}</div>
                          <div className="text-xs text-ink-400">{a.student_email}</div>
                        </td>
                        <td className="py-2 text-ink-600">#{a.attempt_number}</td>
                        <td className="py-2 text-ink-600">{a.score_percent}%</td>
                        <td className="py-2">
                          <Badge variant={a.passed ? "success" : "danger"}>{a.passed ? "Passed" : "Failed"}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {tab === "edit" && (
            <div className="mt-4 flex justify-between gap-2 border-t border-ink-100 pt-4">
              <div>
                {hasQuiz && (
                  <Button type="button" variant="danger" onClick={deleteQuiz}>
                    Delete quiz
                  </Button>
                )}
              </div>
              <div className="flex gap-2">
                <Button type="button" variant="secondary" onClick={onClose}>
                  Close
                </Button>
                <Button type="button" onClick={save} disabled={saving}>
                  {saving ? "Saving…" : "Save quiz"}
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </Modal>
  );
}
