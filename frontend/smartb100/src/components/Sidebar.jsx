import { Plus, MessageSquare, LogOut, Sun, Moon, Leaf } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import '../index.css';

export default function Sidebar({ conversations, activeConvId, onSelectConversation, onNewConversation, theme, onToggleTheme }) {
    const { user, logout } = useAuth();

    return (
        <div className="sidebar glass-panel">
            <div className="sidebar-header">
                <div className="sidebar-brand">
                    <Leaf size={22} className="brand-icon" />
                    <span className="brand-name">AgroBot</span>
                </div>
                <button className="new-chat-btn" onClick={onNewConversation}>
                    <Plus size={18} />
                    <span>Novo Chat</span>
                </button>
            </div>
            
            <div className="sidebar-content">
                <div className="history-label">Histórico</div>
                <div className="conversation-list">
                    {conversations.map(conv => (
                        <div 
                            key={conv.id} 
                            className={`conversation-item ${activeConvId === conv.id ? 'active' : ''}`}
                            onClick={() => onSelectConversation(conv.id)}
                        >
                            <MessageSquare size={16} />
                            <span className="truncate">{conv.title}</span>
                        </div>
                    ))}
                    {conversations.length === 0 && (
                        <div className="empty-history">Nenhuma conversa anterior</div>
                    )}
                </div>
            </div>

            <div className="sidebar-footer">
                <div className="user-info">
                    <div className="avatar">{user?.username?.[0]?.toUpperCase() || 'U'}</div>
                    <span className="truncate">{user?.username}</span>
                </div>
                <div className="sidebar-actions">
                    <button className="icon-btn" onClick={onToggleTheme} title={theme === 'dark' ? 'Modo Claro' : 'Modo Escuro'}>
                        {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
                    </button>
                    <button className="logout-btn" onClick={logout} title="Sair">
                        <LogOut size={18} />
                    </button>
                </div>
            </div>
        </div>
    );
}
