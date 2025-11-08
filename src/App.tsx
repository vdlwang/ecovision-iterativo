import { useState, useEffect } from "react";
import { Login } from "./components/Login";
import { Sidebar } from "./components/Sidebar";
import { MonitorPanel } from "./components/MonitorPanel";
import { GateConfiguration } from "./components/GateConfiguration";
import { AccuracyControl } from "./components/AccuracyControl";
import { StatisticsPanel } from "./components/StatisticsPanel";
import { UserProfile } from "./components/UserProfile";
import { Toaster } from "./components/ui/sonner";
import { getSupabaseClient } from "./utils/supabase/client";
import { projectId, publicAnonKey } from "./utils/supabase/info";

const supabase = getSupabaseClient();

export default function App() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [activeTab, setActiveTab] = useState("monitor");
  const [isSystemRunning, setIsSystemRunning] = useState(false);
  const [minAccuracy, setMinAccuracy] = useState(85);
  const [modelVersion, setModelVersion] = useState("YOLOv8n");
  const [gateConfigs, setGateConfigs] = useState<{
    [key: number]: string;
  }>({
    1: "papel",
    2: "plastico",
    3: "metal",
  });

  // Verifica se o usuário está autenticado
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleDemoMode = () => {
    setIsDemoMode(true);
    setUser({ email: "demo@ecovision.com", id: "demo-user" });
    setLoading(false);
  };

  const handleToggleSystem = async () => {
    const newState = !isSystemRunning;
    setIsSystemRunning(newState);
    
    try {
      const endpoint = newState ? 'esteira/ligar' : 'esteira/desligar';
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-ea835390/${endpoint}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${publicAnonKey}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      if (!response.ok) {
        console.error('Erro ao controlar esteira');
      }
      
      // Ativa/desativa o modelo IA
      const modelEndpoint = newState ? 'modelo/ativar' : 'modelo/desativar';
      await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-ea835390/${modelEndpoint}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${publicAnonKey}`,
            'Content-Type': 'application/json'
          }
        }
      );
    } catch (error) {
      console.error('Erro ao comunicar com backend:', error);
    }
  };

  const handleAccuracyChange = async (newAccuracy: number) => {
    setMinAccuracy(newAccuracy);
    
    try {
      // Atualiza no backend
      await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-ea835390/config`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${publicAnonKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            gateConfigs,
            minAccuracy: newAccuracy,
            modelVersion
          })
        }
      );
      
      // Calibra o modelo
      await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-ea835390/modelo/calibrar`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${publicAnonKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ limite: newAccuracy })
        }
      );
    } catch (error) {
      console.error('Erro ao atualizar confiança:', error);
    }
  };

  const handleModelVersionChange = async (newVersion: string) => {
    setModelVersion(newVersion);
    
    try {
      await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-ea835390/config`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${publicAnonKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            gateConfigs,
            minAccuracy,
            modelVersion: newVersion
          })
        }
      );
    } catch (error) {
      console.error('Erro ao atualizar modelo:', error);
    }
  };

  const handleGateConfigChange = async (newConfigs: {
    [key: number]: string;
  }) => {
    setGateConfigs(newConfigs);
    
    try {
      await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-ea835390/config`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${publicAnonKey}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            gateConfigs: newConfigs,
            minAccuracy,
            modelVersion
          })
        }
      );
    } catch (error) {
      console.error('Erro ao atualizar cancelas:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-recycling-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-recycling-primary-darker">Carregando EcoVision...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Login onDemoMode={handleDemoMode} />;
  }

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        userEmail={user.email}
        onLogout={() => {
          if (isDemoMode) {
            setUser(null);
            setIsDemoMode(false);
          } else {
            supabase.auth.signOut().then(() => {
              setUser(null);
            });
          }
        }}
      />

      {/* Main Content */}
      <div className="flex-1 overflow-auto w-full md:ml-20 lg:ml-20">
        <div className="container mx-auto p-4 md:p-6 space-y-4 md:space-y-6 max-w-7xl">
          {/* Header */}
          <div className="space-y-2 pt-16 md:pt-0">
            <h1 className="text-recycling-primary-darker text-xl md:text-2xl lg:text-3xl">
              {activeTab === "monitor" && "Monitor do Sistema"}
              {activeTab === "cancelas" && "Configuração de Cancelas"}
              {activeTab === "modelo" && "Especificações de Modelo"}
              {activeTab === "dashboard" && "Dashboard de Estatísticas"}
              {activeTab === "perfil" && "Perfil do Usuário"}
            </h1>
            <p className="text-muted-foreground text-sm">
              {activeTab === "monitor" && "Monitoramento em tempo real da esteira de reciclagem com câmera"}
              {activeTab === "cancelas" && "Configure quais materiais cada cancela irá separar"}
              {activeTab === "modelo" && "Ajuste o modelo de IA e a confiança mínima"}
              {activeTab === "dashboard" && "Visualize estatísticas e performance do sistema"}
              {activeTab === "perfil" && "Gerencie suas informações e visualize seu histórico"}
            </p>
          </div>

          {/* Content */}
          <div>
            {activeTab === "monitor" && (
              <MonitorPanel
                gateConfigs={gateConfigs}
                minAccuracy={minAccuracy}
                isRunning={isSystemRunning}
                onToggleSystem={handleToggleSystem}
                modelVersion={modelVersion}
                userId={user.id}
              />
            )}

            {activeTab === "cancelas" && (
              <GateConfiguration
                gateConfigs={gateConfigs}
                onConfigChange={handleGateConfigChange}
                isSystemRunning={isSystemRunning}
              />
            )}

            {activeTab === "modelo" && (
              <AccuracyControl
                minAccuracy={minAccuracy}
                onAccuracyChange={handleAccuracyChange}
                isSystemRunning={isSystemRunning}
                modelVersion={modelVersion}
                onModelVersionChange={handleModelVersionChange}
              />
            )}

            {activeTab === "dashboard" && (
              <StatisticsPanel
                isSystemRunning={isSystemRunning}
                gateConfigs={gateConfigs}
                userId={user.id}
              />
            )}

            {activeTab === "perfil" && (
              <UserProfile user={user} />
            )}
          </div>
        </div>
      </div>

      {/* Toast notifications */}
      <Toaster />
    </div>
  );
}
