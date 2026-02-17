import { Chip, type ChipProps } from "@mui/material";
import { useAppTheme } from "@/context/ThemeContext";

type Status = "ACCEPTED" | "OK" | "REJECTED" | "FAIL" | "BLOCKED" | "WARNING" | "OFFLINE" | "ONLINE" | "DUPLICATE" | "ERROR" | "PENDING";

export default function StatusPill({ status, colorStatus, ...rest }: Omit<ChipProps, "color"> & { status: string; colorStatus?: string }) {
    const { tokens } = useAppTheme();
    const colorMap: Record<Status, { bg: string; fg: string }> = {
        ACCEPTED: { bg: tokens.status.okBg, fg: tokens.status.ok },
        OK: { bg: tokens.status.okBg, fg: tokens.status.ok },
        ONLINE: { bg: tokens.status.okBg, fg: tokens.status.ok },
        REJECTED: { bg: tokens.status.blockedBg, fg: tokens.status.blocked },
        FAIL: { bg: tokens.status.blockedBg, fg: tokens.status.blocked },
        BLOCKED: { bg: tokens.status.blockedBg, fg: tokens.status.blocked },
        ERROR: { bg: tokens.status.blockedBg, fg: tokens.status.blocked },
        WARNING: { bg: tokens.status.warningBg, fg: tokens.status.warning },
        PENDING: { bg: tokens.status.warningBg, fg: tokens.status.warning },
        DUPLICATE: { bg: tokens.status.infoBg, fg: tokens.status.info },
        OFFLINE: { bg: tokens.status.warningBg, fg: tokens.status.warning },
    };
    const key = (colorStatus || status).toUpperCase() as Status;
    const c = colorMap[key] ?? { bg: tokens.status.offlineBg, fg: tokens.status.offline };
    return <Chip label={status} size="small" sx={{ bgcolor: c.bg, color: c.fg, fontWeight: 700, letterSpacing: 0.5, px: 0.5 }} {...rest} />;
}
