import { apiClient } from "./client";

export interface MedicalExam {
    id: number;
    employee_id: number;
    terminal_name: string;
    result: string;
    pressure_systolic?: number;
    pressure_diastolic?: number;
    pulse?: number;
    temperature?: number;
    alcohol_mg_l: number;
    timestamp: string;
    employee?: {
        id: number;
        employee_no: string;
        first_name: string;
        last_name: string;
        patronymic?: string;
    };
}

export interface MedicalStats {
    date: string;
    total: number;
    passed: number;
    failed: number;
}

export interface MedicalExamFilters {
    skip?: number;
    limit?: number;
    employee_id?: number;
    result?: string;
    start_date?: string;
    end_date?: string;
    search?: string;
}

export async function fetchMedicalExams(params?: MedicalExamFilters): Promise<MedicalExam[]> {
    let query = "";
    if (params) {
        const searchParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== "") {
                searchParams.append(key, String(value));
            }
        });
        query = "?" + searchParams.toString();
    }
    return apiClient.get("/medical/exams" + query);
}

export async function fetchMedicalStats(targetDate?: string): Promise<MedicalStats> {
    const query = targetDate ? `?target_date=${encodeURIComponent(targetDate)}` : "";
    return apiClient.get("/medical/stats" + query);
}

export async function syncMedicalExams(): Promise<{ status: string; new_exams_count: number }> {
    return apiClient.post("/medical/sync-exams", {});
}

export interface EsmoEmployee {
    id: string | number;
    pass_id: string;
    full_name: string;
    organization: string;
    department: string;
    position: string;
}

export async function fetchEsmoEmployees(): Promise<EsmoEmployee[]> {
    return apiClient.get("/medical/esmo-employees");
}

export async function syncEsmoEmployees(): Promise<EsmoEmployee[]> {
    return apiClient.post("/medical/sync-employees", {});
}
