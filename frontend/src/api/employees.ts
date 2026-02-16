import { apiClient } from "./client";
import * as mocks from "@/mocks/employees";

export interface Employee {
    id: number;
    employee_no: string;
    first_name: string;
    last_name: string;
    patronymic: string | null;
    department: string | null;
    position: string | null;
    is_active: boolean;
}

export interface EmployeeCreate {
    employee_no: string;
    first_name: string;
    last_name: string;
    patronymic?: string | null;
    department?: string | null;
    position?: string | null;
}

export async function fetchEmployees(): Promise<Employee[]> {
    if (apiClient.useMocks) return mocks.mockEmployees;
    return apiClient.get("/employees");
}

export async function createEmployee(data: EmployeeCreate): Promise<Employee> {
    return apiClient.post("/employees", data);
}
