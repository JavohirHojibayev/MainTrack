import { apiClient } from "./client";
import * as mocks from "@/mocks/dashboard";

export interface KPI {
    insideMine: number;
    esmoOk: number;
    toolDebts: number;
    blockedAttempts: number;
}

export interface InsideMineRow { employee_no: string; full_name: string; last_in: string; }
export interface ToolDebtRow { employee_no: string; full_name: string; last_take: string; }
export interface BlockedRow { event_type: string; event_ts: string; employee_id: number; device_id: number; reject_reason: string; }

export async function fetchInsideMine(): Promise<InsideMineRow[]> {
    if (apiClient.useMocks) return mocks.mockInsideMine;
    return apiClient.get("/reports/inside-mine");
}

export async function fetchToolDebts(): Promise<ToolDebtRow[]> {
    if (apiClient.useMocks) return mocks.mockToolDebts;
    return apiClient.get("/reports/tool-debts");
}

export async function fetchBlockedAttempts(): Promise<BlockedRow[]> {
    if (apiClient.useMocks) return mocks.mockBlocked;
    return apiClient.get("/reports/blocked-attempts");
}

export interface DailySummaryRow {
    employee_no: string;
    full_name: string;
    total_minutes: number;
    last_in: string | null;
    last_out: string | null;
    is_inside: boolean;
}

export async function fetchDailyMineSummary(day: string): Promise<DailySummaryRow[]> {
    return apiClient.get(`/reports/daily-mine-summary?day=${day}`);
}

export async function fetchEsmoSummary(day: string): Promise<number> {
    return apiClient.get(`/reports/esmo-summary?day=${day}`);
}
