import { useEffect, useState } from 'react';
import { Card } from './ui/card';
import { Label } from './ui/label';
import { Slider } from './ui/slider';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { RotateCw, Save } from 'lucide-react';
import { toast } from 'sonner@2.0.3';
import { useStableWebSocket } from '../hooks/useStableWebSocket';

interface MaterialConfig {
  name: string;
  key: string;
  servoAngle: number;
  icon: string;
  color: string;
}

export function ConfigGatesPanel() {
  // Chaves e ângulos padrão iguais aos de load_config() no backend
  const [materials, setMaterials] = useState<MaterialConfig[]>([
    { name: 'Plástico', key: 'plastic', servoAngle: 50, icon: '🥤', color: 'bg-red-600' },
    { name: 'Metal', key: 'metal', servoAngle: 150, icon: '🔩', color: 'bg-yellow-600' },
    { name: 'Vidro', key: 'glass', servoAngle: 130, icon: '🍷', color: 'bg-blue-600' },
    { name: 'Papel', key: 'paper', servoAngle: 110, icon: '📄', color: 'bg-blue-600' },
  ]);

  const [connected, setConnected] = useState(false);
  const { connected: wsConnected, send } = useStableWebSocket('ws://localhost:8765', {
    onMessage: (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'config' && data.class_to_angle) {
          // Atualizar ângulos com dados do backend
          const newMaterials = materials.map(m => ({
            ...m,
            servoAngle: data.class_to_angle[m.key] ?? m.servoAngle
          }));
          setMaterials(newMaterials);
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

  const updateMaterialAngle = (index: number, angle: number) => {
    const newMaterials = [...materials];
    newMaterials[index].servoAngle = angle;
    setMaterials(newMaterials);
  };

  const testServo = (angle: number, materialName: string) => {
    if (send({ command: angle.toString() })) {
      toast.success(`Testando ${materialName}: servo → ${angle}°`);
    } else {
      toast.error('Backend desconectado. Execute: python backend/ecovision_local_modf.py');
    }
  };

  const saveConfiguration = () => {
    const config = {
      type: 'save_config',
      class_to_angle: materials.reduce((acc, m) => {
        acc[m.key] = m.servoAngle;
        return acc;
      }, {} as Record<string, number>),
    };

    if (send(config)) {
      toast.success('Configuração salva! Os ângulos já estão valendo.');
    } else {
      toast.error('Backend desconectado: a configuração não foi salva.');
    }
  };

  return (
    <div className="p-4 md:p-8 space-y-4 md:space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-white text-xl md:text-2xl mb-1 md:mb-2">Cancelas de Separação</h2>
          <p className="text-neutral-400 text-sm md:text-base">Configure o ângulo do servo para direcionar cada material</p>
        </div>
        <Badge variant="outline" className={`${connected ? 'bg-green-600/20 text-green-600 border-green-600/30' : 'bg-red-600/20 text-red-600 border-red-600/30'}`}>
          {connected ? 'Backend Conectado' : 'Backend Offline'}
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        <div className="space-y-4 md:space-y-6">
          <Card className="bg-neutral-900 border-neutral-800 p-4 md:p-6">
            <h3 className="text-white mb-3 md:mb-4 text-base md:text-lg">Mapeamento Material → Servo</h3>
            <p className="text-neutral-400 text-xs md:text-sm mb-4 md:mb-6">
              Configure o ângulo (0-180°) do servo para cada material. 
              Quando detectado, o servo move para direcionar o item à cancela correta.
            </p>

            <div className="space-y-4 md:space-y-6">
              {materials.map((material, index) => (
                <div key={index} className="p-3 md:p-4 bg-neutral-800 rounded-lg">
                  <div className="flex items-center gap-3 mb-3 md:mb-4">
                    <div className={`w-10 h-10 md:w-12 md:h-12 ${material.color}/20 rounded-lg flex items-center justify-center text-xl md:text-2xl flex-shrink-0`}>
                      {material.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm md:text-base">{material.name}</p>
                      <p className="text-neutral-400 text-xs md:text-sm">
                        Ângulo: {material.servoAngle}°
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => testServo(material.servoAngle, material.name)}
                      className="bg-neutral-700 border-neutral-600 text-white hover:bg-neutral-600 text-xs md:text-sm flex-shrink-0"
                    >
                      <RotateCw className="w-3 h-3 md:w-4 md:h-4 md:mr-2" />
                      <span className="hidden md:inline">Testar</span>
                    </Button>
                  </div>

                  <div>
                    <Label className="text-neutral-300 text-xs md:text-sm mb-2 block">
                      Posição do Servo
                    </Label>
                    <Slider
                      min={0}
                      max={180}
                      step={5}
                      value={[material.servoAngle]}
                      onValueChange={([value]) => updateMaterialAngle(index, value)}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-neutral-500 mt-1">
                      <span>0°</span>
                      <span>90°</span>
                      <span>180°</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Button
            onClick={saveConfiguration}
            disabled={!connected}
            className="w-full bg-green-600 hover:bg-green-700 text-white"
          >
            <Save className="w-4 h-4 mr-2" />
            Salvar Configuração
          </Button>

          <p className="text-neutral-500 text-xs text-center">
            {connected
              ? 'Os ângulos passam a valer assim que a configuração é salva'
              : 'Backend offline: os valores acima são os padrões, não os do config.json. Inicie o backend para carregar e salvar.'}
          </p>
        </div>
      </div>
    </div>
  );
}