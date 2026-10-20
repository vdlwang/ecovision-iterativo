import { useRef, useState } from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Play, Pause } from 'lucide-react';
import { useStableWebSocket } from '../hooks/useStableWebSocket';

interface Detection {
  class: string;
  confidence: number;
  bbox: [number, number, number, number];
}

interface FrameData {
  frame: string;
  detections: Detection[];
  fps: number;
  motor_running: boolean;
}

export function MonitorPanel() {
  const [detections, setDetections] = useState<Detection[]>([]);
  const [fps, setFps] = useState(0);
  const [motorRunning, setMotorRunning] = useState(true);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { connected, send } = useStableWebSocket('ws://localhost:8765', {
    onMessage: (event) => {
      try {
        const data: FrameData = JSON.parse(event.data);

        // Atualizar canvas com frame
        const canvas = canvasRef.current;
        if (canvas && data.frame) {
          const ctx = canvas.getContext('2d');
          if (ctx) {
            const img = new Image();
            img.onload = () => {
              canvas.width = img.width;
              canvas.height = img.height;
              ctx.drawImage(img, 0, 0);

              // Desenhar bounding boxes
              data.detections?.forEach(det => {
                const [x1, y1, x2, y2] = det.bbox;
                ctx.strokeStyle = '#22c55e';
                ctx.lineWidth = 3;
                ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

                // Label
                ctx.fillStyle = '#22c55e';
                ctx.fillRect(x1, y1 - 25, 200, 25);
                ctx.fillStyle = '#000';
                ctx.font = '14px monospace';
                ctx.fillText(
                  `${det.class} ${(det.confidence * 100).toFixed(1)}%`,
                  x1 + 5,
                  y1 - 8
                );
              });
            };
            img.src = `data:image/jpeg;base64,${data.frame}`;
          }
        }

        setDetections(data.detections || []);
        setFps(data.fps || 0);
        setMotorRunning(data.motor_running ?? true);
      } catch (error) {
        // Silencioso
      }
    },
  });

  const sendCommand = (command: string) => {
    send({ command });
  };

  const materialIcons: Record<string, string> = {
    'plastic': '♻️',
    'metal': '🔩',
    'corrugated carton': '📦',
    'paper': '📄',
    'cardboard': '📦',
    'glass': '🍾',
  };

  const getMaterialIcon = (className: string) => {
    const lower = className.toLowerCase();
    for (const [key, icon] of Object.entries(materialIcons)) {
      if (lower.includes(key)) return icon;
    }
    return '📦';
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-white text-2xl mb-2">Monitor em Tempo Real</h2>
          <p className="text-neutral-400">Detecções YOLO + Controle da Esteira</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className={`${connected ? 'bg-green-600/20 text-green-600 border-green-600/30' : 'bg-red-600/20 text-red-600 border-red-600/30'}`}>
            {connected ? 'Conectado' : 'Desconectado'}
          </Badge>
          <Badge variant="outline" className="bg-neutral-800 text-white border-neutral-700">
            {fps} FPS
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card className="bg-neutral-900 border-neutral-800 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white">Feed da Câmera</h3>
              <Badge variant="outline" className="bg-green-600/20 text-green-600 border-green-600/30">
                {detections.length} detecções
              </Badge>
            </div>
            
            <div className="relative bg-neutral-950 rounded-lg overflow-hidden">
              <canvas
                ref={canvasRef}
                className="w-full h-auto"
              />
              
              {!connected && (
                <div className="absolute inset-0 flex items-center justify-center bg-neutral-950">
                  <div className="text-center">
                    <div className="text-6xl mb-4">📹</div>
                    <p className="text-neutral-500 mb-2">Aguardando conexão...</p>
                    <p className="text-neutral-600 text-sm">Execute: python backend/ecovision_local_modf.py</p>
                  </div>
                </div>
              )}
            </div>
          </Card>

          <Card className="bg-neutral-900 border-neutral-800 p-4 md:p-6">
            <h3 className="text-white mb-3 md:mb-4 text-base md:text-lg">Detecções Ativas</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
              {detections.slice(0, 4).map((detection, index) => (
                <div
                  key={index}
                  className="p-3 md:p-4 bg-neutral-800 rounded-lg text-center"
                >
                  <div className="text-3xl md:text-4xl mb-2">
                    {getMaterialIcon(detection.class)}
                  </div>
                  <p className="text-white text-xs md:text-sm mb-1 truncate" title={detection.class}>
                    {detection.class}
                  </p>
                  <p className="text-green-500 text-xs">
                    {(detection.confidence * 100).toFixed(1)}%
                  </p>
                </div>
              ))}
              
              {detections.length === 0 && (
                <div className="col-span-2 md:col-span-4 p-6 md:p-8 text-center text-neutral-500 text-sm md:text-base">
                  Nenhuma detecção no momento
                </div>
              )}
            </div>
          </Card>
        </div>

        <div className="space-y-4 md:space-y-6">
          <Card className="bg-neutral-900 border-neutral-800 p-4 md:p-6">
            <h3 className="text-white mb-3 md:mb-4 text-base md:text-lg">Controle da Esteira</h3>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 md:p-4 bg-neutral-800 rounded-lg">
                <span className="text-neutral-300 text-sm md:text-base">Motor</span>
                <Badge className={motorRunning ? 'bg-green-600' : 'bg-red-600'}>
                  {motorRunning ? 'Ligado' : 'Parado'}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-2 md:gap-3">
                <Button
                  onClick={() => {
                    setMotorRunning(true);
                    sendCommand('MOTOR ON');
                  }}
                  className="bg-green-600 hover:bg-green-700 text-white text-sm md:text-base"
                >
                  <Play className="w-3 h-3 md:w-4 md:h-4 mr-2" />
                  Ligar
                </Button>
                <Button
                  onClick={() => {
                    setMotorRunning(false);
                    sendCommand('MOTOR OFF');
                  }}
                  variant="outline"
                  className="bg-neutral-800 border-neutral-700 text-white hover:bg-neutral-700 text-sm md:text-base"
                >
                  <Pause className="w-3 h-3 md:w-4 md:h-4 mr-2" />
                  Parar
                </Button>
              </div>
            </div>
          </Card>

          <Card className="bg-neutral-900 border-neutral-800 p-4 md:p-6">
            <h3 className="text-white mb-3 md:mb-4 text-base md:text-lg">Status do Sistema</h3>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between p-2 md:p-3 bg-neutral-800 rounded-lg">
                <span className="text-neutral-400 text-xs md:text-sm">Câmera</span>
                <Badge className={connected ? 'bg-green-600' : 'bg-neutral-600'}>
                  {connected ? 'Ativo' : 'Inativo'}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between p-2 md:p-3 bg-neutral-800 rounded-lg">
                <span className="text-neutral-400 text-xs md:text-sm">YOLO</span>
                <Badge className={connected ? 'bg-green-600' : 'bg-neutral-600'}>
                  {connected ? 'Rodando' : 'Parado'}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between p-2 md:p-3 bg-neutral-800 rounded-lg">
                <span className="text-neutral-400 text-xs md:text-sm">ESP32</span>
                <Badge className={connected ? 'bg-green-600' : 'bg-neutral-600'}>
                  {connected ? 'COM8' : 'N/A'}
                </Badge>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}