import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { UserPlus } from 'lucide-react';
import '../index.css';

export default function Register() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { register } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await register(username, password);
            navigate('/chat');
        } catch (err) {
            setError(err.message || 'Falha ao registrar');
        }
    };

    return (
        <div className="auth-container">
            <div className="auth-card glass-panel">
                <div className="auth-header">
                    <div className="logo-icon">
                        <UserPlus size={32} />
                    </div>
                    <h2>Crie sua conta</h2>
                    <p>Comece a explorar o sistema</p>
                </div>

                {error && <div className="auth-error">{error}</div>}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="form-group">
                        <label>Usuário</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="Escolha um nome de usuário"
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>Senha</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Crie uma senha forte"
                            required
                        />
                    </div>
                    <button type="submit" className="btn-primary">
                        Cadastrar
                    </button>
                </form>

                <div className="auth-footer">
                    Já tem uma conta? <Link to="/login">Faça Login</Link>
                </div>
            </div>
        </div>
    );
}
