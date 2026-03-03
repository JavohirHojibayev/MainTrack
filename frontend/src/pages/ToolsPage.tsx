import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, TextField, Button, CircularProgress } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import DownloadIcon from "@mui/icons-material/DownloadRounded";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdfRounded";
import GlassCard from "@/components/GlassCard";
import LocalizedDateInput from "@/components/LocalizedDateInput";
import StatusPill from "@/components/StatusPill";
import { useAppTheme } from "@/context/ThemeContext";
import { downloadXls } from "@/utils/exportXls";
import { fetchLampSelfRows, issueLampSelf, returnLampSelf, type LampSelfRow } from "@/api/tools";
import { formatEmployeeNo } from "@/utils/employeeNo";
import dayjs from "dayjs";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

const pageTitleGradientSx = {
    backgroundImage: "linear-gradient(45deg, #3b82f6 0%, #06b6d4 100%)",
    WebkitBackgroundClip: "text !important",
    backgroundClip: "text",
    WebkitTextFillColor: "transparent !important",
    color: "transparent !important",
    display: "inline-block",
};

type ToolsFilters = {
    start_date: string;
    end_date: string;
    search: string;
};

type ToolIssueRow = LampSelfRow & {
    id: string;
};

export default function ToolsPage() {
    const { t } = useTranslation();
    const { tokens } = useAppTheme();
    const [rows, setRows] = useState<ToolIssueRow[]>([]);
    const [loading, setLoading] = useState(false);
    const [filters, setFilters] = useState<ToolsFilters>({
        start_date: "",
        end_date: "",
        search: "",
    });
    const [appliedFilters, setAppliedFilters] = useState<ToolsFilters>({
        start_date: "",
        end_date: "",
        search: "",
    });
    const [actionLoading, setActionLoading] = useState<Record<number, "issue" | "return" | undefined>>({});

    const formatDateTime = (value: string | null | undefined): string => {
        if (!value) return "-";
        const parsed = dayjs(value);
        return parsed.isValid() ? parsed.format("DD.MM.YYYY HH:mm") : "-";
    };

    const formatStatus = (value: string | null | undefined): string => {
        if (value === "ISSUED") return t("tools.status.issued");
        if (value === "DONE") return t("tools.status.done");
        if (value === "FAIL") return t("tools.status.fail");
        return t("tools.status.notIssued");
    };

    const formatEsmoStatus = (value: string | null | undefined): string => {
        if (value === "passed") return t("status.passed");
        if (value === "review") return t("status.review");
        return t("status.failed");
    };

    const esmoStatusColor = (value: string | null | undefined): string => {
        if (value === "passed") return "OK";
        if (value === "review") return "WARNING";
        return "FAIL";
    };

    const isActiveIssue = (row: ToolIssueRow): boolean => {
        if (!row.issued_at) return false;
        if (!row.returned_at) return true;
        const issued = dayjs(row.issued_at);
        const returned = dayjs(row.returned_at);
        if (!issued.isValid()) return false;
        if (!returned.isValid()) return true;
        return issued.isAfter(returned);
    };

    const loadRows = async () => {
        setLoading(true);
        try {
            const data = await fetchLampSelfRows({
                start_date: appliedFilters.start_date,
                end_date: appliedFilters.end_date,
                search: appliedFilters.search,
            });
            setRows(
                data.map((row) => ({
                    ...row,
                    id: `${row.employee_id}-${row.employee_no}`,
                }))
            );
        } catch (err) {
            console.error("Failed to load tools rows", err);
            setRows([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadRows();
    }, [appliedFilters.start_date, appliedFilters.end_date, appliedFilters.search]);

    const handleApply = () => {
        setAppliedFilters({
            start_date: filters.start_date,
            end_date: filters.end_date,
            search: filters.search.trim(),
        });
    };

    const handleIssue = async (row: ToolIssueRow) => {
        setActionLoading((prev) => ({ ...prev, [row.employee_id]: "issue" }));
        try {
            await issueLampSelf(row.employee_id);
            await loadRows();
        } catch (err) {
            console.error("Failed to issue lamp/self-rescuer", err);
        } finally {
            setActionLoading((prev) => ({ ...prev, [row.employee_id]: undefined }));
        }
    };

    const handleReturn = async (row: ToolIssueRow) => {
        setActionLoading((prev) => ({ ...prev, [row.employee_id]: "return" }));
        try {
            await returnLampSelf(row.employee_id);
            await loadRows();
        } catch (err) {
            console.error("Failed to return lamp/self-rescuer", err);
        } finally {
            setActionLoading((prev) => ({ ...prev, [row.employee_id]: undefined }));
        }
    };

    const exportXLS = () => {
        const headers = [
            t("tools.col.employeeNo"),
            t("tools.col.name"),
            t("tools.col.turnstileTime"),
            t("tools.col.esmoTime"),
            t("tools.col.esmoStatus"),
            t("tools.col.issuedAt"),
            t("tools.col.returnedAt"),
            t("tools.col.status"),
            t("tools.col.issuer"),
        ];
        const dataRows = rows.map((r) => [
            formatEmployeeNo(r.employee_no),
            r.full_name,
            formatDateTime(r.turnstile_time),
            formatDateTime(r.esmo_time),
            formatEsmoStatus(r.esmo_status),
            formatDateTime(r.issued_at),
            formatDateTime(r.returned_at),
            formatStatus(r.status),
            r.issuer || "-",
        ]);
        downloadXls(headers, dataRows, `lamp_self_${new Date().toISOString().split("T")[0]}.xls`);
    };

    const exportPDF = () => {
        const doc = new jsPDF({ orientation: "landscape" });

        doc.setFontSize(16);
        doc.text(t("tools.title"), 14, 18);
        doc.setFontSize(10);
        doc.setTextColor(100);
        doc.text(`${t("events.generated")}: ${new Date().toLocaleString()}`, 14, 25);

        const tableData = rows.map((r) => [
            formatEmployeeNo(r.employee_no),
            r.full_name,
            formatDateTime(r.turnstile_time),
            formatDateTime(r.esmo_time),
            formatEsmoStatus(r.esmo_status),
            formatDateTime(r.issued_at),
            formatDateTime(r.returned_at),
            formatStatus(r.status),
            r.issuer || "-",
        ]);

        autoTable(doc, {
            head: [[
                t("tools.col.employeeNo"),
                t("tools.col.name"),
                t("tools.col.turnstileTime"),
                t("tools.col.esmoTime"),
                t("tools.col.esmoStatus"),
                t("tools.col.issuedAt"),
                t("tools.col.returnedAt"),
                t("tools.col.status"),
                t("tools.col.issuer"),
            ]],
            body: tableData,
            startY: 30,
            theme: "grid",
            headStyles: { fillColor: [59, 130, 246] },
            styles: { fontSize: 9 },
        });

        doc.save(`lamp_self_${new Date().toISOString().split("T")[0]}.pdf`);
    };

    const columns: GridColDef<ToolIssueRow>[] = useMemo(
        () => [
            {
                field: "employee_no",
                headerName: t("tools.col.employeeNo"),
                width: 130,
                minWidth: 130,
                valueGetter: (value) => formatEmployeeNo(value),
            },
            { field: "full_name", headerName: t("tools.col.name"), width: 320, minWidth: 320 },
            {
                field: "turnstile_time",
                headerName: t("tools.col.turnstileTime"),
                width: 170,
                valueFormatter: (value) => formatDateTime(value as string | null),
            },
            {
                field: "esmo_time",
                headerName: t("tools.col.esmoTime"),
                width: 170,
                valueFormatter: (value) => formatDateTime(value as string | null),
            },
            {
                field: "esmo_status",
                headerName: t("tools.col.esmoStatus"),
                width: 140,
                renderCell: (params) => (
                    <StatusPill
                        status={formatEsmoStatus(params.value as string | null)}
                        colorStatus={esmoStatusColor(params.value as string | null)}
                    />
                ),
            },
            {
                field: "issued_at",
                headerName: t("tools.col.issuedAt"),
                width: 170,
                renderCell: (params) => {
                    const row = params.row as ToolIssueRow;
                    const loadingAction = actionLoading[row.employee_id] === "issue";
                    const isEsmoEligible = row.esmo_status === "passed" || row.esmo_status === "review";
                    if (row.issued_at) return formatDateTime(row.issued_at);
                    if (!isEsmoEligible) return "-";
                    return (
                        <Button
                            size="small"
                            variant="outlined"
                            onClick={() => handleIssue(row)}
                            disabled={loadingAction}
                            sx={{ textTransform: "none", minWidth: 92 }}
                        >
                            {loadingAction ? <CircularProgress size={14} /> : t("tools.issueNow")}
                        </Button>
                    );
                },
            },
            {
                field: "returned_at",
                headerName: t("tools.col.returnedAt"),
                width: 170,
                renderCell: (params) => {
                    const row = params.row as ToolIssueRow;
                    const active = isActiveIssue(row);
                    const loadingAction = actionLoading[row.employee_id] === "return";
                    if (!active && row.returned_at) return formatDateTime(row.returned_at);
                    if (!active) return "-";
                    return (
                        <Button
                            size="small"
                            variant="outlined"
                            onClick={() => handleReturn(row)}
                            disabled={loadingAction}
                            sx={{ textTransform: "none", minWidth: 92 }}
                        >
                            {loadingAction ? <CircularProgress size={14} /> : t("tools.returnNow")}
                        </Button>
                    );
                },
            },
            {
                field: "status",
                headerName: t("tools.col.status"),
                width: 130,
                renderCell: (params) => {
                    const raw = String(params.value ?? "");
                    const centeredSx = { display: "flex", alignItems: "center", height: "100%", width: "100%" };
                    if (raw === "NOT_ISSUED") {
                        return (
                            <Box sx={centeredSx}>
                                <Typography variant="body2" sx={{ color: tokens.text.secondary }}>
                                    {formatStatus(raw)}
                                </Typography>
                            </Box>
                        );
                    }
                    if (raw === "ISSUED") {
                        return (
                            <Box sx={centeredSx}>
                                <StatusPill status={formatStatus(raw)} colorStatus="WARNING" />
                            </Box>
                        );
                    }
                    if (raw === "DONE") {
                        return (
                            <Box sx={centeredSx}>
                                <StatusPill status={formatStatus(raw)} colorStatus="OK" />
                            </Box>
                        );
                    }
                    if (raw === "FAIL") {
                        return (
                            <Box sx={centeredSx}>
                                <StatusPill status={formatStatus(raw)} colorStatus="FAIL" />
                            </Box>
                        );
                    }
                    return (
                        <Box sx={centeredSx}>
                            <Typography variant="body2">{formatStatus(raw)}</Typography>
                        </Box>
                    );
                },
            },
            {
                field: "issuer",
                headerName: t("tools.col.issuer"),
                width: 160,
                valueFormatter: (value) => ((value as string | null) || "-"),
            },
        ],
        [actionLoading, t, tokens.text.secondary]
    );

    return (
        <Box sx={{ height: "calc(100vh - 120px)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <Typography variant="h4" sx={{ mb: 3, fontSize: "2.5rem", fontWeight: 700, flexShrink: 0 }}>
                <Box component="span" sx={pageTitleGradientSx}>{t("tools.title")}</Box>
            </Typography>

            <Box sx={{ mb: 4, display: "flex", gap: 2, alignItems: "center", flexWrap: "nowrap", flexShrink: 0 }}>
                <LocalizedDateInput
                    label={t("tools.dateFrom")}
                    value={filters.start_date}
                    onChange={(next) => setFilters((f) => ({ ...f, start_date: next }))}
                />
                <LocalizedDateInput
                    label={t("tools.dateTo")}
                    value={filters.end_date}
                    onChange={(next) => setFilters((f) => ({ ...f, end_date: next }))}
                />
                <TextField
                    label={t("tools.search")}
                    placeholder={t("tools.searchHint")}
                    value={filters.search}
                    onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") handleApply();
                    }}
                    sx={{ minWidth: 170 }}
                />
                <Button
                    variant="contained"
                    onClick={handleApply}
                    sx={{ height: 40, minWidth: 100, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap" }}
                >
                    {t("tools.apply")}
                </Button>
                <Button
                    variant="contained"
                    startIcon={<DownloadIcon />}
                    onClick={exportXLS}
                    disabled={rows.length === 0 || loading}
                    sx={{ height: 40, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap", background: "linear-gradient(135deg, #06b6d4, #3b82f6)", "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" } }}
                >
                    {t("tools.exportCsv")}
                </Button>
                <Button
                    variant="contained"
                    startIcon={<PictureAsPdfIcon />}
                    onClick={exportPDF}
                    disabled={rows.length === 0 || loading}
                    sx={{ height: 40, borderRadius: "50px", textTransform: "none", fontWeight: "bold", whiteSpace: "nowrap", background: "linear-gradient(135deg, #06b6d4, #3b82f6)", "&:hover": { background: "linear-gradient(135deg, #0891b2, #2563eb)" } }}
                >
                    {t("tools.exportPdf")}
                </Button>
            </Box>

            <GlassCard sx={{ p: 0, flex: 1, width: "fit-content", minWidth: 1280, overflow: "hidden", "& .MuiDataGrid-root": { border: "none" } }}>
                <DataGrid
                    rows={rows}
                    columns={columns}
                    loading={loading}
                    pageSizeOptions={[25, 50, 100]}
                    initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
                    disableColumnSorting
                    disableColumnMenu
                    sx={{
                        height: "100%",
                        width: "100%",
                        "& .MuiDataGrid-columnHeaders": { bgcolor: tokens.bg.tableHeader },
                        "& .MuiDataGrid-row:nth-of-type(even)": { bgcolor: tokens.bg.tableRowAlt },
                        "& .MuiDataGrid-cell": { borderColor: tokens.mode === "dark" ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" },
                    }}
                />
            </GlassCard>
        </Box>
    );
}
