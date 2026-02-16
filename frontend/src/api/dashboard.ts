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
