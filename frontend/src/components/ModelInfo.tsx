import { useModelStore } from '../stores/modelStore';
import { Sidebar } from './Sidebar';

export function ModelInfo() {
  const { selectedModel, selectModel } = useModelStore();

  if (!selectedModel) return null;

  // Моковые версии для примера
  const versions = selectedModel.versions || [
    { id: '1', name: 'unsloth/DeepSeek-V3.1-Terminus-GGUF', size: '3.9 mi', updated: '7 days ago' },
    { id: '2', name: 'unsloth/DeepSeek-V3.1-Terminus-GGUF', size: '3.9 mi', updated: '7 days ago' },
    { id: '3', name: 'unsloth/DeepSeek-V3.1-Terminus-GGUF', size: '3.9 mi', updated: '7 days ago' },
  ];

  return (
    <div className="fixed inset-0 z-50 bg-[#0f1419] flex">
      {/* Sidebar слева */}
      <Sidebar />
      
      {/* Основной контент */}
      <div className="flex-1 flex overflow-hidden">
        {/* Центральная часть с информацией */}
        <div className="flex-1 overflow-y-auto">
          {/* Хедер с кнопкой назад и поиском */}
          <div className="bg-[#1a1f2e] border-b border-gray-800 px-6 py-4 flex items-center gap-4">
            <button 
              onClick={() => selectModel(null)}
              className="text-gray-400 hover:text-white transition"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            
            <div className="flex-1 relative">
              <input 
                type="text" 
                placeholder="Search for models..."
                className="w-full bg-[#0f1419] text-white px-4 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500"
              />
              <svg className="w-5 h-5 text-gray-400 absolute right-3 top-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            
            <div className="text-sm text-gray-400">
              {selectedModel.name}
            </div>
          </div>

          {/* Контент модели */}
          <div className="p-6 max-w-4xl">
            {/* Заголовок */}
            <div className="mb-6">
              <h1 className="text-3xl font-bold text-white mb-2">{selectedModel.name}</h1>
              <div className="flex items-center gap-3 text-sm">
                <span className="px-3 py-1 bg-blue-500/10 text-blue-400 rounded-full">
                  {selectedModel.size}
                </span>
                <button className="px-4 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition">
                  Follow DeepSeek
                </button>
                <span className="text-gray-400">
                  Downloads last month: {selectedModel.downloads}
                </span>
              </div>
            </div>

            {/* Табы */}
            <div className="border-b border-gray-700 mb-6">
              <div className="flex gap-6 text-sm">
                <button className="pb-3 border-b-2 border-white text-white">Model card</button>
                <button className="pb-3 text-gray-400 hover:text-white transition">Files and versions</button>
                <button className="pb-3 text-gray-400 hover:text-white transition">Community</button>
              </div>
            </div>

            {/* Описание */}
            <div className="prose prose-invert max-w-none">
              <p className="text-gray-300 mb-4">{selectedModel.description}</p>
              
              <p className="text-gray-300 mb-4">
                Whisper is a state-of-the-art model for automatic speech recognition (ASR) and speech translation, 
                proposed in the paper Robust Speech Recognition via Large-Scale Weak Supervision by Alec Radford et al. 
                from OpenAI. Trained on &gt;5M hours of labeled data, Whisper demonstrates a strong ability to generalise 
                to many datasets and domains in a zero-shot setting.
              </p>

              <p className="text-gray-300 mb-4">
                Whisper large-v3 has the same architecture as the previous large and large-v2 models, except for the 
                following minor differences:
              </p>

              <ol className="list-decimal list-inside text-gray-300 mb-4 space-y-2">
                <li>The spectrogram input uses 128 Mel frequency bins instead of 80</li>
                <li>A new language token for Cantonese</li>
              </ol>

              <p className="text-gray-300">
                The Whisper large-v3 model was trained on 1 million hours of weakly labeled audio and 4 million hours 
                of pseudo-labeled audio collected using Whisper large-v2. The model was trained for 2.0 epochs over 
                this mixture dataset.
              </p>
            </div>
          </div>
        </div>

        {/* Правая панель с версиями */}
        <div className="w-80 bg-[#1a1f2e] border-l border-gray-800 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-sm font-semibold text-white mb-4">Versions:</h3>
            <div className="space-y-3">
              {versions.map((version) => (
                <div 
                  key={version.id}
                  className="p-3 bg-[#0f1419] rounded-lg hover:bg-[#151b24] transition cursor-pointer"
                >
                  <div className="text-sm text-white mb-1">{version.name}</div>
                  <div className="text-xs text-gray-400">
                    Text generation • XL 22B • {version.size}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Updated {version.updated} • {selectedModel.size}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
