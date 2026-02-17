import { apiClient } from "./client";

export interface ReportSummary {
    turnstile_in: int;
    turnstile_out: int;
    esmo_ok: int;
    esmo_fail: int;
    tool_takes: int;
    tool_returns: int;
    mine_in: int;
    mine_out: int;
    blocked: int;
}

export const fetchReportSummary = async (dateFrom: string, dateTo: string): Promise<ReportSummary> => {
    return apiClient.get<ReportSummary>(`/reports/summary?date_from=${dateFrom}&date_to=${dateTo}`);
};
