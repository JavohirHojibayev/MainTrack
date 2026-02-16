export const mockInsideMine = [
    { employee_no: "M-001", full_name: "Karimov Asror", last_in: "2026-02-11T08:15:00Z" },
    { employee_no: "M-002", full_name: "Toshmatov Bek", last_in: "2026-02-11T08:22:00Z" },
    { employee_no: "M-005", full_name: "Abdullayev Farhod", last_in: "2026-02-11T07:50:00Z" },
    { employee_no: "M-008", full_name: "Raxmatullayev Sardor", last_in: "2026-02-11T09:01:00Z" },
    { employee_no: "M-012", full_name: "Yusupov Alisher", last_in: "2026-02-11T08:45:00Z" },
];

export const mockToolDebts = [
    { employee_no: "M-003", full_name: "Sobirov Jasur", last_take: "2026-02-10T14:30:00Z" },
    { employee_no: "M-007", full_name: "Normatov Ulugbek", last_take: "2026-02-10T15:12:00Z" },
];

export const mockBlocked = [
    { event_type: "MINE_IN", event_ts: "2026-02-11T09:10:00Z", employee_id: 4, device_id: 3, reject_reason: "No recent ESMO_OK" },
    { event_type: "TOOL_TAKE", event_ts: "2026-02-11T08:55:00Z", employee_id: 6, device_id: 2, reject_reason: "No recent ESMO_OK" },
];
