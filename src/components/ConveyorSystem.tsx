import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Play, Pause, AlertTriangle, CheckCircle, Camera, Video } from "lucide-react";
import { ImageWithFallback } from "./figma/ImageWithFallback";

interface Detection {
  id: string;
  material: string;
  confidence: number;
  timestamp: Date;
  gateAssigned: number | null;
}

interface ConveyorSystemProps {
  gateConfigs: { [key: number]: string };
  minAccuracy: number;
  isRunning: boolean;
  onToggleSystem: () => void;
}

const materialColors = {
  papel: { bg: "bg-material-paper", text: "text-white" },
  metal: { bg: "bg-material-metal", text: "text-white" },
  plastico: { bg: "bg-material-plastic", text: "text-white" },
  vidro: { bg: "bg-material-glass", text: "text-gray-800" }
};

export function ConveyorSystem({ 
  gateConfigs, 
  minAccuracy, 
  isRunning, 
  onToggleSystem 
}: ConveyorSystemProps) {
  const [recentDetections, setRecentDetections] = useState<Detection[]>([]);
  const [gateStates, setGateStates] = useState({
    1: { active: false, lastActivated: null as Date | null },
    2: { active: false, lastActivated: null as Date | null },
    3: { active: false, lastActivated: null as Date | null }
  });

  // Simula detecções em tempo real quando o sistema está rodando
  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      const materials = ["papel", "metal", "plastico", "vidro"];
      const randomMaterial = materials[Math.floor(Math.random() * materials.length)];
      const confidence = Math.random() * 40 + 60; // 60-100%
      
      const detection: Detection = {
        id: Date.now().toString(),
        material: randomMaterial,
        confidence,
        timestamp: new Date(),
        gateAssigned: null
      };

      // Determina qual cancela deve ser acionada
      if (confidence >= minAccuracy) {
        const assignedGate = Object.entries(gateConfigs).find(
          ([_, material]) => material === randomMaterial
        );
        
        if (assignedGate) {
          detection.gateAssigned = parseInt(assignedGate[0]);
          
          // Ativa a cancela por 2 segundos
          setGateStates(prev => ({
            ...prev,
            [detection.gateAssigned!]: { 
              active: true, 
              lastActivated: new Date() 
            }
          }));
          
          setTimeout(() => {
            setGateStates(prev => ({
              ...prev,
              [detection.gateAssigned!]: { 
                active: false, 
                lastActivated: prev[detection.gateAssigned! as keyof typeof prev].lastActivated 
              }
            }));
          }, 2000);
        }
      }

      setRecentDetections(prev => [detection, ...prev.slice(0, 9)]);
    }, 3000 + Math.random() * 2000); // 3-5 segundos entre detecções

    return () => clearInterval(interval);
  }, [isRunning, minAccuracy, gateConfigs]);

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
      {/* Status do Sistema */}
      <Card className="border-2 border-recycling-primary/20">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4 bg-recycling-lighter/30">
          <CardTitle className="flex items-center gap-2 text-recycling-primary-darker">
            Status do Sistema
            {isRunning ? (
              <CheckCircle className="h-5 w-5 text-recycling-primary" />
            ) : (
              <AlertTriangle className="h-5 w-5 text-material-glass" />
            )}
          </CardTitle>
          <Button 
            onClick={onToggleSystem} 
            variant={isRunning ? "destructive" : "default"}
            className={isRunning 
              ? "bg-material-rejected hover:bg-material-rejected/90" 
              : "bg-recycling-primary hover:bg-recycling-primary-dark"
            }
          >
            {isRunning ? <Pause className="h-4 w-4 mr-2" /> : <Play className="h-4 w-4 mr-2" />}
            {isRunning ? "Parar Sistema" : "Iniciar Sistema"}
          </Button>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Badge 
              variant={isRunning ? "default" : "secondary"}
              className={isRunning ? "bg-recycling-accent text-white" : ""}
            >
              {isRunning ? "EM OPERAÇÃO" : "PARADO"}
            </Badge>
            <span className="text-sm text-muted-foreground">
              Acurácia mínima: {minAccuracy}%
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Visualização das Câmeras */}
      <Card className="border-2 border-recycling-primary/20">
        <CardHeader className="bg-recycling-lighter/30">
          <CardTitle className="flex items-center gap-2 text-recycling-primary-darker">
            <Camera className="h-5 w-5 text-recycling-primary" />
            Monitoramento de Câmeras
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Câmera Principal da Esteira */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-medium text-recycling-primary-darker">Câmera Principal - Esteira</h4>
                <Badge variant="outline" className="border-recycling-primary text-recycling-primary">
                  <Video className="h-3 w-3 mr-1" />
                  {isRunning ? "AO VIVO" : "INATIVO"}
                </Badge>
              </div>
              <div className="relative bg-gray-900 rounded-lg overflow-hidden border-2 border-recycling-primary/30">
                <div className="aspect-video w-full">
                  {isRunning ? (
                    <div className="relative w-full h-full">
                      <ImageWithFallback
                        src="https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=400&h=225&fit=crop&crop=center"
                        alt="Vista da esteira principal"
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/30"></div>
                      <div className="absolute bottom-2 left-2 text-white text-xs bg-black/50 px-2 py-1 rounded">
                        CAM-01 | {new Date().toLocaleTimeString()}
                      </div>
                      {/* Indicador de detecção ativa */}
                      {recentDetections.length > 0 && (
                        <div className="absolute top-2 right-2">
                          <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                      <div className="text-center">
                        <Camera className="h-12 w-12 mx-auto mb-2" />
                        <p className="text-sm">Câmera Inativa</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Câmera de Classificação */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-medium text-recycling-primary-darker">Câmera de Classificação</h4>
                <Badge variant="outline" className="border-recycling-primary text-recycling-primary">
                  <Video className="h-3 w-3 mr-1" />
                  {isRunning ? "AO VIVO" : "INATIVO"}
                </Badge>
              </div>
              <div className="relative bg-gray-900 rounded-lg overflow-hidden border-2 border-recycling-primary/30">
                <div className="aspect-video w-full">
                  {isRunning ? (
                    <div className="relative w-full h-full">
                      <ImageWithFallback
                        src="https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?w=400&h=225&fit=crop&crop=center"
                        alt="Vista de classificação de materiais"
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/30"></div>
                      <div className="absolute bottom-2 left-2 text-white text-xs bg-black/50 px-2 py-1 rounded">
                        CAM-02 | {new Date().toLocaleTimeString()}
                      </div>
                      {/* Overlay de detecção */}
                      {recentDetections.length > 0 && (
                        <div className="absolute top-4 left-4 bg-black/70 text-white px-3 py-2 rounded text-xs">
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                            <span>Detectando: {recentDetections[0]?.material}</span>
                          </div>
                          <div className="text-xs opacity-75 mt-1">
                            Confiança: {recentDetections[0]?.confidence.toFixed(1)}%
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-400">
                      <div className="text-center">
                        <Camera className="h-12 w-12 mx-auto mb-2" />
                        <p className="text-sm">Câmera Inativa</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Visualização da Esteira */}
      <Card className="border-2 border-recycling-primary/20">
        <CardHeader className="bg-recycling-lighter/30">
          <CardTitle className="text-recycling-primary-darker">Esteira Rolante</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="relative">
            {/* Esteira */}
            <div className="w-full h-24 bg-gradient-to-r from-gray-300 via-gray-400 to-gray-300 rounded-lg relative overflow-hidden border-2 border-recycling-primary/30">
              {/* Padrão da esteira em movimento */}
              <div className={`absolute inset-0 bg-gradient-to-r from-transparent via-recycling-primary/20 to-transparent opacity-50 ${
                isRunning ? 'animate-pulse' : ''
              }`} />
              
              {/* Direção do movimento */}
              <div className="absolute top-1/2 left-4 transform -translate-y-1/2">
                <div className="flex items-center text-recycling-primary-darker">
                  <span className="text-sm mr-2 font-medium">Entrada</span>
                  {isRunning && (
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-recycling-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-recycling-accent rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-recycling-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  )}
                </div>
              </div>
              
              <div className="absolute top-1/2 right-4 transform -translate-y-1/2">
                <span className="text-sm text-recycling-primary-darker font-medium">Saída</span>
              </div>
            </div>

            {/* Cancelas */}
            <div className="flex justify-center mt-6 space-x-8">
              {[1, 2, 3].map((gateNumber) => {
                const gateColor = getGateColor(gateNumber);
                const isActive = gateStates[gateNumber as keyof typeof gateStates].active;
                
                return (
                  <div key={gateNumber} className="flex flex-col items-center space-y-2">
                    <div className="text-sm font-medium text-recycling-primary-darker">Cancela {gateNumber}</div>
                    <div 
                      className={`w-16 h-16 rounded-lg flex items-center justify-center transition-all duration-300 border-2 ${
                        isActive 
                          ? `${gateColor.bg} ${gateColor.text} border-recycling-primary shadow-lg shadow-recycling-primary/30 scale-110` 
                          : `${gateColor.bg} ${gateColor.text} border-recycling-primary/30`
                      }`}
                    >
                      <span className="text-xs text-center font-medium">
                        {gateConfigs[gateNumber] || "Não config."}
                      </span>
                    </div>
                    {isActive && (
                      <Badge variant="default" className="text-xs bg-recycling-accent text-white">ATIVA</Badge>
                    )}
                  </div>
                );
              })}
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
            <p className="text-muted-foreground text-center py-4">
              {isRunning ? "Aguardando detecções..." : "Sistema parado"}
            </p>
          ) : (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {recentDetections.map((detection) => {
                const materialColor = getMaterialColor(detection.material);
                
                return (
                  <div 
                    key={detection.id} 
                    className="flex items-center justify-between p-3 bg-recycling-lighter/20 rounded-lg border border-recycling-primary/10"
                  >
                    <div className="flex items-center space-x-3">
                      <Badge 
                        className={`${materialColor.bg} ${materialColor.text} border-none`}
                      >
                        {detection.material}
                      </Badge>
                      <span className="text-sm">
                        {detection.confidence.toFixed(1)}% confiança
                      </span>
                      {detection.confidence < minAccuracy && (
                        <span className="text-xs text-material-rejected font-medium">REJEITADO</span>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      {detection.gateAssigned && (
                        <Badge variant="outline" className="border-recycling-primary text-recycling-primary">
                          Cancela {detection.gateAssigned}
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
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