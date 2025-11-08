import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Settings, Save } from "lucide-react";
import { toast } from "sonner@2.0.3";

interface GateConfigurationProps {
  gateConfigs: { [key: number]: string };
  onConfigChange: (configs: { [key: number]: string }) => void;
  isSystemRunning?: boolean;
}

const materialOptions = [
  { value: "papel", label: "Papel/Papelão", color: "bg-material-paper", textColor: "text-white" },
  { value: "metal", label: "Metal", color: "bg-material-metal", textColor: "text-white" },
  { value: "plastico", label: "Plástico", color: "bg-material-plastic", textColor: "text-white" },
  { value: "vidro", label: "Vidro", color: "bg-material-glass", textColor: "text-gray-800" },
  { value: "none", label: "Não configurado", color: "bg-gray-300", textColor: "text-gray-600" }
];

export function GateConfiguration({ gateConfigs, onConfigChange, isSystemRunning = false }: GateConfigurationProps) {
  // Normaliza valores vazios/undefined para "none" no estado inicial
  const normalizeConfigs = (configs: { [key: number]: string }) => {
    return {
      1: configs[1] || "none",
      2: configs[2] || "none",
      3: configs[3] || "none",
    };
  };
  
  const [tempConfigs, setTempConfigs] = useState(normalizeConfigs(gateConfigs));
  const [hasChanges, setHasChanges] = useState(false);

  const handleConfigChange = (gateNumber: number, material: string) => {
    const newConfigs = {
      ...tempConfigs,
      [gateNumber]: material
    };
    setTempConfigs(newConfigs);
    setHasChanges(JSON.stringify(newConfigs) !== JSON.stringify(tempConfigs));
  };

  const handleSave = () => {
    // Validar se não há materiais duplicados (exceto "none")
    const assignedMaterials = Object.values(tempConfigs).filter(material => material !== "none");
    const uniqueMaterials = new Set(assignedMaterials);
    
    if (assignedMaterials.length !== uniqueMaterials.size) {
      toast.error("Cada material pode ser atribuído a apenas uma cancela!");
      return;
    }

    // Converte "none" de volta para "" antes de salvar
    const configsToSave = {
      1: tempConfigs[1] === "none" ? "" : tempConfigs[1],
      2: tempConfigs[2] === "none" ? "" : tempConfigs[2],
      3: tempConfigs[3] === "none" ? "" : tempConfigs[3],
    };
    
    onConfigChange(configsToSave);
    setHasChanges(false);
    toast.success("Configuração salva com sucesso!");
  };

  const handleReset = () => {
    setTempConfigs(normalizeConfigs(gateConfigs));
    setHasChanges(false);
  };

  const getMaterialInfo = (material: string) => {
    return materialOptions.find(option => option.value === material) || materialOptions[4];
  };

  return (
    <Card className="border-2 border-recycling-primary/20">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6 bg-recycling-lighter/30">
        <CardTitle className="flex items-center gap-2 text-recycling-primary-darker">
          <Settings className="h-5 w-5 text-recycling-primary" />
          Configuração das Cancelas
        </CardTitle>
        {hasChanges && (
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleReset}>
              Cancelar
            </Button>
            <Button size="sm" onClick={handleSave} className="bg-recycling-primary hover:bg-recycling-primary-dark">
              <Save className="h-4 w-4 mr-2" />
              Salvar
            </Button>
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((gateNumber) => {
            const currentMaterial = tempConfigs[gateNumber] || "none";
            const materialInfo = getMaterialInfo(currentMaterial);
            const selectValue = currentMaterial;
            
            return (
              <div key={gateNumber} className="space-y-4">
                <div className="text-center">
                  <h3 className="font-medium mb-2 text-recycling-primary-darker">Cancela {gateNumber}</h3>
                  <div 
                    className={`w-20 h-20 mx-auto rounded-lg flex items-center justify-center ${materialInfo.color} ${materialInfo.textColor} mb-3 border-2 border-recycling-primary/20 shadow-md`}
                  >
                    <span className="text-2xl font-medium">{gateNumber}</span>
                  </div>
                  <Badge 
                    variant={currentMaterial !== "none" ? "default" : "secondary"}
                    className={currentMaterial !== "none" ? "bg-recycling-accent text-white" : ""}
                  >
                    {materialInfo.label}
                  </Badge>
                </div>
                
                <Select 
                  value={selectValue} 
                  onValueChange={(value) => handleConfigChange(gateNumber, value)}
                >
                  <SelectTrigger className="border-recycling-primary/30 focus:ring-recycling-primary">
                    <SelectValue placeholder="Selecione o material" />
                  </SelectTrigger>
                  <SelectContent>
                    {materialOptions.map((option) => {
                      // Verifica se o material já está sendo usado por outra cancela (exceto "none")
                      const isUsedElsewhere = option.value !== "none" && 
                        Object.entries(tempConfigs).some(
                          ([gate, material]) => 
                            parseInt(gate) !== gateNumber && material === option.value && material !== "none"
                        );
                      
                      return (
                        <SelectItem 
                          key={option.value} 
                          value={option.value || "none-fallback"}
                          disabled={isUsedElsewhere}
                        >
                          <div className="flex items-center gap-2">
                            <div 
                              className={`w-3 h-3 rounded-full ${option.color} border border-gray-400`} 
                            />
                            {option.label}
                            {isUsedElsewhere && (
                              <span className="text-xs text-muted-foreground ml-2">
                                (Em uso)
                              </span>
                            )}
                          </div>
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
              </div>
            );
          })}
        </div>
        
        <div className="mt-8 p-4 bg-recycling-lighter/50 rounded-lg border border-recycling-primary/20">
          <h4 className="font-medium mb-2 text-recycling-primary-darker">Tipos de Materiais</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {materialOptions.slice(0, 4).map((option) => (
              <div key={option.value} className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${option.color} border border-gray-400`} />
                <span className="text-sm text-recycling-primary-darker">{option.label}</span>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Cada material pode ser atribuído a apenas uma cancela. 
            As cancelas não configuradas não serão acionadas.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}