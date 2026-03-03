import { apiClient } from "./client";

export interface LampSelfFilters {
    start_date?: string;
    end_date?: string;
    search?: string;
}

export interface LampSelfRow {
    employee_id: number;
    employee_no: string;
    full_name: string;
    turnstile_time: string | null;
    esmo_time: string | null;
    esmo_status: "passed" | "review" | "fail" | string;
    tool_name: string;
    quantity: number;
    issued_at: string | null;
    returned_at: string | null;
    issuer: string | null;
    status: "NOT_ISSUED" | "ISSUED" | "DONE" | "FAIL" | string;
}

export interface LampSelfActionResult {
    success: boolean;
    status: "NOT_ISSUED" | "ISSUED" | "DONE" | "FAIL" | string;
    message: string;
    event_id?: number | null;
    event_ts?: string | null;
}

export async function fetchLampSelfRows(params?: LampSelfFilters): Promise<LampSelfRow[]> {
    if (apiClient.useMocks) return [];

    const qs = new URLSearchParams();
    if (params?.start_date) qs.set("start_date", params.start_date);
    if (params?.end_date) qs.set("end_date", params.end_date);
    if (params?.search) qs.set("search", params.search);
    const query = qs.toString();

    return apiClient.get(`/reports/lamp-self-rescuer${query ? `?${query}` : ""}`);
}

export async function issueLampSelf(employeeId: number): Promise<LampSelfActionResult> {
    return apiClient.post("/reports/lamp-self-rescuer/issue", { employee_id: employeeId });
}

export async function returnLampSelf(employeeId: number): Promise<LampSelfActionResult> {
    return apiClient.post("/reports/lamp-self-rescuer/return", { employee_id: employeeId });
}
