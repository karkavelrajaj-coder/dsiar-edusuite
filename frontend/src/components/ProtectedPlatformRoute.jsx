import { Navigate, Outlet } from "react-router-dom";
import { usePlatformAuth } from "../context/PlatformAuthContext";

export function ProtectedPlatformRoute() {
  const { admin, loading } = usePlatformAuth();

  if (loading) {
    return <div className="flex h-screen items-center justify-center text-gray-500">Loading…</div>;
  }

  if (!admin) return <Navigate to="/platform/login" replace />;

  return <Outlet />;
}
