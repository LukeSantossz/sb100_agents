import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";

const TOKEN = "header.payload.signature";

type Reply = Response | Promise<Response> | ((init: RequestInit) => Response | Promise<Response>);

interface Call {
  url: string;
  init: RequestInit;
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Stub fetch with one queue of replies per path; record every call. */
function stubApi(routes: Record<string, Reply[]>): Call[] {
  const calls: Call[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
      const url = String(input);
      calls.push({ url, init });
      const queue = routes[url];
      if (!queue || queue.length === 0) throw new Error(`unexpected request to ${url}`);
      const reply = queue.length > 1 ? queue.shift()! : queue[0];
      return typeof reply === "function" ? reply(init) : reply;
    }),
  );
  return calls;
}

function config(threshold = 0.5, timeout = 600): Reply[] {
  return [json({ hallucination_threshold: threshold, chat_timeout: timeout })];
}

// A factory, not one Response: a second sign-in would find the body already read.
function signedIn(): Reply[] {
  return [() => json({ access_token: TOKEN, token_type: "bearer" })];
}

function chatCalls(calls: Call[]): Call[] {
  return calls.filter((call) => call.url === "/api/chat");
}

function body(call: Call): Record<string, unknown> {
  return JSON.parse(String(call.init.body)) as Record<string, unknown>;
}

async function signIn(user: ReturnType<typeof userEvent.setup>): Promise<void> {
  await user.type(screen.getByLabelText("Username"), "farmer");
  await user.type(screen.getByLabelText("Password"), "correct horse");
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  await screen.findByText(/signed in/i);
}

