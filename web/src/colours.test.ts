import { describe, expect, it } from "vitest";

import tokens from "../../docs/brand/tokens/tokens.css?raw";
import styles from "./styles.css?raw";

const BANDS = ["low", "moderate", "high"] as const;

/** The light block of a stylesheet: everything before a prefers-color-scheme: dark rule. */
function lightBlock(css: string): string {
  const at = css.indexOf("@media (prefers-color-scheme: dark)");
  return at < 0 ? css : css.slice(0, at);
}

function variable(css: string, name: string): string {
  const match = new RegExp(`--${name}:\s*([^;]+);`).exec(css);
  if (!match) throw new Error(`--${name} is not declared`);
  return match[1].trim();
}

/** Resolve a token to a hex colour, following var() through the brand tokens. */
function resolve(value: string): string {
  const ref = /^var\(--([\w-]+)\)$/.exec(value);
  if (!ref) return value;
  return resolve(variable(lightBlock(tokens), ref[1]));
}

function luminance(hex: string): number {
  const channels = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
  if (!channels) throw new Error(`not a six-digit hex colour: ${hex}`);
  const [r, g, b] = channels.slice(1).map((pair) => {
    const c = parseInt(pair, 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

describe("status colours", () => {
  // The page is light only (spec 0026), so the light background is the only one.
  it("status_colours_pass_contrast", () => {
    const background = resolve(variable(lightBlock(tokens), "sb-bg"));
    for (const band of BANDS) {
      const colour = resolve(variable(styles, `status-${band}`));
      expect(contrast(colour, background), `${band} on ${background}`).toBeGreaterThanOrEqual(4.5);
    }
  });
});
