/**
 * Shared design-system primitives for the LMS.
 *
 * The goal: every page composes from the SAME half-dozen building blocks
 * (Card, Button, Badge, ProgressBar, Modal, EmptyState, PageHeader) instead
 * of hand-rolling its own <div className="rounded-xl border ...">. That's
 * what makes the app read as one enterprise product instead of a stack of
 * independently-styled forms.
 */
import { useEffect } from "react";

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && (
          <div className="text-xs font-semibold uppercase tracking-wider text-brand-600">
            {eyebrow}
          </div>
        )}
        <h1 className="mt-1 font-display text-2xl font-bold text-ink-900 sm:text-3xl">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm text-ink-500">{description}</p>}
      </div>
      {actions && <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ children, className = "", padded = true, as: As = "div", ...rest }) {
  return (
    <As
      className={`rounded-2xl border border-ink-200/70 bg-white shadow-card ${
        padded ? "p-5 sm:p-6" : ""
      } ${className}`}
      {...rest}
    >
      {children}
    </As>
  );
}

const buttonVariants = {
  primary:
    "bg-brand-600 text-white hover:bg-brand-700 focus-visible:ring-brand-300 disabled:bg-brand-300",
  secondary:
    "bg-white text-ink-700 border border-ink-200 hover:bg-ink-50 focus-visible:ring-ink-200",
  ghost: "text-ink-600 hover:bg-ink-100 focus-visible:ring-ink-200",
  danger:
    "bg-white text-danger-600 border border-danger-100 hover:bg-danger-50 focus-visible:ring-danger-200",
  dangerSolid: "bg-danger-600 text-white hover:bg-danger-700 focus-visible:ring-danger-200",
  success: "bg-success-600 text-white hover:bg-success-700 focus-visible:ring-success-200",
};

const buttonSizes = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-5 py-2.5 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  as: As = "button",
  ...rest
}) {
  return (
    <As
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition focus-visible:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-60 ${buttonVariants[variant]} ${buttonSizes[size]} ${className}`}
      {...rest}
    />
  );
}

const badgeVariants = {
  brand: "bg-brand-50 text-brand-700",
  neutral: "bg-ink-100 text-ink-600",
  success: "bg-success-50 text-success-700",
  warning: "bg-warning-50 text-warning-700",
  danger: "bg-danger-50 text-danger-700",
  live: "bg-live-50 text-live-600",
};

export function Badge({ children, variant = "neutral", dot = false, className = "" }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${badgeVariants[variant]} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

export function ProgressBar({ value, className = "", trackClassName = "", barClassName = "" }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className={`h-2 w-full overflow-hidden rounded-full bg-ink-100 ${trackClassName} ${className}`}>
      <div
        className={`h-full rounded-full bg-brand-600 transition-all ${barClassName}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function ProgressRing({ value, size = 44, stroke = 4 }) {
  const pct = Math.max(0, Math.min(1, value));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - pct);
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--color-ink-100)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-brand-600)"
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-[11px] font-bold text-ink-700">
        {Math.round(pct * 100)}%
      </div>
    </div>
  );
}

export function EmptyState({ icon = "📭", title, description, action }) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-ink-200 bg-ink-50/50 px-6 py-14 text-center">
      <div className="text-3xl">{icon}</div>
      <div className="mt-3 font-display text-base font-semibold text-ink-800">{title}</div>
      {description && <p className="mt-1 max-w-sm text-sm text-ink-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Spinner({ className = "" }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

export function LoadingScreen({ label = "Loading…" }) {
  return (
    <div className="flex items-center gap-2 py-16 text-sm text-ink-400">
      <Spinner className="h-4 w-4" />
      {label}
    </div>
  );
}

export function IconButton({ children, className = "", ...rest }) {
  return (
    <button
      className={`inline-flex h-8 w-8 items-center justify-center rounded-lg text-ink-500 transition hover:bg-ink-100 hover:text-ink-800 ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Field({ label, hint, children }) {
  return (
    <label className="block">
      {label && <span className="mb-1 block text-xs font-semibold text-ink-600">{label}</span>}
      {children}
      {hint && <span className="mt-1 block text-xs text-ink-400">{hint}</span>}
    </label>
  );
}

const inputBase =
  "w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100";

export function Input(props) {
  return <input className={inputBase} {...props} />;
}

export function Textarea(props) {
  return <textarea className={`${inputBase} resize-y`} rows={3} {...props} />;
}

export function Select(props) {
  return <select className={inputBase} {...props} />;
}

const URL_PATTERN = /(https?:\/\/[^\s<]+|www\.[^\s<]+)/g;

/**
 * Renders free-text the user typed (an assignment description, a session
 * description, a pasted GitHub/Colab/Drive submission link, ...) the way
 * they actually typed it: line breaks and blank-line paragraphs preserved
 * (a plain `<p>{text}</p>` collapses all of that per normal HTML
 * whitespace rules), and any http(s)/www. URL turned into a real clickable
 * link instead of inert text. Used everywhere free text like this is
 * displayed, so the whole app is consistent.
 */
export function RichText({ text, className = "", as: As = "div" }) {
  if (!text) return <As className={`whitespace-pre-wrap break-words ${className}`} />;
  const nodes = [];
  let lastIndex = 0;
  let match;
  const re = new RegExp(URL_PATTERN);
  while ((match = re.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    let url = match[0];
    // Don't swallow trailing punctuation that's almost certainly not part
    // of the URL itself (end of sentence, closing paren, etc).
    const trailingMatch = url.match(/[),.;:!?'"]+$/);
    let trailing = "";
    if (trailingMatch) {
      trailing = trailingMatch[0];
      url = url.slice(0, -trailing.length);
    }
    const href = url.startsWith("www.") ? `https://${url}` : url;
    nodes.push(
      <a
        key={match.index}
        href={href}
        target="_blank"
        rel="noreferrer"
        className="font-medium text-brand-600 underline decoration-brand-200 underline-offset-2 hover:text-brand-700"
      >
        {url}
      </a>
    );
    if (trailing) nodes.push(trailing);
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));

  return <As className={`whitespace-pre-wrap break-words ${className}`}>{nodes}</As>;
}

export function Modal({ open, onClose, title, children, wide = false }) {
  useEffect(() => {
    if (!open) return;
    function onKey(e) {
      if (e.key === "Escape") onClose?.();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 px-4 backdrop-blur-[1px]">
      <div
        className={`max-h-[85vh] w-full overflow-y-auto rounded-2xl bg-white p-6 shadow-card-lg ${
          wide ? "max-w-2xl" : "max-w-md"
        }`}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg font-bold text-ink-900">{title}</h2>
          <IconButton onClick={onClose} aria-label="Close">
            ✕
          </IconButton>
        </div>
        {children}
      </div>
    </div>
  );
}
