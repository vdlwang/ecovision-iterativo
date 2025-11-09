import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Play, Pause, AlertTriangle, CheckCircle, ArrowRight } from "lucide-react";
import { CameraFeed } from "./CameraFeed";
import { projectId, publicAnonKey } from "../utils/supabase/info";

interface Detection {
  id: string;
  material: string;
  confidence: number;
  timestamp: Date;
  gateAssigned: number | null;
}

interface MonitorPanelProps {
  gateConfigs: { [key: number]: string };
  minAccuracy: number;
  isRunning: boolean;
  onToggleSystem: () => void;
  modelVersion: string;
  userId: string;
  userToken: string | null;
}

const materialColors = {
  papel: { bg: "bg-material-paper", text: "text-white" },
  metal: { bg: "bg-material-metal", text: "text-white" },
  plastico: { bg: "bg-material-plastic", text: "text-white" },
  vidro: { bg: "bg-material-glass", text: "text-gray-800" }
};

export function MonitorPanel({ 
  gateConfigs, 
  minAccuracy, 
  isRunning, 
  onToggleSystem,
  modelVersion,
  userId,
  userToken
}: MonitorPanelProps) {
  const [recentDetections, setRecentDetections] = useState<Detection[]>([]);
  const [beltRunning, setBeltRunning] = useState(false);
  const [gateStates, setGateStates] = useState({
    1: { active: false, lastActivated: null as Date | null },
    2: { active: false, lastActivated: null as Date | null },
    3: { active: false, lastActivated: null as Date | null }
  });

  // Handler para detecções da câmera
  const handleCameraDetection = async (detection: any) => {
    const material = detection.class;
    const confidence = detection.confidence * 100;

    console.log(`[DETECÇÃO] Material: ${material}, Confiança: ${confidence.toFixed(1)}%`);

    const newDetection: Detection = {
      id: Date.now().toString(),
      material,
      confidence,
      timestamp: new Date(),
      gateAssigned: null
    };

    // Verifica se confiança é suficiente
    if (confidence >= minAccuracy) {
      // Encontra cancela configurada para este material
      const assignedGate = Object.entries(gateConfigs).find(
        ([_, mat]) => mat === material
      );

      if (assignedGate) {
        const gateNumber = parseInt(assignedGate[0]);
        newDetection.gateAssigned = gateNumber;

        console.log(`[CANCELA] Acionando cancela ${gateNumber} para ${material}`);

        // Envia comando serial para ESP
        try {
          await sendSerialCommand(gateNumber);
          
          // Registra detecção no banco de dados
          await saveDetection(newDetection, userId);

          // Ativa cancela visualmente
          setGateStates(prev => ({
            ...prev,
            [gateNumber]: { 
              active: true, 
              lastActivated: new Date() 
            }
          }));

          // Desativa após 2 segundos
          setTimeout(() => {
            setGateStates(prev => ({
              ...prev,
              [gateNumber]: { 
                active: false, 
                lastActivated: prev[gateNumber as keyof typeof prev].lastActivated 
              }
            }));
          }, 2000);
        } catch (error) {
          console.error('[ERRO] Falha ao acionar cancela:', error);
        }
      } else {
        console.log(`[AVISO] Nenhuma cancela configurada para ${material}`);
      }
    } else {
      console.log(`[REJEIÇÃO] Confiança ${confidence.toFixed(1)}% abaixo do mínimo ${minAccuracy}%`);
    }

    setRecentDetections(prev => [newDetection, ...prev.slice(0, 9)]);
  };

  // Simula envio de comando serial para ESP32
  const sendSerialCommand = async (gateNumber: number) => {
    console.log(`[SERIAL] Simulando comando - Esteira: ON, Cancela: ${gateNumber}`);
    // Nota: Implementar endpoint /serial/send no backend se conectar ESP32 real
  };

  // Salva detecção no banco de dados
  const saveDetection = async (detection: Detection, userId: string) => {
    try {
      // Detecções são salvas via endpoint /inference durante o processamento
      console.log(`[BD] Detecção registrada: ${detection.material} (${detection.confidence.toFixed(1)}%)`);
    } catch (error) {
      console.error('[BD] Erro ao salvar detecção:', error);
    }
  };

  const getMaterialColor = (material: string) => {
    return materialColors[material as keyof typeof materialColors] || { bg: "bg-gray-500", text: "text-white" };
  };

  const getGateColor = (gateNumber: number) => {
    const material = gateConfigs[gateNumber];
    if (!material) return { bg: "bg-gray-200", text: "text-gray-600" };
    return materialColors[material as keyof typeof materialColors];
  };

  return (
    <div className="space-y-6">
      {/* Card Unificado: Esteira + Câmera */}
      <Card className="border-2 border-recycling-primary/20">
        <CardHeader className="bg-recycling-lighter/30">
          <CardTitle className="text-recycling-primary-darker">Monitor do Sistema</CardTitle>
        </CardHeader>
        <CardContent className="pt-6 pb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 h-full">
            {/* Coluna Esquerda: Câmera Principal */}
            <div className="space-y-4 md:pr-8 md:border-r-2 md:border-recycling-primary/30 pb-6 md:pb-0 border-b-2 md:border-b-0 border-recycling-primary/30">
              <CameraFeed
                isRunning={isRunning}
                onDetection={handleCameraDetection}
                modelVersion={modelVersion}
                minConfidence={minAccuracy}
                onToggleSystem={onToggleSystem}
                inline={true}
                userToken={userToken}
              />
            </div>

            {/* Coluna Direita: Esteira Rolante */}
            <div className="space-y-4 md:pl-8">
              {/* Título e Controles da Esteira */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-recycling-primary-darker">Esteira Rolante</h3>
                  <Badge variant={beltRunning ? "default" : "secondary"} className={beltRunning ? "bg-recycling-accent text-white" : ""}>
                    {beltRunning ? "EM MOVIMENTO" : "PARADA"}
                  </Badge>
                </div>
                
                {/* Controle da Esteira */}
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-3 bg-white/50 rounded-lg border border-recycling-primary/20">
                  <div className="flex items-center gap-2">
                    {beltRunning ? (
                      <CheckCircle className="h-4 w-4 text-recycling-primary" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-material-glass" />
                    )}
                    <span className="text-sm font-medium text-recycling-primary-darker">
                      {beltRunning ? "Transportador Ativo" : "Transportador Parado"}
                    </span>
                  </div>
                  <Button 
                    onClick={() => setBeltRunning(!beltRunning)}
                    variant={beltRunning ? "destructive" : "default"}
                    size="sm"
                    className={beltRunning 
                      ? "bg-material-rejected hover:bg-material-rejected/90" 
                      : "bg-recycling-primary hover:bg-recycling-primary-dark"
                    }
                  >
                    {beltRunning ? <Pause className="h-3 w-3 mr-1.5" /> : <Play className="h-3 w-3 mr-1.5" />}
                    {beltRunning ? "Parar" : "Iniciar"}
                  </Button>
                </div>
                
                <p className="text-xs text-muted-foreground mt-2">Confiança mínima: {minAccuracy}%</p>
              </div>

              {/* Visualização da esteira */}
              <div className="relative">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-recycling-primary-darker">Transportador</span>
                </div>
              
              <div className="relative w-full h-24 bg-gray-300 rounded-lg overflow-hidden border-2 border-recycling-primary/30">
                {/* Animação de movimento */}
                {beltRunning && (
                  <>
                    <div 
                      className="absolute inset-0 opacity-30"
                      style={{
                        background: 'repeating-linear-gradient(90deg, transparent, transparent 20px, rgba(52, 71, 103, 0.1) 20px, rgba(52, 71, 103, 0.1) 40px)',
                        animation: 'conveyor-move 2s linear infinite'
                      }}
                    />
                    <style>{`
                      @keyframes conveyor-move {
                        0% { transform: translateX(0); }
                        100% { transform: translateX(40px); }
                      }
                    `}</style>
                  </>
                )}
                
                {/* Labels */}
                <div className="absolute top-1/2 left-3 transform -translate-y-1/2 flex items-center gap-2">
                  <span className="text-xs font-medium text-recycling-primary-darker bg-white/80 px-2 py-1 rounded">Entrada</span>
                  {beltRunning && <ArrowRight className="w-4 h-4 text-recycling-primary animate-pulse" />}
                </div>
                <div className="absolute top-1/2 right-3 transform -translate-y-1/2">
                  <span className="text-xs font-medium text-recycling-primary-darker bg-white/80 px-2 py-1 rounded">Saída</span>
                </div>
              </div>

              {/* Cancelas */}
              <div className="flex justify-center mt-6 space-x-6">
                {[1, 2, 3].map((gateNumber) => {
                  const gateColor = getGateColor(gateNumber);
                  const isActive = gateStates[gateNumber as keyof typeof gateStates].active;
                  
                  return (
                    <div key={gateNumber} className="flex flex-col items-center space-y-2">
                      <div className="text-xs font-medium text-recycling-primary-darker">Cancela {gateNumber}</div>
                      <div 
                        className={`w-16 h-16 rounded-lg flex items-center justify-center transition-all duration-300 border-2 ${
                          isActive 
                            ? `${gateColor.bg} ${gateColor.text} border-recycling-primary shadow-lg shadow-recycling-primary/30 scale-110` 
                            : `${gateColor.bg} ${gateColor.text} border-recycling-primary/30`
                        }`}
                      >
                        <span className="text-xs text-center font-medium leading-tight px-1">
                          {gateConfigs[gateNumber] || "Não conf."}
                        </span>
                      </div>
                      {isActive && (
                        <Badge variant="default" className="text-[10px] px-2 py-0 bg-recycling-accent text-white">ATIVA</Badge>
                      )}
                    </div>
                  );
                })}
              </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Detecções Recentes */}
      <Card className="border-2 border-recycling-primary/20">
        <CardHeader className="bg-recycling-lighter/30">
          <CardTitle className="text-recycling-primary-darker">Detecções Recentes</CardTitle>
        </CardHeader>
        <CardContent>
          {recentDetections.length === 0 ? (
            <p className="text-muted-foreground text-center py-4 text-sm">
              {isRunning ? "Aguardando detecções..." : "Sistema parado"}
            </p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {recentDetections.map((detection) => {
                const materialColor = getMaterialColor(detection.material);
                
                return (
                  <div 
                    key={detection.id} 
                    className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-2.5 bg-recycling-lighter/20 rounded-lg border border-recycling-primary/10 gap-2"
                  >
                    <div className="flex items-center space-x-2.5">
                      <Badge 
                        className={`${materialColor.bg} ${materialColor.text} border-none text-xs`}
                      >
                        {detection.material}
                      </Badge>
                      <span className="text-xs">
                        {detection.confidence.toFixed(1)}%
                      </span>
                      {detection.confidence < minAccuracy && (
                        <span className="text-[10px] text-material-rejected font-medium">REJEITADO</span>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      {detection.gateAssigned && (
                        <Badge variant="outline" className="border-recycling-primary text-recycling-primary text-[10px] px-1.5">
                          C{detection.gateAssigned}
                        </Badge>
                      )}
                      <span className="text-[10px] text-muted-foreground">
                        {detection.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
