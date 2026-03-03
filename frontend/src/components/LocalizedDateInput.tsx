import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { DatePicker, LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { enUS, ruRU } from "@mui/x-date-pickers/locales";
import { type SxProps, type Theme } from "@mui/material/styles";
import dayjs from "dayjs";
import "dayjs/locale/en-gb";
import "dayjs/locale/ru";
import "dayjs/locale/uz-latn";

type Props = {
    label: string;
    value: string;
    onChange: (value: string) => void;
    minWidth?: number;
    sx?: SxProps<Theme>;
};

export default function LocalizedDateInput({
    label,
    value,
    onChange,
    minWidth = 140,
    sx,
}: Props) {
    const { i18n, t } = useTranslation();

    const adapterLocale = i18n.language === "ru" ? "ru" : i18n.language === "uz" ? "uz-latn" : "en-gb";
    const baseLocaleText =
        i18n.language === "ru"
            ? ruRU.components.MuiLocalizationProvider.defaultProps.localeText
            : enUS.components.MuiLocalizationProvider.defaultProps.localeText;

    const localeText = useMemo(
        () => ({
            ...baseLocaleText,
            fieldDayPlaceholder: () => t("common.dateTokenDay"),
            fieldMonthPlaceholder: () => t("common.dateTokenMonth"),
            fieldYearPlaceholder: () => t("common.dateTokenYear"),
            clearButtonLabel: t("common.clear"),
            todayButtonLabel: t("common.today"),
            cancelButtonLabel: t("common.cancel"),
            okButtonLabel: t("common.confirm"),
        }),
        [baseLocaleText, t]
    );

    return (
        <LocalizationProvider dateAdapter={AdapterDayjs} adapterLocale={adapterLocale} localeText={localeText}>
            <DatePicker
                label={label}
                format="DD.MM.YYYY"
                openTo="day"
                views={["year", "month", "day"]}
                value={value ? dayjs(value) : null}
                onChange={(next) => onChange(next && next.isValid() ? next.format("YYYY-MM-DD") : "")}
                slotProps={{
                    actionBar: { actions: ["clear", "today"] },
                    calendarHeader: { format: "MMMM YYYY" },
                    textField: {
                        InputLabelProps: { shrink: true },
                        sx: {
                            minWidth,
                            "& .MuiInputBase-input": {
                                color: "#334155",
                            },
                            "& .MuiInputBase-input::placeholder": (theme) => ({
                                color: theme.palette.text.secondary,
                                opacity: 1,
                            }),
                            "& .MuiPickersInputBase-sectionsContainer": {
                                width: 140,
                                opacity: 1,
                            },
                            "& .MuiPickersSectionList-root": {
                                opacity: 1,
                            },
                            "& .MuiPickersInputBase-sectionContent, & .MuiPickersSectionList-sectionContent":
                                (theme) => ({
                                    color: theme.palette.text.secondary,
                                }),
                            "& .MuiSvgIcon-root": {
                                color: "#6b7280",
                            },
                            ...(sx as object),
                        },
                    },
                    popper: {
                        sx: {
                            "& .MuiPaper-root": {
                                borderRadius: "16px",
                                border: "1px solid rgba(255,255,255,0.18)",
                                backdropFilter: "blur(16px)",
                            },
                            "& .MuiDateCalendar-root": {
                                width: 300,
                                maxHeight: 352,
                            },
                            "& .MuiPickersCalendarHeader-root": {
                                minHeight: 40,
                                marginTop: 2,
                                marginBottom: 2,
                                paddingInline: 10,
                            },
                            "& .MuiPickersCalendarHeader-labelContainer": {
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 0.25,
                                overflow: "visible",
                                whiteSpace: "nowrap",
                                color: (theme) => theme.palette.text.primary,
                                opacity: 1,
                            },
                            "& .MuiPickersCalendarHeader-label": {
                                fontSize: "1.04rem",
                                fontWeight: 600,
                                whiteSpace: "nowrap",
                                lineHeight: 1.2,
                                color: (theme) => theme.palette.text.primary,
                                opacity: 1,
                            },
                            "& .MuiPickersCalendarHeader-switchViewIcon": {
                                color: (theme) => theme.palette.text.secondary,
                                opacity: 1,
                            },
                            "& .MuiDayCalendar-weekDayLabel": {
                                width: 34,
                                height: 24,
                                fontSize: "0.82rem",
                            },
                            "& .MuiPickersDay-root": {
                                width: 32,
                                height: 32,
                                fontSize: "0.92rem",
                                margin: "0 2px",
                            },
                            "& .MuiPickersArrowSwitcher-button, & .MuiPickersCalendarHeader-switchViewButton":
                                {
                                    padding: 4,
                                },
                            "& .MuiPickersLayout-actionBar": {
                                padding: "4px 12px 10px",
                            },
                            "& .MuiPickersLayout-actionBar .MuiButton-root": {
                                fontSize: "0.88rem",
                                minWidth: "auto",
                                padding: "4px 8px",
                            },
                        },
                    },
                }}
            />
        </LocalizationProvider>
    );
}
