import { useEffect, useRef, useState } from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Play, Pause, Camera } from 'lucide-react';
import { toast } from 'sonner@2.0.3';
import { useStableWebSocket } from '../hooks/useStableWebSocket';
import { BadgeBackend } from './BadgeBackend';
import { AjusteCamera, EstadoAjuste, ModoAjuste } from './AjusteCamera';
import { BACKEND_WS_URL } from '../config';

interface Detection {
  class: string;
  material: string;
  confidence: number;
  bbox: [number, number, number, number];
  // ID da trilha do rastreador (T15); null sem rastreamento
  id?: number | null;
}

interface FrameData {
  frame: string;
  detections: Detection[];
  fps: number;
  motor_running: boolean;
  serial_port: string | null;
  // Captura para a anotação (T4)
  captura_automatica?: boolean;
  capturas_gravadas?: number;
  // Foco e exposição da câmera; null se a fonte não tem (vídeo, URL)
  foco?: EstadoAjuste | null;
  exposicao?: Exposicao | null;
}

// Com a exposição, o ganho (o automático mexe nos dois; travar fixa os dois)
interface Exposicao extends EstadoAjuste {
  ganho: number;
}

// Faixas da C920 (v4l2-ctl --list-ctrls); outra câmera pode ter outras.
// focus_absolute; exposure_time_absolute, em 100 µs
const FOCO_MIN = 0;
const FOCO_MAX = 250;
const EXPOSICAO_MIN = 3;
const EXPOSICAO_MAX = 2047;

// Resposta do backend ao botão "Capturar agora"
interface CapturaManual {
  type: 'captura_manual';
  ok: boolean;
  arquivo: string | null;
  erro: string | null;
}

