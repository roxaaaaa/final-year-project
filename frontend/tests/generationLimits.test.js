import { describe, expect, it } from "vitest";
import { computeGenerationsFromMeResponse } from "../lib/generationLimits";

describe("computeGenerationsFromMeResponse", () => {
  it("returns null user when data is missing", () => {
    expect(computeGenerationsFromMeResponse(null).user).toBeNull();
    expect(computeGenerationsFromMeResponse(undefined).user).toBeNull();
  });

  it("returns null user when id is missing", () => {
    const r = computeGenerationsFromMeResponse({ email: "a@b.com" });
    expect(r.user).toBeNull();
  });

  it("applies teacher quota", () => {
    const r = computeGenerationsFromMeResponse({
      id: "1",
      persona: "teacher",
      generations_number: 2,
    });
    expect(r.generationsTotal).toBe(5);
    expect(r.generationsRemaining).toBe(3);
  });

  it("applies student quota", () => {
    const r = computeGenerationsFromMeResponse({
      id: "2",
      persona: "student",
      generations_number: 1,
    });
    expect(r.generationsTotal).toBe(3);
    expect(r.generationsRemaining).toBe(2);
  });
});
