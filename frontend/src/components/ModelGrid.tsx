import { useEffect } from 'react';
import { ModelCard } from './ModelCard';
import { ModelInfo } from './ModelInfo';
import { Header } from './Header';
import { useModelStore } from '../stores/modelStore';

interface ModelGridProps {
  onChatOpen: (modelId: string) => void;
}

export function ModelGrid({ onChatOpen }: ModelGridProps) {
  const { getFilteredModels, searchModels, isLoading } = useModelStore();
  const models = getFilteredModels();

  useEffect(() => {
    searchModels('');
  }, []);

  console.log('ModelGrid получил onChatOpen:', onChatOpen);

  return (
    <div className="h-screen flex flex-col bg-[#0f1419]">
      <Header />
      
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-400 text-lg">Загрузка моделей...</div>
          </div>
        ) : models.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-6">
            {models.map((model) => (
              <ModelCard key={model.id} model={model} onChatOpen={onChatOpen} />
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-gray-400">Модели не найдены</div>
          </div>
        )}
      </div>
      
      <ModelInfo onChatOpen={onChatOpen} />

    </div>
  );
}
