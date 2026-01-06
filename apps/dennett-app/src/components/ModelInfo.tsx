import { useState } from 'react';
import { useModelStore } from '../stores/modelStore';
import { Sidebar } from './Sidebar';

interface ModelInfoProps {
  onChatOpen: (modelId?: string) => void;
}

export function ModelInfo({ onChatOpen }: ModelInfoProps) {
  const { selectedModel, selectModel } = useModelStore();
  const [showExtendedInfo, setShowExtendedInfo] = useState(false);

  if (!selectedModel) return null;

  const versions = selectedModel.versions || [
    { id: '1', name: 'unsloth/DeepSeek-V3.1-Terminus-GGUF', size: '3.9 mi', updated: '7 days ago' },
    { id: '2', name: 'unsloth/DeepSeek-V3.1-Terminus-GGUF', size: '3.9 mi', updated: '7 days ago' },
    { id: '3', name: 'unsloth/DeepSeek-V3.1-Terminus-GGUF', size: '3.9 mi', updated: '7 days ago' },
  ];

  // Моковые данные для таблицы
  const modelFiles = [
    {
      name: 'DeepSeek-V3.1-Terminus-IQ4_NL-00001-of-00008.gguf',
      fineTune: 'Присутствует только если есть разные варианты файтюнинга',
      quantum: 'IQ4_NL',
      context: '128',
      count: '379Gb',
      architecture: 'Столбец архитектуры присутствует только если у разных файлов разные архитектуры',
      partCount: '7',
      ggufVersion: '1'
    }
  ];

  return (
    <div className="fixed inset-0 z-50 bg-[#0f1419] flex">
      <Sidebar onChatOpen={onChatOpen} />
      
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto">
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

          <div className="p-6 max-w-5xl mx-auto">
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

            <div className="border-b border-gray-700 mb-6 flex items-center justify-between">
              <div className="flex gap-6 text-sm">
                <button className="pb-3 border-b-2 border-white text-white">Model card</button>
                <button className="pb-3 text-gray-400 hover:text-white transition">Files and versions</button>
                <button className="pb-3 text-gray-400 hover:text-white transition">Community</button>
              </div>
              
              {/* Toggle Extended Information */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">extended information</span>
                <button
                  onClick={() => setShowExtendedInfo(!showExtendedInfo)}
                  className={`relative w-11 h-6 rounded-full transition-colors ${
                    showExtendedInfo ? 'bg-blue-600' : 'bg-gray-700'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                      showExtendedInfo ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>
            </div>

            {/* Extended Information Table */}
            {showExtendedInfo && (
              <div className="mb-6 overflow-x-auto">
                <table className="w-full border border-gray-700 rounded-lg overflow-hidden">
                  <thead className="bg-[#1a1f2e]">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 border-b border-gray-700">Name</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 border-b border-gray-700">Fine-tune</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 border-b border-gray-700">Quantum</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 border-b border-gray-700">Context</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 border-b border-gray-700">Count</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 border-b border-gray-700">Architecture</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 border-b border-gray-700">Part_count</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 border-b border-gray-700">GGUF version</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-300 border-b border-gray-700">Download</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modelFiles.map((file, index) => (
                      <tr key={index} className="border-b border-gray-800 hover:bg-[#1a1f2e] transition">
                        <td className="px-4 py-3 text-sm text-gray-300">{file.name}</td>
                        <td className="px-4 py-3 text-xs text-gray-400">{file.fineTune}</td>
                        <td className="px-4 py-3 text-sm text-gray-300">{file.quantum}</td>
                        <td className="px-4 py-3 text-sm text-gray-300">{file.context}</td>
                        <td className="px-4 py-3 text-sm text-gray-300">{file.count}</td>
                        <td className="px-4 py-3 text-xs text-gray-400">{file.architecture}</td>
                        <td className="px-4 py-3 text-sm text-gray-300 text-center">{file.partCount}</td>
                        <td className="px-4 py-3 text-sm text-gray-300 text-center">{file.ggufVersion}</td>
                        <td className="px-4 py-3">
                          <button className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition">
                            Download
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="prose prose-invert max-w-none">
              <h2 className="text-xl font-semibold text-white mb-4">text-generation</h2>
              
              <p className="text-gray-300 mb-4 leading-relaxed">
                Whisper is a state-of-the-art model for automatic speech recognition (ASR) and speech translation, 
                proposed in the paper Robust Speech Recognition via Large-Scale Weak Supervision by Alec Radford et al. 
                from OpenAI. Trained on &gt;5M hours of labeled data, Whisper demonstrates a strong ability to generalise 
                to many datasets and domains in a zero-shot setting.
              </p>

              <p className="text-gray-300 mb-4 leading-relaxed">
                Whisper large-v3 has the same architecture as the previous large and large-v2 models, except for the 
                following minor differences:
              </p>

              <ol className="list-decimal list-inside text-gray-300 mb-4 space-y-2">
                <li className="leading-relaxed">The spectrogram input uses 128 Mel frequency bins instead of 80</li>
                <li className="leading-relaxed">A new language token for Cantonese</li>
              </ol>

              <p className="text-gray-300 leading-relaxed">
                The Whisper large-v3 model was trained on 1 million hours of weakly labeled audio and 4 million hours 
                of pseudo-labeled audio collected using Whisper large-v2. The model was trained for 2.0 epochs over 
                this mixture dataset.
              </p>
            </div>
          </div>
        </div>

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
