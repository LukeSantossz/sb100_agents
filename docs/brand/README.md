# SmartB100 brand

The mark is a sprout above a ground line with a root system below it. The roots are
the retrieval graph: they end in chunk glyphs, and the three chunks retrieval returns
(`top_k` defaults to 3) are drawn in amber with the whole path to each. The decision
and the alternatives are in [spec 0024](../specs/0024-give-the-repository-a-visual-identity.md).

These files are built output. The generator is not in this repository, so a change to
the identity means editing the SVGs by hand or rebuilding them outside it.

## Files

Every asset comes in a light and a dark version. A name without `-dark` is the light one.

| File | Use |
| --- | --- |
| `cover-light.svg`, `cover-dark.svg` | README cover, 1280 x 640. The README switches them with the reader's GitHub theme. |
| `smartb100-logo.svg`, `smartb100-logo-dark.svg` | Mark and wordmark side by side, for headers. |
| `smartb100-mark.svg`, `smartb100-mark-dark.svg` | Mark alone, on a 48-unit grid. |
| `avatar-light-500.png`, `avatar-dark-500.png` | GitHub or social avatar, 500 x 500. |
| `social-preview-1280x640.png` | GitHub social preview (the dark cover). |
| `favicon/favicon.svg` | Browser tab icon. Switches with the browser's colour scheme. |
| `favicon/favicon.ico` | Fallback icon with 16, 32 and 48 px images. |
| `favicon/icon-16.png`, `icon-32.png`, `icon-48.png` | The same sizes as PNG. The 16 px icon is drawn on its own pixel grid. |
| `favicon/apple-touch-icon.png` | iOS home screen icon, 180 x 180. |
| `tokens/tokens.json`, `tokens/tokens.css` | Colour and type tokens. The CSS also maps them to light and dark roles. Change both together. |

The SVGs contain no `<text>` and load nothing: the wordmark is converted to outlines.
`tests/test_brand_assets.py` checks this.

## Palette

| Role | Dark ground | Light ground |
| --- | --- | --- |
| Background | Ink `#0F1412` | Paper `#F5F6F3` |
| Leaf | Sprout `#73E09A` | Leaf `#1F7A47` |
| Root | `#5FB97E` | `#2E7D4F` |
| Evidence (retrieved chunks) | `#F2B53A` | `#8A5A00` |
| Chunk | `#3A4540` | `#B9C1BB` |

The amber marks evidence only. Use it for what retrieval returned, not as a general
accent.

## Type

The wordmark is `SmartB100` in Cascadia Mono, weight 600. Cascadia Mono is licensed
under the SIL Open Font License 1.1, which allows its glyphs to be embedded as outlines
in a logo. Body text uses the system sans stack in `tokens.json`.
