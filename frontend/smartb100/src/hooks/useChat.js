import { useState, useRef, useEffect, useCallback } from 'react';
import { sendChatMessage } from '../services/api';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const sendMessage = useCallback(async (content) => {
    if (!content.trim()) return false;

    const userMessage = { role: 'user', content };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const data = await sendChatMessage(content);
      const aiMessage = { role: 'ai', content: data.answer };
      setMessages(prev => [...prev, aiMessage]);
      return true;
    } catch (error) {
      console.error('Erro ao buscar resposta:', error);
      setMessages(prev => [
        ...prev,
        { role: 'ai', content: 'Erro: Não foi possível se conectar à API.', isError: true }
      ]);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    messages,
    isLoading,
    messagesEndRef,
    sendMessage
  };
}
