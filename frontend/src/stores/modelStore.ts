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

function parseCompactNumber(value?: string): number {
  if (!value) return 0;
  const v = value.trim().toUpperCase();
  // Common formats: "15.2M", "900K", "1.1B".
  const m = v.match(/^([0-9]+(?:\.[0-9]+)?)\s*([KMB])?$/);
  if (!m) return Number.parseFloat(v) || 0;
  const num = Number.parseFloat(m[1]);
  const unit = m[2];
  if (!unit) return num;
  if (unit === 'K') return num * 1_000;
  if (unit === 'M') return num * 1_000_000;
  if (unit === 'B') return num * 1_000_000_000;
  return num;
}

function transformModel(hfModel: HFModel): Model {
  return {
    id: hfModel.repo_id,
    name: hfModel.model_name,
    description: hfModel.task || 'No description',
    type: hfModel.tags?.[0] || 'text-generation',
    size: 'Unknown',
    weight: 0,
    updated: new Date(hfModel.last_modified).toLocaleDateString(),
    downloads: `${(hfModel.downloads / 1_000_000).toFixed(1)}M`,
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
      // If query is empty, we load popular models (API will return top items).
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
        models: [],
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
    const { models, filters } = get();
    let list = [...models];

    const q = (filters.searchQuery || '').trim().toLowerCase();
    if (q) {
      list = list.filter((m) => {
        const hay = `${m.name} ${m.id} ${m.type} ${m.description}`.toLowerCase();
        return hay.includes(q);
      });
    }

    if (filters.selectedTasks && filters.selectedTasks.length > 0) {
      const tasks = filters.selectedTasks.map((t) => t.toLowerCase());
      list = list.filter((m) => {
        const hay = `${m.type} ${m.description}`.toLowerCase();
        return tasks.some((t) => hay.includes(t));
      });
    }

    // Weight range is currently UI-only: we don't have real weights in HF results.
    // Sorting: "popular" and "downloads" are approximated by downloads count.
    if (filters.sortBy === 'downloads' || filters.sortBy === 'popular') {
      list.sort((a, b) => parseCompactNumber(b.downloads) - parseCompactNumber(a.downloads));
    }

    return list;
  },
}));
