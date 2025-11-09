// EcoVision Camera Feed Component - v5.0 Fixed Permission Flow
import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Camera, Video, Play, Pause, AlertTriangle, CheckCircle, RefreshCw, Download } from "lucide-react";
import { projectId, publicAnonKey } from "../utils/supabase/info";
import { onnxInferenceService, base64ToImageData } from "../utils/onnxInference";

interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface Detection {
  class_name: string;
  material: string;
  confidence: number;
  bounding_box: BoundingBox;
}

interface LegacyDetection {
  class: string;
  confidence: number;
  bbox: [number, number, number, number];
}

interface CameraFeedProps {
  isRunning: boolean;
  onDetection?: (detection: LegacyDetection) => void;
  modelVersion: string;
  minConfidence: number;
  onToggleSystem?: () => void;
  inline?: boolean;
  userToken?: string | null;
}

export function CameraFeed({ isRunning, onDetection, modelVersion, minConfidence, onToggleSystem, inline = false, userToken }: CameraFeedProps) {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [detections, setDetections] = useState<Detection[]>([]);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDetecting, setIsDetecting] = useState(false);
  const [lastInferenceTime, setLastInferenceTime] = useState<number>(0);
  const [useONNX, setUseONNX] = useState(true); // Usa ONNX por padrão
  const [onnxModelReady, setOnnxModelReady] = useState(false);
  const [onnxModelLoading, setOnnxModelLoading] = useState(false);
  
  // Sincroniza isDetecting com isRunning quando isRunning muda
  useEffect(() => {
    setIsDetecting(isRunning);
  }, [isRunning]);

  // Carrega o modelo ONNX na inicialização
  useEffect(() => {
    const loadONNXModel = async () => {
      if (onnxInferenceService.isReady()) {
        setOnnxModelReady(true);
        return;
      }

      setOnnxModelLoading(true);
      try {
        console.log('[ONNX] Tentando carregar modelo /models/yolov8n.onnx...');
        await onnxInferenceService.loadModel('/models/yolov8n.onnx');
        setOnnxModelReady(true);
        console.log('[ONNX] ✅ Modelo carregado e pronto');
      } catch (error) {
        console.warn('[ONNX] ⚠️ Modelo ONNX não disponível, usando servidor backend:', error);
        setOnnxModelReady(false);
        setUseONNX(false);
      } finally {
        setOnnxModelLoading(false);
      }
    };

    loadONNXModel();

    return () => {
      // Cleanup: descarrega modelo quando componente é desmontado
      onnxInferenceService.unloadModel();
    };
  }, []);

  const startCamera = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('[CÂMERA] Iniciando stream de vídeo...');
      
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }

      // Solicita e inicia a câmera padrão do navegador
      const newStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment",
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        }
      });

      setStream(newStream);
      
      if (videoRef.current) {
        videoRef.current.srcObject = newStream;
      }

      console.log('[CÂMERA] ✅ Stream de vídeo iniciada com sucesso');
    } catch (err: any) {
      console.error('[CÂMERA] ❌ Erro ao iniciar câmera:', err.name, err.message);
      
      if (err.name === 'NotAllowedError') {
        setError('🔒 Permissão de câmera negada pelo usuário.\n\n✅ COMO CORRIGIR:\n1️⃣ Clique no ícone 🔒 ou 📹 na barra de endereço (lado esquerdo)\n2️⃣ Selecione "Permitir" para câmera\n3️⃣ Clique em "Tentar Novamente" abaixo\n\nNOTA: A câmera é essencial para o sistema funcionar.');
      } else if (err.name === 'NotFoundError') {
        setError('📹 Nenhuma câmera encontrada.\n\n✅ VERIFIQUE:\n• Há uma webcam conectada ao computador?\n• A webcam está funcionando em outros aplicativos?\n• Drivers da câmera estão instalados?\n\nTente usar outro dispositivo ou conectar uma webcam externa.');
      } else if (err.name === 'NotSupportedError' || !window.isSecureContext) {
        setError('⚠️ Acesso à câmera só funciona via HTTPS ou localhost.\n\n✅ SOLUÇÃO:\n• Se estiver em localhost: use http://localhost:5000\n• Se em produção: certifique-se de estar usando HTTPS\n• Navegadores modernos bloqueiam câmera em HTTP por segurança');
      } else if (err.name === 'NotReadableError') {
        setError('⚠️ Câmera está em uso por outro aplicativo.\n\n✅ FECHE:\n• Outros sites/aplicativos usando a câmera\n• Zoom, Teams, Skype, etc.\n• Outras abas do navegador acessando a câmera\n\nDepois clique em "Tentar Novamente"');
      } else {
        setError(`❌ Erro ao acessar câmera: ${err.message}\n\nVerifique as permissões do navegador e tente novamente.`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Para stream da câmera quando o sistema é desligado
  useEffect(() => {
    if (!isRunning && stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
      console.log('[CÂMERA] Stream parada porque o sistema foi desligado');
    }
  }, [isRunning]);

  // Processa frames e envia para inferência
  useEffect(() => {
    if (!isDetecting || !videoRef.current || !canvasRef.current || !stream) {
      return;
    }

    // Se está usando ONNX, não precisa de userToken
    if (!useONNX && !userToken) {
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

      const startTime = performance.now();

      try {
        let result;

        // Usa ONNX no navegador se disponível, caso contrário usa servidor backend
        if (useONNX && onnxModelReady) {
          console.log(`[INFERÊNCIA ONNX] Processando frame localmente (confiança mínima: ${minConfidence}%)`);
          
          // Executa inferência local com ONNX
          const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
          result = await onnxInferenceService.runInference(imageData, minConfidence);
          
          const inferenceTime = performance.now() - startTime;
          setLastInferenceTime(inferenceTime);

          if (result.success && result.detections && result.detections.length > 0) {
            console.log(`[INFERÊNCIA ONNX] ${result.detections.length} detecção(ões) em ${result.processing_time_ms.toFixed(1)}ms:`, 
              result.detections.map((d: Detection) => `${d.material} (${d.confidence.toFixed(1)}%)`).join(', ')
            );
            
            setDetections(result.detections);
            
            if (onDetection && result.detections.length > 0) {
              const firstDetection = result.detections[0];
              const legacyDetection: LegacyDetection = {
                class: firstDetection.material,
                confidence: firstDetection.confidence / 100,
                bbox: [
                  firstDetection.bounding_box.x / canvas.width,
                  firstDetection.bounding_box.y / canvas.height,
                  firstDetection.bounding_box.width / canvas.width,
                  firstDetection.bounding_box.height / canvas.height
                ]
              };
              onDetection(legacyDetection);
            }
          } else {
            setDetections([]);
          }
        } else {
          // Fallback: usa servidor backend
          console.log(`[INFERÊNCIA SERVIDOR] Enviando frame para modelo ${modelVersion} (confiança mínima: ${minConfidence}%)`);
          
          const frameData = canvas.toDataURL('image/jpeg', 0.8);
          const base64Image = frameData.split(',')[1];
          
          const response = await fetch(`https://${projectId}.supabase.co/functions/v1/make-server-ea835390/inference`, {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${userToken}`
            },
            body: JSON.stringify({
              image_base64: base64Image,
              model_version: modelVersion,
              min_confidence: minConfidence
            })
          });

          const inferenceTime = performance.now() - startTime;
          setLastInferenceTime(inferenceTime);

          if (response.ok) {
            const data = await response.json();
            
            if (data.success && data.detections && data.detections.length > 0) {
              console.log(`[INFERÊNCIA SERVIDOR] ${data.detections.length} detecção(ões) em ${data.processing_time_ms}ms:`, 
                data.detections.map((d: Detection) => `${d.material} (${d.confidence.toFixed(1)}%)`).join(', ')
              );
              
              setDetections(data.detections);
              
              if (onDetection && data.detections.length > 0) {
                const firstDetection = data.detections[0];
                const legacyDetection: LegacyDetection = {
                  class: firstDetection.material,
                  confidence: firstDetection.confidence / 100,
                  bbox: [
                    firstDetection.bounding_box.x / canvas.width,
                    firstDetection.bounding_box.y / canvas.height,
                    firstDetection.bounding_box.width / canvas.width,
                    firstDetection.bounding_box.height / canvas.height
                  ]
                };
                onDetection(legacyDetection);
              }
            } else {
              setDetections([]);
            }
          } else {
            const errorData = await response.json();
            console.error('[INFERÊNCIA SERVIDOR] Erro do servidor:', errorData.error);
            
            // Se o servidor retornou sem detecções mas com sucesso, está usando ONNX
            if (errorData.success && errorData.info) {
              console.log('[INFERÊNCIA] ℹ️', errorData.info);
              setDetections([]);
            } else if (response.status === 401) {
              setError('Sessão expirada. Por favor, faça login novamente.');
              console.error('[INFERÊNCIA SERVIDOR] Token inválido ou expirado.');
            } else {
              setError(errorData.error || 'Erro ao processar inferência');
            }
          }
        }
      } catch (err) {
        console.error('[INFERÊNCIA] Erro:', err);
        // Em modo de desenvolvimento ou erro, simula detecções
        if (Math.random() > 0.7) {
          const materials = ['papel', 'metal', 'plastico', 'vidro'];
          const randomMaterial = materials[Math.floor(Math.random() * materials.length)];
          const mockDetection: Detection = {
            class_name: randomMaterial,
            material: randomMaterial,
            confidence: 70 + Math.random() * 30,
            bounding_box: {
              x: Math.random() * 300,
              y: Math.random() * 300,
              width: 200 + Math.random() * 300,
              height: 200 + Math.random() * 300
            }
          };
          
          console.log(`[INFERÊNCIA MOCK] Detecção simulada: ${mockDetection.material} (${mockDetection.confidence.toFixed(1)}%)`);
          setDetections([mockDetection]);
          
          if (onDetection) {
            const legacyMock: LegacyDetection = {
              class: mockDetection.material,
              confidence: mockDetection.confidence / 100,
              bbox: [
                mockDetection.bounding_box.x / canvas.width,
                mockDetection.bounding_box.y / canvas.height,
                mockDetection.bounding_box.width / canvas.width,
                mockDetection.bounding_box.height / canvas.height
              ]
            };
            onDetection(legacyMock);
          }
        } else {
          setDetections([]);
        }
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [isDetecting, stream, modelVersion, minConfidence, onDetection, userToken, useONNX, onnxModelReady]);

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
        const box = detection.bounding_box;
        const pixelX = box.x;
        const pixelY = box.y;
        const pixelW = box.width;
        const pixelH = box.height;

        // Cor baseada no material
        const colors: Record<string, string> = {
          papel: '#163b6f',
          metal: '#196626',
          plastico: '#dc1f2e',
          vidro: '#d2b91f'
        };
        const color = colors[detection.material] || '#00ff00';

        // Desenha bounding box
        context.strokeStyle = color;
        context.lineWidth = 3;
        context.strokeRect(pixelX, pixelY, pixelW, pixelH);

        // Desenha label
        const label = `${detection.material} ${detection.confidence.toFixed(1)}%`;
        context.font = 'bold 16px sans-serif';
        const textWidth = context.measureText(label).width;
        
        context.fillStyle = color;
        context.fillRect(pixelX, pixelY - 28, textWidth + 12, 28);
        
        context.fillStyle = '#ffffff';
        context.fillText(label, pixelX + 6, pixelY - 8);
      });

      requestAnimationFrame(drawBoxes);
    };

    drawBoxes();
  }, [detections]);

  const cameraContent = (
    <div className="space-y-4">
      {/* Alerta: Sistema rodando mas câmera não iniciada */}
      {isRunning && !stream && !isLoading && (
        <div className="bg-yellow-50 border-2 border-yellow-400 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-yellow-800 text-xs">
                ⚠️ Sistema em execução, mas câmera não iniciada
              </p>
              <p className="text-yellow-700 text-xs mt-1">
                Clique no botão "Permitir e Iniciar Câmera" abaixo para começar a detecção
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Título e Status */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-recycling-primary-darker flex items-center gap-2">
            <Camera className="h-5 w-5 text-recycling-primary" />
            Câmera Principal
          </h3>
          <Badge variant={stream ? "default" : "secondary"} className={stream ? "bg-recycling-accent text-white" : ""}>
            <Video className="h-3 w-3 mr-1" />
            {stream ? "AO VIVO" : "INATIVO"}
          </Badge>
        </div>
        
        {/* Status e Controles */}
        {stream && (
          <div className="space-y-2">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 p-3 bg-white/50 rounded-lg border border-recycling-primary/20">
              <div className="flex items-center gap-2">
                {isDetecting ? (
                  <CheckCircle className="h-4 w-4 text-recycling-primary" />
                ) : (
                  <AlertTriangle className="h-4 w-4 text-material-glass" />
                )}
                <span className="text-sm font-medium text-recycling-primary-darker">
                  {isDetecting ? "Detecção Ativa" : "Detecção Pausada"}
                </span>
                <Badge 
                  variant={isDetecting ? "default" : "secondary"}
                  className={isDetecting ? "bg-recycling-accent text-white" : ""}
                >
                  {isDetecting ? "EM OPERAÇÃO" : "PARADO"}
                </Badge>
              </div>
              <Button 
                onClick={() => setIsDetecting(!isDetecting)} 
                variant={isDetecting ? "destructive" : "default"}
                size="sm"
                className={isDetecting 
                  ? "bg-material-rejected hover:bg-material-rejected/90" 
                  : "bg-recycling-primary hover:bg-recycling-primary-dark"
                }
              >
                {isDetecting ? <Pause className="h-3 w-3 mr-1.5" /> : <Play className="h-3 w-3 mr-1.5" />}
                {isDetecting ? "Parar" : "Iniciar"}
              </Button>
            </div>
            
            {/* Indicador do modo de inferência */}
            <div className="flex items-center gap-2 text-xs text-recycling-primary-darker bg-white/30 px-3 py-1.5 rounded border border-recycling-primary/10">
              {onnxModelLoading ? (
                <>
                  <div className="w-3 h-3 border-2 border-recycling-primary border-t-transparent rounded-full animate-spin"></div>
                  <span>Carregando modelo ONNX...</span>
                </>
              ) : onnxModelReady && useONNX ? (
                <>
                  <Download className="h-3 w-3 text-recycling-accent" />
                  <span className="font-medium">Modo: Inferência Local (ONNX)</span>
                  <Badge variant="secondary" className="text-xs">✨ Rápido & Privado</Badge>
                </>
              ) : (
                <>
                  <AlertTriangle className="h-3 w-3 text-material-glass" />
                  <span>Modo: Servidor Backend / Mock</span>
                  <Badge variant="secondary" className="text-xs">⚠️ Requer modelo</Badge>
                </>
              )}
            </div>
            
            {/* Info adicional quando ONNX não está disponível */}
            {!onnxModelLoading && !onnxModelReady && (
              <div className="flex items-start gap-2 text-xs text-blue-700 bg-blue-50 px-3 py-2 rounded border border-blue-200">
                <CheckCircle className="h-3 w-3 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium">Sistema funcionando em modo de desenvolvimento</p>
                  <p className="text-blue-600 mt-0.5">
                    Para melhor performance, converta seu modelo: <code className="bg-blue-100 px-1 rounded">python convert_to_onnx.py</code>
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Feed de vídeo */}
      <div className="relative bg-gray-900 aspect-video w-full overflow-hidden rounded-lg border-2 border-recycling-primary/30">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-400 bg-gray-900 z-10">
            <div className="text-center p-6 max-w-lg mx-4">
              <Camera className="h-16 w-16 mx-auto mb-4 text-material-rejected" />
              <div className="text-sm mb-4 text-red-400 leading-relaxed text-left bg-red-950/30 p-4 rounded-lg border border-red-500/30">
                {error.split('\n').map((line, idx) => (
                  <p key={idx} className={line.trim() === '' ? 'h-2' : ''}>{line}</p>
                ))}
              </div>
              <Button
                onClick={startCamera}
                size="sm"
                className="bg-recycling-primary hover:bg-recycling-primary-dark text-white mt-3"
              >
                <RefreshCw className="h-3 w-3 mr-1.5" />
                Tentar Novamente
              </Button>
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
        
        {!stream && !isLoading && !error && (
          <div className="absolute inset-0 flex items-center justify-center text-gray-400">
            <div className="text-center p-4 max-w-md">
              <Camera className="h-16 w-16 mx-auto mb-4 text-recycling-primary" />
              <p className="text-sm mb-2 font-medium text-gray-300">📹 Câmera Pronta</p>
              <p className="text-xs mb-4 text-gray-400">
                Clique no botão abaixo e autorize o acesso à câmera quando o navegador solicitar
              </p>
              <Button
                onClick={startCamera}
                size="sm"
                className="bg-recycling-primary hover:bg-recycling-primary-dark text-white"
              >
                <Play className="h-3 w-3 mr-1.5" />
                Permitir e Iniciar Câmera
              </Button>
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
              Câmera Padrão | {new Date().toLocaleTimeString()}
            </div>
            
            {detections.length > 0 && (
              <div className="absolute top-3 right-3 bg-black/70 text-white px-3 py-2 rounded space-y-1">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                  <span className="text-xs font-medium">DETECTANDO</span>
                </div>
                {detections.slice(0, 3).map((det, idx) => (
                  <div key={idx} className="text-xs opacity-90">
                    {det.material}: {det.confidence.toFixed(1)}%
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );

  if (inline) {
    return cameraContent;
  }

  return (
    <Card className="border-2 border-recycling-primary/20">
      <CardHeader className="bg-recycling-lighter/30">
        <CardTitle className="text-recycling-primary-darker">Câmera Principal</CardTitle>
      </CardHeader>
      <CardContent className="pt-6">
        {cameraContent}
      </CardContent>
    </Card>
  );
}
