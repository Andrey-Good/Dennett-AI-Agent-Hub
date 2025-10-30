const API_BASE = 'http://localhost:5208';

async function fetchAPI(url: string, options: RequestInit = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    
    return response.json();
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
}

export interface HFModel {
  repo_id: string;
  model_name: string;
  author: string;
  task: string;
  license: string | null;
  downloads: number;
  likes: number;
  last_modified: string;
  tags: string[];
  private: boolean;
}

export const api = {
  hub: {
    search: async (query: string = 'llama', limit: number = 20): Promise<HFModel[]> => {
      try {
        const data = await fetchAPI(`${API_BASE}/hub/search?query=${encodeURIComponent(query)}&limit=${limit}`);
        return data;
      } catch (error) {
        console.error('Search error:', error);
        return [];
      }
    },

    getDetails: async (author: string, modelName: string) => {
      return fetchAPI(`${API_BASE}/hub/model/${author}/${modelName}`);
    },
  },

  local: {
    list: async () => {
      try {
        return await fetchAPI(`${API_BASE}/local/models`);
      } catch (error) {
        console.error('Local models error:', error);
        return [];
      }
    },
  },
};
