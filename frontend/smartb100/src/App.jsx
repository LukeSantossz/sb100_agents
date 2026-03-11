import { useState, useRef, useEffect } from "react";
import "./App.css";
import logoUrl from "./assets/images/logo.png";
import backgroundUrl from "./assets/images/background.png";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isStarted, setIsStarted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isStarted) {
      scrollToBottom();
    }
  }, [messages, isStarted]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    if (!isStarted) {
      setIsStarted(true);
    }

    const userMessage = { role: "user", content: inputValue };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      const response = await fetch(`http://localhost:8000/chat?question=${encodeURIComponent(userMessage.content)}`);
      const data = await response.json();
      
      const aiMessage = { role: "ai", content: data.answer };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error("Erro ao buscar a resposta da API", error);
      setMessages((prev) => [
        ...prev,
        { role: "ai", content: "Erro: Não foi possível se conectar à API." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isStarted) {
    return (
      <div 
        className="start-screen"
        style={{ backgroundImage: `url(${backgroundUrl})`, backgroundSize: 'cover', backgroundPosition: 'center' }}
      >
        <div className="center-container">
          <img src={logoUrl} alt="SmartB100 Logo" className="logo" />
          <h1 className="title">SmartB100</h1>
          <form onSubmit={handleSubmit} className="initial-form">
            <div className="input-group">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Digite sua pergunta aqui..."
                className="initial-input"
                autoFocus
              />
              <button type="submit" className="icon-send-btn" disabled={!inputValue.trim()}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-screen">
      <header className="chat-header">
        <h2>SmartB100</h2>
      </header>

      <div className="chat-container">
        <div className="messages">
          {messages.map((msg, index) => (
            <div key={index} className={`message-wrapper ${msg.role}`}>
              <div className="message-bubble" style={{ whiteSpace: "pre-wrap" }}>
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message-wrapper ai">
              <div className="message-bubble error">
                Carregando resposta...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="chat-input-area">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Digite outra pergunta..."
            className="chat-input"
          />
          <button type="submit" className="send-btn" disabled={!inputValue.trim() || isLoading}>
            Enviar
          </button>
        </form>
      </div>
    </div>
  );
}