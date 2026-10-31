import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

import logo from "../../docs/brand/smartb100-logo.svg";
import AgentHead from "./AgentHead";
import {
  ApiError,
  type Expertise,
  type PageConfig,
  askQuestion,
  fetchConfig,
  signIn,
} from "./api";
import { BAND_LABELS, classifyScore, formatScore } from "./score";

interface Turn {
  id: number;
  question: string;
  askedAt: Date;
  answer: string;
  answeredAt: Date;
  score: number;
}

interface Pending {
  question: string;
  askedAt: Date;
}

interface Failure extends Pending {
  message: string;
}

// How close to the bottom, in pixels, still counts as reading the newest message.
const NEAR_BOTTOM = 80;

const EXPERTISE: [Expertise, string][] = [
  ["beginner", "Iniciante"],
  ["intermediate", "Intermediário"],
  ["expert", "Especialista"],
];

const DEFAULT_NAME = "Produtor";
const DEFAULT_EXPERTISE: Expertise = "intermediate";

const REMARK_PLUGINS = [remarkGfm];

function userMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Algo deu errado. Tente de novo.";
}

// A v4 UUID from getRandomValues. crypto.randomUUID exists only in a secure context,
// and the Docker page is plain HTTP when opened from another machine on the LAN.
function newSessionId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join("-");
}

// navigator.clipboard, like randomUUID, exists only in a secure context. Without it a
// copy button would do nothing, so none is shown.
function hasClipboard(): boolean {
  return typeof navigator !== "undefined" && navigator.clipboard !== undefined;
}

/** The browser's clock at send or arrival; the API returns no timestamp. */
function Time({ at }: { at: Date }) {
  return (
    <time dateTime={at.toISOString()}>
      {at.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
    </time>
  );
}

function Score({ score, threshold }: { score: number; threshold: number }) {
  const band = classifyScore(score, threshold);
  return (
    <p className={`score score-${band}`}>
      Pontuação de alucinação {formatScore(score)}: <strong>{BAND_LABELS[band]}</strong>
    </p>
  );
}

function Question({ text, at }: { text: string; at: Date }) {
  return (
    <div className="question">
      <p>{text}</p>
      <Time at={at} />
    </div>
  );
}

const COPY_LABELS = { idle: "Copiar", copied: "Copiado", failed: "Falha ao copiar" };

function CopyButton({ text, label }: { text: string; label?: string }) {
  const [status, setStatus] = useState<keyof typeof COPY_LABELS>("idle");

  useEffect(() => {
    if (status === "idle") return;
    const timer = setTimeout(() => setStatus("idle"), 2000);
    return () => clearTimeout(timer);
  }, [status]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setStatus("copied");
    } catch {
      // A denied permission copies nothing; say so rather than look unchanged.
      setStatus("failed");
    }
  }

  return (
    <button type="button" className="quiet" aria-label={label} onClick={() => void copy()}>
      {COPY_LABELS[status]}
    </button>
  );
}

