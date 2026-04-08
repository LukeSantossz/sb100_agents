import { Plus, MessageSquare, LogOut } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import '../index.css';

export default function Sidebar({ conversations, activeConvId, onSelectConversation, onNewConversation }) {
    const { user, logout } = useAuth();

    return (
        <div className="sidebar glass-panel">
            <div className="sidebar-header">
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
                <button className="logout-btn" onClick={logout} title="Sair">
                    <LogOut size={18} />
                </button>
            </div>
        </div>
    );
}
