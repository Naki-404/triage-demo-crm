import { describe, expect, it } from "vitest";
import { api } from "./api";

describe("api helpers", () => {
  it("builds customer export URL under /api", () => {
    expect(api.exportUrl("csv")).toBe("/api/customers/export?fmt=csv");
    expect(api.exportUrl("xlsx")).toContain("/api/customers/export");
  });
});
