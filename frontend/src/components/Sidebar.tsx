import { Camera, Settings, Recycle, Menu, X, Sliders, LogOut, User } from 'lucide-react';
import { Button } from './ui/button';

type Panel = 'monitor' | 'gates' | 'model';

interface SidebarProps {
  currentPanel: Panel;
  onPanelChange: (panel: Panel) => void;
  isOpen: boolean;
  onToggle: () => void;
  onLogout: () => void;
}

export function Sidebar({ currentPanel, onPanelChange, isOpen, onToggle, onLogout }: SidebarProps) {
  const menuItems = [
    { id: 'monitor' as Panel, label: 'Monitor', icon: Camera },
    { id: 'gates' as Panel, label: 'Cancelas de Separação', icon: Settings },
    { id: 'model' as Panel, label: 'Configuração do Modelo', icon: Sliders },
  ];

  return (
    <>
      {/* Botão Menu Hambúrguer - Fixo no canto superior esquerdo em mobile */}
      <button
        onClick={onToggle}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-neutral-900 rounded-lg text-white hover:bg-neutral-800 transition-colors border border-neutral-800"
      >
        {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>

      {/* Overlay para mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:relative
        inset-y-0 left-0
        z-50
        w-64 bg-neutral-900 border-r border-neutral-800 
        flex flex-col
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Header */}
        <div className="p-6 border-b border-neutral-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
              <Recycle className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-white">EcoVision</h1>
              <p className="text-neutral-400 text-xs">Sistema de Reciclagem</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 overflow-y-auto">
          <ul className="space-y-2">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentPanel === item.id;
              
              return (
                <li key={item.id}>
                  <button
                    onClick={() => onPanelChange(item.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-green-600 text-white'
                        : 'text-neutral-400 hover:bg-neutral-800 hover:text-white'
                    }`}
                  >
                    <Icon className="w-5 h-5 flex-shrink-0" />
                    <span className="truncate text-sm">{item.label}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-neutral-800">
          <Button
            onClick={onLogout}
            variant="outline"
            className="w-full bg-neutral-800 border-neutral-700 text-white hover:bg-neutral-700"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sair
          </Button>
        </div>
      </aside>
    </>
  );
}