import { useState, useEffect } from 'react';
import { useModelStore } from '../stores/modelStore';

export function Header() {
  const [searchQuery, setSearchQuery] = useState('');
  const { searchModels, models, isLoading } = useModelStore();

  // Debounced search (300ms). We trigger a search when the input is empty
  // (to load popular models) or when it has at least 2 characters.
  useEffect(() => {
    if (searchQuery.length === 0 || searchQuery.length >= 2) {
      const timer = setTimeout(() => {
        searchModels(searchQuery);
      }, 300);

      return () => clearTimeout(timer);
    }
  }, [searchQuery, searchModels]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    searchModels(searchQuery);
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    searchModels('');
  };

  return (
    <header className="bg-[#1a1f2e] border-b border-gray-800 px-6 py-4">
      <div className="flex items-center gap-4">
        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="flex-1 relative max-w-2xl">
          <svg
            className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="text"
            placeholder="Search for models..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="w-full bg-[#0f1419] text-white pl-10 pr-10 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500 transition"
          />

          {/* Loading indicator */}
          {isLoading && (
            <div className="absolute right-10 top-1/2 transform -translate-y-1/2">
              <svg
                className="animate-spin h-5 w-5 text-gray-400"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                ></circle>
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                ></path>
              </svg>
            </div>
          )}

          {/* Clear button */}
          {searchQuery && (
            <button
              type="button"
              onClick={handleClearSearch}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </form>

        {/* Right side (placeholder) */}
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">Models: {models.length}</span>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
            Import model from disk
          </button>
        </div>
      </div>
    </header>
  );
}
