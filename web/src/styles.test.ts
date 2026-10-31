import { describe, expect, it } from "vitest";

import styles from "./styles.css?raw";

/** The body of the first `@media` block whose query contains `query`. */
function mediaBlock(css: string, query: string): string {
  const at = css.indexOf(query);
  if (at < 0) throw new Error(`no @media block for ${query}`);
  const open = css.indexOf("{", at);
  let depth = 0;
  for (let i = open; i < css.length; i++) {
    if (css[i] === "{") depth++;
    if (css[i] === "}" && --depth === 0) return css.slice(open + 1, i);
  }
  throw new Error(`unclosed @media block for ${query}`);
}

describe("page styles", () => {
  it("motion_stops_when_reduced", () => {
    const reduced = mediaBlock(styles, "prefers-reduced-motion: reduce");
    expect(reduced).toMatch(/\.agent-head[^{]*\{[^}]*animation:\s*none/);
  });

  it("the_page_stays_light", () => {
    expect(styles).toMatch(/color-scheme:\s*light;/);
    expect(styles).toMatch(/--sb-bg:\s*var\(--sb-paper\);/);
    expect(styles).not.toContain("prefers-color-scheme: dark");
  });
});
