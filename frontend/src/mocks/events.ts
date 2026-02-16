export const mockEvents = [
    { id: 1, event_ts: "2026-02-11T09:10:00Z", event_type: "MINE_IN", employee_id: 4, device_id: 3, status: "REJECTED", reject_reason: "No recent ESMO_OK", raw_id: "evt-001" },
    { id: 2, event_ts: "2026-02-11T08:55:00Z", event_type: "TOOL_TAKE", employee_id: 6, device_id: 2, status: "REJECTED", reject_reason: "No recent ESMO_OK", raw_id: "evt-002" },
    { id: 3, event_ts: "2026-02-11T08:22:00Z", event_type: "TURNSTILE_IN", employee_id: 2, device_id: 1, status: "ACCEPTED", reject_reason: null, raw_id: "evt-003" },
    { id: 4, event_ts: "2026-02-11T08:20:00Z", event_type: "ESMO_OK", employee_id: 2, device_id: 4, status: "ACCEPTED", reject_reason: null, raw_id: "evt-004" },
    { id: 5, event_ts: "2026-02-11T08:15:00Z", event_type: "MINE_IN", employee_id: 1, device_id: 3, status: "ACCEPTED", reject_reason: null, raw_id: "evt-005" },
    { id: 6, event_ts: "2026-02-11T07:50:00Z", event_type: "TURNSTILE_IN", employee_id: 5, device_id: 1, status: "ACCEPTED", reject_reason: null, raw_id: "evt-006" },
    { id: 7, event_ts: "2026-02-11T07:48:00Z", event_type: "ESMO_OK", employee_id: 5, device_id: 4, status: "ACCEPTED", reject_reason: null, raw_id: "evt-007" },
    { id: 8, event_ts: "2026-02-11T07:45:00Z", event_type: "TOOL_TAKE", employee_id: 1, device_id: 2, status: "ACCEPTED", reject_reason: null, raw_id: "evt-008" },
    { id: 9, event_ts: "2026-02-10T17:00:00Z", event_type: "TURNSTILE_OUT", employee_id: 3, device_id: 1, status: "ACCEPTED", reject_reason: null, raw_id: "evt-009" },
    { id: 10, event_ts: "2026-02-10T16:50:00Z", event_type: "MINE_OUT", employee_id: 3, device_id: 3, status: "ACCEPTED", reject_reason: null, raw_id: "evt-010" },
];