export default function App() {
  const [config, setConfig] = useState<PageConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  // The token lives in this state only: a reload signs the user out, and no
  // script on the page can read it back from storage.
  const [token, setToken] = useState<string | null>(null);
  const [signedInAs, setSignedInAs] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [signingIn, setSigningIn] = useState(false);
  const [signInError, setSignInError] = useState<string | null>(null);

  const [name, setName] = useState(DEFAULT_NAME);
  const [expertise, setExpertise] = useState<Expertise>(DEFAULT_EXPERTISE);
  const [sessionId, setSessionId] = useState(newSessionId);

  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState<Pending | null>(null);
  const [chatError, setChatError] = useState<Failure | null>(null);

  // Below 48rem the sidebar is closed until the Menu button opens it.
  const [menuOpen, setMenuOpen] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const chat = useRef<HTMLElement>(null);
  const atBottom = useRef(true);
  const canCopy = hasClipboard();

  function loadConfig() {
    setConfigError(null);
    fetchConfig()
      .then(setConfig)
      .catch((error: unknown) => setConfigError(userMessage(error)));
  }

  useEffect(loadConfig, []);

  function trackScroll() {
    const el = chat.current;
    if (el) atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight <= NEAR_BOTTOM;
  }

  // A question just sent always scrolls into view. An answer or error that arrives
  // scrolls only for a reader at the bottom, so one reading back keeps their place.
  // jsdom has no scrollIntoView, hence the optional call.
  useEffect(() => {
    if (pending !== null || atBottom.current) end.current?.scrollIntoView?.({ block: "end" });
  }, [turns, pending, chatError]);

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username || !password) {
      setSignInError("Informe usuário e senha para entrar.");
      return;
    }
    setSigningIn(true);
    setSignInError(null);
    try {
      setToken(await signIn(username, password));
      // Another account must not see, or continue, the previous account's conversation.
      if (signedInAs && username !== signedInAs) {
        setSessionId(newSessionId());
        setTurns([]);
      }
      setSignedInAs(username);
      setPassword("");
      setChatError(null);
      setMenuOpen(false);
    } catch (error) {
      setSignInError(userMessage(error));
    } finally {
      setSigningIn(false);
    }
  }

  async function send() {
    const text = question.trim();
    if (!token || !config || pending || !text) return;
    const askedAt = new Date();
    setPending({ question: text, askedAt });
    setChatError(null);
    try {
      const reply = await askQuestion(token, sessionId, text, { name, expertise }, config.chat_timeout);
      setTurns((previous) => [
        ...previous,
        {
          id: previous.length,
          question: text,
          askedAt,
          answer: reply.answer,
          answeredAt: new Date(),
          score: reply.hallucination_score,
        },
      ]);
      // The field stays editable while waiting; keep a draft of the next question.
      setQuestion((current) => (current.trim() === text ? "" : current));
    } catch (error) {
      // The failed question stays on screen above the error, even if the input was edited
      // meanwhile; sending it again is the user's call. An expired token sends the user
      // back to sign in, with the conversation kept in memory.
      if (error instanceof ApiError && error.unauthorized) {
        setToken(null);
        setSignInError(userMessage(error));
      } else {
        setChatError({ question: text, askedAt, message: userMessage(error) });
      }
    } finally {
      setPending(null);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  }

  function newSession() {
    setSessionId(newSessionId());
    setTurns([]);
    setChatError(null);
    setMenuOpen(false);
  }

  function signOut() {
    setToken(null);
    setSignedInAs("");
    setUsername("");
    setPassword("");
    setSignInError(null);
    setName(DEFAULT_NAME);
    setExpertise(DEFAULT_EXPERTISE);
    setQuestion("");
    newSession();
  }

  const configNotice = configError && (
    <div className="notice notice-row">
      <p role="alert">{configError}</p>
      <button type="button" onClick={loadConfig}>
        Tentar de novo
      </button>
    </div>
  );

  if (token === null) {
    return (
      <main className="sign-in">
        <div className="sign-in-card stack">
          <img className="logo" src={logo} alt="SmartB100" width="201" height="48" />
          <p className="tagline">Respostas do Boletim 100 do IAC</p>
          {configNotice}
          <form onSubmit={handleSignIn} className="stack" aria-labelledby="sign-in-heading">
            <h1 id="sign-in-heading">Entre na sua conta</h1>
            <label>
              Usuário
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
              />
            </label>
            <label>
              Senha
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
              />
            </label>
            <button type="submit" disabled={signingIn}>
              Entrar
            </button>
            {signInError && (
              <p className="notice" role="alert">
                {signInError}
              </p>
            )}
            <p className="hint">
              As contas são criadas com <code>POST /auth/register</code>; veja o README.
            </p>
          </form>
        </div>
      </main>
    );
  }

  const canAsk = config !== null && pending === null;
  const empty = turns.length === 0 && pending === null && chatError === null;

  return (
    <div className="app">
      <header className="topbar">
        <button
          type="button"
          className="menu-toggle"
          aria-controls="sidebar"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          Menu
        </button>
        <p className="tagline">Respostas do Boletim 100 do IAC</p>
      </header>

      <aside id="sidebar" className="sidebar" data-open={String(menuOpen)}>
        <img className="logo" src={logo} alt="SmartB100" width="201" height="48" />

        <button type="button" className="new-chat" onClick={newSession} disabled={pending !== null}>
          Nova conversa
        </button>

        <section aria-labelledby="profile-heading" className="stack">
          <h2 id="profile-heading">Perfil</h2>
          <label>
            Nome
            <input value={name} maxLength={255} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            Nível de conhecimento
            <select
              value={expertise}
              onChange={(event) => setExpertise(event.target.value as Expertise)}
            >
              {EXPERTISE.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </section>

        <section aria-labelledby="session-heading" className="stack">
          <h2 id="session-heading">Sessão</h2>
          <div className="session-row">
            <code className="session-id">{sessionId.slice(0, 8)}</code>
            {/* The key resets the button: a new id was never copied. */}
            {canCopy && <CopyButton key={sessionId} text={sessionId} label="Copiar id da sessão" />}
          </div>
        </section>

        <footer className="account">
          <p role="status">Conectado como {signedInAs}.</p>
          <button type="button" className="quiet" onClick={signOut} disabled={pending !== null}>
            Sair
          </button>
        </footer>
      </aside>

      <div className="main">
        {configNotice}

        <main className="chat" ref={chat} onScroll={trackScroll}>
          {empty ? (
            <div className="empty">
              <AgentHead state="idle" />
              <h1>Pergunte sobre calagem e adubação</h1>
              <p>
                As respostas vêm do Boletim 100 do IAC. Cada uma traz uma pontuação de
                alucinação.
              </p>
            </div>
          ) : (
            <ol className="conversation" aria-label="Conversa">
              {turns.map((turn) => (
                <li key={turn.id}>
                  <Question text={turn.question} at={turn.askedAt} />
                  <article className="answer">
                    <AgentHead state="done" />
                    <div className="answer-card">
                      <div className="markdown">
                        <Markdown remarkPlugins={REMARK_PLUGINS}>{turn.answer}</Markdown>
                      </div>
                      <footer className="answer-meta">
                        {config && (
                          <Score score={turn.score} threshold={config.hallucination_threshold} />
                        )}
                        <Time at={turn.answeredAt} />
                        {canCopy && <CopyButton text={turn.answer} />}
                      </footer>
                    </div>
                  </article>
                </li>
              ))}
              {pending !== null && (
                <li>
                  <Question text={pending.question} at={pending.askedAt} />
                  <div className="answer">
                    <AgentHead state="processing" />
                    <p className="answer-card waiting" role="status">
                      Aguardando a resposta. Em uma máquina só com CPU, isso pode levar minutos.
                    </p>
                  </div>
                </li>
              )}
              {chatError !== null && (
                <li>
                  <Question text={chatError.question} at={chatError.askedAt} />
                  <div className="answer">
                    <AgentHead state="error" />
                    <p className="answer-card notice" role="alert">
                      {chatError.message}
                    </p>
                  </div>
                </li>
              )}
            </ol>
          )}
          <div ref={end} />
        </main>

        <form onSubmit={handleSubmit} className="composer">
          <label htmlFor="question" className="visually-hidden">
            Sua pergunta
          </label>
          <textarea
            id="question"
            rows={2}
            maxLength={2000}
            value={question}
            placeholder="Pergunte sobre calagem e adubação"
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button type="submit" disabled={!canAsk || !question.trim()}>
            Enviar
          </button>
        </form>
      </div>
    </div>
  );
}
