# SPEC: docs(brand): lay the README cover out as a banner with the chat page

## Problem

The README cover from spec 0024 is a 1280 x 640 poster: a large wordmark, a pipeline line, a
row of stack dots and the root graph. On the repository page it takes half a screen before
the first word of the README, and it shows the retrieval graph but not the product a reader
would use, the chat page of spec 0025 and spec 0026.

The Developer asked for the cover to follow the model of the VisioSoil app's README cover
(`LukeSantossz/visiosoil-app`, `docs/design/brand/readme-cover.svg`): a short banner with
the mark and the name on the left, one sentence under them, three feature pills, and on
the right a coloured panel holding a phone that shows the product's own screen.

## Design Decision

Rebuild `cover-light.svg` and `cover-dark.svg` as a 1280 x 400 banner in that model, in
SmartB100's own identity:

- **Card.** 1280 x 400, corners of 16, clipped. The left side is Paper `#F5F6F3` in the
  light cover and Ink `#0F1412` in the dark one; the right panel, from x = 760, is a green
  tint of the palette, `#D9EEDF` light and `#1D3A28` dark. A hairline in the rule colour
  edges the card.
- **Name.** The mark on a 96 px tile with corners of 22, the dark mark on an Ink tile, then
  `SmartB100` in Cascadia Mono 600.
- **Sentence.** "Answers from IAC Boletim 100, / each with a hallucination score.", the
  current cover's line, in Cascadia Mono 400 and the muted text colour.
- **Pills.** "Grounded answers", "Hallucination score" and "Three reader profiles", three of
  the features the README's What It Does section lists.
- **Phone.** A phone frame showing the chat page with its real Portuguese copy: the top bar
  with the mark and the name, one question bubble in Leaf, an answer card whose text is drawn
  as grey lines, the score line in the page's own words, "Pontuação de alucinação 0,18: Risco
  baixo", with the band in the page's low-risk colour, and the composer with its placeholder
  "Pergunte sobre calagem e adubação". The question and the score are illustrative, as the
  VisioSoil cover's camera screen is.
- All text is Cascadia Mono converted to outlines, as spec 0024 requires, and the generator
  stays outside the repository for the reason spec 0024 gives.

## Alternatives Considered

- **Keep the root graph in the right panel.** It is the identity's own picture and needs no
  invented question, but the model the Developer named puts the product's screen there, and
  the graph stays in the mark on the left.
- **A browser window instead of a phone.** Closer to how the chat page is mostly opened, but
  at 520 px wide it shrinks the page's text below legibility, and it departs from the model.
- **Draw the phone's text in a sans face.** The chat page itself uses the system sans stack,
  but no sans face here is under a licence that plainly allows embedding its outlines, and
  spec 0024 already licenses Cascadia Mono for that use.
- **Resize the social preview to match.** GitHub asks for a 2:1 social preview, so
  `social-preview-1280x640.png` keeps its 1280 x 640 poster.

## Scope

- Includes: `docs/brand/cover-light.svg` and `docs/brand/cover-dark.svg` rebuilt as above;
  the cover's row in `docs/brand/README.md`; a test pinning the banner's size.
- Does NOT include: the social preview PNG, the avatar or any GitHub setting; the mark, the
  logo, the favicon or the tokens; the generator; any other README text, including the
  cover's `alt`, which still describes the banner.

## Acceptance Criteria

- `cover_is_a_banner`: both cover SVGs declare a 1280 x 400 `viewBox`, `width` and
  `height` (red before the change: they are 1280 x 640).
- `svgs_need_no_font`, `svgs_load_nothing`, `every_svg_has_a_title`,
  `cover_follows_the_theme`, `favicon_ico_holds_three_sizes` and
  `readme_states_the_affiliation` still pass.
- `full_suite_stays_green`: `mf check` and `pytest tests/ -m "not requires_infra"` pass.

## Reproducibility

Open the branch page on GitHub and switch the appearance setting between light and dark;
the README shows the matching cover. `pytest tests/test_brand_assets.py` checks the
criteria above.

## Risks and Assumptions

- Assumption: a 1280 x 400 SVG under `width="100%"` renders at the README's full width on
  GitHub, as the VisioSoil cover does.
- Risk: the phone's 8.5 px text is small on a narrow screen. Accepted: it is a picture of
  the page, and the sentence and the pills on the left carry the message.
- Risk: the illustrative score could be read as a measured one. Accepted: the cover shows
  the page, not a result, and the README's Known Issues section states what the score is.
