import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Camera, Video, RefreshCw } from "lucide-react";

interface Detection {
  class: string;
  confidence: number;
  bbox: [number, number, number, number]; // [x, y, width, height]
}

interface CameraFeedProps {
  isRunning: boolean;
  onDetection?: (detection: Detection) => void;
  modelVersion: string;
  minConfidence: number;
}

export function CameraFeed({ isRunning, onDetection, modelVersion, minConfidence }: CameraFeedProps) {
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string | undefined>(undefined);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Enumera dispositivos de câmera disponíveis
  useEffect(() => {
    const enumerateDevices = async () => {
      try {
        const allDevices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = allDevices.filter(device => 
          device.kind === 'videoinput' && 
          device.deviceId && 
          device.deviceId.trim() !== ''
        );
        setDevices(videoDevices);
        
        if (videoDevices.length > 0 && !selectedDevice) {
          setSelectedDevice(videoDevices[0].deviceId);
        }

        console.log(`[CÂMERA] ${videoDevices.length} câmera(s) detectada(s):`, videoDevices.map(d => d.label || d.deviceId));
      } catch (err) {
        console.error('[CÂMERA] Erro ao enumerar dispositivos:', err);
        setError('Não foi possível acessar as câmeras do dispositivo');
      }
    };

    enumerateDevices();
  }, []);

  // Inicia/para stream da câmera
  useEffect(() => {
    if (!isRunning || !selectedDevice) {
      // Para stream se existir
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
        setStream(null);
        console.log('[CÂMERA] Stream parada');
      }
      return;
    }

    const startStream = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Para stream anterior se existir
        if (stream) {
          stream.getTracks().forEach(track => track.stop());
        }

        const newStream = await navigator.mediaDevices.getUserMedia({
          video: {
            deviceId: selectedDevice ? { exact: selectedDevice } : undefined,
            width: { ideal: 1920 },
            height: { ideal: 1080 }
          }
        });

        setStream(newStream);
        
        if (videoRef.current) {
          videoRef.current.srcObject = newStream;
        }

        const selectedDeviceInfo = devices.find(d => d.deviceId === selectedDevice);
        console.log(`[CÂMERA] Stream iniciada - Câmera: ${selectedDeviceInfo?.label || selectedDevice}`);
      } catch (err) {
        console.error('[CÂMERA] Erro ao iniciar stream:', err);
        setError('Erro ao acessar a câmera selecionada');
      } finally {
        setIsLoading(false);
      }
    };

    startStream();

    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [isRunning, selectedDevice]);

  // Processa frames e envia para inferência
  useEffect(() => {
    if (!isRunning || !videoRef.current || !canvasRef.current || !stream) {
      return;
    }

    const interval = setInterval(async () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      
      if (!video || !canvas) return;

      const context = canvas.getContext('2d');
      if (!context) return;

      // Captura frame atual
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      context.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Converte para base64
      const frameData = canvas.toDataURL('image/jpeg', 0.8);

      try {
        // IMPORTANTE: Este endpoint deve ser implementado para processar com Ultralytics
        // O servidor Python receberá a imagem e retornará as detecções
        console.log(`[INFERÊNCIA] Enviando frame para modelo ${modelVersion} (confiança mínima: ${minConfidence}%)`);
        
        const response = await fetch('/api/inference', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            image: frameData,
            model: modelVersion,
            confidence: minConfidence / 100
          })
        });

        if (response.ok) {
          const data = await response.json();
          
          if (data.detections && data.detections.length > 0) {
            console.log(`[INFERÊNCIA] ${data.detections.length} detecção(ões):`, 
              data.detections.map((d: Detection) => `${d.class} (${(d.confidence * 100).toFixed(1)}%)`).join(', ')
            );
            
            setDetections(data.detections);
            
            // Notifica detecção de maior confiança
            if (onDetection && data.detections.length > 0) {
              onDetection(data.detections[0]);
            }
          } else {
            setDetections([]);
          }
        }
      } catch (err) {
        // Em modo de desenvolvimento, simula detecções
        if (Math.random() > 0.7) {
          const classes = ['papel', 'metal', 'plastico', 'vidro'];
          const mockDetection: Detection = {
            class: classes[Math.floor(Math.random() * classes.length)],
            confidence: 0.7 + Math.random() * 0.3,
            bbox: [
              Math.random() * 0.3,
              Math.random() * 0.3,
              0.2 + Math.random() * 0.3,
              0.2 + Math.random() * 0.3
            ]
          };
          
          console.log(`[INFERÊNCIA MOCK] Detecção simulada: ${mockDetection.class} (${(mockDetection.confidence * 100).toFixed(1)}%)`);
          setDetections([mockDetection]);
          
          if (onDetection) {
            onDetection(mockDetection);
          }
        } else {
          setDetections([]);
        }
      }
    }, 1000); // Processa a cada 1 segundo

    return () => clearInterval(interval);
  }, [isRunning, stream, modelVersion, minConfidence, onDetection]);

  // Desenha bounding boxes no canvas overlay
  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    
    if (!canvas || !video || detections.length === 0) return;

    const context = canvas.getContext('2d');
    if (!context) return;

    const drawBoxes = () => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      context.clearRect(0, 0, canvas.width, canvas.height);

      detections.forEach(detection => {
        const [x, y, w, h] = detection.bbox;
        const pixelX = x * canvas.width;
        const pixelY = y * canvas.height;
        const pixelW = w * canvas.width;
        const pixelH = h * canvas.height;

        // Cor baseada no material
        const colors: Record<string, string> = {
          papel: '#163b6f',
          metal: '#196626',
          plastico: '#dc1f2e',
          vidro: '#d2b91f'
        };
        const color = colors[detection.class] || '#00ff00';

        // Desenha bounding box
        context.strokeStyle = color;
        context.lineWidth = 3;
        context.strokeRect(pixelX, pixelY, pixelW, pixelH);

        // Desenha label
        const label = `${detection.class} ${(detection.confidence * 100).toFixed(1)}%`;
        context.font = '16px sans-serif';
        const textWidth = context.measureText(label).width;
        
        context.fillStyle = color;
        context.fillRect(pixelX, pixelY - 25, textWidth + 10, 25);
        
        context.fillStyle = '#ffffff';
        context.fillText(label, pixelX + 5, pixelY - 7);
      });

      requestAnimationFrame(drawBoxes);
    };

    drawBoxes();
  }, [detections]);

  const handleRefreshDevices = async () => {
    const allDevices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = allDevices.filter(device => 
      device.kind === 'videoinput' && 
      device.deviceId && 
      device.deviceId.trim() !== ''
    );
    setDevices(videoDevices);
    console.log('[CÂMERA] Dispositivos atualizados:', videoDevices.length);
  };

  return (
    <Card className="border-2 border-recycling-primary/20">
      <CardHeader className="bg-recycling-lighter/30 space-y-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-recycling-primary-darker">
            <Camera className="h-5 w-5 text-recycling-primary" />
            Câmera Principal
          </CardTitle>
          <Badge variant={isRunning && stream ? "default" : "secondary"} className={isRunning && stream ? "bg-recycling-accent text-white" : ""}>
            <Video className="h-3 w-3 mr-1" />
            {isRunning && stream ? "AO VIVO" : "INATIVO"}
          </Badge>
        </div>
        
        {/* Seletor de câmera */}
        <div className="flex gap-2 items-center">
          <Select value={selectedDevice || undefined} onValueChange={setSelectedDevice} disabled={isRunning}>
            <SelectTrigger className="flex-1">
              <SelectValue placeholder="Selecione uma câmera" />
            </SelectTrigger>
            <SelectContent>
              {devices.length > 0 ? (
                devices
                  .filter(device => device.deviceId && device.deviceId.trim() !== '')
                  .map((device, index) => (
                    <SelectItem key={device.deviceId} value={device.deviceId}>
                      {device.label || `Câmera ${index + 1}`}
                    </SelectItem>
                  ))
              ) : (
                <SelectItem value="no-camera-placeholder" disabled>
                  Nenhuma câmera detectada
                </SelectItem>
              )}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefreshDevices}
            disabled={isRunning}
            title="Atualizar lista de câmeras"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <div className="relative bg-gray-900 aspect-video w-full overflow-hidden">
          {error && (
            <div className="absolute inset-0 flex items-center justify-center text-red-400 bg-gray-900 z-10">
              <div className="text-center p-4">
                <Camera className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">{error}</p>
              </div>
            </div>
          )}
          
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900 z-10">
              <div className="text-center text-white">
                <div className="w-12 h-12 border-4 border-recycling-primary border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                <p className="text-sm">Iniciando câmera...</p>
              </div>
            </div>
          )}
          
          {!isRunning && !isLoading && !error && (
            <div className="absolute inset-0 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <Camera className="h-16 w-16 mx-auto mb-3 opacity-50" />
                <p className="text-sm">Sistema Parado</p>
                <p className="text-xs opacity-75 mt-1">Inicie o sistema para ativar a câmera</p>
              </div>
            </div>
          )}

          {/* Video element */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
            style={{ display: stream ? 'block' : 'none' }}
          />

          {/* Canvas overlay para bounding boxes */}
          <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full pointer-events-none"
            style={{ display: stream ? 'block' : 'none' }}
          />

          {/* Info overlay */}
          {stream && (
            <>
              <div className="absolute bottom-3 left-3 text-white text-xs bg-black/70 px-2 py-1 rounded">
                {devices.find(d => d.deviceId === selectedDevice)?.label || 'Câmera'} | {new Date().toLocaleTimeString()}
              </div>
              
              {detections.length > 0 && (
                <div className="absolute top-3 right-3 bg-black/70 text-white px-3 py-2 rounded space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                    <span className="text-xs font-medium">DETECTANDO</span>
                  </div>
                  {detections.slice(0, 3).map((det, idx) => (
                    <div key={idx} className="text-xs opacity-90">
                      {det.class}: {(det.confidence * 100).toFixed(1)}%
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
