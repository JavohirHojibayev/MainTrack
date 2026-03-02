import { apiClient } from "./client";

export interface ReportSummary {
    turnstile_in: number;
    turnstile_out: number;
    esmo_ok: number;
    esmo_fail: number;
    tool_takes: number;
    tool_returns: number;
    mine_in: number;
    mine_out: number;
    blocked: number;
}

export const fetchReportSummary = async (dateFrom?: string, dateTo?: string): Promise<ReportSummary> => {
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    const query = params.toString();
    return apiClient.get<ReportSummary>(`/reports/summary${query ? `?${query}` : ""}`);
};
