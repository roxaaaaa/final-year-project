import { describe, expect, it } from "vitest";
import { serialiseAutosavedExam, serialisePracticeExam } from "../lib/examStorage";

describe("serialisePracticeExam", () => {
  it("matches practice navigation payload shape", () => {
    const s = serialisePracticeExam("Soils", "higher", [{ q: 1 }]);
    expect(JSON.parse(s)).toEqual({
      topic: "Soils",
      level: "higher",
      questions: [{ q: 1 }],
    });
  });
});

describe("serialiseAutosavedExam", () => {
  it("includes generatedAt", () => {
    const s = serialiseAutosavedExam("T", "ordinary", [], "2020-01-01T00:00:00.000Z");
    expect(JSON.parse(s)).toEqual({
      topic: "T",
      level: "ordinary",
      questions: [],
      generatedAt: "2020-01-01T00:00:00.000Z",
    });
  });
});
