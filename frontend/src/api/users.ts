import { apiClient } from "./client";

export interface User {
    id: number;
    username: string;
    role: string;
    is_active: boolean;
}

export interface UserCreatePayload {
    username: string;
    password: string;
    role: string;
}

export interface ResetPasswordPayload {
    password: string;
}

export const fetchUsers = async (): Promise<User[]> => {
    return apiClient.get<User[]>("/users");
};

export const createUser = async (data: UserCreatePayload): Promise<User> => {
    return apiClient.post<User>("/users", data);
};

export const resetPassword = async (userId: number, data: ResetPasswordPayload): Promise<User> => {
    return apiClient.put<User>(`/users/${userId}/password`, data);
};

export const deleteUser = async (userId: number): Promise<void> => {
    return apiClient.del<void>(`/users/${userId}`);
};
