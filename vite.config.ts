import {defineConfig} from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({plugins:[react()],server:{proxy:{"/api":{target:process.env.OOSYS_DEV_API_ORIGIN??"http://127.0.0.1:8000",changeOrigin:true}}}});