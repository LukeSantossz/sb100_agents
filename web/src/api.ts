/**
 * Calls to the SmartB100 API. Every path starts with /api, which the Vite dev
 * server and nginx both proxy to the API with the prefix stripped.
 *
 * Every error thrown here carries a message meant for the user, in Portuguese like
 * the rest of the page; status codes and URLs stay out of it.
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

const UNREACHABLE = "Não foi possível conectar à API. Verifique se o servidor está rodando e tente de novo.";

export async function fetchConfig(): Promise<PageConfig> {
  let response: Response;
  try {
    response = await fetch("/api/config");
  } catch {
    throw new ApiError(UNREACHABLE);
  }
  if (!response.ok) throw new ApiError("Não foi possível carregar as configurações da página.");
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
    throw new ApiError("Falha ao entrar: usuário ou senha incorretos.");
  }
  if (response.status === 429) throw new ApiError("Muitas tentativas. Aguarde um minuto e tente de novo.");
  if (!response.ok) throw new ApiError("Falha ao entrar. Tente de novo.");
  const body = (await response.json()) as { access_token: string };
  return body.access_token;
}

function chatFailure(status: number): ApiError {
  if (status === 401) return new ApiError("Sua sessão expirou. Entre de novo.", true);
  if (status === 429) return new ApiError("Limite de pedidos atingido. Aguarde alguns segundos e envie de novo.");
  if (status === 503) {
    return new ApiError(
      "Serviço temporariamente indisponível. O backend pode estar iniciando (Ollama ou " +
        "Qdrant). Envie a pergunta de novo em alguns instantes.",
    );
  }
  if (status === 504) {
    return new ApiError(
      "O gateway esgotou o tempo de espera. O servidor ainda pode terminar e registrar " +
        "esta resposta, então enviar a pergunta de novo pode respondê-la duas vezes.",
    );
  }
  if (status >= 400 && status < 500) {
    return new ApiError(`Sua pergunta foi recusada (código ${status}). Revise e tente de novo.`);
  }
  return new ApiError("O servidor encontrou um problema. Tente de novo em instantes.");
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
        `Sem resposta após ${timeoutSeconds.toLocaleString("pt-BR")} s. O servidor ainda pode ` +
          "terminar e registrar esta resposta, então enviar a pergunta de novo pode " +
          "respondê-la duas vezes. Em uma máquina só com CPU, o Ollama pode levar vários " +
          "minutos por resposta.",
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
