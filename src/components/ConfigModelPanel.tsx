import { useEffect, useState } from 'react';
import { Card } from './ui/card';
import { Label } from './ui/label';
import { Input } from './ui/input';
import { Slider } from './ui/slider';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Save, RefreshCw } from 'lucide-react';
import { toast } from 'sonner@2.0.3';
import { useStableWebSocket } from '../hooks/useStableWebSocket';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';

export function ConfigModelPanel() {
  const [confidence, setConfidence] = useState(0.4);
  const [modelType, setModelType] = useState('yolov8s');
  const [modelPath, setModelPath] = useState('');
  const [serialPort, setSerialPort] = useState('COM8');
  const [baudRate, setBaudRate] = useState(115200);
  const [cameraIndex, setCameraIndex] = useState(0);
  const [connected, setConnected] = useState(false);
  const { connected: wsConnected, send } = useStableWebSocket('ws://localhost:8765', {
    onMessage: (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'config') {
          if (data.confidence !== undefined) setConfidence(data.confidence);
          if (data.model_path) setModelPath(data.model_path);
          if (data.serial_port) setSerialPort(data.serial_port);
          if (data.baud_rate) setBaudRate(data.baud_rate);
          if (data.camera_index !== undefined) setCameraIndex(data.camera_index);
        }
      } catch (error) {
        // Silencioso
      }
    },
  });

  useEffect(() => {
    setConnected(wsConnected);
    if (wsConnected) {
      send({ type: 'get_config' });
    }
  }, [wsConnected, send]);

  const handleModelTypeChange = (value: string) => {
    setModelType(value);
    setModelPath(`../yolo_models/taco/${value}.pt`);
  };

  const saveConfiguration = () => {
    const config = {
      type: 'save_config',
      confidence: confidence,
      model_path: modelPath,
      serial_port: serialPort,
      baud_rate: baudRate,
      camera_index: cameraIndex,
    };

    if (send(config)) {
      toast.success('Configuração salva! Reinicie o backend para aplicar.');
    } else {
      try {
        localStorage.setItem('ecovision_config_model', JSON.stringify(config));
        toast.success('Configuração salva localmente! Inicie o backend para aplicar.');
      } catch (error) {
        toast.error('Erro ao salvar');
      }
    }
  };

  const testConnection = () => {
    if (send({ command: 'MOTOR ON' })) {
      setTimeout(() => {
        send({ command: 'MOTOR OFF' });
      }, 2000);
      toast.success('Teste de conexão enviado! Verifique o motor.');
    } else {
      toast.error('Backend desconectado');
    }
  };

  return (
    <div className="p-4 md:p-8 space-y-4 md:space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-white text-xl md:text-2xl mb-1 md:mb-2">Configuração do Modelo</h2>
          <p className="text-neutral-400 text-sm md:text-base">Configure modelo YOLO, confiança e hardware</p>
        </div>
        <Badge variant="outline" className={`${connected ? 'bg-green-600/20 text-green-600 border-green-600/30' : 'bg-red-600/20 text-red-600 border-red-600/30'}`}>
          {connected ? 'Backend Conectado' : 'Backend Offline'}
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        <div className="space-y-4 md:space-y-6">
          <Card className="bg-neutral-900 border-neutral-800 p-4 md:p-6">
            <h3 className="text-white mb-3 md:mb-4 text-base md:text-lg">Configuração do Modelo YOLO</h3>
            
            <div className="space-y-4">
              <div>
                <Label className="text-neutral-300 mb-2 block text-sm md:text-base">
                  Tipo de Modelo
                </Label>
                <Select value={modelType} onValueChange={handleModelTypeChange}>
                  <SelectTrigger className="bg-neutral-800 border-neutral-700 text-white">
                    <SelectValue placeholder="Selecione o modelo" />
                  </SelectTrigger>
                  <SelectContent className="bg-neutral-800 border-neutral-700">
                    <SelectItem value="yolov8n" className="text-white">YOLOv8 Nano (mais rápido)</SelectItem>
                    <SelectItem value="yolov8s" className="text-white">YOLOv8 Small (balanceado)</SelectItem>
                    <SelectItem value="yolov8m" className="text-white">YOLOv8 Medium</SelectItem>
                    <SelectItem value="yolov8l" className="text-white">YOLOv8 Large</SelectItem>
                    <SelectItem value="yolov8x" className="text-white">YOLOv8 XLarge (mais preciso)</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-neutral-500 text-xs mt-1">
                  Modelos maiores são mais precisos mas mais lentos
                </p>
              </div>

              <div>
                <Label htmlFor="model-path" className="text-neutral-300 mb-2 block text-sm md:text-base">
                  Caminho do Modelo
                </Label>
                <Input
                  id="model-path"
                  value={modelPath}
                  onChange={(e) => setModelPath(e.target.value)}
                  placeholder="../yolo_models/taco/best.pt"
                  className="bg-neutral-800 border-neutral-700 text-white"
                />
                <p className="text-neutral-500 text-xs mt-1">
                  Caminho relativo para o arquivo .pt do modelo treinado
                </p>
              </div>

              <div>
                <Label htmlFor="confidence" className="text-neutral-300 mb-2 block text-sm md:text-base">
                  Confiança Mínima: {(confidence * 100).toFixed(0)}%
                </Label>
                <Slider
                  id="confidence"
                  min={0}
                  max={1}
                  step={0.05}
                  value={[confidence]}
                  onValueChange={([value]) => setConfidence(value)}
                  className="w-full"
                />
                <p className="text-neutral-500 text-xs mt-1">
                  Detecções abaixo deste valor serão ignoradas
                </p>
              </div>
            </div>
          </Card>

          <Card className="bg-neutral-900 border-neutral-800 p-4 md:p-6">
            <h3 className="text-white mb-3 md:mb-4 text-base md:text-lg">Conexão Serial (ESP32)</h3>
            
            <div className="space-y-4">
              <div>
                <Label htmlFor="serial-port" className="text-neutral-300 mb-2 block text-sm md:text-base">
                  Porta Serial
                </Label>
                <Input
                  id="serial-port"
                  value={serialPort}
                  onChange={(e) => setSerialPort(e.target.value)}
                  placeholder="COM8 ou /dev/ttyUSB0"
                  className="bg-neutral-800 border-neutral-700 text-white"
                />
                <p className="text-neutral-500 text-xs mt-1">
                  Windows: COMx | Linux/Mac: /dev/ttyUSBx
                </p>
              </div>

              <div>
                <Label htmlFor="baud-rate" className="text-neutral-300 mb-2 block text-sm md:text-base">
                  Baud Rate
                </Label>
                <Input
                  id="baud-rate"
                  type="number"
                  value={baudRate}
                  onChange={(e) => setBaudRate(parseInt(e.target.value))}
                  className="bg-neutral-800 border-neutral-700 text-white"
                />
                <p className="text-neutral-500 text-xs mt-1">
                  Padrão: 115200
                </p>
              </div>

              <Button
                onClick={testConnection}
                variant="outline"
                className="w-full bg-neutral-800 border-neutral-700 text-white hover:bg-neutral-700"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Testar Conexão Serial
              </Button>
            </div>
          </Card>

          <Card className="bg-neutral-900 border-neutral-800 p-4 md:p-6">
            <h3 className="text-white mb-3 md:mb-4 text-base md:text-lg">Configuração da Câmera</h3>
            
            <div>
              <Label htmlFor="camera-index" className="text-neutral-300 mb-2 block text-sm md:text-base">
                Índice da Câmera
              </Label>
              <Input
                id="camera-index"
                type="number"
                value={cameraIndex}
                onChange={(e) => setCameraIndex(parseInt(e.target.value))}
                className="bg-neutral-800 border-neutral-700 text-white"
              />
              <p className="text-neutral-500 text-xs mt-1">
                Geralmente 0 (primeira câmera). Tente 1, 2 se não funcionar
              </p>
            </div>
          </Card>

          <Button
            onClick={saveConfiguration}
            className="w-full bg-green-600 hover:bg-green-700 text-white"
          >
            <Save className="w-4 h-4 mr-2" />
            Salvar Configuração
          </Button>

          <p className="text-neutral-500 text-xs text-center">
            Reinicie o backend após salvar para aplicar as mudanças
          </p>
        </div>
      </div>
    </div>
  );
}