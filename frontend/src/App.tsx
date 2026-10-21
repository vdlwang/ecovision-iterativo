import { useState, useEffect } from 'react';
import { toast } from 'sonner@2.0.3';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ToastProvider } from './components/ToastProvider';
import { LoginScreen } from './components/LoginScreen';
import { Sidebar } from './components/Sidebar';
import { MonitorPanel } from './components/MonitorPanel';
import { ConfigGatesPanel } from './components/ConfigGatesPanel';
import { ConfigModelPanel } from './components/ConfigModelPanel';
import { useStableWebSocket } from './hooks/useStableWebSocket';

type Panel = 'monitor' | 'gates' | 'model';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentPanel, setCurrentPanel] = useState<Panel>('monitor');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { connected } = useStableWebSocket('ws://localhost:8765');

  // Painéis de configuração só com o backend conectado: se ele cair, volta para o Monitor
  useEffect(() => {
    if (!connected && currentPanel !== 'monitor') {
      setCurrentPanel('monitor');
      toast.error('Backend desconectado: configurações indisponíveis.');
    }
  }, [connected, currentPanel]);

  // Verificar se há sessão salva
  useEffect(() => {
    const savedAuth = localStorage.getItem('ecovision_authenticated');
    if (savedAuth === 'true') {
      setIsAuthenticated(true);
    }
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
    localStorage.setItem('ecovision_authenticated', 'true');
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    localStorage.removeItem('ecovision_authenticated');
    setCurrentPanel('monitor');
  };

  if (!isAuthenticated) {
    return (
      <ErrorBoundary>
        <LoginScreen onLogin={handleLogin} />
        <ToastProvider />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <div className="flex h-screen bg-neutral-950 overflow-hidden">
        <Sidebar
          currentPanel={currentPanel}
          onPanelChange={setCurrentPanel}
          backendConnected={connected}
          onLogout={handleLogout}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
        />
        
        <main className="flex-1 overflow-auto">
          {currentPanel === 'monitor' && <MonitorPanel />}
          {currentPanel === 'gates' && <ConfigGatesPanel />}
          {currentPanel === 'model' && <ConfigModelPanel />}
        </main>
      </div>
      <ToastProvider />
    </ErrorBoundary>
  );
}
