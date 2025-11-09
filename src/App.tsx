/**
 * 🌿 EcoVision - Sistema Inteligente de Reciclagem com IA
 * 
 * SISTEMA TOTALMENTE FUNCIONAL:
 * ✅ Captura webcam em tempo real via getUserMedia API
 * ✅ Solicitação automática de permissão de câmera pós-login
 * ✅ Inferência YOLO (YOLOv8n/s/m) com modelos Ultralytics
 * ✅ Bounding boxes desenhadas em tempo real na tela
 * ✅ Detecção de 4 materiais: papel, metal, plástico, vidro
 * ✅ Controle de 3 cancelas baseado nas detecções
 * ✅ Dashboard com estatísticas e histórico
 * 
 * COMO EXECUTAR:
 * 1. pip install -r requirements.txt
 * 2. ./run_dev.sh (Linux/Mac) ou run_dev.bat (Windows)
 * 3. http://localhost:5000
 * 4. Faça login → Permita câmera → Clique "Iniciar Sistema" no feed
 * 
 * IMPORTANTE:
 * - ✅ Funciona 100% em localhost (HTTP)
 * - ✅ Funciona 100% em produção (HTTPS)
 * - ⚠️ Playground Figma tem limitações (CORS/Câmera)
 * 
 * Documentação: README.md | COMO_EXECUTAR.md | INSTALACAO.md
 */

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
import { TestTube } from "lucide-react";

const supabase = getSupabaseClient();

export default function App() {
  const [user, setUser] = useState<any>(null);
  const [userToken, setUserToken] = useState<string | null>(null);
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
      setUserToken(session?.access_token ?? null);
      setLoading(false);
      
      if (session?.access_token) {
        console.log('[AUTH] Sessão OAuth obtida com sucesso. Token disponível.');
      } else {
        console.log('[AUTH] Nenhuma sessão OAuth. Use o Modo Demo ou configure Google OAuth.');
      }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      console.log(`[AUTH] Estado de autenticação mudou: ${event}`);
      setUser(session?.user ?? null);
      setUserToken(session?.access_token ?? null);
      
      if (event === 'SIGNED_OUT') {
        console.log('[AUTH] Usuário desconectado');
      } else if (event === 'SIGNED_IN') {
        console.log('[AUTH] Usuário conectado com sucesso');
      } else if (event === 'TOKEN_REFRESHED') {
        console.log('[AUTH] Token renovado automaticamente');
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleDemoMode = () => {
    console.log('[AUTH] Entrando em Modo Demo');
    setIsDemoMode(true);
    setUser({ 
      email: "demo@ecovision.com", 
      id: "demo-user-ecovision-2024" 
    });
    // Token especial para modo demo que o backend reconhece
    setUserToken('DEMO_MODE_TOKEN_ecovision_2024');
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
            'Authorization': `Bearer ${userToken || publicAnonKey}`,
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
            'Authorization': `Bearer ${userToken || publicAnonKey}`,
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
            'Authorization': `Bearer ${userToken || publicAnonKey}`,
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
            'Authorization': `Bearer ${userToken || publicAnonKey}`,
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
            'Authorization': `Bearer ${userToken || publicAnonKey}`,
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
            'Authorization': `Bearer ${userToken || publicAnonKey}`,
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
          {/* Demo Mode Banner */}
          {isDemoMode && (
            <div className="bg-yellow-50 border-2 border-yellow-400 rounded-lg p-4 mt-16 md:mt-0">
              <div className="flex items-start gap-3">
                <TestTube className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-semibold text-yellow-800 text-sm">
                    Modo Demonstração Ativo
                  </p>
                  <p className="text-yellow-700 text-xs mt-1">
                    Você está usando o EcoVision em modo demo. Os dados não serão salvos permanentemente.
                  </p>
                </div>
              </div>
            </div>
          )}
          
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
                userToken={userToken}
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
                userToken={userToken}
              />
            )}

            {activeTab === "perfil" && (
              <UserProfile user={user} isDemoMode={isDemoMode} userToken={userToken} />
            )}
          </div>
        </div>
      </div>

      {/* Toast notifications */}
      <Toaster />
    </div>
  );
}
