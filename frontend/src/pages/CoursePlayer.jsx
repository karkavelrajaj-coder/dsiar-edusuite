import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { Badge, Button, LoadingScreen, ProgressBar } from "../components/ui";
import ModuleQuizPanel from "../components/ModuleQuizPanel";

/**
 * Real course-player layout: a curriculum sidebar (every lesson listed once,
 * with its completion state) and a main pane that shows exactly ONE lesson
 * at a time — video, then its resources, then a completion action. This
 * replaces the earlier "every lesson's video stacked on one long page"
 * layout, which was carried over from the Streamlit app's single-page
 * constraint and doesn't hold up as a real course player.
 *
 * A module's "steps" are its lessons followed by its quiz (if it has one) —
 * buildFlatItems() flattens the whole course into that single ordered
 * sequence, which drives progress, Next/Previous navigation, and which
 * item auto-selects on load. Without this, "Next" after the last lesson of
 * a module would skip straight to the next module instead of routing
 * through that module's quiz, and the top progress bar would only ever
 * count lessons even though quizzes are now part of "complete" too.
 */
function buildFlatItems(modules, quizStatus) {
  const items = [];
  for (const m of modules) {
    for (const l of m.lessons) {
      items.push({ type: "lesson", id: l.id, moduleId: m.id, completed: l.completed });
    }
    const qs = quizStatus[m.id];
    if (qs) {
      items.push({ type: "quiz", id: m.id, moduleId: m.id, completed: qs.passed });
    }
  }
  return items;
}

