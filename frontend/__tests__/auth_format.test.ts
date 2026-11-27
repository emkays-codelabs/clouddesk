import { describe, expect, it } from "vitest";
import { canAct, isAdmin } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { formatDate, humanize, truncate } from "@/lib/format";
import type { User } from "@/lib/types";

const user = (role: User["role"]): User => ({ id: "1", email: "a@b.c", full_name: "A", role });

describe("role-aware actions", () => {
  it("lets agents and admins act and keeps viewers read-only", () => {
    expect(canAct(user("viewer"))).toBe(false);
    expect(canAct(user("agent"))).toBe(true);
    expect(canAct(user("admin"))).toBe(true);
    expect(canAct(null)).toBe(false);
  });

  it("reserves admin features for admins", () => {
    expect(isAdmin(user("admin"))).toBe(true);
    expect(isAdmin(user("agent"))).toBe(false);
  });
});

describe("format helpers", () => {
  it("humanizes status names", () => {
    expect(humanize("waiting_on_approval")).toBe("waiting on approval");
    expect(humanize(null)).toBe("");
  });

  it("shows a dash for a missing or invalid date", () => {
    expect(formatDate(null)).toBe("-");
    expect(formatDate("not a date")).toBe("-");
    expect(formatDate("2026-11-27T10:00:00Z")).not.toBe("-");
  });

  it("truncates long text with an ellipsis", () => {
    expect(truncate("abcdef", 4)).toBe("abc…");
    expect(truncate("abc", 4)).toBe("abc");
  });

  it("joins class names and skips falsy ones", () => {
    expect(cn("a", false, null, "b", undefined)).toBe("a b");
  });
});
