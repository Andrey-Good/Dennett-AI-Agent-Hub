export interface Model {
  id: string;
  name: string;
  description: string;
  type: string;
  size: string;
  weight: number;
  updated: string;
  downloads: string;
  versions?: ModelVersion[];
}

export interface ModelVersion {
  id: string;
  name: string;
  size: string;
  updated: string;
}

export interface FilterState {
  searchQuery: string;
  selectedTasks: string[];
  weightRange: [number, number];
  sortBy: 'popular' | 'recent' | 'downloads';
}
