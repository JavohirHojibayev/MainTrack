export function normalizeNumericEmployeeNo(value: string): string {
    const raw = String(value || "").trim();
    if (!/^\d+$/.test(raw)) return raw;
    const stripped = raw.replace(/^0+/, "");
    return stripped || "0";
}

export function formatEmployeeNo(value: unknown, minLength = 8): string {
    const raw = String(value ?? "").trim();
    if (!raw) return "";
    if (!/^\d+$/.test(raw)) return raw;
    const normalized = normalizeNumericEmployeeNo(raw);
    return normalized.padStart(minLength, "0");
}

export function employeeNoSearchHaystack(value: unknown, minLength = 8): string {
    const raw = String(value ?? "").trim();
    if (!raw) return "";
    if (!/^\d+$/.test(raw)) return raw.toLowerCase();
    const normalized = normalizeNumericEmployeeNo(raw);
    const padded = formatEmployeeNo(raw, minLength);
    return `${raw} ${normalized} ${padded}`.toLowerCase();
}
