# SPEC: feat(web): redesign the web page around the conversation

## Problem

The page from spec 0025 is a form with a conversation under it. Its copy is in English,
even though `CONTEXT.md` says User copy is Portuguese because the readers are Brazilian.
Answers and questions look the same, nothing on screen shows that a request is in flight
except one line of text, Markdown tables in an answer show as raw pipes, and on a phone
the sign-in and profile fields push the conversation below the fold.

## Design Decision

The same features, laid out like a chat product: a sidebar for the account, profile and
session, and a main column that is the conversation and a composer. The API contract
does not change.

- **Portuguese copy.** Every string the page shows is in Portuguese, including the error
  messages in `api.ts` and the score bands. `index.html` declares `lang="pt-BR"`. Scores
  use a decimal comma (`0,12`). Code, comments and tests stay in English.
- **Layout.**
  - Sidebar: the logo, a "Nova conversa" button (today's New session), the account
    (sign-in form, or "Conectado como ..."), the profile (name, expertise) and the
    session id.
  - Main column: the conversation, then the composer.
  - Below 48rem the sidebar is hidden behind a "Menu" button with `aria-expanded`, and
    the conversation fills the screen.
- **Messages.**
  - The question sits in a bubble on the right, with the time it was sent.
  - The answer sits in a card on the left, with the agent head, the Markdown, and a
    footer holding the score ("Pontuação de alucinação 0,12: Risco baixo") and the time
    it arrived.
  - Times come from the browser's clock at send and at arrival, shown as `HH:MM` in a
    `<time>` element.
- **The agent head.**
  - What it is: a 44 px inline SVG component in the assistant slot. It is a rounded head
    with a matte neutral shell drawn with gradients, a dark face, two soft green eyes and
    a small sprout on top. It has no body.
  - What it does not replace: the logo is untouched and appears only in the sidebar.
  - States, each set only by the request flow, never by a timer:
    - `idle`: an empty conversation.
    - `processing`: while `POST /chat` is in flight.
    - `done`: on every answered turn.
    - `error`: on a failed request, next to the message that says what happened.
  - Motion and accessibility: in `processing` the eyes pulse and the sprout sways, in CSS
    only. Under `prefers-reduced-motion: reduce` nothing moves. The head is
    `aria-hidden`, because the text beside it already says the same thing.
- **Tables.** `remark-gfm` renders GFM tables, strikethrough and task lists. Raw HTML is
  still not rendered.
- **Copy.** An answer has a "Copiar" button, and the session id has one too. The buttons
  show only when `navigator.clipboard` exists: the API is limited to secure contexts, and
  the Docker page is plain HTTP on the LAN, where a button that does nothing would be a
  lie.
- **Light only.** The page pins the light semantic tokens and declares
  `color-scheme: light`, so an OS dark preference no longer changes it. The dark tokens
  and the dark logo stay in `docs/brand/` for the README. Status colours are checked
  against the light background only.
- **No new runtime dependency besides `remark-gfm`.** No 3D library, image asset or
  animation runtime: the head is SVG and CSS.

## Alternatives Considered

- **A 3D head with Three.js or a GLB model.** Real depth, but it adds about 600 kB of
  JavaScript, a WebGL context and an asset pipeline for a 44 px avatar. Gradients on an
  SVG give the same read at that size.
- **A raster or Lottie animation.** It needs an asset per state and either a runtime or
  a sprite, and its frames cannot be stopped one by one for reduced motion as CSS can.
- **More states ("searching", "typing").** They would have to be faked with timers:
  `/chat` returns one JSON body at the end and streams nothing (#132). They wait for
  streaming.
- **Keep the English copy.** It goes against the User copy entry in `CONTEXT.md` and
  against the readers the corpus is for.
- **Keep the dark theme.** It doubles the visual check and the colour tests for a mode
  the Developer chose to drop.
- **Elements from the reference image with no data behind them:** the Favoritos, Guias
  práticos and Tabelas e doses navigation, chapter and page sources, related questions,
  feedback thumbs, bookmarks, attachments and a settings gear. Each would be a button
  that does nothing, or content the API does not return.

## Scope

- Includes:
  - `web/src/`: the new layout, the agent head component, the Portuguese copy in
    `App.tsx`, `api.ts` and `score.ts`, the copy buttons, the menu, and the styles.
  - `web/index.html`: `lang="pt-BR"`.
  - `remark-gfm` in `web/package.json` and `web/package-lock.json`.
  - The web tests moved to the Portuguese names, and the new tests below.
  - `colours.test.ts` checking the light theme only.
- Does NOT include:
  - The list of past conversations. Spec 0027 adds the backend history and the list in
    the sidebar.
  - Any change to `api/`, `agent/` or the `/chat`, `/auth` or `/config` contracts.
  - Source citations (#123), the empty-context warning (part 2 of #125), feedback
    (#131), streaming and the states that need it (#132), or telling a measured score
    from one never computed (#249).
  - A dark theme, or any change to the logo or to `docs/brand/`.
  - Creating an account from the page.

## Acceptance Criteria

Web, in `web/src/`, with Vitest. The tests from spec 0025 keep passing under their
Portuguese names.

- `user_copy_is_portuguese`: the sign-in, profile, session and composer controls are
  found by their Portuguese names. A 503 shows the Portuguese message. `index.html`
  declares `lang="pt-BR"`.
- `scores_use_a_decimal_comma`: a score of 0.1 shows as `0,10` with "Risco baixo".
- `the_agent_head_follows_the_request`: the head reports `idle` on an empty
  conversation, `processing` while the chat request is pending, `done` on the answer,
  and `error` when the request fails. No state changes while the request stays pending.
- `motion_stops_when_reduced`: `styles.css` has a `prefers-reduced-motion: reduce` block
  that turns off the head's animations.
- `tables_render`: an answer with a GFM table renders a `table` element with its cells.
  Raw HTML still renders as text.
- `each_message_shows_its_time`: the question and the answer each carry a `<time>`
  element with a `dateTime` that parses as a date.
- `copy_needs_a_clipboard`: with `navigator.clipboard`, "Copiar" writes the answer's
  Markdown to it. Without `navigator.clipboard`, no copy button is shown.
- `the_menu_toggles_the_sidebar`: the "Menu" button flips `aria-expanded` and the
  sidebar's visibility state.
- `the_page_stays_light`: `styles.css` declares `color-scheme: light`, pins `--sb-bg` to
  the paper colour after the brand tokens, and has no `prefers-color-scheme: dark` block.
- `status_colours_pass_contrast`: each band colour reaches 4.5:1 against the light
  background.

Both:

- `full_suite_stays_green`: `mf check`, and in `web/` `npm ci`, `npm run typecheck`,
  `npm test` and `npm run build` all pass. `pytest` is unaffected, since no Python
  changes.
- `the_page_is_checked_at_three_widths`: screenshots at 1440, 820 and 390 px wide,
  against a stub API, of an empty conversation, a pending question, two answers with a
  table and two score bands, and a failure. They are attached to the PR and not
  committed.

## Reproducibility

- Tests: `npm --prefix web ci`, then `npm --prefix web run typecheck`,
  `npm --prefix web test` and `npm --prefix web run build`.
- Visual check: run a stub of `/config`, `/auth/token` and `/chat` on :8000, then
  `npm --prefix web run dev` and open `http://localhost:5173` at each width.
- Node 22.12+, versions locked in `web/package-lock.json`.

## Risks and Assumptions

- Risk: a 44 px SVG may not read as "3D" to everyone. Accepted: depth comes from shading
  only, and the screenshots in the PR are the check.
- Risk: the copy buttons are absent on the plain-HTTP LAN page. Accepted: there is no
  clipboard API to call there, and hiding the button is honest.
- Risk: an OS dark preference no longer has any effect. Accepted: it is the Developer's
  choice for this page.
- Assumption: the times shown are the browser's clock. The API returns no timestamp,
  and spec 0027 can replace them with stored times.
- Assumption: `remark-gfm` 4.x works with `react-markdown` 10.x, its documented pairing.
