import { Model } from '../types';
import { useModelStore } from '../stores/modelStore';

interface ModelCardProps {
  model: Model;
}

export function ModelCard({ model }: ModelCardProps) {
  const { selectedModel, selectModel } = useModelStore();
  const isSelected = selectedModel?.id === model.id;

  return (
    <div 
      className={`p-4 bg-[#1a1f2e] rounded-lg cursor-pointer hover:bg-[#222838] transition-all border ${
        isSelected ? 'border-blue-500 ring-1 ring-blue-500' : 'border-gray-800'
      }`}
      onClick={() => selectModel(model)}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-base font-semibold text-white leading-tight flex-1 mr-2">
          {model.name}
        </h3>
        <span className="text-xs text-gray-500 whitespace-nowrap">
          {model.updated}
        </span>
      </div>

      {/* Tags */}
      <div className="flex flex-wrap gap-2 mb-3">
        <span className="px-2 py-1 bg-[#0f1419] text-blue-400 text-xs rounded border border-gray-700">
          {model.type}
        </span>
        <span className="px-2 py-1 bg-[#0f1419] text-gray-400 text-xs rounded border border-gray-700">
          {model.description}
        </span>
      </div>

      {/* Stats */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-800">
        <span className="text-xs text-gray-500">Unknown</span>
        <span className="text-xs text-gray-400">{model.downloads}</span>
      </div>
    </div>
  );
}



