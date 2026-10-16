import Constants from "expo-constants";

/** Racine de l'API **sans** `/v1` : les chemins du schéma OpenAPI commencent déjà par `/v1/`. */
const brut = process.env.EXPO_PUBLIC_API_URL ?? "http://10.0.2.2:8000"; // 10.0.2.2 = ordinateur hôte vu de l'émulateur Android
export const API_URL = brut.replace(/\/+$/, "").replace(/\/v1$/, "");

/** WebSocket de la messagerie (`/ws/v1/`) : même hôte que l'API, schéma ws/wss. */
export const WS_URL = `${API_URL.replace(/^http/, "ws")}/ws/v1/`;

export const WEB_HOST = process.env.EXPO_PUBLIC_WEB_HOST ?? "logeo.example";
export const APP_VERSION: string = Constants.expoConfig?.version ?? "0.0.0";
export const EAS_PROJECT_ID: string | undefined =
  (Constants.expoConfig?.extra as { eas?: { projectId?: string } } | undefined)?.eas?.projectId || undefined;