export default function CoursePlayer() {
  const { courseId } = useParams();
  const [course, setCourse] = useState(null);
  const [error, setError] = useState("");
  const [celebration, setCelebration] = useState("");
  const [activeLessonId, setActiveLessonId] = useState(null);
  const [activeQuizModuleId, setActiveQuizModuleId] = useState(null);
  const [quizStatus, setQuizStatus] = useState({}); // moduleId -> quiz summary, or null if no quiz
  const [collapsedModules, setCollapsedModules] = useState({});
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Pure fetch, no state writes — see reload() for why this matters.
  async function fetchQuizStatuses(modules) {
    const entries = await Promise.all(
      modules.map(async (m) => {
        try {
          const res = await api.get(`/modules/${m.id}/quiz`);
          return [m.id, res.data]; // null if the module has no quiz
        } catch {
          return [m.id, null];
        }
      })
    );
    return Object.fromEntries(entries);
  }

  // Fetches the course plus every module's quiz status, THEN applies both
  // to state together. Setting course before quizStatus has arrived (the
  // old approach) rendered a real frame with quizzes not yet counted —
  // "39 lessons, 3%" flashing before the quiz statuses came back and
  // recomputed it as "49 items, 4%", plus a spurious "this course doesn't
  // have any lessons yet" the instant course.modules existed but no item
  // was selected yet. Resolving both requests first and calling setCourse
  // + setQuizStatus back to back (same tick, no await between them) lets
  // React batch them into one render, so the very first render already
  // has the right combined total.
  async function reload() {
    const res = await api.get(`/courses/${courseId}`);
    const qs = await fetchQuizStatuses(res.data.modules);
    setCourse(res.data);
    setQuizStatus(qs);
    return { modules: res.data.modules, quizStatus: qs };
  }

  async function load() {
    try {
      const { modules, quizStatus: qs } = await reload();
      if (activeLessonId == null && activeQuizModuleId == null) {
        const items = buildFlatItems(modules, qs);
        const firstIncomplete = items.find((i) => !i.completed) || items[0];
        if (firstIncomplete) {
          if (firstIncomplete.type === "lesson") setActiveLessonId(firstIncomplete.id);
          else setActiveQuizModuleId(firstIncomplete.moduleId);
        }
      }
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  const flatLessons = useMemo(() => course?.modules.flatMap((m) => m.lessons) || [], [course]);
  const flatItems = useMemo(() => (course ? buildFlatItems(course.modules, quizStatus) : []), [course, quizStatus]);
  const totalItems = flatItems.length;
  const completedItems = flatItems.filter((i) => i.completed).length;
  const overallProgress = totalItems ? completedItems / totalItems : 0;

  const activeIndex = flatItems.findIndex(
    (i) => (i.type === "lesson" && i.id === activeLessonId) || (i.type === "quiz" && i.moduleId === activeQuizModuleId)
  );
  const activeItem = activeIndex >= 0 ? flatItems[activeIndex] : null;
  const activeLesson = activeItem?.type === "lesson" ? flatLessons.find((l) => l.id === activeLessonId) : null;
  const activeModule = course?.modules.find((m) => m.lessons.some((l) => l.id === activeLessonId));
  const nextItem = activeIndex >= 0 ? flatItems[activeIndex + 1] : null;
  const prevItem = activeIndex > 0 ? flatItems[activeIndex - 1] : null;

  function selectLesson(lessonId) {
    setActiveLessonId(lessonId);
    setActiveQuizModuleId(null);
    setSidebarOpen(false);
  }

  function selectQuiz(moduleId) {
    setActiveQuizModuleId(moduleId);
    setActiveLessonId(null);
    setSidebarOpen(false);
  }

  function goToItem(item) {
    if (!item) return;
    if (item.type === "lesson") selectLesson(item.id);
    else selectQuiz(item.moduleId);
  }

  async function markComplete(lessonId) {
    const res = await api.post(`/lessons/${lessonId}/complete`);
    if (res.data.certificate_issued) {
      setCelebration("🎓 Course complete and assignment approved — your certificate is ready! Check Certificates.");
    }
    const { modules, quizStatus: qs } = await reload();
    const items = buildFlatItems(modules, qs);
    const idx = items.findIndex((i) => i.type === "lesson" && i.id === lessonId);
    const next = idx >= 0 ? items[idx + 1] : null;
    if (next) goToItem(next);
    else selectLesson(lessonId);
  }

  function toggleModule(moduleId) {
    setCollapsedModules((prev) => ({ ...prev, [moduleId]: !prev[moduleId] }));
  }

  if (error) return <div className="text-sm text-danger-600">{error}</div>;
  if (!course) return <LoadingScreen label="Loading course…" />;

  return (
    <div className="-mx-4 -my-6 flex h-[calc(100vh-3.5rem)] flex-col sm:-mx-8 sm:-my-8 lg:h-screen">
      {/* Top bar */}
      <div className="flex flex-shrink-0 items-center gap-3 border-b border-ink-200 bg-white px-4 py-3 sm:px-6">
        <Link
          to="/my-learning"
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-ink-500 hover:bg-ink-100"
        >
          ←
        </Link>
        <div className="min-w-0 flex-1">
          <div className="truncate font-display text-sm font-bold text-ink-900 sm:text-base">{course.title}</div>
          <div className="mt-1 flex items-center gap-2">
            <ProgressBar value={overallProgress} className="w-32 sm:w-56" />
            <span className="text-xs font-medium text-ink-500">
              {completedItems}/{totalItems} completed · {Math.round(overallProgress * 100)}%
            </span>
          </div>
        </div>
        <button
          onClick={() => setSidebarOpen(true)}
          className="flex h-8 items-center gap-1.5 rounded-lg border border-ink-200 px-3 text-xs font-medium text-ink-600 hover:bg-ink-50 lg:hidden"
        >
          📑 Curriculum
        </button>
      </div>

      {celebration && (
        <div className="flex-shrink-0 bg-success-50 px-4 py-2.5 text-sm text-success-700 sm:px-6">{celebration}</div>
      )}

      <div className="relative flex min-h-0 flex-1">
        {/* Curriculum sidebar */}
        <aside
          className={`absolute inset-y-0 left-0 z-30 w-80 flex-shrink-0 overflow-y-auto border-r border-ink-200 bg-white transition-transform lg:static lg:z-auto lg:translate-x-0 ${
            sidebarOpen ? "translate-x-0 shadow-card-lg" : "-translate-x-full"
          }`}
        >
          <div className="flex items-center justify-between border-b border-ink-100 px-4 py-3 lg:hidden">
            <span className="text-sm font-semibold text-ink-800">Curriculum</span>
            <button onClick={() => setSidebarOpen(false)} className="text-ink-400">✕</button>
          </div>
          <div className="p-3">
            {course.modules.map((m, mi) => {
              const moduleDone = m.lessons.filter((l) => l.completed).length;
              const collapsed = collapsedModules[m.id];
              return (
                <div key={m.id} className="mb-2 overflow-hidden rounded-xl border border-ink-100">
                  <button
                    onClick={() => toggleModule(m.id)}
                    className="flex w-full items-center justify-between gap-2 bg-ink-50 px-3 py-2.5 text-left"
                  >
                    <div className="min-w-0">
                      <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-400">
                        Module {mi + 1}
                      </div>
                      <div className="truncate text-sm font-semibold text-ink-800">{m.title}</div>
                    </div>
                    <div className="flex flex-shrink-0 items-center gap-2">
                      <span className="text-[11px] font-medium text-ink-400">
                        {moduleDone}/{m.lessons.length}
                      </span>
                      <span className={`text-xs text-ink-400 transition-transform ${collapsed ? "-rotate-90" : ""}`}>▾</span>
                    </div>
                  </button>
                  {!collapsed && (
                    <ul>
                      {m.lessons.map((l) => {
                        const active = !activeQuizModuleId && l.id === activeLessonId;
                        return (
                          <li key={l.id}>
                            <button
                              onClick={() => selectLesson(l.id)}
                              className={`flex w-full items-start gap-2.5 border-t border-ink-100 px-3 py-2.5 text-left text-sm transition ${
                                active ? "bg-brand-50 text-brand-700" : "text-ink-600 hover:bg-ink-50"
                              }`}
                            >
                              <span className="mt-0.5 flex-shrink-0">
                                {l.completed ? (
                                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-success-600 text-[9px] text-white">✓</span>
                                ) : active ? (
                                  <span className="flex h-4 w-4 items-center justify-center rounded-full border-2 border-brand-600" />
                                ) : (
                                  <span className="flex h-4 w-4 items-center justify-center rounded-full border-2 border-ink-200" />
                                )}
                              </span>
                              <span className={`min-w-0 flex-1 truncate ${active ? "font-semibold" : ""}`}>{l.title}</span>
                              {l.youtube_id && <span className="flex-shrink-0 text-xs text-ink-300">▶</span>}
                            </button>
                          </li>
                        );
                      })}
                      {quizStatus[m.id] && (
                        <li>
                          <button
                            onClick={() => selectQuiz(m.id)}
                            className={`flex w-full items-start gap-2.5 border-t border-ink-100 px-3 py-2.5 text-left text-sm transition ${
                              activeQuizModuleId === m.id ? "bg-brand-50 text-brand-700" : "text-ink-600 hover:bg-ink-50"
                            }`}
                          >
                            <span className="mt-0.5 flex-shrink-0">
                              {quizStatus[m.id].passed ? (
                                <span className="flex h-4 w-4 items-center justify-center rounded-full bg-success-600 text-[9px] text-white">✓</span>
                              ) : (
                                <span className="flex h-4 w-4 items-center justify-center rounded-full border-2 border-ink-200 text-[9px]">
                                  {quizStatus[m.id].lessons_complete ? "" : "🔒"}
                                </span>
                              )}
                            </span>
                            <span className={`min-w-0 flex-1 truncate ${activeQuizModuleId === m.id ? "font-semibold" : ""}`}>
                              📝 Module Quiz
                            </span>
                          </button>
                        </li>
                      )}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        </aside>
        {sidebarOpen && (
          <div className="fixed inset-0 z-20 bg-ink-900/40 lg:hidden" onClick={() => setSidebarOpen(false)} />
        )}

        {/* Active lesson / module quiz */}
        <div className="min-w-0 flex-1 overflow-y-auto">
          {activeQuizModuleId ? (
            <div className="mx-auto max-w-3xl px-4 py-6 sm:px-8">
              <div className="text-xs font-semibold uppercase tracking-wide text-brand-600">
                {course.modules.find((m) => m.id === activeQuizModuleId)?.title}
              </div>
              <h1 className="mt-1 font-display text-xl font-bold text-ink-900 sm:text-2xl">📝 Module Quiz</h1>
              <div className="mt-5">
                <ModuleQuizPanel
                  moduleId={activeQuizModuleId}
                  onPassed={(res) => {
                    if (res.certificate_issued) {
                      setCelebration("🎓 Course complete and assignment approved — your certificate is ready! Check Certificates.");
                    }
                    load();
                  }}
                />
              </div>

              <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-ink-100 pt-6">
                <Button variant="secondary" disabled={!prevItem} onClick={() => goToItem(prevItem)}>
                  ← Previous
                </Button>
                <div className="flex-1" />
                {nextItem ? (
                  <Button variant="secondary" onClick={() => goToItem(nextItem)}>
                    {nextItem.type === "quiz" ? "Next module quiz →" : "Next lesson →"}
                  </Button>
                ) : activeItem?.completed ? (
                  // No nextItem alone just means this quiz is last in the
                  // flat sequence — it says nothing about whether THIS
                  // quiz has actually been passed yet, so it can't gate
                  // the "finished" badge on its own (that was the bug:
                  // showing "finished" while the last quiz was still
                  // unpassed, even mid-"Loading quiz…").
                  <Badge variant="success">🎉 You've finished this course</Badge>
                ) : (
                  <span className="text-xs text-ink-400">Pass this quiz above to finish the course.</span>
                )}
              </div>
            </div>
          ) : !activeLesson ? (
            <div className="p-8 text-sm text-ink-500">
              {totalItems === 0 ? "This course doesn't have any lessons yet." : "Loading…"}
            </div>
          ) : (
            <div className="mx-auto max-w-3xl px-4 py-6 sm:px-8">
              <div className="text-xs font-semibold uppercase tracking-wide text-brand-600">{activeModule?.title}</div>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <h1 className="font-display text-xl font-bold text-ink-900 sm:text-2xl">{activeLesson.title}</h1>
                {activeLesson.completed && <Badge variant="success">✓ Completed</Badge>}
              </div>

              {activeLesson.youtube_id ? (
                <div className="mt-5 aspect-video w-full overflow-hidden rounded-2xl bg-black shadow-card-lg">
                  <iframe
                    key={activeLesson.id}
                    className="h-full w-full"
                    src={`https://www.youtube.com/embed/${activeLesson.youtube_id}`}
                    title={activeLesson.title}
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                </div>
              ) : (
                <div className="mt-5 flex aspect-video w-full items-center justify-center rounded-2xl border border-dashed border-ink-200 bg-ink-50 text-sm text-ink-400">
                  No video attached to this lesson yet.
                </div>
              )}

              {(activeLesson.ppt_link || activeLesson.colab_link || activeLesson.dataset_link) && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {activeLesson.ppt_link && (
                    <ResourceLink href={activeLesson.ppt_link} icon="📊" label="Slides" />
                  )}
                  {activeLesson.colab_link && (
                    <ResourceLink href={activeLesson.colab_link} icon="💻" label="Practice link" />
                  )}
                  {activeLesson.dataset_link && (
                    <ResourceLink href={activeLesson.dataset_link} icon="📁" label="Resource" />
                  )}
                </div>
              )}

              <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-ink-100 pt-6">
                <Button variant="secondary" disabled={!prevItem} onClick={() => goToItem(prevItem)}>
                  ← Previous
                </Button>
                <div className="flex-1" />
                {!activeLesson.completed ? (
                  <Button onClick={() => markComplete(activeLesson.id)}>
                    Mark complete{nextItem ? (nextItem.type === "quiz" ? " & take quiz" : " & continue") : ""}
                  </Button>
                ) : nextItem ? (
                  <Button onClick={() => goToItem(nextItem)}>
                    {nextItem.type === "quiz" ? "Take Module Quiz →" : "Next lesson →"}
                  </Button>
                ) : (
                  <Badge variant="success">🎉 You've finished this course</Badge>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ResourceLink({ href, icon, label }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1.5 rounded-lg border border-ink-200 bg-white px-3 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-50"
    >
      {icon} {label}
    </a>
  );
}
