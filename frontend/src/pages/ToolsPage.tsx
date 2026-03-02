import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Box, Typography, TextField, Button } from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import DownloadIcon from "@mui/icons-material/DownloadRounded";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdfRounded";
import GlassCard from "@/components/GlassCard";
import { useAppTheme } from "@/context/ThemeContext";
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

type ToolIssueRow = {
    id: string;
    employee_no: string;
    full_name: string;
    turnstile_time: string;
    esmo_time: string;
    tool_name: string;
    quantity: number;
    issued_at: string;
    issuer: string;
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

    const loadRows = async () => {
        setLoading(true);
        try {
            // Placeholder: backend integration will be added in next stage.
            setRows([]);
        } catch (err) {
            console.error("Failed to load tools rows", err);
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

    const exportCSV = () => {
        const header = `${t("tools.col.employeeNo")};${t("tools.col.name")};${t("tools.col.turnstileTime")};${t("tools.col.esmoTime")};${t("tools.col.toolName")};${t("tools.col.quantity")};${t("tools.col.issuedAt")};${t("tools.col.issuer")}\n`;
        const csvRows = rows
            .map((r) =>
                `"${r.employee_no}";"${r.full_name}";"${r.turnstile_time ? dayjs(r.turnstile_time).format("DD.MM.YYYY HH:mm") : "-"}";"${r.esmo_time ? dayjs(r.esmo_time).format("DD.MM.YYYY HH:mm") : "-"}";"${r.tool_name}";"${r.quantity}";"${r.issued_at ? dayjs(r.issued_at).format("DD.MM.YYYY HH:mm") : "-"}";"${r.issuer}"`
            )
            .join("\n");

        const blob = new Blob(["\uFEFF" + header + csvRows], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `tools_${new Date().toISOString().split("T")[0]}.csv`);
        link.click();
    };

    const exportPDF = () => {
        const doc = new jsPDF({ orientation: "landscape" });

        doc.setFontSize(16);
        doc.text(t("tools.title"), 14, 18);
        doc.setFontSize(10);
        doc.setTextColor(100);
        doc.text(`${t("events.generated")}: ${new Date().toLocaleString()}`, 14, 25);

        const tableData = rows.map((r) => [
            r.employee_no,
            r.full_name,
            r.turnstile_time ? dayjs(r.turnstile_time).format("DD.MM.YYYY HH:mm") : "-",
            r.esmo_time ? dayjs(r.esmo_time).format("DD.MM.YYYY HH:mm") : "-",
            r.tool_name,
            String(r.quantity),
            r.issued_at ? dayjs(r.issued_at).format("DD.MM.YYYY HH:mm") : "-",
            r.issuer,
        ]);

        autoTable(doc, {
            head: [[
                t("tools.col.employeeNo"),
                t("tools.col.name"),
                t("tools.col.turnstileTime"),
                t("tools.col.esmoTime"),
                t("tools.col.toolName"),
                t("tools.col.quantity"),
                t("tools.col.issuedAt"),
                t("tools.col.issuer"),
            ]],
            body: tableData,
            startY: 30,
            theme: "grid",
            headStyles: { fillColor: [59, 130, 246] },
            styles: { fontSize: 9 },
        });

        doc.save(`tools_${new Date().toISOString().split("T")[0]}.pdf`);
    };

    const columns: GridColDef<ToolIssueRow>[] = useMemo(
        () => [
            { field: "full_name", headerName: t("tools.col.name"), width: 420, minWidth: 420 },
            {
                field: "turnstile_time",
                headerName: t("tools.col.turnstileTime"),
                width: 180,
                valueFormatter: (value) => (value ? dayjs(value as string).format("DD.MM.YYYY HH:mm") : "-"),
            },
            {
                field: "esmo_time",
                headerName: t("tools.col.esmoTime"),
                width: 180,
                valueFormatter: (value) => (value ? dayjs(value as string).format("DD.MM.YYYY HH:mm") : "-"),
            },
            { field: "tool_name", headerName: t("tools.col.toolName"), width: 180 },
            { field: "quantity", headerName: t("tools.col.quantity"), width: 100 },
            {
                field: "issued_at",
                headerName: t("tools.col.issuedAt"),
                width: 180,
                valueFormatter: (value) => (value ? dayjs(value as string).format("DD.MM.YYYY HH:mm") : "-"),
            },
            { field: "issuer", headerName: t("tools.col.issuer"), width: 180 },
        ],
        [t]
    );

    return (
        <Box sx={{ height: "calc(100vh - 120px)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
            <Typography variant="h4" sx={{ mb: 3, fontSize: "2.5rem", fontWeight: 700, flexShrink: 0 }}>
                <Box component="span" sx={pageTitleGradientSx}>{t("tools.title")}</Box>
            </Typography>

            <Box sx={{ mb: 4, display: "flex", gap: 2, alignItems: "center", flexWrap: "nowrap", flexShrink: 0 }}>
                <TextField
                    label={t("tools.dateFrom")}
                    type="date"
                    value={filters.start_date}
                    onChange={(e) => setFilters((f) => ({ ...f, start_date: e.target.value }))}
                    InputLabelProps={{ shrink: true }}
                    sx={{ minWidth: 160 }}
                />
                <TextField
                    label={t("tools.dateTo")}
                    type="date"
                    value={filters.end_date}
                    onChange={(e) => setFilters((f) => ({ ...f, end_date: e.target.value }))}
                    InputLabelProps={{ shrink: true }}
                    sx={{ minWidth: 160 }}
                />
                <TextField
                    label={t("tools.search")}
                    placeholder={t("tools.searchHint")}
                    value={filters.search}
                    onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
                    onKeyDown={(e) => {
                        if (e.key === "Enter") handleApply();
                    }}
                    sx={{ minWidth: 220 }}
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
                    onClick={exportCSV}
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

            <GlassCard sx={{ p: 0, flex: 1, width: "fit-content", minWidth: 1180, overflow: "hidden", "& .MuiDataGrid-root": { border: "none" } }}>
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
