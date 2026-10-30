# SPEC: docs(brand): give the repository a visual identity

## Problem

The repository has no mark, cover, favicon or avatar, so its README opens on a row of
badges and its future web UI has nothing of its own to wear.

## Design Decision

One identity, "Raiz-índice": a sprout with one leaf above a ground line, and below it a
root system that is also the retrieval graph. The roots taper with depth and end in chunk
glyphs, a square with three text lines. The three chunks retrieval returns (`top_k`
defaults to 3 in `core/config.py`) and the whole root path to each are drawn in amber and
ranked 1 to 3. The plant says what the corpus is about; the roots say what the system does.

- Wordmark `SmartB100`, Cascadia Mono 600, converted to outlines, so no SVG depends on an
  installed font.
- Palette: Ink `#0F1412`, Paper `#F5F6F3`, Sprout `#73E09A`, Leaf `#1F7A47`, Root
  `#5FB97E` / `#2E7D4F`, Evidence `#F2B53A` / `#8A5A00`, chunk `#3A4540` / `#B9C1BB`,
  dark / light. The amber is the project's own, not a vendor colour.
- Every asset exists in a light and a dark version. The README cover switches with the
  reader's GitHub theme through `<picture>` and `prefers-color-scheme`; `favicon.svg`
  switches with the browser's.
- The 16 px icon is drawn on its own pixel grid, because the 48-unit vector loses the
  roots at that size. 32 px and up use the vector.
- Assets live under `docs/brand/` as built output. The generator stays outside the
  repository: it pulls four npm packages (opentype.js, svgo, @resvg/resvg-js and the
  Cascadia Mono font files) that the project would otherwise never need.

## Alternatives Considered

- **D2, Horizonte.** A square soil section whose roots drop at right angles, like the
  output of `tree`. It avoids the leaf every agtech brand uses and makes a strong favicon,
  but alone it does not read as a plant and leans on the cover to tell the story.
- **D3, Raízes medidas.** Three root tips in the low, moderate and high bands of the
  hallucination score. It ties straight to the score, but a traffic light is the stock
  dashboard image, the UI's band colours fail on a light ground, and three hues weigh
  down a 16 px icon.
- **Qdrant's red for the retrieved chunk**, as an earlier variation did. It names one
  dependency in the identity and would have to change if the vector store does.
- **Versioning the generator.** Reproducible in one command, at the cost of a Node
  toolchain in a Python repository for files that change rarely.

## Scope

- Includes: `docs/brand/` with the mark, logo and cover SVGs (light and dark), the 500 px
  avatar PNGs, the 1280 x 640 social preview PNG, the favicon set (`favicon.svg`,
  `favicon.ico` with 16, 32 and 48 px, `apple-touch-icon.png`, `icon-16/32/48.png`), the
  colour and type tokens as JSON and CSS, and a short `docs/brand/README.md` naming each
  file, its use, the palette and the font licence; the README cover at the top; one
  affiliation line in the README License section: "Independent project. Not affiliated
  with or endorsed by the Instituto Agronômico (IAC)."
- Does NOT include: the generator script or any npm dependency; uploading the avatar or
  social preview, or any other GitHub setting, which the Developer does by hand; the web
  UI that will use the favicon and tokens; any change to the framework's
  `.standards/docs/standards/design.md`, which binds only the framework's own explainer
  page; any other README text.

## Acceptance Criteria

- `svgs_need_no_font`: no SVG under `docs/brand/` contains a `<text>` element.
- `svgs_load_nothing`: no file under `docs/brand/` references a URL other than the SVG
  namespace.
- `every_svg_has_a_title`: each mark, logo and cover SVG carries a `<title>`, so a
  screen reader announces it. `favicon.svg` is exempt: a browser tab never reads it out.
- `cover_follows_the_theme`: the README opens with a `<picture>` whose dark source is
  `docs/brand/cover-dark.svg`, whose fallback `<img>` is `docs/brand/cover-light.svg`, and
  whose `alt` names the project.
- `favicon_ico_holds_three_sizes`: `favicon.ico` declares 16, 32 and 48 px images.
- `readme_states_the_affiliation`: the License section contains the affiliation line
  verbatim.
- `full_suite_stays_green`: `mf check` and `pytest tests/ -m "not requires_infra"` pass.

## Reproducibility

The cover renders on GitHub in both themes; check by switching the GitHub appearance
setting on the branch page. `python -I` scripts against `docs/brand/` check the first
five criteria.

## Risks and Assumptions

- Risk: with the generator outside the repository, a later change to the identity
  means rebuilding or hand-editing the SVGs. Accepted: the files are small, outlined and
  readable, and the palette and geometry are written down here and in
  `docs/brand/README.md`.
- Assumption: Cascadia Mono is under the SIL Open Font License 1.1, which allows
  embedding outlined glyphs in a logo. The brand README names the licence.
- Assumption: GitHub honours `prefers-color-scheme` in `<picture>` sources in a README,
  which it documents.
