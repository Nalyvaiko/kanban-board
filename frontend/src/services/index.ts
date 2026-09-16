import type { JiraApi } from "./api";
import { HttpJiraApi } from "./http/httpApi";

/**
 * The single entry point for every backend call in the app.
 * Backed by the FastAPI server (see backend/); point VITE_API_BASE_URL
 * at a different host to target another environment.
 */
export const api: JiraApi = new HttpJiraApi();

export type { JiraApi };
export * from "./types";
