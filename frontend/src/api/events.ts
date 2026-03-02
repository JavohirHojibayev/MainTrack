import { apiClient } from "./client";
import * as mocks from "@/mocks/events";

export interface EventRow {
    id: number;
    event_ts: string;
    event_type: string;
    employee_id: number;
    device_id: number;
    status: string;
    reject_reason: string | null;
    raw_id: string;
    employee_no?: string;
    first_name?: string;
    last_name?: string;
    patronymic?: string;
    device_name?: string;
    device_host?: string;
}

export interface EventFilters {
    date_from?: string;
    date_to?: string;
    employee_no?: string;
    search?: string;
    device_id?: number;
    event_type?: string;
    turnstile_only?: boolean;
    status?: string;
    limit?: number;
    offset?: number;
}

function buildEventParams(filters: EventFilters = {}): URLSearchParams {
    const params = new URLSearchParams();
    if (filters.date_from) params.set("date_from", filters.date_from);
    if (filters.date_to) params.set("date_to", filters.date_to);
    if (filters.employee_no) params.set("employee_no", filters.employee_no);
    if (filters.search) params.set("search", filters.search);
    if (filters.device_id) params.set("device_id", String(filters.device_id));
    if (filters.event_type) params.set("event_type", filters.event_type);
    if (filters.turnstile_only) params.set("turnstile_only", "true");
    if (filters.status) params.set("status", filters.status);
    if (filters.limit) params.set("limit", String(filters.limit));
    if (filters.offset !== undefined) params.set("offset", String(filters.offset));
    return params;
}

export async function fetchEvents(filters: EventFilters = {}): Promise<EventRow[]> {
    if (apiClient.useMocks) return mocks.mockEvents;
    const params = buildEventParams(filters);
    const qs = params.toString();
    return apiClient.get(`/events${qs ? `?${qs}` : ""}`);
}

export interface EventPage {
    items: EventRow[];
    total: number;
}

export async function fetchEventsPaged(filters: EventFilters = {}): Promise<EventPage> {
    if (apiClient.useMocks) {
        const all = mocks.mockEvents;
        const offset = filters.offset ?? 0;
        const limit = filters.limit ?? 25;
        return {
            items: all.slice(offset, offset + limit),
            total: all.length,
        };
    }
    const params = buildEventParams(filters);
    const qs = params.toString();
    return apiClient.get(`/events/paged${qs ? `?${qs}` : ""}`);
}
