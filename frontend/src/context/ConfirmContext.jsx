import { createContext, useCallback, useContext, useRef, useState } from "react";
import { Button } from "../components/ui";

/**
 * App-wide "are you sure?" dialog. Every destructive or hard-to-undo action
 * (delete, role change, ending a live session for everyone, grading a
 * submission, submitting an assignment) routes through this instead of
 * firing immediately — and instead of the browser's ugly native confirm().
 *
 * Usage:
 *   const confirm = useConfirm();
 *   async function handleDelete() {
 *     const ok = await confirm({
 *       title: "Delete this course?",
 *       message: "This permanently removes the course and all its modules and lessons.",
 *       confirmLabel: "Delete course",
 *     });
 *     if (!ok) return;
 *     ...
 *   }
 */
const ConfirmContext = createContext(null);

export function ConfirmProvider({ children }) {
  const [state, setState] = useState(null);
  const resolver = useRef(null);
  const [busy, setBusy] = useState(false);

  const confirm = useCallback((options) => {
    setState({
      title: "Are you sure?",
      message: "",
      confirmLabel: "Yes, proceed",
      cancelLabel: "Cancel",
      variant: "danger", // "danger" | "brand"
      ...options,
    });
    setBusy(false);
    return new Promise((resolve) => {
      resolver.current = resolve;
    });
  }, []);

  function settle(result) {
    setState(null);
    setBusy(false);
    resolver.current?.(result);
    resolver.current = null;
  }

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {state && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-ink-900/50 px-4 backdrop-blur-[1px]"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="confirm-dialog-title"
          onKeyDown={(e) => {
            if (e.key === "Escape") settle(false);
          }}
        >
          <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-card-lg">
            <div
              className={`flex h-11 w-11 items-center justify-center rounded-full text-xl ${
                state.variant === "danger" ? "bg-danger-50 text-danger-600" : "bg-brand-50 text-brand-600"
              }`}
            >
              {state.variant === "danger" ? "⚠" : "❓"}
            </div>
            <h2 id="confirm-dialog-title" className="mt-3 font-display text-lg font-bold text-ink-900">
              {state.title}
            </h2>
            {state.message && <p className="mt-1.5 text-sm leading-relaxed text-ink-500">{state.message}</p>}
            <div className="mt-6 flex justify-end gap-2">
              <Button variant="secondary" autoFocus onClick={() => settle(false)}>
                {state.cancelLabel}
              </Button>
              <Button
                variant={state.variant === "danger" ? "dangerSolid" : "primary"}
                disabled={busy}
                onClick={() => {
                  setBusy(true);
                  settle(true);
                }}
              >
                {state.confirmLabel}
              </Button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  const ctx = useContext(ConfirmContext);
  if (!ctx) throw new Error("useConfirm must be used within a ConfirmProvider");
  return ctx;
}
