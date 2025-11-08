import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Progress } from "./ui/progress";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from "recharts";
import { TrendingUp, Package, Zap, AlertTriangle, RefreshCw, Calendar } from "lucide-react";
import { projectId, publicAnonKey } from "../utils/supabase/info";

interface StatisticsPanelProps {
  isSystemRunning: boolean;
  gateConfigs: { [key: number]: string };
  userId: string;
}

export function StatisticsPanel({ isSystemRunning, gateConfigs, userId }: StatisticsPanelProps) {
  const [stats, setStats] = useState({
    totalProcessed: 0,
    totalSeparated: 0,
    totalRejected: 0,
    materialCounts: {
      papel: 0,
      metal: 0,
      plastico: 0,
      vidro: 0
    },
    gateCounts: {
      1: 0,
      2: 0,
      3: 0
    },
    efficiency: 0,
    uptime: 0
  });
  
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [loading, setLoading] = useState(false);

  const [dailyData, setDailyData] = useState([
    { hora: "08:00", processados: 45, separados: 38 },
    { hora: "09:00", processados: 52, separados: 46 },
    { hora: "10:00", processados: 48, separados: 42 },
    { hora: "11:00", processados: 61, separados: 55 },
    { hora: "12:00", processados: 35, separados: 31 },
    { hora: "13:00", processados: 58, separados: 52 },
    { hora: "14:00", processados: 67, separados: 59 }
  ]);

  // Carrega estatísticas do banco de dados
  const loadStats = async () => {
    if (!userId) return;
    
    setLoading(true);
    console.log(`[DASHBOARD] Carregando estatísticas para usuário ${userId}`);
    
    try {
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-ea835390/dashboard/stats?userId=${userId}`,
        {
          headers: {
            'Authorization': `Bearer ${publicAnonKey}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setStats(data.stats);
          setLastUpdate(new Date());
          console.log('[DASHBOARD] Estatísticas atualizadas');
        }
      }
    } catch (error) {
      console.error('[DASHBOARD] Erro ao carregar estatísticas:', error);
    } finally {
      setLoading(false);
    }
  };

  // Carrega estatísticas ao montar e quando sistema estiver rodando
  useEffect(() => {
    loadStats();
    
    if (isSystemRunning) {
      const interval = setInterval(loadStats, 10000); // Atualiza a cada 10 segundos
      return () => clearInterval(interval);
    }
  }, [userId, isSystemRunning]);

  const pieData = [
    { name: "Papel/Papelão", value: stats.materialCounts.papel, color: "#163b6f" },
    { name: "Metal", value: stats.materialCounts.metal, color: "#196626" },
    { name: "Plástico", value: stats.materialCounts.plastico, color: "#dc1f2e" },
    { name: "Vidro", value: stats.materialCounts.vidro, color: "#d2b91f" }
  ].filter(item => item.value > 0);

  const materialColors = {
    papel: { bg: "bg-material-paper", text: "text-white" },
    metal: { bg: "bg-material-metal", text: "text-white" },
    plastico: { bg: "bg-material-plastic", text: "text-white" },
    vidro: { bg: "bg-material-glass", text: "text-gray-800" }
  };

  const getMaterialColor = (material: string) => {
    return materialColors[material as keyof typeof materialColors] || { bg: "bg-gray-500", text: "text-white" };
  };

  return (
    <div className="space-y-6">
      {/* Header com última atualização e botão refresh */}
      <Card className="border-2 border-recycling-primary/20">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>
                Última atualização: {lastUpdate ? lastUpdate.toLocaleString('pt-BR') : 'Carregando...'}
              </span>
            </div>
            <Button
              onClick={loadStats}
              disabled={loading}
              variant="outline"
              size="sm"
              className="border-recycling-primary text-recycling-primary hover:bg-recycling-lighter/30"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Atualizar
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Cards de estatísticas principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-recycling-primary/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Processado</p>
                <p className="text-2xl font-medium text-recycling-primary-darker">{stats.totalProcessed}</p>
              </div>
              <Package className="h-8 w-8 text-recycling-primary" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-recycling-primary/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Separados</p>
                <p className="text-2xl font-medium text-recycling-primary">{stats.totalSeparated}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-recycling-primary" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-recycling-primary/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Rejeitados</p>
                <p className="text-2xl font-medium text-material-rejected">{stats.totalRejected}</p>
              </div>
              <AlertTriangle className="h-8 w-8 text-material-rejected" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-recycling-primary/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Eficiência</p>
                <p className="text-2xl font-medium text-recycling-accent">{stats.efficiency}%</p>
              </div>
              <Zap className="h-8 w-8 text-recycling-accent" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gráfico de barras - Performance por hora */}
        <Card className="border-recycling-primary/20">
          <CardHeader className="bg-recycling-lighter/30">
            <CardTitle className="text-recycling-primary-darker">Performance por Hora</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Legenda de cores */}
            <div className="mb-4 pb-4 border-b border-recycling-primary/20">
              <div className="flex justify-center gap-6">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: "#abf2ab" }}></div>
                  <span className="text-sm text-recycling-primary-darker">Processados</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded" style={{ backgroundColor: "#008148" }}></div>
                  <span className="text-sm text-recycling-primary-darker">Separados</span>
                </div>
              </div>
            </div>
            
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dailyData}>
                  <XAxis dataKey="hora" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="processados" fill="#abf2ab" name="Processados" />
                  <Bar dataKey="separados" fill="#008148" name="Separados" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Gráfico de pizza - Distribuição por material */}
        <Card className="border-recycling-primary/20">
          <CardHeader className="bg-recycling-lighter/30">
            <CardTitle className="text-recycling-primary-darker">Distribuição por Material</CardTitle>
            {/* Legenda superior */}
            <div className="flex flex-wrap justify-center gap-4 mt-3">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: "#163b6f" }}></div>
                <span className="text-xs text-recycling-primary-darker">Papel/Papelão</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: "#196626" }}></div>
                <span className="text-xs text-recycling-primary-darker">Metal</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: "#dc1f2e" }}></div>
                <span className="text-xs text-recycling-primary-darker">Plástico</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: "#d2b91f" }}></div>
                <span className="text-xs text-recycling-primary-darker">Vidro</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  <p>Nenhum dado disponível ainda</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detalhamento das cancelas */}
      <Card className="border-recycling-primary/20">
        <CardHeader className="bg-recycling-lighter/30">
          <CardTitle className="text-recycling-primary-darker">Performance das Cancelas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((gateNumber) => {
              const material = gateConfigs[gateNumber];
              const count = stats.gateCounts[gateNumber as keyof typeof stats.gateCounts];
              const percentage = stats.totalSeparated > 0 
                ? Math.round((count / stats.totalSeparated) * 100) 
                : 0;
              const materialColor = material ? getMaterialColor(material) : null;

              return (
                <div key={gateNumber} className="text-center space-y-3">
                  <h4 className="font-medium text-recycling-primary-darker">Cancela {gateNumber}</h4>
                  <Badge 
                    className={materialColor 
                      ? `${materialColor.bg} ${materialColor.text} border-none` 
                      : "bg-gray-300 text-gray-600"
                    }
                  >
                    {material || "Não configurado"}
                  </Badge>
                  <div className="space-y-2">
                    <div className="text-2xl font-medium text-recycling-primary-darker">{count}</div>
                    <div className="text-sm text-muted-foreground">itens separados</div>
                    <Progress 
                      value={percentage} 
                      className="w-full [&>div]:bg-recycling-primary" 
                    />
                    <div className="text-xs text-muted-foreground">{percentage}% do total</div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}