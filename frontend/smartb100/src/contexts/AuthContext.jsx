import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const AuthContext = createContext({});

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (token) {
            // Se houvesse uma rota /me para checar, bateríamos nela aqui.
            // Para simplificar, assumimos que o token é válido enquanto não expirar e bater num endpoint
            setIsAuthenticated(true);
        }
        setIsLoading(false);

        const handleAuthExpired = () => {
            setIsAuthenticated(false);
            setUser(null);
        };

        window.addEventListener('auth-expired', handleAuthExpired);
        return () => window.removeEventListener('auth-expired', handleAuthExpired);
    }, []);

    const login = async (username, password) => {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const data = await api.postForm('/token', formData.toString(), {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });

        localStorage.setItem('token', data.access_token);
        setIsAuthenticated(true);
        setUser({ username });
    };

    const register = async (username, password) => {
        await api.post('/register', { username, password });
        // Opcionalmente fazer login direto
        await login(username, password);
    };

    const logout = () => {
        localStorage.removeItem('token');
        setIsAuthenticated(false);
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
