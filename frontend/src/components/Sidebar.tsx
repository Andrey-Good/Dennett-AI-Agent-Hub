// src/components/Sidebar.tsx
import React from 'react';
import { useModelStore } from '../stores/modelStore';

export function Sidebar() {
  const { filters, updateFilters } = useModelStore();
  const [activeTab, setActiveTab] = React.useState('main');

  const tasks = [
    { id: 'text-generation', label: 'Text Generation' },
    { id: 'text-to-text', label: 'Text-to-text' },
    { id: 'any-to-any', label: 'Any-to-any' },
    { id: 'image-to-text', label: 'Image-to-text' },
    { id: '3d-to-text', label: '3D-to-Text' },
    { id: 'image-text-to-text', label: 'Image-text-to-text' },
    { id: 'translation', label: 'Translation' },
    { id: 'text-to-video', label: 'Text-to-Video' }
  ];

  return (
    <div className="w-[350px] bg-[#0d1117] flex h-screen border-r border-gray-800">
      {/* Icon Bar - Always visible on left */}
      <div className="w-16 flex flex-col items-center py-4 gap-4 border-r border-gray-800">
        <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors" title="Microphone">
          <svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
            <path d="M3.5 6.5A.5.5 0 0 1 4 7v1a4 4 0 0 0 8 0V7a.5.5 0 0 1 1 0v1a5 5 0 0 1-4.5 4.975V15h3a.5.5 0 0 1 0 1h-7a.5.5 0 0 1 0-1h3v-2.025A5 5 0 0 1 3 8V7a.5.5 0 0 1 .5-.5z"/>
            <path d="M10 8a2 2 0 1 1-4 0V3a2 2 0 1 1 4 0v5z"/>
          </svg>
        </button>
        <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors" title="Search">
          <svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
            <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
          </svg>
        </button>
        <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors" title="Chat">
          <svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
            <path d="M2.678 11.894a1 1 0 0 1 .287.801 10.97 10.97 0 0 1-.398 2c1.395-.323 2.247-.697 2.634-.893a1 1 0 0 1 .71-.074A8.06 8.06 0 0 0 8 14c3.996 0 7-2.807 7-6 0-3.192-3.004-6-7-6S1 4.808 1 8c0 1.468.617 2.83 1.678 3.894zm-.493 3.905a21.682 21.682 0 0 1-.713.129c-.2.032-.352-.176-.273-.362a9.68 9.68 0 0 0 .244-.637l.003-.01c.248-.72.45-1.548.524-2.319C.743 11.37 0 9.76 0 8c0-3.866 3.582-7 8-7s8 3.134 8 7-3.582 7-8 7a9.06 9.06 0 0 1-2.347-.306c-.52.263-1.639.742-3.468 1.105z"/>
          </svg>
        </button>
        <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors" title="Link">
          <svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
            <path d="M4.715 6.542 3.343 7.914a3 3 0 1 0 4.243 4.243l1.828-1.829A3 3 0 0 0 8.586 5.5L8 6.086a1.002 1.002 0 0 0-.154.199 2 2 0 0 1 .861 3.337L6.88 11.45a2 2 0 1 1-2.83-2.83l.793-.792a4.018 4.018 0 0 1-.128-1.287z"/>
            <path d="M6.586 4.672A3 3 0 0 0 7.414 9.5l.775-.776a2 2 0 0 1-.896-3.346L9.12 3.55a2 2 0 1 1 2.83 2.83l-.793.792c.112.42.155.855.128 1.287l1.372-1.372a3 3 0 1 0-4.243-4.243L6.586 4.672z"/>
          </svg>
        </button>
        <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors" title="Settings">
          <svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
            <path d="M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492zM5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0z"/>
            <path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52l-.094-.319z"/>
          </svg>
        </button>
        <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors" title="Controls">
          <svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
            <path fillRule="evenodd" d="M11.5 2a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM9.05 3a2.5 2.5 0 0 1 4.9 0H16v1h-2.05a2.5 2.5 0 0 1-4.9 0H0V3h9.05zM4.5 7a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM2.05 8a2.5 2.5 0 0 1 4.9 0H16v1H6.95a2.5 2.5 0 0 1-4.9 0H0V8h2.05zm9.45 4a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm-2.45 1a2.5 2.5 0 0 1 4.9 0H16v1h-2.05a2.5 2.5 0 0 1-4.9 0H0v-1h9.05z"/>
          </svg>
        </button>
        <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded transition-colors" title="Globe">
          <svg width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
            <path d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8zm7.5-6.923c-.67.204-1.335.82-1.887 1.855A7.97 7.97 0 0 0 5.145 4H7.5V1.077zM4.09 4a9.267 9.267 0 0 1 .64-1.539 6.7 6.7 0 0 1 .597-.933A7.025 7.025 0 0 0 2.255 4H4.09zm-.582 3.5c.03-.877.138-1.718.312-2.5H1.674a6.958 6.958 0 0 0-.656 2.5h2.49zM4.847 5a12.5 12.5 0 0 0-.338 2.5H7.5V5H4.847zM8.5 5v2.5h2.99a12.495 12.495 0 0 0-.337-2.5H8.5zM4.51 8.5a12.5 12.5 0 0 0 .337 2.5H7.5V8.5H4.51zm3.99 0V11h2.653c.187-.765.306-1.608.338-2.5H8.5zM5.145 12c.138.386.295.744.468 1.068.552 1.035 1.218 1.65 1.887 1.855V12H5.145zm.182 2.472a6.696 6.696 0 0 1-.597-.933A9.268 9.268 0 0 1 4.09 12H2.255a7.024 7.024 0 0 0 3.072 2.472zM3.82 11a13.652 13.652 0 0 1-.312-2.5h-2.49c.062.89.291 1.733.656 2.5H3.82zm6.853 3.472A7.024 7.024 0 0 0 13.745 12H11.91a9.27 9.27 0 0 1-.64 1.539 6.688 6.688 0 0 1-.597.933zM8.5 12v2.923c.67-.204 1.335-.82 1.887-1.855.173-.324.33-.682.468-1.068H8.5zm3.68-1h2.146c.365-.767.594-1.61.656-2.5h-2.49a13.65 13.65 0 0 1-.312 2.5zm2.802-3.5a6.959 6.959 0 0 0-.656-2.5H12.18c.174.782.282 1.623.312 2.5h2.49zM11.27 2.461c.247.464.462.98.64 1.539h1.835a7.024 7.024 0 0 0-3.072-2.472c.218.284.418.598.597.933zM10.855 4a7.966 7.966 0 0 0-.468-1.068C9.835 1.897 9.17 1.282 8.5 1.077V4h2.355z"/>
          </svg>
        </button>
      </div>

      {/* Content Area - Always visible */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* Tabs */}
        <div className="flex gap-2 mb-4">
          {['Main', 'Tasks', 'Languages', 'Licence'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab.toLowerCase())}
              className={`text-xs px-2.5 py-1 rounded transition-colors ${
                activeTab === tab.toLowerCase()
                  ? 'bg-gray-700 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Weight Slider */}
        <div className="mb-4">
          <div className="flex justify-between text-xs mb-1.5 text-gray-400">
            <span>Weight</span>
            <span className="text-gray-500">{filters.weightRange[0].toFixed(1)}B {filters.weightRange[1]}B</span>
          </div>
          <input
            type="range"
            min="0.1"
            max="1000"
            step="0.1"
            value={filters.weightRange[0]}
            onChange={(e) => updateFilters({ weightRange: [parseFloat(e.target.value), 1000] })}
            className="w-full h-1 bg-gray-800 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-[9px] text-gray-600 mt-1">
            <span>0.1</span>
            <span>1</span>
            <span>10</span>
            <span>50</span>
            <span>100</span>
            <span>250</span>
            <span>500</span>
            <span>1000</span>
          </div>
        </div>

        {/* Tasks */}
        <div>
          <h3 className="text-xs font-medium mb-2 text-gray-400">Tasks</h3>
          <div className="space-y-0.5">
            {tasks.map((task) => {
              const isSelected = filters.selectedTasks.includes(task.id);
              return (
                <label key={task.id} className="flex items-center gap-2 px-2 py-1 rounded text-xs cursor-pointer hover:bg-gray-800">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => {
                      const newTasks = isSelected
                        ? filters.selectedTasks.filter(t => t !== task.id)
                        : [...filters.selectedTasks, task.id];
                      updateFilters({ selectedTasks: newTasks });
                    }}
                    className="w-3.5 h-3.5 rounded border-gray-600"
                  />
                  <span className={isSelected ? 'text-gray-200' : 'text-gray-500'}>{task.label}</span>
                </label>
              );
            })}
            <button className="w-full flex items-center gap-2 px-2 py-1 rounded text-xs text-gray-500 hover:bg-gray-800">
              <span className="text-lg">+</span>
              <span>+42</span>
            </button>
          </div>
        </div>

        {/* Bottom Button */}
        <div className="mt-auto pt-4 border-t border-gray-800">
          <button className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs text-gray-400 hover:bg-gray-800">
            <span className="w-3 h-3 rounded-full bg-white"></span>
            <span>Поддержка Dennet</span>
          </button>
        </div>
      </div>
    </div>
  );
}
