import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User as UserIcon } from 'lucide-react';
import '../index.css';

export default function MainChat({ messages, onSendMessage, isLoading }) {
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
                        <Bot size={48} className="empty-icon" />
                        <h2>Bem-vindo ao AgroBot!</h2>
                        <p>Tire suas dúvidas técnicas sobre o Agronegócio abaixo.</p>
                    </div>
                ) : (
                    <div className="messages-list">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`message-wrapper ${msg.role}`}>
                                <div className="message-avatar">
                                    {msg.role === 'assistant' ? <Bot size={20} /> : <UserIcon size={20} />}
                                </div>
                                <div className="message-content">
                                    {msg.content}
                                    {/* Exibir o contexto se existir (pode ser útil já que modificamos o backend) */}
                                    {msg.role === 'assistant' && msg.context && (
                                        <div className="message-context-box">
                                            <strong>Contextos baseados no PDF:</strong>
                                            <ul>
                                                {msg.context.map((ctx, i) => (
                                                    <li key={i}>{ctx}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        {isLoading && (
                            <div className="message-wrapper assistant loading-wrapper">
                                <div className="message-avatar"><Bot size={20} /></div>
                                <div className="message-content typing-indicator">
                                    <span>.</span><span>.</span><span>.</span>
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
                        placeholder="Envie uma mensagem..."
                        rows="1"
                        disabled={isLoading}
                    />
                    <button type="submit" disabled={!input.trim() || isLoading} className="send-btn">
                        <Send size={18} />
                    </button>
                </form>
                <div className="input-footer">
                    O Assistente pode cometer erros de interpretação. Considere verificar as fontes.
                </div>
            </div>
        </div>
    );
}
