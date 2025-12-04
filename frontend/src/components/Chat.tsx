import { useState } from 'react';
import { Sidebar } from './Sidebar';

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface ChatProps {
  isOpen: boolean;
  onClose: () => void;
  selectedModel: string | null;
}

export function Chat({ isOpen, onClose, selectedModel }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    { 
      id: 1, 
      text: 'Hi, how can I help you today?', 
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [isTyping, setIsTyping] = useState(false);

  const handleSendMessage = () => {
    if (!input.trim()) return;
    
    const newMessage: Message = {
      id: messages.length + 1,
      text: input,
      sender: 'user',
      timestamp: new Date()
    };
    
    setMessages([...messages, newMessage]);
    setInput('');
    
    // Имитация печати бота
    setIsTyping(true);
    setTimeout(() => {
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: prev.length + 1,
        text: 'This is a simulated response. Connect your AI model here!',
        sender: 'bot',
        timestamp: new Date()
      }]);
    }, 1500);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-[#0f1419] z-[999] flex">
      <Sidebar onChatOpen={onClose} />

      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="h-16 bg-gradient-to-r from-[#1a1f2e] to-[#161b26] border-b border-gray-800 flex items-center justify-between px-6 shadow-lg">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <div>
              <h3 className="text-white text-sm font-semibold">Chat Assistant</h3>
              {selectedModel && (
                <p className="text-xs text-gray-400">{selectedModel}</p>
              )}
            </div>
          </div>
          <button 
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-all"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg) => (
            <div 
              key={msg.id}
              className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
            >
              <div className={`max-w-[70%] ${msg.sender === 'user' ? 'order-2' : 'order-1'}`}>
                <div className={`flex items-end gap-2 ${msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  {/* Avatar */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 ${
                    msg.sender === 'user' 
                      ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white' 
                      : 'bg-gradient-to-br from-purple-500 to-purple-600 text-white'
                  }`}>
                    {msg.sender === 'user' ? 'U' : 'AI'}
                  </div>
                  
                  {/* Message bubble */}
                  <div className={`rounded-2xl px-4 py-3 shadow-md ${
                    msg.sender === 'user'
                      ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-br-sm'
                      : 'bg-[#1f2937] text-gray-100 rounded-bl-sm border border-gray-700'
                  }`}>
                    <p className="text-sm leading-relaxed">{msg.text}</p>
                    <span className={`text-[10px] mt-1 block ${
                      msg.sender === 'user' ? 'text-blue-100' : 'text-gray-500'
                    }`}>
                      {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
          
          {/* Typing indicator */}
          {isTyping && (
            <div className="flex justify-start animate-fadeIn">
              <div className="flex items-end gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center text-xs font-semibold text-white">
                  AI
                </div>
                <div className="bg-[#1f2937] rounded-2xl rounded-bl-sm px-4 py-3 border border-gray-700">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="p-4 bg-[#1a1f2e] border-t border-gray-800">
          <div className="max-w-4xl mx-auto">
            <div className="relative flex items-end gap-3">
              <div className="flex-1 relative">
                <textarea
                  rows={1}
                  className="w-full px-4 py-3 pr-12 bg-[#0f1419] border border-gray-700 rounded-2xl text-white text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all resize-none placeholder-gray-500"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message..."
                  style={{ minHeight: '44px', maxHeight: '120px' }}
                />
                <button 
                  className="absolute right-2 bottom-2 text-gray-400 hover:text-white transition-colors"
                  onClick={() => {}}
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                </button>
              </div>
              <button 
                onClick={handleSendMessage}
                disabled={!input.trim()}
                className="w-11 h-11 bg-gradient-to-br from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 disabled:from-gray-700 disabled:to-gray-700 disabled:cursor-not-allowed rounded-2xl text-white font-medium transition-all shadow-lg hover:shadow-blue-500/50 flex items-center justify-center"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Right panel - Settings */}
      <div className="w-80 bg-[#0d1117] border-l border-gray-800 p-6 overflow-y-auto">
        {/* Temperature */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-3">
            <h3 className="text-white text-sm font-semibold">Temperature</h3>
            <span className="text-blue-400 text-sm font-bold bg-blue-500/10 px-2 py-1 rounded-lg">
              {temperature.toFixed(1)}
            </span>
          </div>
          
          <div className="relative mb-2">
            <input 
              type="range" 
              min="0" 
              max="1" 
              step="0.1"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full h-2 rounded-lg appearance-none cursor-pointer slider-gradient"
              style={{
                background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${temperature * 100}%, #374151 ${temperature * 100}%, #374151 100%)`
              }}
            />
          </div>
          
          <div className="flex justify-between text-xs">
            <span className="text-gray-400 font-medium">🎯 Precise</span>
            <span className="text-gray-400 font-medium">🎨 Creative</span>
          </div>
          
          <div className="mt-3 p-3 bg-[#1a1f2e] rounded-lg border border-gray-800">
            <p className="text-xs text-gray-400 leading-relaxed">
              Controls randomness: Lower = more focused, Higher = more creative
            </p>
          </div>
        </div>
        
        {/* Model */}
        <div className="mb-6">
          <h3 className="text-white text-sm font-semibold mb-3">Active Model</h3>
          <div className="p-4 bg-gradient-to-br from-[#1a1f2e] to-[#161b26] rounded-xl border border-gray-700 shadow-lg">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white font-medium mb-1 truncate">
                  {selectedModel || 'No model selected'}
                </p>
                <p className="text-xs text-gray-400">
                  {selectedModel ? 'Ready to chat' : 'Select a model to start'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div>
          <h3 className="text-white text-sm font-semibold mb-3">Session Stats</h3>
          <div className="space-y-2">
            <div className="flex justify-between items-center p-3 bg-[#1a1f2e] rounded-lg border border-gray-800">
              <span className="text-xs text-gray-400">Messages</span>
              <span className="text-sm text-white font-semibold">{messages.length}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-[#1a1f2e] rounded-lg border border-gray-800">
              <span className="text-xs text-gray-400">Tokens Used</span>
              <span className="text-sm text-white font-semibold">~{messages.length * 50}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
