import { useState } from 'react';
import logoUrl from '../assets/images/logo.png';

const SUGGESTIONS = [
  'Qual a melhor época para plantar soja?',
  'Como corrigir acidez do solo?',
  'Pragas comuns na cultura de milho'
];

export default function StartScreen({ onSubmit }) {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    onSubmit(inputValue);
    setInputValue('');
  };

  const handleSuggestion = (suggestion) => {
    onSubmit(suggestion);
  };

  return (
    <div className="start-screen">
      <div className="start-content">
        <div className="logo-container">
          <img src={logoUrl} alt="SmartB100" className="logo" />
          <h1 className="logo-text">Smart<span>B100</span></h1>
        </div>

        <h2 className="welcome-title">Como posso ajudar?</h2>
        <p className="welcome-subtitle">
          Seu assistente inteligente para agricultura e agronegócio
        </p>

        <form onSubmit={handleSubmit} className="start-input-container">
          <div className="start-input-wrapper">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Faça uma pergunta sobre agricultura..."
              className="start-input"
              autoFocus
            />
            <button
              type="submit"
              className="start-send-btn"
              disabled={!inputValue.trim()}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 2L11 13" />
                <path d="M22 2L15 22L11 13L2 9L22 2Z" />
              </svg>
            </button>
          </div>
        </form>

        <div className="suggestions">
          {SUGGESTIONS.map((suggestion, index) => (
            <button
              key={index}
              className="suggestion-chip"
              onClick={() => handleSuggestion(suggestion)}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
