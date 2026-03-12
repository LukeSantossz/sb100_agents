const API_BASE = '/api';

export async function sendChatMessage(question) {
  const response = await fetch(`${API_BASE}/chat?question=${encodeURIComponent(question)}`);

  if (!response.ok) {
    throw new Error(`Erro na API: ${response.status}`);
  }

  return response.json();
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE}/health`);
  return response.json();
}
