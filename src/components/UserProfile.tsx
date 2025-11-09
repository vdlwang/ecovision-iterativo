import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { User, Mail, Calendar, Activity, TrendingUp, Package, TestTube } from "lucide-react";
import { projectId, publicAnonKey } from "../utils/supabase/info";

interface UserProfileProps {
  user: any;
  isDemoMode?: boolean;
  userToken?: string;
}

interface UserStats {
  totalSessions: number;
  totalDetections: number;
  totalProcessed: number;
  lastSession: string | null;
  favoriteConfiguration: {
    cancela1: string;
    cancela2: string;
    cancela3: string;
    minAccuracy: number;
    modelVersion: string;
  } | null;
}

export function UserProfile({ user, isDemoMode = false, userToken }: UserProfileProps) {
  const [stats, setStats] = useState<UserStats>({
    totalSessions: 0,
    totalDetections: 0,
    totalProcessed: 0,
    lastSession: null,
    favoriteConfiguration: null
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUserStats();
  }, [user, userToken]);

  const loadUserStats = async () => {
    if (!user?.id) {
      setLoading(false);
      return;
    }
    
    if (!userToken) {
      console.log('[PERFIL] Aguardando token de autenticação... Token não disponível.');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      console.log(`[PERFIL] Carregando estatísticas do usuário ${user.email}`);
      console.log(`[PERFIL] Token sendo enviado: ${userToken.substring(0, 30)}...`);
      
      // Busca estatísticas do usuário no backend
      const response = await fetch(
        `https://${projectId}.supabase.co/functions/v1/make-server-ea835390/user/stats?userId=${user.id}`,
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
          console.log(`[PERFIL] Estatísticas carregadas: ${data.stats.totalSessions} sessões, ${data.stats.totalDetections} detecções`);
        } else {
          console.error('[PERFIL] Erro na resposta:', data.error);
        }
      } else {
        console.error('[PERFIL] Erro HTTP:', response.status);
        const errorData = await response.text();
        console.error('[PERFIL] Detalhes:', errorData);
      }
    } catch (error) {
      console.error('[PERFIL] Erro ao carregar estatísticas:', error);
    } finally {
      setLoading(false);
    }
  };

  const getUserInitials = (email: string) => {
    const parts = email.split('@')[0].split('.');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return email.substring(0, 2).toUpperCase();
  };

  return (
    <div className="space-y-6">
      {/* Informações do Usuário */}
      <Card className="border-2 border-recycling-primary/20">
        <CardHeader className="bg-recycling-lighter/30">
          <CardTitle className="text-recycling-primary-darker">Informações do Perfil</CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
            <Avatar className="w-24 h-24 border-4 border-recycling-primary/20">
              <AvatarImage src={user?.user_metadata?.avatar_url} />
              <AvatarFallback className="text-2xl bg-recycling-primary text-white">
                {getUserInitials(user?.email || '')}
              </AvatarFallback>
            </Avatar>
            
            <div className="flex-1 text-center md:text-left space-y-3">
              <div>
                <h2 className="text-2xl font-semibold text-recycling-primary-darker">
                  {user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Usuário'}
                </h2>
                <div className="flex items-center gap-2 justify-center md:justify-start text-muted-foreground mt-1">
                  <Mail className="h-4 w-4" />
                  <span className="text-sm">{user?.email}</span>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 justify-center md:justify-start">
                <Badge variant="outline" className="border-recycling-primary text-recycling-primary">
                  <User className="h-3 w-3 mr-1" />
                  Usuário Ativo
                </Badge>
                <Badge variant="outline" className="border-recycling-accent text-recycling-accent">
                  <Activity className="h-3 w-3 mr-1" />
                  EcoVision
                </Badge>
                {isDemoMode && (
                  <Badge className="bg-yellow-500 text-white">
                    <TestTube className="h-3 w-3 mr-1" />
                    Modo Demo
                  </Badge>
                )}
              </div>

              {user?.created_at && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground justify-center md:justify-start">
                  <Calendar className="h-4 w-4" />
                  <span>Membro desde {new Date(user.created_at).toLocaleDateString('pt-BR')}</span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Estatísticas do Usuário */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-recycling-primary/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total de Sessões</p>
                <p className="text-2xl font-medium text-recycling-primary-darker">
                  {loading ? '...' : stats.totalSessions}
                </p>
              </div>
              <Activity className="h-8 w-8 text-recycling-primary" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-recycling-primary/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Detecções Realizadas</p>
                <p className="text-2xl font-medium text-recycling-accent">
                  {loading ? '...' : stats.totalDetections}
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-recycling-accent" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-recycling-primary/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Itens Processados</p>
                <p className="text-2xl font-medium text-recycling-primary">
                  {loading ? '...' : stats.totalProcessed}
                </p>
              </div>
              <Package className="h-8 w-8 text-recycling-primary" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Última Sessão */}
      {stats.lastSession && (
        <Card className="border-2 border-recycling-primary/20">
          <CardHeader className="bg-recycling-lighter/30">
            <CardTitle className="text-recycling-primary-darker">Última Sessão</CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>{new Date(stats.lastSession).toLocaleString('pt-BR')}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Configuração Favorita */}
      {stats.favoriteConfiguration && (
        <Card className="border-2 border-recycling-primary/20">
          <CardHeader className="bg-recycling-lighter/30">
            <CardTitle className="text-recycling-primary-darker">Configuração Mais Utilizada</CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground mb-3">Configuração de Cancelas:</p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2 bg-recycling-lighter/20 rounded">
                    <span className="text-sm">Cancela 1:</span>
                    <Badge className="bg-material-paper text-white">
                      {stats.favoriteConfiguration.cancela1}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-recycling-lighter/20 rounded">
                    <span className="text-sm">Cancela 2:</span>
                    <Badge className="bg-material-plastic text-white">
                      {stats.favoriteConfiguration.cancela2}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-recycling-lighter/20 rounded">
                    <span className="text-sm">Cancela 3:</span>
                    <Badge className="bg-material-metal text-white">
                      {stats.favoriteConfiguration.cancela3}
                    </Badge>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-sm text-muted-foreground mb-3">Parâmetros do Modelo:</p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between p-2 bg-recycling-lighter/20 rounded">
                    <span className="text-sm">Confiança Mínima:</span>
                    <span className="font-medium text-recycling-primary">
                      {stats.favoriteConfiguration.minAccuracy}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2 bg-recycling-lighter/20 rounded">
                    <span className="text-sm">Versão do Modelo:</span>
                    <span className="font-medium text-recycling-primary">
                      {stats.favoriteConfiguration.modelVersion}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Histórico de Execuções */}
      <Card className="border-2 border-recycling-primary/20">
        <CardHeader className="bg-recycling-lighter/30">
          <CardTitle className="text-recycling-primary-darker">Histórico de Execuções</CardTitle>
        </CardHeader>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground text-center py-8">
            Histórico detalhado em desenvolvimento. Em breve você poderá visualizar todas as suas sessões anteriores.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
