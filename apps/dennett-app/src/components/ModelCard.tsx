import { Model } from '../types';
import { useModelStore } from '../stores/modelStore';

interface ModelCardProps {
  model: Model;
  onChatOpen: (modelId: string) => void;
}

export function ModelCard({ model, onChatOpen }: ModelCardProps) {
  const { selectedModel, selectModel } = useModelStore();
  const isSelected = selectedModel?.id === model.id;

  console.log('ModelCard рендер, model:', model.name, 'onChatOpen:', typeof onChatOpen);

  return (
    <div 
      className={`p-4 bg-[#1a1f2e] rounded-lg hover:bg-[#222838] transition-all border ${
        isSelected ? 'border-blue-500 ring-1 ring-blue-500' : 'border-gray-800'
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <h3 
          className="text-base font-semibold text-white leading-tight flex-1 mr-2 cursor-pointer"
          onClick={() => selectModel(model)}
        >
          {model.name}
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              console.log('🔥 КНОПКА CHAT НАЖАТА! modelId:', model.id);
              onChatOpen(model.id);
            }}
            className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded transition-colors relative z-10"
            title="Chat"
          >
            <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
              <path d="M2.678 11.894a1 1 0 0 1 .287.801 10.97 10.97 0 0 1-.398 2c1.395-.323 2.247-.697 2.634-.893a1 1 0 0 1 .71-.074A8.06 8.06 0 0 0 8 14c3.996 0 7-2.807 7-6 0-3.192-3.004-6-7-6S1 4.808 1 8c0 1.468.617 2.83 1.678 3.894zm-.493 3.905a21.682 21.682 0 0 1-.713.129c-.2.032-.352-.176-.273-.362a9.68 9.68 0 0 0 .244-.637l.003-.01c.248-.72.45-1.548.524-2.319C.743 11.37 0 9.76 0 8c0-3.866 3.582-7 8-7s8 3.134 8 7-3.582 7-8 7a9.06 9.06 0 0 1-2.347-.306c-.52.263-1.639.742-3.468 1.105z"/>
            </svg>
          </button>
          <span className="text-xs text-gray-500 whitespace-nowrap">
            {model.updated}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-3">
        <span className="px-2 py-1 bg-[#0f1419] text-blue-400 text-xs rounded border border-gray-700">
          {model.type}
        </span>
        <span className="px-2 py-1 bg-[#0f1419] text-gray-400 text-xs rounded border border-gray-700">
          {model.description}
        </span>
      </div>

      <div className="flex items-center justify-between pt-3 border-t border-gray-800">
        <span className="text-xs text-gray-500">Unknown</span>
        <span className="text-xs text-gray-400">{model.downloads}</span>
      </div>
    </div>
  );
}
