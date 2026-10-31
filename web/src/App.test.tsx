import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import indexHtml from "../index.html?raw";
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
  await user.type(screen.getByLabelText("Usuário"), "farmer");
  await user.type(screen.getByLabelText("Senha"), "correct horse");
  await user.click(screen.getByRole("button", { name: "Entrar" }));
  await screen.findByText(/conectado como/i);
}

async function ask(user: ReturnType<typeof userEvent.setup>, question: string): Promise<void> {
  await user.clear(screen.getByLabelText("Sua pergunta"));
  await user.type(screen.getByLabelText("Sua pergunta"), question);
  await user.click(screen.getByRole("button", { name: "Enviar" }));
}

/** The state each agent head on the page reports, in page order. */
function heads(): (string | null)[] {
  return Array.from(document.querySelectorAll(".agent-head"), (head) =>
    head.getAttribute("data-state"),
  );
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

    expect(screen.queryByLabelText("Sua pergunta")).toBeNull();
    await signIn(user);

    const login = calls.find((call) => call.url === "/api/auth/token")!;
    expect(login.init.method).toBe("POST");
    const form = new URLSearchParams(String(login.init.body));
    expect(form.get("username")).toBe("farmer");
    expect(form.get("password")).toBe("correct horse");
    await waitFor(() =>
      expect((screen.getByLabelText("Sua pergunta") as HTMLTextAreaElement).disabled).toBe(false),
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

    await user.clear(screen.getByLabelText("Nome"));
    await user.type(screen.getByLabelText("Nome"), "Ana");
    await user.selectOptions(screen.getByLabelText("Nível de conhecimento"), "expert");
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
      /ainda pode terminar/i,
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
      /ainda pode terminar/i,
    ],
    ["a 503", json({ detail: "unavailable" }, 503), /temporariamente indisponível/i],
    ["a 504", json({ detail: "timeout" }, 504), /esgotou o tempo/i],
    [
      "a network error",
      () => Promise.reject(new TypeError("Failed to fetch")),
      /não foi possível conectar à api/i,
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
      expect((screen.getByLabelText("Sua pergunta") as HTMLTextAreaElement).value).toBe(
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

    expect((await screen.findByRole("alert")).textContent).toMatch(/configurações da página/i);
    await user.click(screen.getByRole("button", { name: "Tentar de novo" }));
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
    await screen.findByRole("button", { name: "Entrar" });

    await user.clear(screen.getByLabelText("Usuário"));
    await user.type(screen.getByLabelText("Usuário"), "other");
    await user.type(screen.getByLabelText("Senha"), "battery staple");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    await screen.findByText(/conectado como other/i);

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
    await screen.findByRole("button", { name: "Entrar" });

    await user.type(screen.getByLabelText("Senha"), "correct horse");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    await screen.findByText(/conectado como farmer/i);

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

    expect((await screen.findByRole("alert")).textContent).toMatch(/entre de novo/i);
    expect(screen.queryByLabelText("Sua pergunta")).toBeNull();
    expect(screen.getByRole("button", { name: "Entrar" })).toBeTruthy();
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
    expect(within(first).getByText(/0,10/)).toBeTruthy();
    expect(within(first).getByText(/risco baixo/i)).toBeTruthy();
    expect(within(second).getByText(/0,90/)).toBeTruthy();
    expect(within(second).getByText(/risco alto/i)).toBeTruthy();
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
    await user.click(screen.getByRole("button", { name: "Nova conversa" }));

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
    await user.click(screen.getByRole("button", { name: "Nova conversa" }));
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
    await screen.findByText(/aguardando a resposta/i);
    await user.clear(screen.getByLabelText("Sua pergunta"));
    await user.type(screen.getByLabelText("Sua pergunta"), "Next question?");
    answer(json({ answer: "An answer.", hallucination_score: 0.1 }));
    await screen.findByText("An answer.");

    expect((screen.getByLabelText("Sua pergunta") as HTMLTextAreaElement).value).toBe(
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

  it("user_copy_is_portuguese", async () => {
    stubApi({ "/api/config": config(), "/api/auth/token": signedIn() });
    const user = userEvent.setup();
    render(<App />);

    for (const label of ["Usuário", "Senha"]) {
      expect(screen.getByLabelText(label)).toBeTruthy();
    }
    expect(screen.getByRole("button", { name: "Entrar" })).toBeTruthy();
    await signIn(user);
    for (const label of ["Nome", "Nível de conhecimento", "Sua pergunta"]) {
      expect(screen.getByLabelText(label)).toBeTruthy();
    }
    for (const name of ["Nova conversa", "Sair", "Enviar"]) {
      expect(screen.getByRole("button", { name })).toBeTruthy();
    }
    expect(indexHtml).toContain('<html lang="pt-BR">');
  });

  it("sign_in_has_its_own_screen", async () => {
    stubApi({ "/api/config": config(), "/api/auth/token": signedIn() });
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByLabelText("Usuário")).toBeTruthy();
    expect(screen.queryByLabelText("Sua pergunta")).toBeNull();
    expect(screen.queryByRole("button", { name: "Nova conversa" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Menu" })).toBeNull();

    await signIn(user);
    expect(screen.queryByLabelText("Usuário")).toBeNull();
    expect(screen.queryByLabelText("Senha")).toBeNull();
    expect(screen.getByLabelText("Sua pergunta")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Nova conversa" })).toBeTruthy();
  });

  it("sign_out_clears_the_conversation", async () => {
    let answer: (response: Response) => void = () => {};
    const calls = stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [
        json({ answer: "First answer.", hallucination_score: 0.1 }),
        () => new Promise<Response>((resolve) => (answer = resolve)),
        json({ answer: "Later answer.", hallucination_score: 0.1 }),
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);
    await user.clear(screen.getByLabelText("Nome"));
    await user.type(screen.getByLabelText("Nome"), "Ana");
    await ask(user, "First question?");
    await screen.findByText("First answer.");

    // A pending question keeps "Sair" disabled: its answer must not land after sign-out.
    await ask(user, "Second question?");
    await screen.findByText(/aguardando a resposta/i);
    expect((screen.getByRole("button", { name: "Sair" }) as HTMLButtonElement).disabled).toBe(true);
    answer(json({ answer: "Second answer.", hallucination_score: 0.1 }));
    await screen.findByText("Second answer.");

    await user.type(screen.getByLabelText("Sua pergunta"), "A draft");
    await user.click(screen.getByRole("button", { name: "Sair" }));
    expect((screen.getByLabelText("Usuário") as HTMLInputElement).value).toBe("");
    expect(screen.queryByLabelText("Sua pergunta")).toBeNull();

    await signIn(user);
    expect(screen.queryByText("First answer.")).toBeNull();
    expect(screen.queryByText("Second answer.")).toBeNull();
    expect((screen.getByLabelText("Nome") as HTMLInputElement).value).toBe("Produtor");
    expect((screen.getByLabelText("Sua pergunta") as HTMLTextAreaElement).value).toBe("");
    await ask(user, "Third question?");
    await screen.findByText("Later answer.");
    const [first, , third] = chatCalls(calls);
    expect(body(third).session_id).not.toBe(body(first).session_id);
  });

  it("the_agent_head_follows_the_request", async () => {
    let answer: (response: Response) => void = () => {};
    stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [
        () => new Promise<Response>((resolve) => (answer = resolve)),
        json({ detail: "unavailable" }, 503),
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);
    expect(heads()).toEqual(["idle"]);

    await ask(user, "First question?");
    await waitFor(() => expect(heads()).toEqual(["processing"]));
    // A request that stays pending keeps the state: nothing advances it on a timer.
    await new Promise((resolve) => setTimeout(resolve, 300));
    expect(heads()).toEqual(["processing"]);

    answer(json({ answer: "An answer.", hallucination_score: 0.1 }));
    await screen.findByText("An answer.");
    expect(heads()).toEqual(["done"]);

    await ask(user, "Second question?");
    await screen.findByRole("alert");
    expect(heads()).toEqual(["done", "error"]);
  });

  it("tables_render", async () => {
    stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [
        json({
          answer: "| Cultura | Dose |\n| --- | --- |\n| Soja | 2 t/ha |",
          hallucination_score: 0.1,
        }),
      ],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);

    await ask(user, "Which dose?");

    const table = await screen.findByRole("table");
    expect(within(table).getByRole("cell", { name: "Soja" })).toBeTruthy();
    expect(within(table).getByRole("cell", { name: "2 t/ha" })).toBeTruthy();
  });

  it("each_message_shows_its_time", async () => {
    stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [json({ answer: "An answer.", hallucination_score: 0.1 })],
    });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);

    await ask(user, "First question?");
    await screen.findByText("An answer.");

    const question = screen.getByText("First question?").closest("li")!;
    const answer = screen.getByText("An answer.").closest("article")!;
    for (const message of [question, answer]) {
      const time = message.querySelector("time");
      expect(time).not.toBeNull();
      expect(Number.isNaN(Date.parse(time!.dateTime))).toBe(false);
    }
  });

  it("copy_needs_a_clipboard: with a clipboard", async () => {
    stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [json({ answer: "Use **lime**.", hallucination_score: 0.1 })],
    });
    // setup() puts its own clipboard stub on navigator.
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);

    await ask(user, "Which lime?");
    await screen.findByText("lime");
    await user.click(screen.getByRole("button", { name: "Copiar" }));

    expect(await navigator.clipboard.readText()).toBe("Use **lime**.");
  });

  it("copy_needs_a_clipboard: without a clipboard", async () => {
    stubApi({
      "/api/config": config(),
      "/api/auth/token": signedIn(),
      "/api/chat": [json({ answer: "An answer.", hallucination_score: 0.1 })],
    });
    const user = userEvent.setup();
    // A plain-HTTP origin has no clipboard API.
    const own = Object.getOwnPropertyDescriptor(navigator, "clipboard");
    Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
    try {
      render(<App />);
      await signIn(user);
      await ask(user, "First question?");
      await screen.findByText("An answer.");

      expect(screen.queryByRole("button", { name: /copiar/i })).toBeNull();
    } finally {
      if (own) Object.defineProperty(navigator, "clipboard", own);
      else Reflect.deleteProperty(navigator, "clipboard");
    }
  });

  it("the_menu_toggles_the_sidebar", async () => {
    stubApi({ "/api/config": config(), "/api/auth/token": signedIn() });
    const user = userEvent.setup();
    render(<App />);
    await signIn(user);

    const menu = screen.getByRole("button", { name: "Menu" });
    const sidebar = document.getElementById(menu.getAttribute("aria-controls")!)!;
    expect(menu.getAttribute("aria-expanded")).toBe("false");
    expect(sidebar.dataset.open).toBe("false");

    await user.click(menu);
    expect(menu.getAttribute("aria-expanded")).toBe("true");
    expect(sidebar.dataset.open).toBe("true");

    await user.click(menu);
    expect(menu.getAttribute("aria-expanded")).toBe("false");
  });
});
