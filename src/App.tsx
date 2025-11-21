import { useState, useEffect } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ToastProvider } from './components/ToastProvider';
import { LoginScreen } from './components/LoginScreen';
import { Sidebar } from './components/Sidebar';
import { MonitorPanel } from './components/MonitorPanel';
import { ConfigGatesPanel } from './components/ConfigGatesPanel';
import { ConfigModelPanel } from './components/ConfigModelPanel';

export type Page = 'monitor' | 'config-gates' | 'config-model';

interface User {
  name: string;
  email: string;
  avatar?: string;
  isDemo: boolean;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [currentPage, setCurrentPage] = useState<Page>('monitor');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Verifica se há sessão salva
  useEffect(() => {
    const savedUser = localStorage.getItem('ecovision_user');
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (error) {
        localStorage.removeItem('ecovision_user');
      }
    }
  }, []);

  const handleLogin = (userData: User) => {
    setUser(userData);
    localStorage.setItem('ecovision_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('ecovision_user');
    setCurrentPage('monitor');
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'monitor':
        return <MonitorPanel />;
      case 'config-gates':
        return <ConfigGatesPanel />;
      case 'config-model':
        return <ConfigModelPanel />;
      default:
        return <MonitorPanel />;
    }
  };

  const handlePageChange = (page: Page) => {
    setCurrentPage(page);
    setSidebarOpen(false); // Fecha sidebar no mobile ao trocar de página
  };

  // Mostra tela de login se não estiver autenticado
  if (!user) {
    return (
      <ErrorBoundary>
        <ToastProvider />
        <LoginScreen onLogin={handleLogin} />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <ToastProvider />
      <div className="flex h-screen bg-neutral-950 overflow-hidden">
        <Sidebar 
          currentPage={currentPage} 
          onPageChange={handlePageChange}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
          user={user}
          onLogout={handleLogout}
        />
        <main className="flex-1 overflow-auto">
          {renderPage()}
        </main>
      </div>
    </ErrorBoundary>
  );
}