export function MonitorPanel() {
  const [detections, setDetections] = useState<Detection[]>([]);
  const [fps, setFps] = useState(0);
  const [motorRunning, setMotorRunning] = useState(true);
  const [serialPort, setSerialPort] = useState<string | null>(null);
  const [capturaAutomatica, setCapturaAutomatica] = useState(false);
  const [capturasGravadas, setCapturasGravadas] = useState(0);
  const [foco, setFoco] = useState<EstadoAjuste | null>(null);
  const [exposicao, setExposicao] = useState<Exposicao | null>(null);
  // Câmera e YOLO contam como ativos se chegou frame nos últimos 3 s
  const [ultimoFrame, setUltimoFrame] = useState(0);
  const [agora, setAgora] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setAgora(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { connected, send } = useStableWebSocket(BACKEND_WS_URL, {
    onMessage: (event) => {
      try {
        const mensagem = JSON.parse(event.data);
        if (mensagem.type === 'captura_manual') {
          const r = mensagem as CapturaManual;
          if (r.ok) toast.success(`Quadro capturado: ${r.arquivo}`);
          else toast.error(`Captura não feita: ${r.erro}`);
          return;
        }
        // Outras respostas (ex.: config) não são quadros
        if (mensagem.type) return;
        const data: FrameData = mensagem;

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

              // Desenhar bounding boxes (o backend envia o quadro sem elas)
              data.detections?.forEach(det => {
                const [x1, y1, x2, y2] = det.bbox;
                ctx.strokeStyle = '#22c55e';
                ctx.lineWidth = 3;
                ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

                // Label com a largura do texto; dentro da caixa se não couber acima
                const label = `${det.id != null ? `#${det.id} ` : ''}${det.class} (${det.material}) ${(det.confidence * 100).toFixed(1)}%`;
                ctx.font = '14px monospace';
                const larguraLabel = ctx.measureText(label).width + 10;
                const topoLabel = y1 >= 25 ? y1 - 25 : y1;
                ctx.fillStyle = '#22c55e';
                ctx.fillRect(x1, topoLabel, larguraLabel, 25);
                ctx.fillStyle = '#000';
                ctx.fillText(label, x1 + 5, topoLabel + 17);
              });
            };
            img.src = `data:image/jpeg;base64,${data.frame}`;
          }
        }

        setDetections(data.detections || []);
        setFps(data.fps || 0);
        setMotorRunning(data.motor_running ?? true);
        setSerialPort(data.serial_port ?? null);
        setCapturaAutomatica(data.captura_automatica ?? false);
        setCapturasGravadas(data.capturas_gravadas ?? 0);
        setFoco(data.foco ?? null);
        setExposicao(data.exposicao ?? null);
        if (data.frame) setUltimoFrame(Date.now());
      } catch (error) {
        // Silencioso
      }
    },
  });

  const recebendoFrames = connected && agora - ultimoFrame < 3000;
  // Esteira só com o ESP32 conectado (backend offline ou em modo demo desabilita)
  const semSerial = !connected || !serialPort;

  const sendCommand = (command: string) => {
    send({ command });
  };

  const pedirAjuste = (tipo: 'foco' | 'exposicao') => (modo: ModoAjuste, valor?: number) => {
    send({ type: tipo, modo, ...(valor !== undefined ? { valor } : {}) });
  };

  // Ícone pelo material que o backend já mapeou (taco_to_material)
  const materialIcons: Record<string, string> = {
    'plastic': '♻️',
    'metal': '🔩',
    'paper': '📄',
    'glass': '🍾',
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-white text-2xl mb-2">Monitor em Tempo Real</h2>
          <p className="text-neutral-400">Detecções YOLO + Controle da Esteira</p>
        </div>
        <div className="flex items-center gap-3">
          <BadgeBackend connected={connected} />
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
                    {materialIcons[detection.material] ?? '📦'}
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
                  disabled={semSerial}
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
                  disabled={semSerial}
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
            <h3 className="text-white mb-3 md:mb-4 text-base md:text-lg">Captura (anotação)</h3>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 md:p-4 bg-neutral-800 rounded-lg">
                <span className="text-neutral-300 text-sm md:text-base">Automática</span>
                <Badge className={capturaAutomatica ? 'bg-green-600' : 'bg-neutral-600'}>
                  {capturaAutomatica ? 'Ligada' : 'Desligada'}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-2 md:gap-3">
                <Button
                  onClick={() => {
                    setCapturaAutomatica(true);
                    send({ type: 'captura_automatica', ativa: true });
                  }}
                  disabled={!connected || capturaAutomatica}
                  className="bg-green-600 hover:bg-green-700 text-white text-sm md:text-base"
                >
                  <Play className="w-3 h-3 md:w-4 md:h-4 mr-2" />
                  Ligar
                </Button>
                <Button
                  onClick={() => {
                    setCapturaAutomatica(false);
                    send({ type: 'captura_automatica', ativa: false });
                  }}
                  disabled={!connected || !capturaAutomatica}
                  variant="outline"
                  className="bg-neutral-800 border-neutral-700 text-white hover:bg-neutral-700 text-sm md:text-base"
                >
                  <Pause className="w-3 h-3 md:w-4 md:h-4 mr-2" />
                  Desligar
                </Button>
              </div>

              <Button
                onClick={() => send({ type: 'capturar' })}
                disabled={!recebendoFrames}
                variant="outline"
                className="w-full bg-neutral-800 border-neutral-700 text-white hover:bg-neutral-700 text-sm md:text-base"
              >
                <Camera className="w-3 h-3 md:w-4 md:h-4 mr-2" />
                Capturar agora
              </Button>

              <p className="text-neutral-500 text-xs">
                {capturasGravadas} {capturasGravadas === 1 ? 'quadro gravado' : 'quadros gravados'} nesta execução do backend
              </p>
            </div>
          </Card>

          <AjusteCamera
            titulo="Foco da Câmera"
            rotulo="Foco"
            estado={foco}
            desabilitado={!recebendoFrames || !foco}
            min={FOCO_MIN}
            max={FOCO_MAX}
            ajuda="Travar fixa a lente onde o autofoco a deixou; mexer no slider passa para o manual. Fica gravado no config.json."
            onPedir={pedirAjuste('foco')}
          />

          <AjusteCamera
            titulo="Exposição da Câmera"
            rotulo="Exposição"
            estado={exposicao}
            desabilitado={!recebendoFrames || !exposicao}
            min={EXPOSICAO_MIN}
            max={EXPOSICAO_MAX}
            log
            detalheFixo={exposicao ? `ganho ${Math.round(exposicao.ganho)}` : undefined}
            ajuda="Travar fixa a exposição e o ganho em que o automático estava; o slider (em 100 µs) passa para o manual com o mesmo ganho. A C920 só aceita alguns valores e fica no anterior com os outros. Fica gravado no config.json."
            onPedir={pedirAjuste('exposicao')}
          />

          <Card className="bg-neutral-900 border-neutral-800 p-4 md:p-6">
            <h3 className="text-white mb-3 md:mb-4 text-base md:text-lg">Status do Sistema</h3>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between p-2 md:p-3 bg-neutral-800 rounded-lg">
                <span className="text-neutral-400 text-xs md:text-sm">Câmera</span>
                <Badge className={recebendoFrames ? 'bg-green-600' : 'bg-neutral-600'}>
                  {recebendoFrames ? 'Ativo' : 'Inativo'}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between p-2 md:p-3 bg-neutral-800 rounded-lg">
                <span className="text-neutral-400 text-xs md:text-sm">YOLO</span>
                <Badge className={recebendoFrames ? 'bg-green-600' : 'bg-neutral-600'}>
                  {recebendoFrames ? 'Rodando' : 'Parado'}
                </Badge>
              </div>
              
              <div className="flex items-center justify-between p-2 md:p-3 bg-neutral-800 rounded-lg">
                <span className="text-neutral-400 text-xs md:text-sm">ESP32</span>
                <Badge className={connected && serialPort ? 'bg-green-600' : 'bg-neutral-600'}>
                  {!connected ? 'N/A' : serialPort ?? 'Demo (sem serial)'}
                </Badge>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}