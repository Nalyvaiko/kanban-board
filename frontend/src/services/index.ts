import type { JiraApi } from "./api";
import { HttpJiraApi } from "./http/httpApi";

/**
 * The single entry point for every backend call in the app.
 * Backed by the FastAPI server (see backend/) - same origin as this
 * frontend in production (it's served by that same FastAPI process),
 * localhost:8000 in dev. Override with VITE_API_BASE_URL at build time
 * if neither default is right for your setup.
 */
export const api: JiraApi = new HttpJiraApi();

export type { JiraApi };
export * from "./types";
