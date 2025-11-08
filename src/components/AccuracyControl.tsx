import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Slider } from "./ui/slider";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Target, AlertCircle, CheckCircle, Cpu } from "lucide-react";
import { toast } from "sonner@2.0.3";

interface AccuracyControlProps {
  minAccuracy: number;
  onAccuracyChange: (accuracy: number) => void;
  isSystemRunning: boolean;
  modelVersion?: string;
  onModelVersionChange?: (version: string) => void;
}

export function AccuracyControl({ 
  minAccuracy, 
  onAccuracyChange, 
  isSystemRunning,
  modelVersion = "YOLOv8n",
  onModelVersionChange 
}: AccuracyControlProps) {
  const [tempAccuracy, setTempAccuracy] = useState(minAccuracy);
  const [hasChanges, setHasChanges] = useState(false);

  const handleSliderChange = (value: number[]) => {
    const newValue = value[0];
    setTempAccuracy(newValue);
    setHasChanges(newValue !== minAccuracy);
  };

  const handleInputChange = (value: string) => {
    const numValue = parseInt(value);
    if (!isNaN(numValue) && numValue >= 50 && numValue <= 100) {
      setTempAccuracy(numValue);
      setHasChanges(numValue !== minAccuracy);
    }
  };

  const handleSave = () => {
    onAccuracyChange(tempAccuracy);
    setHasChanges(false);
    toast.success(`Confiança mínima definida para ${tempAccuracy}%`);
  };

  const handleReset = () => {
    setTempAccuracy(minAccuracy);
    setHasChanges(false);
  };

  const getAccuracyLevel = (accuracy: number) => {
    if (accuracy >= 90) return { 
      level: "Muito Alta", 
      color: "text-recycling-primary", 
      variant: "default" as const,
      bgClass: "bg-recycling-primary text-white"
    };
    if (accuracy >= 80) return { 
      level: "Alta", 
      color: "text-recycling-accent", 
      variant: "default" as const,
      bgClass: "bg-recycling-accent text-white"
    };
    if (accuracy >= 70) return { 
      level: "Média", 
      color: "text-material-glass", 
      variant: "secondary" as const,
      bgClass: "bg-material-glass text-gray-800"
    };
    return { 
      level: "Baixa", 
      color: "text-material-rejected", 
      variant: "destructive" as const,
      bgClass: "bg-material-rejected text-white"
    };
  };

  const accuracyInfo = getAccuracyLevel(tempAccuracy);

  const getModelInfo = (version: string) => {
    switch(version) {
      case "YOLOv8n":
        return { name: "YOLOv8 Nano", speed: "Muito Rápido", accuracy: "Boa" };
      case "YOLOv8s":
        return { name: "YOLOv8 Small", speed: "Rápido", accuracy: "Muito Boa" };
      case "YOLOv8m":
        return { name: "YOLOv8 Medium", speed: "Moderado", accuracy: "Excelente" };
      default:
        return { name: "YOLOv8 Nano", speed: "Muito Rápido", accuracy: "Boa" };
    }
  };

  return (
    <div className="space-y-6">
      {/* Seleção de Modelo */}
      <Card className="border-2 border-recycling-primary/20">
        <CardHeader className="bg-recycling-lighter/30">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-recycling-primary-darker">
              <Cpu className="h-5 w-5 text-recycling-primary" />
              Versão do Modelo
            </CardTitle>
            {!isSystemRunning && onModelVersionChange && (
              <Button 
                size="sm" 
                onClick={() => {
                  toast.success(`Modelo ${getModelInfo(modelVersion).name} salvo`);
                }}
                className="bg-recycling-primary hover:bg-recycling-primary-dark"
              >
                Salvar
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-recycling-primary-darker">
              Modelo YOLO Ativo
            </label>
            <Select
              value={modelVersion}
              onValueChange={(value) => {
                if (onModelVersionChange && !isSystemRunning) {
                  onModelVersionChange(value);
                  toast.success(`Modelo alterado para ${getModelInfo(value).name}`);
                } else if (isSystemRunning) {
                  toast.error("Pare o sistema antes de alterar o modelo");
                }
              }}
              disabled={isSystemRunning}
            >
              <SelectTrigger className="border-recycling-primary/30">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="YOLOv8n">YOLOv8 Nano (n)</SelectItem>
                <SelectItem value="YOLOv8s">YOLOv8 Small (s)</SelectItem>
                <SelectItem value="YOLOv8m">YOLOv8 Medium (m)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Controle de Confiança */}
      <Card className="border-2 border-recycling-primary/20">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6 bg-recycling-lighter/30">
          <CardTitle className="flex items-center gap-2 text-recycling-primary-darker">
            <Target className="h-5 w-5 text-recycling-primary" />
            Controle de Confiança
          </CardTitle>
        {hasChanges && (
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleReset}>
              Cancelar
            </Button>
            <Button 
              size="sm" 
              onClick={handleSave}
              disabled={isSystemRunning}
              className="bg-recycling-primary hover:bg-recycling-primary-dark disabled:opacity-50"
            >
              Aplicar
            </Button>
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Status atual */}
        <div className="flex items-center justify-between p-4 bg-recycling-lighter/20 rounded-lg border border-recycling-primary/20">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-recycling-primary-darker">Confiança Mínima Atual:</span>
              <Badge className={getAccuracyLevel(minAccuracy).bgClass}>
                {minAccuracy}%
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Detecções com confiança abaixo de {minAccuracy}% são rejeitadas
            </p>
          </div>
          {isSystemRunning ? (
            <CheckCircle className="h-8 w-8 text-recycling-primary" />
          ) : (
            <AlertCircle className="h-8 w-8 text-material-glass" />
          )}
        </div>

        {/* Controle de slider */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="font-medium text-recycling-primary-darker">Confiança Mínima</label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                min="50"
                max="100"
                value={tempAccuracy}
                onChange={(e) => handleInputChange(e.target.value)}
                className="w-20 text-center border-recycling-primary/30 focus:ring-recycling-primary"
                disabled={isSystemRunning}
              />
              <span className="text-sm text-muted-foreground">%</span>
            </div>
          </div>

          <div className="px-2">
            <Slider
              value={[tempAccuracy]}
              onValueChange={handleSliderChange}
              max={100}
              min={50}
              step={1}
              className="w-full [&_[role=slider]]:bg-recycling-primary [&_[role=slider]]:border-recycling-primary-dark"
              disabled={isSystemRunning}
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>50%</span>
              <span>75%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Indicador de nível */}
          <div className="text-center">
            <Badge className={`text-lg px-4 py-2 ${accuracyInfo.bgClass}`}>
              Precisão: {accuracyInfo.level}
            </Badge>
            <p className="text-sm text-muted-foreground mt-2">
              Valor recomendado: 80-90% para melhor equilíbrio entre precisão e produtividade
            </p>
          </div>
        </div>

        {/* Informações sobre o impacto */}
        <div className="bg-recycling-lighter/50 p-4 rounded-lg border border-recycling-primary/20 space-y-2">
          <h4 className="font-medium text-recycling-primary-darker">Impacto da Configuração</h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-recycling-primary">Confiança Alta (90%+):</span>
              <ul className="text-recycling-primary-dark text-xs mt-1 space-y-1">
                <li>• Maior precisão na separação</li>
                <li>• Menos materiais processados</li>
                <li>• Menor chance de contaminação</li>
              </ul>
            </div>
            <div>
              <span className="font-medium text-recycling-primary">Confiança Baixa (50-70%):</span>
              <ul className="text-recycling-primary-dark text-xs mt-1 space-y-1">
                <li>• Mais materiais processados</li>
                <li>• Maior chance de erro</li>
                <li>• Pode precisar de reprocessamento</li>
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
    </div>
  );
}