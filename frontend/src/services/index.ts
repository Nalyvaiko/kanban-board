import type { JiraApi } from "./api";
import { MockJiraApi } from "./mock/mockApi";

/**
 * The single entry point for every backend call in the app.
 * Swap this factory for an HTTP-backed implementation of `JiraApi`
 * and the rest of the application keeps working unchanged.
 */
export const api: JiraApi = new MockJiraApi();

export type { JiraApi };
export * from "./types";
