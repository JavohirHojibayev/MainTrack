import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
    Box, Typography, Table, TableBody, TableCell, TableHead, TableRow,
    Button, Dialog, DialogTitle, DialogContent, DialogActions, TextField,
    Select, MenuItem, IconButton, CircularProgress
} from "@mui/material";
import AddIcon from "@mui/icons-material/AddRounded";
import LockResetIcon from "@mui/icons-material/LockResetRounded";
import DeleteIcon from "@mui/icons-material/DeleteRounded";
import VisibilityIcon from "@mui/icons-material/VisibilityRounded";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOffRounded";
import GlassCard from "@/components/GlassCard";
import StatusPill from "@/components/StatusPill";
import { fetchUsers, createUser, resetPassword, deleteUser, type User } from "@/api/users";
import { useAppTheme } from "@/context/ThemeContext";
import { useAuth } from "@/context/AuthContext";

const roles = ["admin", "dispatcher", "viewer"] as const;

function extractApiErrorMessage(error: unknown): string {
    const fallback = "Unknown error";
    if (!(error instanceof Error)) return fallback;
    try {
        const parsed = JSON.parse(error.message);
        if (typeof parsed?.detail === "string") return parsed.detail;
    } catch {
        // keep original message
    }
    return error.message || fallback;
}

