export type Band = "low" | "moderate" | "high";

/** Shown next to every score, so the band never depends on colour alone. */
export const BAND_LABELS: Record<Band, string> = {
  low: "Risco baixo",
  moderate: "Risco moderado",
  high: "Risco alto",
};

/** Two decimals with a decimal comma, as Brazilian readers write them. */
export function formatScore(score: number): string {
  return score.toFixed(2).replace(".", ",");
}

/**
 * Place a hallucination score in a band relative to the gate's threshold.
 *
 * The same edges the Gradio page drew: below 0.6 x threshold is low, below
 * 1.2 x threshold moderate, anything else high.
 */
export function classifyScore(score: number, threshold: number): Band {
  if (score < threshold * 0.6) return "low";
  if (score < threshold * 1.2) return "moderate";
  return "high";
}
