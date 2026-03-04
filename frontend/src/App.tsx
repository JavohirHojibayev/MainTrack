import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppThemeProvider } from "@/context/ThemeContext";
import { AuthProvider } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import TurnstileJournalPage from "@/pages/TurnstileJournalPage";
import EsmoJournalPage from "@/pages/EsmoJournalPage";
import EmployeesPage from "@/pages/EmployeesPage";
import DevicesPage from "@/pages/DevicesPage";
import ReportsPage from "@/pages/ReportsPage";
import AdminUsersPage from "@/pages/AdminUsersPage";
import ToolsPage from "@/pages/ToolsPage";

export default function App() {
    return (
        <AppThemeProvider>
            <AuthProvider>
                <BrowserRouter>
                    <Routes>
                        <Route path="/login" element={<LoginPage />} />
                        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                            <Route path="/dashboard" element={<DashboardPage />} />
                            <Route path="/turnstile-journal" element={<TurnstileJournalPage />} />
                            <Route path="/esmo-journal" element={<EsmoJournalPage />} />
                            <Route
                                path="/employees"
                                element={
                                    <ProtectedRoute allowedRoles={["superadmin", "admin", "dispatcher", "medical", "warehouse"]}>
                                        <EmployeesPage />
                                    </ProtectedRoute>
                                }
                            />
                            <Route
                                path="/devices"
                                element={
                                    <ProtectedRoute allowedRoles={["superadmin", "admin", "dispatcher", "medical", "warehouse"]}>
                                        <DevicesPage />
                                    </ProtectedRoute>
                                }
                            />
                            <Route path="/reports" element={<ReportsPage />} />
                            <Route path="/lamp-self-rescuer" element={<ToolsPage />} />
                            <Route path="/tools" element={<Navigate to="/lamp-self-rescuer" replace />} />
                            <Route
                                path="/user-management"
                                element={
                                    <ProtectedRoute allowedRoles={["superadmin", "admin", "dispatcher", "medical", "warehouse"]}>
                                        <AdminUsersPage />
                                    </ProtectedRoute>
                                }
                            />
                            <Route path="/admin/users" element={<Navigate to="/user-management" replace />} />
                        </Route>
                        <Route path="*" element={<Navigate to="/dashboard" replace />} />
                    </Routes>
                </BrowserRouter>
            </AuthProvider>
        </AppThemeProvider>
    );
}
