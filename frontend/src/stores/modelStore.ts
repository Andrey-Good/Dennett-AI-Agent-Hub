import { create } from 'zustand';
import { Model, FilterState } from '../types';
import { api, HFModel } from '../api/client';

interface ModelStore {
  models: Model[];
  localModels: Model[];
  selectedModel: Model | null;
  filters: FilterState;
  isLoading: boolean;
  error: string | null;
  
  searchModels: (query: string) => Promise<void>;
  fetchLocalModels: () => Promise<void>;
  selectModel: (model: Model | null) => void;
  updateFilters: (filters: Partial<FilterState>) => void;
  getFilteredModels: () => Model[];
}

function transformModel(hfModel: HFModel): Model {
  return {
    id: hfModel.repo_id,
    name: hfModel.model_name,
    description: hfModel.task || 'No description',
    type: hfModel.tags[0] || 'text-generation',
    size: 'Unknown',
    weight: 0,
    updated: new Date(hfModel.last_modified).toLocaleDateString(),
    downloads: `${(hfModel.downloads / 1000000).toFixed(1)}M`,
  };
}

export const useModelStore = create<ModelStore>((set, get) => ({
  models: [],
  localModels: [],
  selectedModel: null,
  isLoading: false,
  error: null,
  filters: {
    searchQuery: '',
    selectedTasks: [],
    weightRange: [0.1, 1000],
    sortBy: 'popular',
  },

  searchModels: async (query: string) => {
    set({ isLoading: true, error: null });
    try {
      // Если query пустой - ищем популярные модели (по умолчанию API вернёт топ)
      const searchQuery = query.trim() || '';
      const results = await api.hub.search(searchQuery, 20);
      const models = results.map(transformModel);
      set({ models, isLoading: false });
      console.log(`Loaded ${models.length} models for query: "${searchQuery}"`);
    } catch (error) {
      console.error('Error searching models:', error);
      set({ 
        error: error instanceof Error ? error.message : 'Failed to search models',
        isLoading: false,
        models: [] // Очистить модели при ошибке
      });
    }
  },

  fetchLocalModels: async () => {
    try {
      const results = await api.local.list();
      set({ localModels: results });
    } catch (error) {
      console.error('Error fetching local models:', error);
    }
  },

  selectModel: (model: Model | null) => {
    set({ selectedModel: model });
  },

  updateFilters: (newFilters: Partial<FilterState>) => {
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
    }));
  },

  getFilteredModels: () => {
    const { models } = get();
    return models;
  },
}));
