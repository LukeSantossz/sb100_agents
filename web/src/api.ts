/**
 * Calls to the SmartB100 API. Every path starts with /api, which the Vite dev
 * server and nginx both proxy to the API with the prefix stripped.
 *
 * Every error thrown here carries a message meant for the user; status codes and
 * URLs stay out of it.
 */

export type Expertise = "beginner" | "intermediate" | "expert";

export interface Profile {
  name: string;
  expertise: Expertise;
}

export interface PageConfig {
  hallucination_threshold: number;
  /** Seconds the page waits for POST /chat. */
  chat_timeout: number;
}

export interface Answer {
  answer: string;
  hallucination_score: number;
}

export class ApiError extends Error {
  /** True when the API rejected the token, so the page must sign the user out. */
  readonly unauthorized: boolean;

  constructor(message: string, unauthorized = false) {
    super(message);
    this.name = "ApiError";
    this.unauthorized = unauthorized;
  }
}

const UNREACHABLE = "Could not connect to the API. Check that the server is running and try again.";

export async function fetchConfig(): Promise<PageConfig> {
  let response: Response;
  try {
    response = await fetch("/api/config");
  } catch {
    throw new ApiError(UNREACHABLE);
  }
  if (!response.ok) throw new ApiError("Could not load the page settings from the API.");
  return (await response.json()) as PageConfig;
}

/** Exchange a username and password for a JWT. */
export async function signIn(username: string, password: string): Promise<string> {
  let response: Response;
  try {
    response = await fetch("/api/auth/token", {
      method: "POST",
      body: new URLSearchParams({ username, password }),
    });
  } catch {
    throw new ApiError(UNREACHABLE);
  }
  if (response.status === 401) {
    throw new ApiError("Sign-in failed: incorrect username or password.");
  }
  if (response.status === 429) throw new ApiError("Too many attempts. Wait a minute and try again.");
  if (!response.ok) throw new ApiError("Sign-in failed. Please try again.");
  const body = (await response.json()) as { access_token: string };
  return body.access_token;
}

function chatFailure(status: number): ApiError {
  if (status === 401) return new ApiError("Your session expired. Sign in again.", true);
  if (status === 429) return new ApiError("Request limit exceeded. Wait a few seconds and send again.");
  if (status === 503) {
    return new ApiError(
      "Service temporarily unavailable. The backend may be starting (Ollama or Qdrant). " +
        "Send the question again in a few moments.",
    );
  }
  if (status === 504) {
    return new ApiError(
      "The gateway timed out. The server may still finish and record this answer, " +
        "so sending the question again can answer it twice.",
    );
  }
  if (status >= 400 && status < 500) {
    return new ApiError(`Your question was rejected (code ${status}). Review it and try again.`);
  }
  return new ApiError("The server ran into a problem. Try again shortly.");
}

/**
 * Send one question to POST /chat, once.
 *
 * Never retried: /chat records the turn, so a resend after a timeout or a 5xx can
 * answer and store the same question twice (#99). The user decides to resend.
 */
export async function askQuestion(
  token: string,
  sessionId: string,
  question: string,
  profile: Profile,
  timeoutSeconds: number,
): Promise<Answer> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutSeconds * 1000);
  // The timer runs until the body is read: a server that sends its headers and then
  // stalls must not keep the page waiting past the timeout.
  try {
    let response: Response;
    try {
      response = await fetch("/api/chat", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, question, profile }),
        signal: controller.signal,
      });
    } catch {
      throw new ApiError(UNREACHABLE);
    }
    if (!response.ok) throw chatFailure(response.status);
    return (await response.json()) as Answer;
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ApiError(
        `No answer after ${timeoutSeconds} s. The server may still finish and record this ` +
          "answer, so sending the question again can answer it twice. On a CPU-only " +
          "machine Ollama can take several minutes per answer.",
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
