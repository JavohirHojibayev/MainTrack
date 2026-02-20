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
        first_name: string;
        last_name: string;
    };
}

export interface MedicalStats {
    date: string;
    total: number;
    passed: number;
    failed: number;
}

export async function fetchMedicalExams(params?: any): Promise<MedicalExam[]> {
    let query = "";
    if (params) {
        const searchParams = new URLSearchParams();
        Object.keys(params).forEach(key => {
            if (params[key] !== undefined && params[key] !== null) {
                searchParams.append(key, params[key]);
            }
        });
        query = "?" + searchParams.toString();
    }
    return apiClient.get("/medical/exams" + query);
}

export async function fetchMedicalStats(): Promise<MedicalStats> {
    return apiClient.get("/medical/stats");
}
