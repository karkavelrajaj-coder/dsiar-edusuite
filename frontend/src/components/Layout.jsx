import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const studentLinks = [
  { to: "/catalog", label: "Course Catalog", icon: "📚" },
  { to: "/my-learning", label: "My Learning", icon: "🎓" },
  { to: "/assignments", label: "Assignments", icon: "📝" },
  { to: "/certificates", label: "Certificates", icon: "🏆" },
];

// Live Sessions was originally an add-on built only for D'siar Tech — it's
// off by default for every client (tenants_col().features.live_sessions,
// switched on per company from the Super Admin console) and simply isn't
// shown in navigation unless the current company has it enabled.
const liveSessionLink = { to: "/live-sessions", label: "Live Sessions", icon: "🎥" };
const manageLiveSessionLink = { to: "/admin/live-sessions", label: "Manage Live Sessions", icon: "🗓️" };

const instructorLinks = [
  { to: "/admin/courses", label: "Manage Courses", icon: "🛠️" },
  { to: "/admin/grading", label: "Assignments & Grading", icon: "📥" },
];

const adminOnlyLinks = [
  { to: "/admin/users", label: "Manage Users", icon: "👥" },
  { to: "/admin/settings", label: "Settings", icon: "⚙️" },
];

const roleLabel = { admin: "Administrator", instructor: "Instructor", student: "Student" };

function initials(name = "") {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const liveSessionsOn = !!user.features?.live_sessions;

  let workspaceLinks = [];
  if (user.role === "instructor") workspaceLinks = instructorLinks;
  if (user.role === "admin") workspaceLinks = [...adminOnlyLinks, ...instructorLinks];
  if (liveSessionsOn && (user.role === "admin" || user.role === "instructor")) {
    workspaceLinks = [...workspaceLinks, manageLiveSessionLink];
  }

  const learningLinks = liveSessionsOn ? [...studentLinks, liveSessionLink] : studentLinks;

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  const Nav = (
    <>
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 font-display text-sm font-bold text-white">
          DT
        </div>
        <div className="leading-tight">
          <div className="font-display text-sm font-bold text-white">D'siar Tech</div>
          <div className="text-[11px] font-medium text-ink-400">Learning Platform</div>
        </div>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 pb-4">
        {workspaceLinks.length > 0 && (
          <div>
            <div className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-500">
              Workspace
            </div>
            <div className="space-y-0.5">
              {workspaceLinks.map((l) => (
                <NavItem key={l.to} {...l} />
              ))}
            </div>
          </div>
        )}
        <div>
          <div className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-ink-500">
            Learning
          </div>
          <div className="space-y-0.5">
            {learningLinks.map((l) => (
              <NavItem key={l.to} {...l} />
            ))}
          </div>
        </div>
      </nav>

      <div className="border-t border-white/10 px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-brand-500/90 text-xs font-bold text-white">
            {initials(user.name) || "U"}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-white">{user.name}</div>
            <div className="truncate text-xs text-ink-400">{roleLabel[user.role] || user.role}</div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="mt-3 w-full rounded-lg border border-white/10 px-3 py-1.5 text-sm font-medium text-ink-300 transition hover:border-white/20 hover:bg-white/5 hover:text-white"
        >
          ↩ Log out
        </button>
      </div>
    </>
  );

  return (
    <div className="flex min-h-screen bg-ink-50">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 flex-shrink-0 flex-col bg-ink-900 lg:flex">{Nav}</aside>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div className="absolute inset-0 bg-ink-900/50" onClick={() => setMobileOpen(false)} />
          <aside className="relative flex w-64 flex-col bg-ink-900">{Nav}</aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 flex-shrink-0 items-center gap-3 border-b border-ink-200 bg-white px-4 lg:hidden">
          <button
            onClick={() => setMobileOpen(true)}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-ink-600 hover:bg-ink-100"
            aria-label="Open menu"
          >
            ☰
          </button>
          <div className="font-display text-sm font-bold text-ink-900">D'siar Tech LMS</div>
        </header>
        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-8 sm:py-8">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

function NavItem({ to, label, icon }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
          isActive ? "bg-brand-600 text-white shadow-card" : "text-ink-300 hover:bg-white/5 hover:text-white"
        }`
      }
    >
      <span className="text-base leading-none">{icon}</span>
      {label}
    </NavLink>
  );
}