async function ask(user: ReturnType<typeof userEvent.setup>, question: string): Promise<void> {
  await user.clear(screen.getByLabelText("Your question"));
  await user.type(screen.getByLabelText("Your question"), question);
  await user.click(screen.getByRole("button", { name: "Send" }));
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("web app", () => {
  it("sign_in_keeps_the_token_in_memory", async () => {
    const calls = stubApi({ "/api/config": config(), "/api/auth/token": signedIn() });
    const user = userEvent.setup();
    render(<App />);

    expect((screen.getByLabelText("Your question") as HTMLTextAreaElement).disabled).toBe(true);
    await signIn(user);

    const login = calls.find((call) => call.url === "/api/auth/token")!;
    expect(login.init.method).toBe("POST");
    const form = new URLSearchParams(String(login.init.body));
    expect(form.get("username")).toBe("farmer");
    expect(form.get("password")).toBe("correct horse");
    await waitFor(() =>
      expect((screen.getByLabelText("Your question") as HTMLTextAreaElement).disabled).toBe(false),
    );
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(document.cookie).not.toContain(TOKEN);
  });

  it("a_question_carries_the_token_session_and_profile", async () => {
    const calls = stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [json({ answer: "Apply lime.", hallucination_score: 0.1 })],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);

    await user.clear(screen.getByLabelText("Name"));
    await user.type(screen.getByLabelText("Name"), "Ana");
    await user.selectOptions(screen.getByLabelText("Expertise"), "expert");
    await ask(user, "How do I correct soil acidity?");
    await screen.findByText("Apply lime.");

    const [chat] = chatCalls(calls);
    expect(chat.init.method).toBe("POST");
    expect(new Headers(chat.init.headers).get("Authorization")).toBe(`Bearer ${TOKEN}`);
    const sent = body(chat);
    expect(sent.question).toBe("How do I correct soil acidity?");
    expect(sent.profile).toEqual({ name: "Ana", expertise: "expert" });
    expect(typeof sent.session_id).toBe("string");
    expect(String(sent.session_id).length).toBeGreaterThan(0);
  });

  const failures: [string, Reply, RegExp][] = [
    [
      "a timeout",
      (init) =>
        new Promise<Response>((_, reject) => {
          init.signal?.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          );
        }),
      /may still finish/i,
    ],
    [
      "a body that stalls",
      // Headers arrive at once, then the body never ends: the timeout must cover it too.
      (init) =>
        new Response(
          new ReadableStream({
            start(stream) {
              init.signal?.addEventListener("abort", () =>
                stream.error(new DOMException("aborted", "AbortError")),
              );
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      /may still finish/i,
    ],
    ["a 503", json({ detail: "unavailable" }, 503), /temporarily unavailable/i],
    ["a 504", json({ detail: "timeout" }, 504), /gateway timed out/i],
    [
      "a network error",
      () => Promise.reject(new TypeError("Failed to fetch")),
      /could not connect to the api/i,
    ],
  ];

  it.each(failures)(
    "a_failed_question_is_not_resent: %s",
    { timeout: 10_000 },
    async (_name, reply, message) => {
      // A 50 ms chat timeout, so the timeout case fires within the test.
      const calls = stubApi({
        "/api/config": config(0.5, 0.05),
        "/api/auth/token": signedIn(),
        "/api/chat": [reply],
      });
      const user = userEvent.setup();
      render(<App />);
      await signIn(user);

      await ask(user, "How much lime per hectare?");

      expect(await screen.findByRole("alert")).toHaveProperty(
        "textContent",
        expect.stringMatching(message),
      );
      // Well past a 1 s retry backoff, the shortest the Gradio page used.
      await new Promise((resolve) => setTimeout(resolve, 2500));
      expect(chatCalls(calls)).toHaveLength(1);
      expect((screen.getByLabelText("Your question") as HTMLTextAreaElement).value).toBe(
        "How much lime per hectare?",
      );
    },
  );

  it("the_settings_can_be_loaded_again", async () => {
    stubApi({
      "/api/config": [json({ detail: "error" }, 500), ...config()],
      "/api/auth/token": signedIn(),
      "/api/chat": [json({ answer: "Apply lime.", hallucination_score: 0.1 })],
    });
    const user = userEvent.setup();
    render(<App />);

    expect((await screen.findByRole("alert")).textContent).toMatch(/page settings/i);
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());

    await signIn(user);
    await ask(user, "How much lime per hectare?");
    await screen.findByText("Apply lime.");
  });

  it("another_account_starts_a_clean_conversation", async () => {
    const calls = stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [
        json({ answer: "First answer.", hallucination_score: 0.1 }),
        json({ detail: "Could not validate credentials" }, 401),
        json({ answer: "Other answer.", hallucination_score: 0.1 }),
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);
    await ask(user, "First question?");
    await screen.findByText("First answer.");
    await ask(user, "Second question?");
    await screen.findByRole("button", { name: "Sign in" });

    await user.clear(screen.getByLabelText("Username"));
    await user.type(screen.getByLabelText("Username"), "other");
    await user.type(screen.getByLabelText("Password"), "battery staple");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByText(/signed in as other/i);

    expect(screen.queryByText("First answer.")).toBeNull();
    await ask(user, "Third question?");
    await screen.findByText("Other answer.");
    const [first, , third] = chatCalls(calls);
    expect(body(third).session_id).not.toBe(body(first).session_id);
  });

  it("the_same_account_signing_in_again_keeps_the_conversation", async () => {
    const calls = stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [
        json({ answer: "First answer.", hallucination_score: 0.1 }),
        json({ detail: "Could not validate credentials" }, 401),
        json({ answer: "Later answer.", hallucination_score: 0.1 }),
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);
    await ask(user, "First question?");
    await screen.findByText("First answer.");
    await ask(user, "Second question?");
    await screen.findByRole("button", { name: "Sign in" });

    await user.type(screen.getByLabelText("Password"), "correct horse");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByText(/signed in as farmer/i);

    expect(screen.getByText("First answer.")).toBeTruthy();
    await ask(user, "Third question?");
    await screen.findByText("Later answer.");
    const [first, , third] = chatCalls(calls);
    expect(body(third).session_id).toBe(body(first).session_id);
  });

  it("unauthorized_signs_out", async () => {
    stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [json({ detail: "Could not validate credentials" }, 401)],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);

    await ask(user, "How much lime per hectare?");

    expect((await screen.findByRole("alert")).textContent).toMatch(/sign in again/i);
    expect((screen.getByLabelText("Your question") as HTMLTextAreaElement).disabled).toBe(true);
    expect(screen.getByRole("button", { name: "Sign in" })).toBeTruthy();
  });

  it("each_score_sits_under_its_answer", async () => {
    stubApi({
      "/api/config": config(0.5),
      "/api/auth/token": signedIn(),
      "/api/chat": [
        json({ answer: "First answer.", hallucination_score: 0.1 }),
        json({ answer: "Second answer.", hallucination_score: 0.9 }),
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);

    await ask(user, "First question?");
    await screen.findByText("First answer.");
    await ask(user, "Second question?");
    await screen.findByText("Second answer.");

    const first = screen.getByText("First answer.").closest("article")!;
    const second = screen.getByText("Second answer.").closest("article")!;
    expect(within(first).getByText(/0\.10/)).toBeTruthy();
    expect(within(first).getByText(/low risk/i)).toBeTruthy();
    expect(within(second).getByText(/0\.90/)).toBeTruthy();
    expect(within(second).getByText(/high risk/i)).toBeTruthy();
  });

  it("new_session_keeps_the_sign_in", async () => {
    const calls = stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [json({ answer: "An answer.", hallucination_score: 0.1 })],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);

    await ask(user, "First question?");
    await screen.findByText("An answer.");
    await user.click(screen.getByRole("button", { name: "New session" }));

    expect(screen.queryByText("An answer.")).toBeNull();
    await ask(user, "Second question?");
    await waitFor(() => expect(chatCalls(calls)).toHaveLength(2));

    const [before, after] = chatCalls(calls);
    expect(body(after).session_id).not.toBe(body(before).session_id);
    expect(new Headers(after.init.headers).get("Authorization")).toBe(`Bearer ${TOKEN}`);
  });

  it("starts_without_a_secure_context", async () => {
    // Over plain HTTP on a LAN address the browser offers getRandomValues but not
    // randomUUID, which exists only in a secure context.
    const { getRandomValues } = globalThis.crypto;
    vi.stubGlobal("crypto", { getRandomValues: getRandomValues.bind(globalThis.crypto) });
    const calls = stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [json({ answer: "An answer.", hallucination_score: 0.1 })],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);

    await ask(user, "First question?");
    await screen.findByText("An answer.");
    await user.click(screen.getByRole("button", { name: "New session" }));
    await ask(user, "Second question?");
    await waitFor(() => expect(chatCalls(calls)).toHaveLength(2));

    const [before, after] = chatCalls(calls).map((call) => String(body(call).session_id));
    expect(before).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(after).not.toBe(before);
  });

  it("a_draft_typed_while_waiting_is_kept", async () => {
    let answer: (response: Response) => void = () => {};
    stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [() => new Promise<Response>((resolve) => (answer = resolve))],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);

    await ask(user, "First question?");
    await screen.findByText(/waiting for the answer/i);
    await user.clear(screen.getByLabelText("Your question"));
    await user.type(screen.getByLabelText("Your question"), "Next question?");
    answer(json({ answer: "An answer.", hallucination_score: 0.1 }));
    await screen.findByText("An answer.");

    expect((screen.getByLabelText("Your question") as HTMLTextAreaElement).value).toBe(
      "Next question?",
    );
  });

  it("markdown_renders_without_html", async () => {
    stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [
        json({
          answer: "Use **dolomitic lime**.\n\n<img src=x onerror=alert(1)>",
          hallucination_score: 0.1,
        }),
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);

    await ask(user, "Which lime?");

    const bold = await screen.findByText("dolomitic lime");
    expect(bold.tagName).toBe("STRONG");
    const answer = bold.closest("article")!;
    expect(answer.querySelector("img")).toBeNull();
    expect(answer.textContent).toContain("<img src=x onerror=alert(1)>");
  });
});
