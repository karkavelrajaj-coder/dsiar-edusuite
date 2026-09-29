import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { Badge, Button, Card, Field, Input, PageHeader, Select } from "../../components/ui";
import { useConfirm } from "../../context/ConfirmContext";
import { BulkImportButton } from "../../components/BulkImport";

const roleVariant = { admin: "brand", instructor: "success", student: "neutral" };

// Track is set on the COURSE itself now (Manage Courses), the same for
// every student enrolled — it's shown here read-only, next to each
// enrollment, so there's still a way to see it at a glance.
const TRACKS = [
  { value: "course", label: "Course" },
  { value: "internship", label: "Internship" },
  { value: "diploma", label: "Diploma" },
  { value: "nano_degree", label: "Nano Degree" },
];
const trackLabel = (t) => TRACKS.find((x) => x.value === t)?.label || "Course";
const trackVariant = { course: "brand", internship: "success", diploma: "warning", nano_degree: "neutral" };

export default function ManageUsers() {
  const confirm = useConfirm();
  const [users, setUsers] = useState([]);
  const [courses, setCourses] = useState([]);
  const [enrollments, setEnrollments] = useState([]);
  const [newAccount, setNewAccount] = useState({ name: "", email: "", password: "", role: "student" });
  const [enrollForm, setEnrollForm] = useState({ user_id: "", course_id: "" });
  const [error, setError] = useState("");

  async function load() {
    const [uRes, cRes, eRes] = await Promise.all([
      api.get("/users"),
      api.get("/courses/manage"),
      api.get("/enrollments"),
    ]);
    setUsers(uRes.data);
    setCourses(cRes.data);
    setEnrollments(eRes.data);
  }

  useEffect(() => {
    load();
  }, []);

  async function createAccount(e) {
    e.preventDefault();
    setError("");
    if (newAccount.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    try {
      await api.post("/users", newAccount);
      setNewAccount({ name: "", email: "", password: "", role: "student" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function enrollStudent(e) {
    e.preventDefault();
    setError("");
    if (!enrollForm.user_id || !enrollForm.course_id) return;
    try {
      await api.post("/enrollments", enrollForm);
      setEnrollForm({ user_id: "", course_id: "" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function removeEnrollment(enrollment) {
    const ok = await confirm({
      title: "Remove this enrollment?",
      message: `${enrollment.student_name} will immediately lose access to "${enrollment.course_title}", including its lessons, assignments, and certificate eligibility.`,
      confirmLabel: "Remove enrollment",
    });
    if (!ok) return;
    await api.delete(`/enrollments/${enrollment.id}`);
    load();
  }

  async function updateRole(targetUser, role) {
    if (role === targetUser.role) return;
    const ok = await confirm({
      title: "Change this user's role?",
      message: `${targetUser.name} will change from "${targetUser.role}" to "${role}" and their permissions across the whole platform will change immediately.`,
      confirmLabel: `Change to ${role}`,
      variant: "brand",
    });
    if (!ok) return;
    await api.patch(`/users/${targetUser.id}/role`, { role });
    load();
  }

  async function toggleStatus(targetUser) {
    const disabling = !targetUser.disabled;
    const ok = await confirm({
      title: disabling ? "Deactivate this account?" : "Reactivate this account?",
      message: disabling
        ? `${targetUser.name} won't be able to log in anymore and drops out of the enroll/assign pickers. Nothing of theirs — enrollments, progress, submissions, certificates${targetUser.role === "instructor" ? ", or the courses they teach" : ""} — is deleted, and you can reactivate them anytime.`
        : `${targetUser.name} will be able to log in again and reappear in the enroll/assign pickers.`,
      confirmLabel: disabling ? "Deactivate" : "Reactivate",
      variant: disabling ? "danger" : "brand",
    });
    if (!ok) return;
    setError("");
    try {
      await api.patch(`/users/${targetUser.id}/status`, { disabled: disabling });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  const students = users.filter((u) => u.role === "student" && !u.disabled);

  return (
    <div>
      <PageHeader
        eyebrow="Access"
        title="Manage users"
        description="Only admins create accounts and enroll students — there's no public sign-up, which keeps course access tied to confirmed payment."
        actions={<BulkImportButton kind="enrollments" label="Bulk import enrollments" onDone={load} />}
      />

      {error && <div className="mt-4 rounded-lg bg-danger-50 px-3.5 py-2.5 text-sm text-danger-700">{error}</div>}

      <div className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card as="form" onSubmit={createAccount} className="space-y-3">
          <h2 className="font-display text-sm font-bold text-ink-900">➕ Create a new account</h2>
          <Field label="Full name">
            <Input value={newAccount.name} onChange={(e) => setNewAccount({ ...newAccount, name: e.target.value })} />
          </Field>
          <Field label="Email">
            <Input value={newAccount.email} onChange={(e) => setNewAccount({ ...newAccount, email: e.target.value })} />
          </Field>
          <Field label="Temporary password">
            <Input
              type="password"
              value={newAccount.password}
              onChange={(e) => setNewAccount({ ...newAccount, password: e.target.value })}
            />
          </Field>
          <Field label="Role">
            <Select value={newAccount.role} onChange={(e) => setNewAccount({ ...newAccount, role: e.target.value })}>
              <option value="student">student</option>
              <option value="instructor">instructor</option>
              <option value="admin">admin</option>
            </Select>
          </Field>
          <Button type="submit" className="w-full">Create account</Button>
        </Card>

        <Card as="form" onSubmit={enrollStudent} className="space-y-3">
          <h2 className="font-display text-sm font-bold text-ink-900">🎓 Enroll a student in a course</h2>
          <Field label="Student">
            <Select value={enrollForm.user_id} onChange={(e) => setEnrollForm({ ...enrollForm, user_id: e.target.value })}>
              <option value="">Select student</option>
              {students.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.email})
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Course">
            <Select value={enrollForm.course_id} onChange={(e) => setEnrollForm({ ...enrollForm, course_id: e.target.value })}>
              <option value="">Select course (they've paid for this)</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </Select>
          </Field>
          <Button type="submit" className="w-full">Enroll student</Button>

          <div className="pt-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">Current enrollments</h3>
            <div className="mt-2 max-h-56 overflow-y-auto rounded-lg border border-ink-100">
              <table className="w-full text-sm">
                <tbody>
                  {enrollments.length === 0 && (
                    <tr>
                      <td className="px-3 py-3 text-xs text-ink-400">No enrollments yet.</td>
                    </tr>
                  )}
                  {enrollments.map((e) => (
                    <tr key={e.id} className="border-t border-ink-100 first:border-0">
                      <td className="px-3 py-2">
                        <div className="text-ink-800">{e.student_name}</div>
                        <div className="text-xs text-ink-400">{e.course_title}</div>
                        <div className="mt-1">
                          <Badge variant={trackVariant[e.track] || "neutral"}>{trackLabel(e.track)}</Badge>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-right align-top">
                        <button onClick={() => removeEnrollment(e)} className="text-xs font-medium text-danger-600 hover:underline">
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      </div>

      <Card className="mt-6" padded={false}>
        <div className="p-5 pb-0">
          <h2 className="font-display text-sm font-bold text-ink-900">All users</h2>
        </div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-t border-ink-100 text-left text-xs font-semibold uppercase tracking-wide text-ink-400">
                <th className="px-5 py-2.5">Name</th>
                <th className="px-5 py-2.5">Email</th>
                <th className="px-5 py-2.5">Role</th>
                <th className="px-5 py-2.5">Status</th>
                <th className="px-5 py-2.5">Change role</th>
                <th className="px-5 py-2.5">Account</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className={`border-t border-ink-100 ${u.disabled ? "opacity-60" : ""}`}>
                  <td className="px-5 py-2.5 font-medium text-ink-800">{u.name}</td>
                  <td className="px-5 py-2.5 text-ink-500">{u.email}</td>
                  <td className="px-5 py-2.5">
                    <Badge variant={roleVariant[u.role] || "neutral"}>{u.role}</Badge>
                  </td>
                  <td className="px-5 py-2.5">
                    <Badge variant={u.disabled ? "danger" : "success"}>{u.disabled ? "Deactivated" : "Active"}</Badge>
                  </td>
                  <td className="px-5 py-2.5">
                    <Select
                      value={u.role}
                      onChange={(e) => updateRole(u, e.target.value)}
                      className="w-auto py-1 text-xs"
                      disabled={u.disabled}
                    >
                      <option value="student">student</option>
                      <option value="instructor">instructor</option>
                      <option value="admin">admin</option>
                    </Select>
                  </td>
                  <td className="px-5 py-2.5">
                    <button
                      onClick={() => toggleStatus(u)}
                      className={`text-xs font-medium hover:underline ${u.disabled ? "text-success-600" : "text-danger-600"}`}
                    >
                      {u.disabled ? "Reactivate" : "Deactivate"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
