import { describe, expect, it } from "vitest";

import { formatDate, isOverdue } from "./task-meta";

// What the date picker sends for "Nov 21, 2026".
const DUE_NOV_21 = new Date("2026-11-21").toISOString();

describe("isOverdue", () => {
  it("is not overdue at any point during the due day itself", () => {
    expect(isOverdue(DUE_NOV_21, new Date(2026, 10, 21, 0, 1))).toBe(false);
    expect(isOverdue(DUE_NOV_21, new Date(2026, 10, 21, 23, 59))).toBe(false);
  });

  it("is overdue once the due day has passed", () => {
    expect(isOverdue(DUE_NOV_21, new Date(2026, 10, 22, 0, 1))).toBe(true);
  });

  it("is not overdue before the due day", () => {
    expect(isOverdue(DUE_NOV_21, new Date(2026, 10, 20, 12, 0))).toBe(false);
  });

  it("treats missing or unparseable dates as not overdue", () => {
    expect(isOverdue(null)).toBe(false);
    expect(isOverdue("not a date")).toBe(false);
  });
});

describe("formatDate", () => {
  it("shows the picked calendar day regardless of the viewer's timezone", () => {
    expect(formatDate(DUE_NOV_21)).toMatch(/\b21\b/);
    expect(formatDate(DUE_NOV_21)).not.toMatch(/\b20\b/);
  });

  it("renders a dash for no date", () => {
    expect(formatDate(null)).toBe("—");
  });
});
