import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const backendTarget = process.env.VITE_DEV_BACKEND_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
    plugins: [react()],
    resolve: { alias: { "@": path.resolve(__dirname, "src") } },
    server: {
        host: "0.0.0.0",
        port: 5173,
        open: true,
        proxy: {
            "/api/v1": {
                target: backendTarget,
                changeOrigin: true,
            },
        },
    },
});
