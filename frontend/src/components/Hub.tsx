import React from 'react';

type AgentStatus = 'active' | 'inactive';
type Activation = 'trigger' | 'time';

type Agent = {
  id: string;
  title: string;
  status: AgentStatus;
  activation: Activation;
  lastRun: string;
};

function StatusPill({ status }: { status: AgentStatus }) {
  const isActive = status === 'active';
  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-block w-2 h-2 rounded-full ${
          isActive ? 'bg-emerald-400' : 'bg-red-500'
        }`}
      />
      <span className={`text-xs ${isActive ? 'text-emerald-300' : 'text-red-300'}`}>
        {isActive ? 'Активен' : 'Не активен'}
      </span>
    </div>
  );
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`w-10 h-6 rounded-full border transition-colors relative ${
        checked ? 'bg-emerald-600/30 border-emerald-500/40' : 'bg-[#0f1419] border-gray-700'
      }`}
      aria-pressed={checked}
      title="UI-переключатель (пока без логики)"
    >
      <span
        className={`absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full transition-all ${
          checked ? 'left-5 bg-emerald-300' : 'left-1 bg-gray-400'
        }`}
      />
    </button>
  );
}

function Chip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-xs border transition-colors whitespace-nowrap ${
        active
          ? 'bg-gray-700 text-white border-gray-600'
          : 'bg-gray-800 text-gray-300 border-gray-700 hover:bg-gray-700/70'
      }`}
    >
      {label}
    </button>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  const [enabled, setEnabled] = React.useState(agent.status === 'active');

  return (
    <div className="p-4 bg-[#1a1f2e] rounded-lg border border-gray-800 hover:bg-[#222838] transition-all">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-white leading-tight truncate">{agent.title}</div>
          <div className="mt-2">
            <StatusPill status={enabled ? 'active' : 'inactive'} />
          </div>
        </div>

        <Toggle checked={enabled} onChange={setEnabled} />
      </div>

      <div className="mt-4 space-y-1.5 text-xs text-gray-400">
        <div className="flex items-center justify-between">
          <span>Активация:</span>
          <span className="text-gray-300">
            {agent.activation === 'trigger' ? 'по тригеру' : 'по времени'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>Последний запуск:</span>
          <span className="text-gray-300">{agent.lastRun}</span>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-end">
        <button
          type="button"
          className="px-3 py-1.5 text-xs rounded-lg bg-gray-700/60 hover:bg-gray-700 text-gray-100 border border-gray-600 transition"
        >
          Запустить
        </button>
      </div>
    </div>
  );
}

export function Hub() {
  const chips = [
    'Архитектор агентов',
    'Создание записей в расписании',
    'Мозговой штурмовик',
    'Репетитор по английскому',
    'Заказ ужина',
    'Анализатор новостей',
    'Быстрая сводка по работе',
    'Подсчет калорий по фото',
    'Распределение обязанностей',
    'Поиск кода по 1 строчке',
    'Расписание тренировок',
  ];

  const [activeChip, setActiveChip] = React.useState(chips[0]);
  const [query, setQuery] = React.useState('');

  const agents: Agent[] = [
    { id: 'a1', title: 'Распределение задач по команде', status: 'active', activation: 'trigger', lastRun: '7 days ago' },
    { id: 'a2', title: 'Распределение задач по команде', status: 'inactive', activation: 'trigger', lastRun: '7 days ago' },
    { id: 'a3', title: 'Распределение задач по команде', status: 'active', activation: 'trigger', lastRun: '7 days ago' },
    { id: 'a4', title: 'Распределение задач по команде', status: 'inactive', activation: 'time', lastRun: '7 days ago' },
    { id: 'a5', title: 'Распределение задач по команде', status: 'inactive', activation: 'trigger', lastRun: '7 days ago' },
    { id: 'a6', title: 'Распределение задач по команде', status: 'active', activation: 'trigger', lastRun: '7 days ago' },
    { id: 'a7', title: 'Распределение задач по команде', status: 'inactive', activation: 'trigger', lastRun: '7 days ago' },
    { id: 'a8', title: 'Распределение задач по команде', status: 'active', activation: 'trigger', lastRun: '7 days ago' },
    { id: 'a9', title: 'Распределение задач по команде', status: 'active', activation: 'time', lastRun: '7 days ago' },
  ];

  const filtered = agents.filter((a) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return a.title.toLowerCase().includes(q);
  });

  return (
    <div className="h-screen flex flex-col bg-[#0f1419]">
      {/* Top chips row */}
      <div className="px-6 pt-5">
        <div className="flex items-center gap-2 flex-wrap">
          {chips.map((c) => (
            <Chip key={c} label={c} active={activeChip === c} onClick={() => setActiveChip(c)} />
          ))}
        </div>
      </div>

      {/* Search */}
      <div className="px-6 pt-4">
        <div className="relative max-w-xl">
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
            placeholder="Search for agents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-[#1a1f2e] text-white pl-10 pr-10 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-blue-500 transition"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Grid */}
      <div className="flex-1 px-6 py-6 overflow-y-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>

        <div className="mt-6 text-xs text-gray-500">
          Выбранная категория: <span className="text-gray-300">{activeChip}</span>
        </div>
      </div>
    </div>
  );
}
