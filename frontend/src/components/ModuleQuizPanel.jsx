import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Badge, Button } from "./ui";
import { useConfirm } from "../context/ConfirmContext";

/**
 * The student-facing quiz-taking view for one module — locked state (finish
 * your lessons first), the question form, and the pass/fail result with a
 * per-question review after submitting. Rendered inside CoursePlayer in
 * place of the video player when the student selects a module's quiz.
 */
export default function ModuleQuizPanel({ moduleId, onPassed }) {
  const confirm = useConfirm();
  const [quiz, setQuiz] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [answers, setAnswers] = useState({}); // question_id -> [option_id,...]
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  async function load() {
    setLoading(true);
    setResult(null);
    setAnswers({});
    try {
      const res = await api.get(`/modules/${moduleId}/quiz`);
      setQuiz(res.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [moduleId]);

  function toggleAnswer(question, optionId) {
    setAnswers((prev) => {
      const current = prev[question.id] || [];
      if (question.type === "multi") {
        const next = current.includes(optionId)
          ? current.filter((id) => id !== optionId)
          : [...current, optionId];
        return { ...prev, [question.id]: next };
      }
      return { ...prev, [question.id]: [optionId] };
    });
  }

  async function submit() {
    const unanswered = quiz.questions.filter((q) => !(answers[q.id] || []).length);
    if (unanswered.length) {
      setError(`Answer every question first (${unanswered.length} left).`);
      return;
    }
    setError("");
    const ok = await confirm({
      title: "Submit this quiz?",
      message: "You won't be able to change your answers after this.",
      confirmLabel: "Submit quiz",
      variant: "brand",
    });
    if (!ok) return;

    setSubmitting(true);
    try {
      const payload = {
        answers: quiz.questions.map((q) => ({ question_id: q.id, selected_option_ids: answers[q.id] || [] })),
      };
      const res = await api.post(`/modules/${moduleId}/quiz/submit`, payload);
      setResult(res.data);
      if (res.data.passed) onPassed?.(res.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <div className="py-8 text-center text-sm text-ink-400">Loading quiz…</div>;
  if (error && !quiz) return <div className="text-sm text-danger-600">{error}</div>;
  if (!quiz) return <div className="text-sm text-ink-500">This module doesn't have a quiz yet.</div>;

  if (!quiz.lessons_complete) {
    return (
      <div className="rounded-2xl border border-dashed border-ink-200 bg-ink-50 px-6 py-10 text-center">
        <div className="text-2xl">🔒</div>
        <div className="mt-2 font-display text-sm font-semibold text-ink-800">Finish this module's lessons first</div>
        <p className="mt-1 text-sm text-ink-500">The quiz unlocks once every lesson in this module is marked complete.</p>
      </div>
    );
  }

  // Result screen (just submitted, or re-opening after already passing —
  // show the review from the submit response; for a bare revisit with no
  // fresh submit, fall back to the summary from the GET).
  if (result) {
    const correctCount = result.review.filter((r) => r.correct).length;
    return (
      <div>
        <ResultBanner passed={result.passed} score={result.score_percent} passPercent={result.pass_percent} />
        <div className="mt-4 text-xs font-semibold uppercase tracking-wide text-ink-400">
          {correctCount}/{result.review.length} correct
        </div>
        <div className="mt-2 space-y-3">
          {quiz.questions.map((q) => {
            const r = result.review.find((rr) => rr.question_id === q.id);
            return (
              <div
                key={q.id}
                className={`rounded-xl border p-3.5 ${r?.correct ? "border-success-200 bg-success-50" : "border-danger-200 bg-danger-50"}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="text-sm font-medium text-ink-800">{q.text}</div>
                  <Badge variant={r?.correct ? "success" : "danger"}>{r?.correct ? "Correct" : "Incorrect"}</Badge>
                </div>
                <ul className="mt-2 space-y-1 text-xs text-ink-600">
                  {q.options.map((o) => {
                    const wasSelected = r?.selected_option_ids.includes(o.id);
                    const wasCorrect = r?.correct_option_ids.includes(o.id);
                    return (
                      <li key={o.id} className={wasCorrect ? "font-semibold text-success-700" : wasSelected ? "text-danger-700" : ""}>
                        {wasCorrect ? "✓" : wasSelected ? "✗" : "·"} {o.text}
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>
        {!result.passed && (
          <Button className="mt-4" onClick={load}>
            Try again
          </Button>
        )}
      </div>
    );
  }

  if (quiz.passed) {
    return (
      <div>
        <ResultBanner passed score={quiz.best_score} passPercent={quiz.pass_percent} />
        <p className="mt-3 text-sm text-ink-500">You've already passed this module's quiz.</p>
      </div>
    );
  }

  if (!quiz.can_attempt) {
    return (
      <div className="rounded-2xl border border-dashed border-danger-200 bg-danger-50 px-6 py-10 text-center">
        <div className="text-2xl">⚠️</div>
        <div className="mt-2 font-display text-sm font-semibold text-danger-800">No attempts remaining</div>
        <p className="mt-1 text-sm text-danger-600">
          You've used all {quiz.max_attempts} allowed attempts without passing. Contact your instructor.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-500">
        <span>
          Pass mark: {quiz.pass_percent}% · {quiz.max_attempts === 0 ? "Unlimited attempts" : `${quiz.attempts_used}/${quiz.max_attempts} attempts used`}
        </span>
      </div>

      {error && <div className="mt-3 rounded-lg bg-danger-50 px-3.5 py-2.5 text-sm text-danger-700">{error}</div>}

      <div className="mt-4 space-y-4">
        {quiz.questions.map((q, i) => (
          <div key={q.id} className="rounded-xl border border-ink-200 p-3.5">
            <div className="text-sm font-semibold text-ink-800">
              {i + 1}. {q.text}
            </div>
            <div className="mt-2 space-y-1.5">
              {q.options.map((o) => (
                <label key={o.id} className="flex items-center gap-2 text-sm text-ink-700">
                  <input
                    type={q.type === "multi" ? "checkbox" : "radio"}
                    name={q.id}
                    checked={(answers[q.id] || []).includes(o.id)}
                    onChange={() => toggleAnswer(q, o.id)}
                  />
                  {o.text}
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      <Button className="mt-4" onClick={submit} disabled={submitting}>
        {submitting ? "Submitting…" : "Submit quiz"}
      </Button>
    </div>
  );
}

function ResultBanner({ passed, score, passPercent }) {
  return (
    <div className={`rounded-2xl border px-5 py-4 ${passed ? "border-success-200 bg-success-50" : "border-danger-200 bg-danger-50"}`}>
      <div className={`font-display text-lg font-bold ${passed ? "text-success-700" : "text-danger-700"}`}>
        {passed ? "🎉 Passed!" : "Not quite — try again"}
      </div>
      <div className={`mt-1 text-sm ${passed ? "text-success-600" : "text-danger-600"}`}>
        Score: {score}% (pass mark {passPercent}%)
      </div>
    </div>
  );
}
