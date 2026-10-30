import { describe, expect, it } from "vitest";

import tokens from "../../docs/brand/tokens/tokens.css?raw";
import styles from "./styles.css?raw";

type Theme = "light" | "dark";
const BANDS = ["low", "moderate", "high"] as const;

/** Split a stylesheet into its light block and its prefers-color-scheme: dark block. */
function themeBlocks(css: string): Record<Theme, string> {
  const at = css.indexOf("@media (prefers-color-scheme: dark)");
  if (at < 0) throw new Error("stylesheet has no dark block");
  return { light: css.slice(0, at), dark: css.slice(at) };
}

function variable(css: string, name: string): string {
  const match = new RegExp(`--${name}:\s*([^;]+);`).exec(css);
  if (!match) throw new Error(`--${name} is not declared`);
  return match[1].trim();
}

/** Resolve a token to a hex colour, following var() through the brand tokens. */
function resolve(value: string, theme: Theme): string {
  const ref = /^var\(--([\w-]+)\)$/.exec(value);
  if (!ref) return value;
  const blocks = themeBlocks(tokens);
  const own = new RegExp(`--${ref[1]}:`).test(blocks[theme]) ? blocks[theme] : blocks.light;
  return resolve(variable(own, ref[1]), theme);
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
  it.each(["light", "dark"] as const)("status_colours_pass_contrast: %s", (theme) => {
    const background = resolve(variable(themeBlocks(tokens)[theme], "sb-bg"), theme);
    const own = themeBlocks(styles)[theme];
    for (const band of BANDS) {
      const colour = resolve(variable(own, `status-${band}`), theme);
      expect(contrast(colour, background), `${band} on ${background}`).toBeGreaterThanOrEqual(4.5);
    }
  });
});
