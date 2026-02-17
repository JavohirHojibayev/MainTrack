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

const roles = ["admin", "superadmin", "dispatcher", "medical", "warehouse", "viewer"];

export default function AdminUsersPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(false);

    // Create User State
    const [createOpen, setCreateOpen] = useState(false);
    const [newUser, setNewUser] = useState({ username: "", password: "", role: "viewer" });
    const [creating, setCreating] = useState(false);

    // Reset Password State
    const [resetOpen, setResetOpen] = useState(false);
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const [newPass, setNewPass] = useState("");
    const [showNewPass, setShowNewPass] = useState(false);
    const [resetting, setResetting] = useState(false);

    // Delete User State
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [userToDelete, setUserToDelete] = useState<User | null>(null);
    const [deleting, setDeleting] = useState(false);

    const load = () => {
        setLoading(true);
        fetchUsers().then(setUsers).catch(console.error).finally(() => setLoading(false));
    };

    useEffect(() => { load(); }, []);

    const handleCreate = async () => {
        setCreating(true);
        try {
            await createUser(newUser);
            setCreateOpen(false);
            setNewUser({ username: "", password: "", role: "viewer" });
            load();
        } catch (e: any) {
            console.error(e);
            alert("Error creating user: " + (e.message || "Unknown error"));
        } finally {
            setCreating(false);
        }
    };

    const handleReset = async () => {
        if (!selectedUser) return;
        setResetting(true);
        try {
            await resetPassword(selectedUser.id, { password: newPass });
            setResetOpen(false);
            setNewPass("");
            setSelectedUser(null);
            alert("Password reset successfully");
        } catch (e: any) {
            console.error(e);
            alert("Error resetting password: " + (e.message || "Unknown error"));
        } finally {
            setResetting(false);
        }
    };

    const handleDelete = async () => {
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

            <Box sx={{ display: "flex", gap: 2, alignItems: "flex-start" }}>
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
                            {users.map((u) => (
                                <TableRow key={u.id}>
                                    <TableCell>{u.id}</TableCell>
                                    <TableCell sx={{ fontWeight: 600 }}>{u.username}</TableCell>
                                    <TableCell><StatusPill status={u.role.toUpperCase()} /></TableCell>
                                    <TableCell sx={{ textAlign: "center" }}><StatusPill status={u.is_active ? "OK" : "OFFLINE"} /></TableCell>
                                    <TableCell sx={{ textAlign: "center" }}>
                                        <Box sx={{ display: "flex", gap: 1, justifyContent: "center" }}>
                                            <Button
                                                size="small" variant="outlined" color="warning" startIcon={<LockResetIcon />}
                                                onClick={() => { setSelectedUser(u); setResetOpen(true); }}
                                                sx={{ borderRadius: "8px", textTransform: "none", fontSize: "12px", py: 0.5 }}
                                            >
                                                {t("adminUsers.resetPasswordShort")}
                                            </Button>
                                            <Button
                                                size="small"
                                                variant="outlined"
                                                color="error"
                                                startIcon={<DeleteIcon />}
                                                onClick={() => { setUserToDelete(u); setDeleteOpen(true); }}
                                                disabled={u.username === "admin"}
                                                sx={{ borderRadius: "8px", textTransform: "none", fontSize: "12px", py: 0.5 }}
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

                <Button
                    variant="contained" startIcon={<AddIcon />}
                    onClick={() => setCreateOpen(true)}
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
                        }
                    }}
                >
                    {t("adminUsers.createUser")}
                </Button>
            </Box>

            {/* Create User Dialog */}
            <Dialog
                open={createOpen}
                onClose={() => setCreateOpen(false)}
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
                <DialogTitle sx={{ fontWeight: 700, fontSize: "1.5rem" }}>{t("adminUsers.createUser")}</DialogTitle>
                <DialogContent>
                    <Box sx={{ display: "flex", flexDirection: "column", gap: 3, mt: 1 }}>
                        <TextField
                            label={t("adminUsers.username")}
                            fullWidth
                            value={newUser.username}
                            onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                            variant="filled"
                            InputProps={{ disableUnderline: true, sx: { borderRadius: "12px" } }}
                        />
                        <TextField
                            label={t("adminUsers.password")}
                            type="password"
                            fullWidth
                            value={newUser.password}
                            onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                            variant="filled"
                            InputProps={{ disableUnderline: true, sx: { borderRadius: "12px" } }}
                            helperText="Minimum 6 characters"
                        />
                    </Box>
                </DialogContent>
                <DialogActions sx={{ p: 3 }}>
                    <Button onClick={() => setCreateOpen(false)} sx={{ color: "text.secondary", fontWeight: 600 }}>{t("adminUsers.cancel")}</Button>
                    <Button
                        onClick={handleCreate}
                        variant="contained"
                        disabled={creating}
                        startIcon={creating ? <CircularProgress size={16} /> : null}
                        sx={{
                            borderRadius: "12px",
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
                onClose={() => setResetOpen(false)}
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
                        label={t("adminUsers.newPassword")}
                        type={showNewPass ? "text" : "password"}
                        fullWidth
                        value={newPass}
                        onChange={(e) => setNewPass(e.target.value)}
                        variant="filled"
                        InputProps={{
                            disableUnderline: true,
                            sx: { borderRadius: "12px" },
                            endAdornment: (
                                <IconButton onClick={() => setShowNewPass(!showNewPass)} edge="end" sx={{ mr: 1 }}>
                                    {showNewPass ? <VisibilityOffIcon /> : <VisibilityIcon />}
                                </IconButton>
                            )
                        }}
                        helperText="Minimum 6 characters"
                    />
                </DialogContent>
                <DialogActions sx={{ p: 3 }}>
                    <Button onClick={() => setResetOpen(false)} sx={{ color: "text.secondary", fontWeight: 600 }}>{t("adminUsers.cancel")}</Button>
                    <Button
                        onClick={handleReset}
                        variant="contained"
                        color="warning"
                        disabled={resetting}
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