export default function AdminUsersPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const { role } = useAuth();
    const canManageUsers = String(role || "").toLowerCase() === "superadmin";
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(false);

    // Create User State
    const [createOpen, setCreateOpen] = useState(false);
    const [newUser, setNewUser] = useState<{ username: string; password: string; role: (typeof roles)[number] }>({
        username: "",
        password: "",
        role: "viewer",
    });
    const [showCreatePass, setShowCreatePass] = useState(false);
    const [creating, setCreating] = useState(false);

    // Reset Password State
    const [resetOpen, setResetOpen] = useState(false);
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [resetUsername, setResetUsername] = useState("");
    const [newPass, setNewPass] = useState("");
    const [showNewPass, setShowNewPass] = useState(false);
    const [resetting, setResetting] = useState(false);

    // Delete User State
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [userToDelete, setUserToDelete] = useState<User | null>(null);
    const [deleting, setDeleting] = useState(false);

    const load = async () => {
        setLoading(true);
        try {
            const data = await fetchUsers();
            setUsers(data);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { void load(); }, []);

    const usernameError = newUser.username.trim().length > 0 && newUser.username.trim().length < 3;
    const passwordError = newUser.password.length > 0 && newUser.password.length < 6;
    const canCreate =
        newUser.username.trim().length >= 3 &&
        newUser.password.length >= 6 &&
        roles.includes(newUser.role);
    const resetUsernameTrim = resetUsername.trim();
    const resetUsernameError = resetUsernameTrim.length > 0 && resetUsernameTrim.length < 3;
    const resetPasswordError = newPass.length > 0 && newPass.length < 6;
    const usernameChanged = Boolean(selectedUser && resetUsernameTrim.length >= 3 && resetUsernameTrim !== selectedUser.username);
    const passwordChanged = newPass.length >= 6;
    const canReset = Boolean(selectedUser) && !resetUsernameError && !resetPasswordError && (usernameChanged || passwordChanged);

    const handleCreate = async () => {
        if (!canManageUsers) {
            alert("Permission denied");
            return;
        }
        if (!canCreate) {
            alert("Username: minimum 3 ta belgi, Password: minimum 6 ta belgi.");
            return;
        }
        setCreating(true);
        try {
            await createUser({
                username: newUser.username.trim(),
                password: newUser.password,
                role: newUser.role,
            });
            setCreateOpen(false);
            setNewUser({ username: "", password: "", role: "viewer" });
            await load();
        } catch (e: any) {
            console.error(e);
            alert("Error creating user: " + extractApiErrorMessage(e));
        } finally {
            setCreating(false);
        }
    };

    const handleReset = async () => {
        if (!canManageUsers) {
            alert("Permission denied");
            return;
        }
        if (!selectedUser) return;
        if (!canReset) {
            alert("Login yoki paroldan kamida bittasini o'zgartiring.");
            return;
        }
        setResetting(true);
        try {
            const payload: { username?: string; password?: string } = {};
            if (resetUsernameTrim && resetUsernameTrim !== selectedUser.username) {
                payload.username = resetUsernameTrim;
            }
            if (newPass) {
                payload.password = newPass;
            }
            await resetPassword(selectedUser.id, payload);
            setResetOpen(false);
            setNewPass("");
            setResetUsername("");
            setSelectedUser(null);
            await load();
            alert("Credentials updated successfully");
        } catch (e: any) {
            console.error(e);
            alert("Error updating credentials: " + extractApiErrorMessage(e));
        } finally {
            setResetting(false);
        }
    };

    const handleDelete = async () => {
        if (!canManageUsers) {
            alert("Permission denied");
            return;
        }
        if (!userToDelete) return;
        setDeleting(true);
        try {
            await deleteUser(userToDelete.id);
            setDeleteOpen(false);
            setUserToDelete(null);
            load();
        } catch (e: any) {
            console.error(e);
            alert("Error deleting user: " + (e.message || "Unknown error"));
        } finally {
            setDeleting(false);
        }
    };

    return (
        <Box>
            <Typography variant="h4" sx={{
                mb: 3,
                fontSize: "2.5rem", fontWeight: 700,
                background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                display: "inline-block"
            }}>{t("adminUsers.title")}</Typography>

            <Box sx={{ width: "fit-content", minWidth: 800 }}>
                <GlassCard sx={{ width: "fit-content", minWidth: 800 }}>
                    <Table size="small">
                        <TableHead>
                            <TableRow>
                                <TableCell>{t("adminUsers.col.id")}</TableCell>
                                <TableCell>{t("adminUsers.col.username")}</TableCell>
                                <TableCell>{t("adminUsers.col.role")}</TableCell>
                                <TableCell sx={{ textAlign: "center" }}>{t("adminUsers.col.status")}</TableCell>
                                <TableCell sx={{ textAlign: "center", width: 140 }}>{t("adminUsers.col.actions")}</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {users.map((u, index) => (
                                <TableRow key={u.id}>
                                    <TableCell>{index + 1}</TableCell>
                                    <TableCell sx={{ fontWeight: 600 }}>{u.username}</TableCell>
                                    <TableCell><StatusPill status={u.role.toUpperCase()} /></TableCell>
                                    <TableCell sx={{ textAlign: "center" }}><StatusPill status={u.is_active ? "OK" : "OFFLINE"} /></TableCell>
                                    <TableCell sx={{ textAlign: "center" }}>
                                        <Box sx={{ display: "flex", gap: 1, justifyContent: "center" }}>
                                            <Button
                                                size="small" variant="outlined" color="warning" startIcon={<LockResetIcon />}
                                                onClick={() => {
                                                    if (!canManageUsers) return;
                                                    setSelectedUser(u);
                                                    setResetUsername(u.username);
                                                    setNewPass("");
                                                    setResetOpen(true);
                                                }}
                                                disabled={!canManageUsers}
                                                sx={{
                                                    borderRadius: "8px",
                                                    textTransform: "none",
                                                    fontSize: "12px",
                                                    py: 0.5,
                                                    "&.Mui-disabled": {
                                                        color: tokens.text.muted,
                                                        borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.18)" : "rgba(15,23,42,0.18)",
                                                        backgroundColor: tokens.mode === "dark" ? "rgba(255,255,255,0.04)" : "rgba(15,23,42,0.04)",
                                                    },
                                                }}
                                            >
                                                {t("adminUsers.resetPasswordShort")}
                                            </Button>
                                            <Button
                                                size="small"
                                                variant="outlined"
                                                color="error"
                                                startIcon={<DeleteIcon />}
                                                onClick={() => {
                                                    if (!canManageUsers) return;
                                                    setUserToDelete(u);
                                                    setDeleteOpen(true);
                                                }}
                                                disabled={!canManageUsers || String(u.role || "").toLowerCase() === "superadmin"}
                                                sx={{
                                                    borderRadius: "8px",
                                                    textTransform: "none",
                                                    fontSize: "12px",
                                                    py: 0.5,
                                                    "&.Mui-disabled": {
                                                        color: tokens.text.muted,
                                                        borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.18)" : "rgba(15,23,42,0.18)",
                                                        backgroundColor: tokens.mode === "dark" ? "rgba(255,255,255,0.04)" : "rgba(15,23,42,0.04)",
                                                    },
                                                }}
                                            >
                                                {t("adminUsers.delete")}
                                            </Button>
                                        </Box>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </GlassCard>

                <Box sx={{ mt: 2, display: "flex", justifyContent: "flex-start" }}>
                    <Button
                        variant="contained" startIcon={<AddIcon />}
                        onClick={() => setCreateOpen(true)}
                        disabled={!canManageUsers}
                        sx={{
                            borderRadius: "12px",
                            textTransform: "none",
                            fontWeight: 600,
                            whiteSpace: "nowrap",
                            background: "linear-gradient(45deg, #2563eb, #06b6d4)",
                            boxShadow: "0 4px 14px 0 rgba(37,99,235,0.39)",
                            "&:hover": {
                                background: "linear-gradient(45deg, #1d4ed8, #0891b2)",
                                boxShadow: "0 6px 20px 0 rgba(37,99,235,0.23)"
                            },
                            "&.Mui-disabled": {
                                color: tokens.text.muted,
                                background: tokens.mode === "dark" ? "rgba(255,255,255,0.08)" : "rgba(15,23,42,0.08)",
                                boxShadow: "none",
                            },
                        }}
                    >
                        {t("adminUsers.createUser")}
                    </Button>
                </Box>
            </Box>

            {/* Create User Dialog */}
            <Dialog
                open={createOpen}
                onClose={() => setCreateOpen(false)}
                maxWidth="xs"
                fullWidth
                PaperProps={{
                    sx: {
                        borderRadius: `${tokens.radius.md}px`,
                        background: tokens.bg.card,
                        backdropFilter: `blur(${tokens.glass.blur})`,
                        border: tokens.glass.border,
                        boxShadow: tokens.mode === "dark"
                            ? "0 24px 60px rgba(0, 0, 0, 0.45)"
                            : "0 20px 40px rgba(15, 23, 42, 0.18)",
                    }
                }}
            >
                <DialogTitle
                    sx={{
                        fontWeight: 800,
                        fontSize: "1.35rem",
                        background: "linear-gradient(45deg, #3b82f6, #06b6d4)",
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                        pb: 1,
                    }}
                >
                    {t("adminUsers.createUser")}
                </DialogTitle>
                <DialogContent>
                    <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
                        <TextField
                            label={t("adminUsers.username")}
                            fullWidth
                            value={newUser.username}
                            onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                            variant="outlined"
                            size="small"
                            error={usernameError}
                            helperText={usernameError ? "Minimum 3 characters" : ""}
                            sx={{
                                "& .MuiOutlinedInput-root": { borderRadius: `${tokens.radius.sm}px` },
                            }}
                        />
                        <TextField
                            label={t("adminUsers.password")}
                            type={showCreatePass ? "text" : "password"}
                            fullWidth
                            value={newUser.password}
                            onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                            variant="outlined"
                            size="small"
                            error={passwordError}
                            sx={{
                                "& .MuiOutlinedInput-root": { borderRadius: `${tokens.radius.sm}px` },
                            }}
                            InputProps={{
                                endAdornment: (
                                    <IconButton onClick={() => setShowCreatePass((prev) => !prev)} edge="end" sx={{ mr: 0.5 }}>
                                        {showCreatePass ? <VisibilityOffIcon /> : <VisibilityIcon />}
                                    </IconButton>
                                ),
                            }}
                            helperText="Minimum 6 characters"
                        />
                        <Select
                            fullWidth
                            value={newUser.role}
                            onChange={(e) => setNewUser({ ...newUser, role: e.target.value as (typeof roles)[number] })}
                            variant="outlined"
                            size="small"
                            sx={{ borderRadius: `${tokens.radius.sm}px` }}
                        >
                            {roles.map((role) => (
                                <MenuItem key={role} value={role}>{role.toUpperCase()}</MenuItem>
                            ))}
                        </Select>
                    </Box>
                </DialogContent>
                <DialogActions sx={{ p: 3 }}>
                    <Button onClick={() => setCreateOpen(false)} sx={{ color: "text.secondary", fontWeight: 600 }}>{t("adminUsers.cancel")}</Button>
                    <Button
                        onClick={handleCreate}
                        variant="contained"
                        disabled={creating || !canCreate}
                        startIcon={creating ? <CircularProgress size={16} /> : null}
                        sx={{
                            borderRadius: `${tokens.radius.sm}px`,
                            fontWeight: 700,
                            background: "linear-gradient(45deg, #2563eb, #06b6d4)",
                        }}
                    >
                        {t("adminUsers.save")}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Reset Password Dialog */}
            <Dialog
                open={resetOpen}
                onClose={() => {
                    setResetOpen(false);
                    setResetUsername("");
                    setNewPass("");
                    setSelectedUser(null);
                }}
                maxWidth="xs"
                fullWidth
                PaperProps={{
                    sx: {
                        borderRadius: "24px",
                        background: "rgba(255, 255, 255, 0.8)",
                        backdropFilter: "blur(20px)",
                        border: "1px solid rgba(255, 255, 255, 0.18)"
                    }
                }}
            >
                <DialogTitle sx={{ fontWeight: 700, fontSize: "1.5rem" }}>{t("adminUsers.resetPassword")}</DialogTitle>
                <DialogContent>
                    <Typography variant="body1" sx={{ mb: 3, fontWeight: 500 }}>
                        {t("adminUsers.confirmReset")} <b>{selectedUser?.username}</b>
                    </Typography>
                    <TextField
                        label={t("adminUsers.username")}
                        fullWidth
                        value={resetUsername}
                        onChange={(e) => setResetUsername(e.target.value)}
                        variant="filled"
                        error={resetUsernameError}
                        helperText={resetUsernameError ? "Minimum 3 characters" : ""}
                        InputProps={{ disableUnderline: true, sx: { borderRadius: "12px" } }}
                        sx={{ mb: 2 }}
                    />
                    <TextField
                        label={t("adminUsers.newPassword")}
                        type={showNewPass ? "text" : "password"}
                        fullWidth
                        value={newPass}
                        onChange={(e) => setNewPass(e.target.value)}
                        variant="filled"
                        error={resetPasswordError}
                        InputProps={{
                            disableUnderline: true,
                            sx: { borderRadius: "12px" },
                            endAdornment: (
                                <IconButton onClick={() => setShowNewPass(!showNewPass)} edge="end" sx={{ mr: 1 }}>
                                    {showNewPass ? <VisibilityOffIcon /> : <VisibilityIcon />}
                                </IconButton>
                            )
                        }}
                        helperText="Minimum 6 characters (optional)"
                    />
                </DialogContent>
                <DialogActions sx={{ p: 3 }}>
                    <Button onClick={() => setResetOpen(false)} sx={{ color: "text.secondary", fontWeight: 600 }}>{t("adminUsers.cancel")}</Button>
                    <Button
                        onClick={handleReset}
                        variant="contained"
                        color="warning"
                        disabled={resetting || !canReset}
                        startIcon={resetting ? <CircularProgress size={16} /> : null}
                        sx={{
                            borderRadius: "12px",
                            fontWeight: 700,
                        }}
                    >
                        {t("adminUsers.resetPassword")}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Delete Confirmation Dialog */}
            <Dialog
                open={deleteOpen}
                onClose={() => setDeleteOpen(false)}
                maxWidth="xs"
                fullWidth
                PaperProps={{
                    sx: {
                        borderRadius: "24px",
                        background: "rgba(255, 255, 255, 0.8)",
                        backdropFilter: "blur(20px)",
                        border: "1px solid rgba(255, 255, 255, 0.18)"
                    }
                }}
            >
                <DialogTitle sx={{ fontWeight: 700, fontSize: "1.5rem", color: "error.main" }}>Delete User</DialogTitle>
                <DialogContent>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                        Are you sure you want to delete user <b>{userToDelete?.username}</b>?
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        This action cannot be undone.
                    </Typography>
                </DialogContent>
                <DialogActions sx={{ p: 3 }}>
                    <Button onClick={() => setDeleteOpen(false)} sx={{ color: "text.secondary", fontWeight: 600 }}>Cancel</Button>
                    <Button
                        onClick={handleDelete}
                        variant="contained"
                        color="error"
                        disabled={deleting}
                        startIcon={deleting ? <CircularProgress size={16} color="inherit" /> : <DeleteIcon />}
                        sx={{
                            borderRadius: "12px",
                            fontWeight: 700,
                        }}
                    >
                        Delete
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
