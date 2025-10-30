import { ModelGrid } from './components/ModelGrid';
import { Sidebar } from './components/Sidebar';
import './App.css';

function App() {
  return (
    <div className="flex h-screen bg-[#0f1419]">
      <Sidebar />
      <div className="flex-1">
        <ModelGrid />
      </div>
    </div>
  );
}

export default App;
