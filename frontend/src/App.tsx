import { useState } from 'react';
import { ModelGrid } from './components/ModelGrid';
import { Sidebar } from './components/Sidebar';
import { Chat } from './components/Chat';
import './App.css';

function App() {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);

  const handleOpenChat = (modelId?: string) => {
    console.log('handleOpenChat вызвана, modelId:', modelId);
    if (modelId) {
      setSelectedModel(modelId);
    }
    setIsChatOpen(true);
  };

  return (
    <>
      <div className="flex h-screen bg-[#0f1419]">
        <Sidebar onChatOpen={handleOpenChat} />
        <div className="flex-1">
          <ModelGrid onChatOpen={handleOpenChat} />
        </div>
      </div>
      
      <Chat 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)}
        selectedModel={selectedModel}
      />
    </>
  );
}

export default App;
