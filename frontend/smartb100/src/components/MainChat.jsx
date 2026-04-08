import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User as UserIcon, ThumbsUp, ThumbsDown, ChevronDown, ChevronUp, Leaf } from 'lucide-react';
import '../index.css';

function MessageBubble({ msg, onRateMessage }) {
    const [showContext, setShowContext] = useState(false);
    const hasContext = msg.context && msg.context.length > 0;
    const rated = msg.is_hallucinated !== null && msg.is_hallucinated !== undefined;

    return (
        <div className={`message-wrapper ${msg.role}`}>
            <div className="message-avatar">
                {msg.role === 'assistant' ? <Leaf size={18} /> : <UserIcon size={18} />}
            </div>
            <div className="message-bubble-outer">
                <div className="message-content">
                    {msg.content}
                </div>


                {hasContext && (
                    <div className="context-section">
                        <button
                            className="context-toggle"
                            onClick={() => setShowContext(v => !v)}
                        >
                            {showContext ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            {showContext ? 'Ocultar fontes' : `${msg.context.length} fonte(s) do PDF`}
                        </button>
                        {showContext && (
                            <div className="context-list">
                                {msg.context.map((ctx, i) => (
                                    <div key={i} className="context-item">
                                        <span className="context-index">{i + 1}</span>
                                        <span>{ctx}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {msg.role === 'assistant' && msg.id && (
                    <div className="message-feedback">
                        <span className="feedback-label">Esta resposta foi útil?</span>
                        <div className="feedback-buttons">
                            <button
                                className={`feedback-btn good ${msg.is_hallucinated === 0 ? 'active-good' : ''}`}
                                onClick={() => onRateMessage(msg.id, 0)}
                                title="Resposta correta"
                            >
                                <ThumbsUp size={15} />
                                <span>Correto</span>
                            </button>
                            <button
                                className={`feedback-btn bad ${msg.is_hallucinated === 1 ? 'active-bad' : ''}`}
                                onClick={() => onRateMessage(msg.id, 1)}
                                title="Alucinação detectada"
                            >
                                <ThumbsDown size={15} />
                                <span>Incorreto</span>
                            </button>
                        </div>
                        {rated && (
                            <span className={`rating-badge ${msg.is_hallucinated === 0 ? 'badge-good' : 'badge-bad'}`}>
                                {msg.is_hallucinated === 0 ? '✓ Classificado como correto' : '⚠ Classificado como incorreto'}
                            </span>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}

export default function MainChat({ messages, onSendMessage, onRateMessage, isLoading }) {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading]);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (input.trim() && !isLoading) {
            onSendMessage(input);
            setInput('');
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    return (
        <div className="main-chat">
            <div className="chat-messages-container">
                {messages.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-icon-wrapper">
                            <Leaf size={48} />
                        </div>
                        <h2>Bem-vindo ao AgroBot!</h2>
                        <p>Seu assistente especializado em Agronegócio.<br/>Tire dúvidas técnicas sobre sua operação agrícola.</p>
                        <div className="suggestion-chips">
                            <button onClick={() => onSendMessage("Quais são as melhores práticas para irrigação?")} className="chip">💧 Irrigação</button>
                            <button onClick={() => onSendMessage("Como controlar pragas no plantio?")} className="chip">🐛 Controle de pragas</button>
                            <button onClick={() => onSendMessage("Qual é a época ideal para semear soja?")} className="chip">🌱 Época de plantio</button>
                        </div>
                    </div>
                ) : (
                    <div className="messages-list">
                        {messages.map((msg, idx) => (
                            <MessageBubble key={idx} msg={msg} onRateMessage={onRateMessage} />
                        ))}
                        {isLoading && (
                            <div className="message-wrapper assistant loading-wrapper">
                                <div className="message-avatar"><Leaf size={18} /></div>
                                <div className="message-content typing-indicator">
                                    <span></span><span></span><span></span>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            <div className="chat-input-container glass-panel">
                <form onSubmit={handleSubmit} className="input-form">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Pergunte algo sobre sua operação agrícola..."
                        rows="1"
                        disabled={isLoading}
                    />
                    <button type="submit" disabled={!input.trim() || isLoading} className="send-btn">
                        <Send size={18} />
                    </button>
                </form>
                <div className="input-footer">
                    AgroBot pode cometer erros. Verifique informações críticas com um especialista.
                </div>
            </div>
        </div>
    );
}
