import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { 
  Monitor, 
  Lock, 
  Settings, 
  BarChart3, 
  User,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Leaf,
  Menu,
  X
} from "lucide-react";
import { cn } from "./ui/utils";

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  userEmail?: string;
  onLogout?: () => void;
}

export function Sidebar({ activeTab, onTabChange, userEmail, onLogout }: SidebarProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detecta se é mobile
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) {
        setIsExpanded(true); // No mobile, sempre expandido quando aberto
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const menuItems = [
    { id: "monitor", label: "Monitor", icon: Monitor },
    { id: "cancelas", label: "Cancelas", icon: Lock },
    { id: "modelo", label: "Modelo", icon: Settings },
    { id: "dashboard", label: "Dashboard", icon: BarChart3 },
    { id: "perfil", label: "Perfil", icon: User },
  ];

  const handleLogout = () => {
    if (onLogout) {
      onLogout();
    }
  };

  const handleTabChange = (tab: string) => {
    onTabChange(tab);
    if (isMobile) {
      setIsMobileOpen(false);
    }
  };

  const toggleSidebar = () => {
    if (isMobile) {
      setIsMobileOpen(!isMobileOpen);
    } else {
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <>
      {/* Mobile Menu Button */}
      {isMobile && (
        <Button
          onClick={toggleSidebar}
          className="fixed top-4 left-4 z-50 bg-recycling-primary hover:bg-recycling-primary-dark text-white md:hidden"
          size="icon"
        >
          {isMobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </Button>
      )}

      {/* Overlay para mobile */}
      {isMobile && isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 backdrop-blur-sm transition-opacity"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Overlay para desktop quando sidebar expandida */}
      {!isMobile && isExpanded && (
        <div
          className="fixed inset-0 bg-black/20 z-20 backdrop-blur-[2px] transition-opacity pointer-events-none"
        />
      )}

      {/* Sidebar */}
      <div
        className={cn(
          "h-screen bg-gradient-to-b from-recycling-primary-dark to-recycling-primary flex flex-col transition-all duration-300",
          "shadow-2xl",
          // Desktop
          !isMobile && "fixed left-0 top-0 z-30",
          !isMobile && (isExpanded ? "w-64" : "w-20"),
          // Mobile
          isMobile && "fixed left-0 top-0 z-40 w-64",
          isMobile && (isMobileOpen ? "translate-x-0" : "-translate-x-full")
        )}
    >
      {/* Header */}
      <div className="p-6 border-b border-white/20 cursor-pointer hover:bg-white/5 transition-colors" onClick={() => handleTabChange("monitor")}>
        <div className="flex items-center justify-between">
          {(isExpanded || isMobile) ? (
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center flex-shrink-0">
                <Leaf className="w-6 h-6 text-recycling-primary" />
              </div>
              <div>
                <h1 className="text-white font-bold">EcoVision</h1>
                <p className="text-white/70 text-xs">Sistema de Reciclagem</p>
              </div>
            </div>
          ) : (
            <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center mx-auto">
              <Leaf className="w-6 h-6 text-recycling-primary" />
            </div>
          )}
        </div>
      </div>

      {/* Menu Items */}
      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          
          return (
            <Button
              key={item.id}
              onClick={() => handleTabChange(item.id)}
              variant="ghost"
              className={cn(
                "w-full justify-start gap-3 text-white hover:bg-white/10 transition-colors",
                isActive && "bg-white/20 hover:bg-white/20",
                !isExpanded && !isMobile && "justify-center px-2"
              )}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {(isExpanded || isMobile) && <span>{item.label}</span>}
            </Button>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/20 space-y-2 flex-shrink-0">
        {/* User Info */}
        {(isExpanded || isMobile) && userEmail && (
          <div className="px-3 py-2 bg-white/10 rounded-lg mb-2">
            <p className="text-white/90 text-xs truncate">{userEmail}</p>
          </div>
        )}

        {/* Logout Button */}
        <Button
          onClick={handleLogout}
          variant="ghost"
          className={cn(
            "w-full gap-3 text-white hover:bg-white/10",
            (isExpanded || isMobile) ? "justify-start" : "justify-center px-2"
          )}
        >
          <LogOut className="w-5 h-5 flex-shrink-0" />
          {(isExpanded || isMobile) && <span>Sair</span>}
        </Button>

        {/* Toggle Button - apenas desktop */}
        {!isMobile && (
          <Button
            onClick={toggleSidebar}
            variant="ghost"
            className="w-full justify-center text-white hover:bg-white/10"
          >
            {isExpanded ? (
              <ChevronLeft className="w-5 h-5" />
            ) : (
              <ChevronRight className="w-5 h-5" />
            )}
          </Button>
        )}
      </div>
    </div>
    </>
  );
}
