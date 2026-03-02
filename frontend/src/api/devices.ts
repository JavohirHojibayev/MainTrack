import { apiClient } from "./client";
import * as mocks from "@/mocks/devices";

export interface Device {
    id: number;
    name: string;
    device_code: string;
    host: string | null;
    device_type: string;
    location: string | null;
    api_key: string | null;
    is_active: boolean;
    last_seen: string | null;
}

export interface DeviceCreate {
    name: string;
    device_code: string;
    host?: string | null;
    device_type: string;
    location?: string | null;
    api_key?: string | null;
}

export interface DeviceDataStatus {
    device_id: number;
    last_data_at: string | null;
}

export async function fetchDevices(): Promise<Device[]> {
    if (apiClient.useMocks) return mocks.mockDevices;
    return apiClient.get("/devices");
}

export async function fetchDeviceDataStatus(): Promise<DeviceDataStatus[]> {
    if (apiClient.useMocks) return [];
    return apiClient.get("/devices/data-status");
}

export async function createDevice(data: DeviceCreate): Promise<Device> {
    return apiClient.post("/devices", data);
}

export async function syncHikvisionUsers(): Promise<any> {
    return apiClient.post("/hikvision/sync-users", {});
}

export async function toggleDevicePower(deviceId: number, isActive: boolean, password: string): Promise<Device> {
    return apiClient.post(`/devices/${deviceId}/power`, { is_active: isActive, password });
}
