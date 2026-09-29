import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { ProtectedPlatformRoute } from "./components/ProtectedPlatformRoute";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { PlatformAuthProvider } from "./context/PlatformAuthContext";
import { ConfirmProvider } from "./context/ConfirmContext";
import Login from "./pages/Login";
import Catalog from "./pages/Catalog";
import MyLearning from "./pages/MyLearning";
import CoursePlayer from "./pages/CoursePlayer";
import Assignments from "./pages/Assignments";
import Certificates from "./pages/Certificates";
import LiveSessions from "./pages/LiveSessions";
import ManageCourses from "./pages/admin/ManageCourses";
import ManageUsers from "./pages/admin/ManageUsers";
import Grading from "./pages/admin/Grading";
import ManageLiveSessions from "./pages/admin/ManageLiveSessions";
import Settings from "./pages/admin/Settings";
import PlatformLogin from "./pages/platform/PlatformLogin";
import PlatformConsole from "./pages/platform/PlatformConsole";

function HomeRedirect() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "admin") return <Navigate to="/admin/users" replace />;
  if (user.role === "instructor") return <Navigate to="/admin/courses" replace />;
  return <Navigate to="/catalog" replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <PlatformAuthProvider>
        <ConfirmProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/platform/login" element={<PlatformLogin />} />
            <Route element={<ProtectedPlatformRoute />}>
              <Route path="/platform" element={<PlatformConsole />} />
            </Route>

            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route path="/" element={<HomeRedirect />} />
                <Route path="/catalog" element={<Catalog />} />
                <Route path="/my-learning" element={<MyLearning />} />
                <Route path="/course/:courseId" element={<CoursePlayer />} />
                <Route path="/assignments" element={<Assignments />} />
                <Route path="/certificates" element={<Certificates />} />
                <Route path="/live-sessions" element={<LiveSessions />} />

                <Route element={<ProtectedRoute roles={["admin", "instructor"]} />}>
                  <Route path="/admin/courses" element={<ManageCourses />} />
                  <Route path="/admin/grading" element={<Grading />} />
                  <Route path="/admin/live-sessions" element={<ManageLiveSessions />} />
                </Route>

                <Route element={<ProtectedRoute roles={["admin"]} />}>
                  <Route path="/admin/users" element={<ManageUsers />} />
                  <Route path="/admin/settings" element={<Settings />} />
                </Route>
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ConfirmProvider>
      </PlatformAuthProvider>
    </AuthProvider>
  );
}
