import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend, LineChart, Line, CartesianGrid } from "recharts";
import { TrendingUp, Package, Zap, AlertTriangle, RefreshCw, Calendar, Activity, Target } from "lucide-react";
import { projectId, publicAnonKey } from "../utils/supabase/info";

interface StatisticsPanelProps {
  isSystemRunning: boolean;
  gateConfigs: { [key: number]: string };
  userToken?: string;
}

interface Stats {
  total: number;
  byMaterial: {
    papel: number;
    metal: number;
    plastico: number;
    vidro: number;
  };
  byGate: {
    '1': number;
    '2': number;
    '3': number;
  };
  avgConfidence: number;
  recentDetections: any[];
  totalSessions: number;
}

export function StatisticsPanel({ isSystemRunning, gateConfigs, userToken }: StatisticsPanelProps) {
  const [stats, setStats] = useState<Stats>({
    total: 0,
    byMaterial: {
      papel: 0,
      metal: 0,
      plastico: 0,
      vidro: 0
    },
    byGate: {
      '1': 0,
      '2': 0,
      '3': 0
    },
    avgConfidence: 0,
    recentDetections: [],
    totalSessions: 0
  });
  
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [loading, setLoading] = useState(false);

  // Carrega estatísticas do banco de dados
  const loadStats = async () => {
    if (!userToken) {
      console.log('[DASHBOARD] Aguardando autenticação... Token não disponível.');
      setLoading(false);
      return;
    }
    
    setLoading(true);
    console.log(`[DASHBOARD] Carregando estatísticas do banco de dados...`);
    console.log(`[DASHBOARD] Token sendo enviado: ${userToken.substring(0, 30)}...`);
    
    try {
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-ea835390/stats`,
        {
          headers: {
            'Authorization': `Bearer ${userToken}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setStats(data.stats);
          setLastUpdate(new Date());
          console.log('[DASHBOARD] Estatísticas carregadas:', data.stats);
        } else {
          console.error('[DASHBOARD] Erro na resposta:', data.error);
        }
      } else {
        const errorText = await response.text();
        console.error('[DASHBOARD] Erro HTTP:', response.status);
        console.error('[DASHBOARD] Detalhes do erro:', errorText);
      }
    } catch (error) {
      console.error('[DASHBOARD] Erro ao carregar estatísticas:', error);
    } finally {
      setLoading(false);
    }
  };

  // Carrega ao montar e a cada 30 segundos se o sistema estiver rodando
  useEffect(() => {
    loadStats();
    
    if (isSystemRunning) {
      const interval = setInterval(loadStats, 30000); // Atualiza a cada 30s
      return () => clearInterval(interval);
    }
  }, [isSystemRunning, userToken]);

  // Prepara dados para gráficos
  const materialChartData = [
    { name: "Papel", value: stats.byMaterial.papel, color: "#163b6f" },
    { name: "Metal", value: stats.byMaterial.metal, color: "#196626" },
    { name: "Plástico", value: stats.byMaterial.plastico, color: "#dc1f2e" },
    { name: "Vidro", value: stats.byMaterial.vidro, color: "#d2b91f" }
  ].filter(item => item.value > 0); // Mostra apenas materiais com detecções

  const gateChartData = [
    { 
      name: `Cancela 1${gateConfigs[1] ? ` (${gateConfigs[1]})` : ''}`, 
      value: stats.byGate['1'],
      color: "#034732"
    },
    { 
      name: `Cancela 2${gateConfigs[2] ? ` (${gateConfigs[2]})` : ''}`, 
      value: stats.byGate['2'],
      color: "#008148"
    },
    { 
      name: `Cancela 3${gateConfigs[3] ? ` (${gateConfigs[3]})` : ''}`, 
      value: stats.byGate['3'],
      color: "#abf2ab"
    }
  ].filter(item => item.value > 0);

  const totalMaterials = stats.byMaterial.papel + stats.byMaterial.metal + 
                         stats.byMaterial.plastico + stats.byMaterial.vidro;
  const efficiency = totalMaterials > 0 ? (totalMaterials / stats.total) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Header com Resumo */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl text-recycling-primary-darker mb-1">Dashboard de Estatísticas</h2>
          <p className="text-sm text-gray-600">
            {lastUpdate ? (
              <>Última atualização: {lastUpdate.toLocaleTimeString()}</>
            ) : (
              'Carregando dados...'
            )}
          </p>
        </div>
        <Button 
          onClick={loadStats} 
          disabled={loading}
          variant="outline"
          className="border-recycling-primary text-recycling-primary hover:bg-recycling-lighter"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </Button>
      </div>

      {/* Cards de Métricas Principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-2 border-recycling-primary/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-recycling-lighter/30">
            <CardTitle className="text-sm">Total Processado</CardTitle>
            <Package className="h-4 w-4 text-recycling-primary" />
          </CardHeader>
          <CardContent className="pt-4">
            <div className="text-3xl text-recycling-primary-darker">{stats.total}</div>
            <p className="text-xs text-gray-600 mt-1">
              {stats.totalSessions} sessões registradas
            </p>
          </CardContent>
        </Card>

        <Card className="border-2 border-material-paper/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-blue-50/30">
            <CardTitle className="text-sm">Papel Detectado</CardTitle>
            <Target className="h-4 w-4 text-material-paper" />
          </CardHeader>
          <CardContent className="pt-4">
            <div className="text-3xl" style={{ color: "#163b6f" }}>{stats.byMaterial.papel}</div>
            <p className="text-xs text-gray-600 mt-1">
              {totalMaterials > 0 ? Math.round((stats.byMaterial.papel / totalMaterials) * 100) : 0}% do total
            </p>
          </CardContent>
        </Card>

        <Card className="border-2 border-material-plastic/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-red-50/30">
            <CardTitle className="text-sm">Plástico Detectado</CardTitle>
            <Target className="h-4 w-4 text-material-plastic" />
          </CardHeader>
          <CardContent className="pt-4">
            <div className="text-3xl text-material-plastic">{stats.byMaterial.plastico}</div>
            <p className="text-xs text-gray-600 mt-1">
              {totalMaterials > 0 ? Math.round((stats.byMaterial.plastico / totalMaterials) * 100) : 0}% do total
            </p>
          </CardContent>
        </Card>

        <Card className="border-2 border-recycling-accent/20">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-green-50/30">
            <CardTitle className="text-sm">Confiança Média</CardTitle>
            <Activity className="h-4 w-4 text-recycling-accent" />
          </CardHeader>
          <CardContent className="pt-4">
            <div className="text-3xl text-recycling-accent">{stats.avgConfidence.toFixed(1)}%</div>
            <Progress 
              value={stats.avgConfidence} 
              className="mt-2"
            />
          </CardContent>
        </Card>
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gráfico de Materiais */}
        <Card className="border-2 border-recycling-primary/20">
          <CardHeader className="bg-recycling-lighter/30">
            <CardTitle className="text-recycling-primary-darker flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Distribuição por Material
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            {materialChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={materialChartData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {materialChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <Package className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Nenhuma detecção registrada</p>
                  <p className="text-xs opacity-75 mt-1">Inicie o sistema para começar a coletar dados</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Gráfico de Cancelas */}
        <Card className="border-2 border-recycling-primary/20">
          <CardHeader className="bg-recycling-lighter/30">
            <CardTitle className="text-recycling-primary-darker flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Acionamentos por Cancela
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            {gateChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={gateChartData}>
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="value" name="Acionamentos">
                    {gateChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <Zap className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">Nenhum acionamento registrado</p>
                  <p className="text-xs opacity-75 mt-1">Configure as cancelas para começar</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Detecções Recentes */}
      <Card className="border-2 border-recycling-primary/20">
        <CardHeader className="bg-recycling-lighter/30">
          <CardTitle className="text-recycling-primary-darker flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Detecções Recentes
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          {stats.recentDetections && stats.recentDetections.length > 0 ? (
            <div className="space-y-2">
              {stats.recentDetections.map((detection, index) => (
                <div 
                  key={detection.id || index} 
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
                >
                  <div className="flex items-center gap-3">
                    <Badge 
                      className="capitalize"
                      style={{ 
                        backgroundColor: {
                          papel: '#163b6f',
                          metal: '#196626',
                          plastico: '#dc1f2e',
                          vidro: '#d2b91f'
                        }[detection.material_detected] || '#gray'
                      }}
                    >
                      {detection.material_detected}
                    </Badge>
                    <span className="text-sm">
                      Confiança: {detection.confidence.toFixed(1)}%
                    </span>
                    <Badge variant="outline">
                      Cancela {detection.gate_number}
                    </Badge>
                    {detection.gate_activated && (
                      <Badge variant="default" className="bg-recycling-accent">
                        Acionada
                      </Badge>
                    )}
                  </div>
                  <span className="text-xs text-gray-500">
                    {new Date(detection.timestamp).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-400">
              <AlertTriangle className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p className="text-sm">Nenhuma detecção recente</p>
              <p className="text-xs opacity-75 mt-1">As detecções aparecerão aqui em tempo real</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Status do Sistema */}
      <Card className="border-2 border-recycling-accent/20">
        <CardHeader className="bg-green-50/30">
          <CardTitle className="text-recycling-primary-darker flex items-center gap-2">
            <Activity className="h-5 w-5 text-recycling-accent" />
            Status do Sistema
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-white rounded-lg border">
              <div className="text-2xl text-recycling-primary-darker">{stats.total}</div>
              <div className="text-xs text-gray-600 mt-1">Total de Inferências</div>
            </div>
            <div className="text-center p-4 bg-white rounded-lg border">
              <div className="text-2xl text-recycling-accent">{stats.avgConfidence.toFixed(1)}%</div>
              <div className="text-xs text-gray-600 mt-1">Precisão Média</div>
            </div>
            <div className="text-center p-4 bg-white rounded-lg border">
              <div className="text-2xl text-recycling-primary-darker">{stats.totalSessions}</div>
              <div className="text-xs text-gray-600 mt-1">Sessões</div>
            </div>
            <div className="text-center p-4 bg-white rounded-lg border">
              <Badge 
                variant={isSystemRunning ? "default" : "secondary"}
                className={isSystemRunning ? "bg-recycling-accent" : ""}
              >
                {isSystemRunning ? "ATIVO" : "PARADO"}
              </Badge>
              <div className="text-xs text-gray-600 mt-2">Status Atual</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
