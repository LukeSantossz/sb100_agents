import { describe, expect, it } from "vitest";

import { BAND_LABELS, classifyScore, formatScore } from "./score";

describe("score bands", () => {
  it("score_bands_follow_the_threshold", () => {
    // A threshold other than the 0.5 default, so edges hardcoded for 0.5 fail.
    const threshold = 0.4;
    const low = 0.6 * threshold;
    const moderate = 1.2 * threshold;

    expect(classifyScore(low - 0.001, threshold)).toBe("low");
    expect(classifyScore(low, threshold)).toBe("moderate");
    expect(classifyScore(moderate - 0.001, threshold)).toBe("moderate");
    expect(classifyScore(moderate, threshold)).toBe("high");
    expect(classifyScore(1, threshold)).toBe("high");

    expect(BAND_LABELS).toEqual({
      low: "Risco baixo",
      moderate: "Risco moderado",
      high: "Risco alto",
    });
  });

  it("scores_use_a_decimal_comma", () => {
    expect(formatScore(0.1)).toBe("0,10");
    expect(formatScore(0.7)).toBe("0,70");
    expect(formatScore(1)).toBe("1,00");
  });
});
