import { useState } from 'react';
import { StartScreen, ChatScreen } from './components';
import { useChat } from './hooks/useChat';
import './App.css';

export default function App() {
  const [isStarted, setIsStarted] = useState(false);
  const { messages, isLoading, messagesEndRef, sendMessage } = useChat();

  const handleSubmit = async (content) => {
    if (!isStarted) {
      setIsStarted(true);
    }
    await sendMessage(content);
  };

  if (!isStarted) {
    return <StartScreen onSubmit={handleSubmit} />;
  }

  return (
    <ChatScreen
      messages={messages}
      isLoading={isLoading}
      messagesEndRef={messagesEndRef}
      onSubmit={handleSubmit}
    />
  );
}
