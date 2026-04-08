import { useState, useEffect } from 'react';
import { api } from '../services/api';
import Sidebar from '../components/Sidebar';
import MainChat from '../components/MainChat';
import HallucinationPanel from '../components/HallucinationPanel';
import '../index.css';

export default function Dashboard() {
    const [conversations, setConversations] = useState([]);
    const [activeConvId, setActiveConvId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [showReport, setShowReport] = useState(false);
    const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }, [theme]);

    useEffect(() => {
        loadConversations();
    }, []);

    useEffect(() => {
        if (activeConvId) {
            loadMessages(activeConvId);
        } else {
            setMessages([]);
        }
    }, [activeConvId]);

    const loadConversations = async () => {
        try {
            const data = await api.get('/conversations');
            setConversations(data);
        } catch (e) {
            console.error("Failed to load conversations", e);
        }
    };

    const loadMessages = async (id) => {
        try {
            const data = await api.get(`/conversations/${id}/messages`);
            // Normalise field: backend returns `id`, ensure we have it
            setMessages(data.map(m => ({ ...m, context: m.context || [] })));
        } catch (e) {
            console.error("Failed to load messages", e);
        }
    };

    const handleNewConversation = async () => {
        try {
            const data = await api.post('/conversations', { title: 'Nova Conversa' });
            setConversations([data, ...conversations]);
            setActiveConvId(data.id);
        } catch (e) {
            console.error("Failed to create conversation", e);
        }
    };

    const handleSendMessage = async (text) => {
        let currentConvId = activeConvId;
        
        if (!currentConvId) {
            try {
                const data = await api.post('/conversations', { title: text.substring(0, 30) });
                setConversations([data, ...conversations]);
                currentConvId = data.id;
                setActiveConvId(currentConvId);
            } catch (e) {
                console.error("Failed to create conversation auto", e);
                return;
            }
        }

        // Optimistically add user message
        const userMsg = { role: 'user', content: text, context: [] };
        setMessages(prev => [...prev, userMsg]);
        setIsLoading(true);

        try {
            const res = await api.post(`/conversations/${currentConvId}/chat`, { question: text });
            
            // Refresh conversations to pick up auto-generated title
            loadConversations();

            // Add AI response immediately with all fields from backend
            // message_id is the DB ID of the assistant message
            setMessages(prev => [...prev, {
                id: res.message_id,          // critical: needed for rating
                role: 'assistant',
                content: res.answer,
                context: res.context || [],
                is_hallucinated: null,
            }]);
        } catch (e) {
            console.error("Erro ao enviar msg", e);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: '⚠️ Erro ao obter resposta. Tente novamente.',
                context: [],
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleRateMessage = async (messageId, isHallucinatedValue) => {
        try {
            await api.patch(`/messages/${messageId}/hallucination`, { is_hallucinated: isHallucinatedValue });
            // Update state in place so rating persists in current session
            setMessages(prev => prev.map(m =>
                m.id === messageId ? { ...m, is_hallucinated: isHallucinatedValue } : m
            ));
        } catch (e) {
            console.error("Failed to rate message", e);
        }
    };

    return (
        <div className="dashboard-container">
            <Sidebar 
                conversations={conversations} 
                activeConvId={activeConvId} 
                onSelectConversation={setActiveConvId}
                onNewConversation={handleNewConversation}
                theme={theme}
                onToggleTheme={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
                onOpenReport={() => setShowReport(true)}
            />
            <div className="main-content">
                <MainChat 
                    messages={messages} 
                    onSendMessage={handleSendMessage} 
                    onRateMessage={handleRateMessage}
                    isLoading={isLoading} 
                />
            </div>
            {showReport && <HallucinationPanel onClose={() => setShowReport(false)} />}
        </div>
    );
}
