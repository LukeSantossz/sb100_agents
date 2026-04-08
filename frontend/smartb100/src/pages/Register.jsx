import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { Leaf } from 'lucide-react';
import '../index.css';

export default function Register() {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { register } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await register(username, password);
            navigate('/chat');
        } catch (err) {
            setError(err.message || 'Falha ao registrar');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="auth-wrapper">
            <div className="auth-card glass-panel">
                <div className="auth-brand">
                    <Leaf size={30} className="auth-brand-icon" />
                    <h1>AgroBot</h1>
                </div>
                <h2>Crie sua conta</h2>
                <p>Comece a explorar o assistente agrícola</p>

                {error && <div className="error-msg">{error}</div>}

                <form onSubmit={handleSubmit}>
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
                            placeholder="Crie uma senha"
                            required
                        />
                    </div>
                    <button type="submit" className="auth-btn" disabled={loading}>
                        {loading ? 'Cadastrando...' : 'Criar conta'}
                    </button>
                </form>

                <div className="auth-link">
                    Já tem uma conta? <Link to="/login">Faça Login</Link>
                </div>
            </div>
        </div>
    );
}
