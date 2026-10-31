import { type FormEvent, type KeyboardEvent, useEffect, useState } from "react";
import Markdown from "react-markdown";

import logoDark from "../../docs/brand/smartb100-logo-dark.svg";
import logoLight from "../../docs/brand/smartb100-logo.svg";
import {
  ApiError,
  type Expertise,
  type PageConfig,
  askQuestion,
  fetchConfig,
  signIn,
} from "./api";
import { BAND_LABELS, classifyScore } from "./score";

interface Turn {
  id: number;
  question: string;
  answer: string;
  score: number;
}

const EXPERTISE: [Expertise, string][] = [
  ["beginner", "Beginner"],
  ["intermediate", "Intermediate"],
  ["expert", "Expert"],
];

function userMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Try again.";
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

function Score({ score, threshold }: { score: number; threshold: number }) {
  const band = classifyScore(score, threshold);
  return (
    <p className={`score score-${band}`}>
      Hallucination score {score.toFixed(2)}: <strong>{BAND_LABELS[band]}</strong>
    </p>
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

  const [name, setName] = useState("Farmer");
  const [expertise, setExpertise] = useState<Expertise>("intermediate");
  const [sessionId, setSessionId] = useState(newSessionId);

  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [chatError, setChatError] = useState<string | null>(null);

  function loadConfig() {
    setConfigError(null);
    fetchConfig()
      .then(setConfig)
      .catch((error: unknown) => setConfigError(userMessage(error)));
  }

  useEffect(loadConfig, []);

  async function handleSignIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username || !password) {
      setSignInError("Enter your username and password to sign in.");
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
    } catch (error) {
      setSignInError(userMessage(error));
    } finally {
      setSigningIn(false);
    }
  }

  async function send() {
    const text = question.trim();
    if (!token || !config || pending || !text) return;
    setPending(text);
    setChatError(null);
    try {
      const reply = await askQuestion(token, sessionId, text, { name, expertise }, config.chat_timeout);
      setTurns((previous) => [
        ...previous,
        { id: previous.length, question: text, answer: reply.answer, score: reply.hallucination_score },
      ]);
      // The field stays editable while waiting; keep a draft of the next question.
      setQuestion((current) => (current.trim() === text ? "" : current));
    } catch (error) {
      // The question stays in the input; sending it again is the user's call.
      setChatError(userMessage(error));
      if (error instanceof ApiError && error.unauthorized) setToken(null);
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
  }

  const canAsk = token !== null && config !== null && pending === null;

  return (
    <div className="page">
      <header className="masthead">
        <picture>
          <source media="(prefers-color-scheme: dark)" srcSet={logoDark} />
          <img src={logoLight} alt="SmartB100" width="201" height="48" />
        </picture>
        <p className="tagline">
          Answers from IAC Boletim 100, each with a hallucination score.
        </p>
      </header>

      {configError && (
        <div className="notice notice-error notice-row">
          <p role="alert">{configError}</p>
          <button type="button" onClick={loadConfig}>
            Retry
          </button>
        </div>
      )}

      <div className="layout">
        <aside className="panel">
          <section aria-labelledby="sign-in-heading">
            <h2 id="sign-in-heading">Account</h2>
            {token ? (
              <p role="status">Signed in as {signedInAs}.</p>
            ) : (
              <form onSubmit={handleSignIn} className="stack">
                <label>
                  Username
                  <input
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    autoComplete="username"
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete="current-password"
                  />
                </label>
                <button type="submit" disabled={signingIn}>
                  Sign in
                </button>
                {signInError && (
                  <p className="notice notice-error" role="alert">
                    {signInError}
                  </p>
                )}
                <p className="hint">
                  Accounts are created with <code>POST /auth/register</code>; see the README.
                </p>
              </form>
            )}
          </section>

          <section aria-labelledby="profile-heading" className="stack">
            <h2 id="profile-heading">Profile</h2>
            <label>
              Name
              <input
                value={name}
                maxLength={255}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            <label>
              Expertise
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
            <h2 id="session-heading">Session</h2>
            <p className="session-id">
              Session <code>{sessionId.slice(0, 8)}</code>
            </p>
            <button type="button" onClick={newSession} disabled={pending !== null}>
              New session
            </button>
          </section>
        </aside>

        <main className="chat">
          <ol className="conversation" aria-label="Conversation">
            {turns.map((turn) => (
              <li key={turn.id}>
                <p className="question">{turn.question}</p>
                <article className="answer">
                  <Markdown>{turn.answer}</Markdown>
                  {config && <Score score={turn.score} threshold={config.hallucination_threshold} />}
                </article>
              </li>
            ))}
            {pending !== null && (
              <li>
                <p className="question">{pending}</p>
                <p className="waiting" role="status">
                  Waiting for the answer. On a CPU-only machine this can take minutes.
                </p>
              </li>
            )}
          </ol>

          <form onSubmit={handleSubmit} className="ask">
            <label htmlFor="question">Your question</label>
            <textarea
              id="question"
              rows={3}
              maxLength={2000}
              value={question}
              disabled={token === null}
              placeholder={token ? "Ask about liming and fertilization" : "Sign in to ask a question"}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleKeyDown}
            />
            {chatError && (
              <p className="notice notice-error" role="alert">
                {chatError}
              </p>
            )}
            <button type="submit" disabled={!canAsk || !question.trim()}>
              Send
            </button>
          </form>
        </main>
      </div>
    </div>
  );
}
