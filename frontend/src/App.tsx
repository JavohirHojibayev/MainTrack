import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppThemeProvider } from "@/context/ThemeContext";
import { AuthProvider } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import EventsPage from "@/pages/EventsPage";
import EmployeesPage from "@/pages/EmployeesPage";
import DevicesPage from "@/pages/DevicesPage";
import ReportsPage from "@/pages/ReportsPage";
import AdminUsersPage from "@/pages/AdminUsersPage";

export default function App() {
    return (
        <AppThemeProvider>
            <AuthProvider>
                <BrowserRouter>
                    <Routes>
                        <Route path="/login" element={<LoginPage />} />
                        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                            <Route path="/dashboard" element={<DashboardPage />} />
                            <Route path="/events" element={<EventsPage />} />
                            <Route path="/employees" element={<EmployeesPage />} />
                            <Route path="/devices" element={<DevicesPage />} />
                            <Route path="/reports" element={<ReportsPage />} />
                            <Route path="/admin/users" element={<AdminUsersPage />} />
                        </Route>
                        <Route path="*" element={<Navigate to="/dashboard" replace />} />
                    </Routes>
                </BrowserRouter>
            </AuthProvider>
        </AppThemeProvider>
    );
}
