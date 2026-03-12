import { useState } from 'react';
import logoUrl from '../assets/images/logo.png';

function MessageRow({ role, content, isError, isLoading }) {
  return (
    <div className={`message-row ${role}`}>
      <div className="message-content">
        <div className={`message-avatar ${role}`}>
          {role === 'user' ? 'U' : 'S'}
        </div>
        <div className={`message-text ${isLoading ? 'loading' : ''} ${isError ? 'error' : ''}`}>
          {isLoading ? (
            <span className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </span>
          ) : content}
        </div>
      </div>
    </div>
  );
}

function ChatInput({ onSubmit, isLoading }) {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;
    onSubmit(inputValue);
    setInputValue('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-input-container">
      <div className="chat-input-wrapper">
        <form onSubmit={handleSubmit} className="chat-input-box">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Envie uma mensagem..."
            className="chat-input"
            disabled={isLoading}
          />
          <button
            type="submit"
            className="chat-send-btn"
            disabled={!inputValue.trim() || isLoading}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 2L11 13" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" />
            </svg>
          </button>
        </form>
        <p className="chat-disclaimer">
          SmartB100 pode cometer erros. Verifique informações importantes.
        </p>
      </div>
    </div>
  );
}

export default function ChatScreen({ messages, isLoading, messagesEndRef, onSubmit }) {
  return (
    <div className="chat-screen">
      <header className="chat-header">
        <div className="chat-header-content">
          <img src={logoUrl} alt="SmartB100" className="chat-header-logo" />
          <h2>Smart<span>B100</span></h2>
        </div>
      </header>

      <div className="chat-messages-area">
        {messages.map((msg, index) => (
          <MessageRow
            key={index}
            role={msg.role}
            content={msg.content}
            isError={msg.isError}
          />
        ))}
        {isLoading && (
          <MessageRow role="ai" isLoading={true} />
        )}
        <div ref={messagesEndRef} />
      </div>

      <ChatInput onSubmit={onSubmit} isLoading={isLoading} />
    </div>
  );
}
