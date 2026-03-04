import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

interface ProtectedRouteProps {
    children: React.ReactNode;
    allowedRoles?: string[];
    redirectTo?: string;
}

export default function ProtectedRoute({ children, allowedRoles, redirectTo = "/dashboard" }: ProtectedRouteProps) {
    const { token, role } = useAuth();
    if (!token) return <Navigate to="/login" replace />;
    if (allowedRoles && allowedRoles.length > 0) {
        const currentRole = String(role || "").toLowerCase();
        const isAllowed = allowedRoles.some((allowedRole) => allowedRole.toLowerCase() === currentRole);
        if (!isAllowed) return <Navigate to={redirectTo} replace />;
    }
    return <>{children}</>;
}
