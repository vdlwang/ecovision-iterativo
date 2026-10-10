import { useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Recycle, Play } from 'lucide-react';
import { toast } from 'sonner@2.0.3';

interface LoginScreenProps {
  onLogin: (user: { name: string; email: string; avatar?: string; isDemo: boolean }) => void;
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [loading, setLoading] = useState(false);

  const handleGoogleLogin = async () => {
    setLoading(true);
    
    try {
      // Simulação de OAuth Google
      // Em produção, substituir por OAuth real do Google
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Simula dados do usuário (em produção, virá do Google OAuth)
      const mockUser = {
        name: 'Usuário Google',
        email: 'usuario@gmail.com',
        avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=google',
        isDemo: false
      };
      
      onLogin(mockUser);
      toast.success('Login realizado com sucesso!');
    } catch (error) {
      toast.error('Erro ao fazer login com Google');
      setLoading(false);
    }
  };

  const handleDemoMode = () => {
    const demoUser = {
      name: 'Modo Demonstração',
      email: 'demo@ecovision.local',
      isDemo: true
    };
    
    onLogin(demoUser);
    toast.success('Modo demonstração ativado!');
  };

  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        {/* Logo e Título */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-green-600 rounded-2xl mb-4">
            <Recycle className="w-12 h-12 text-white" />
          </div>
          <h1 className="text-white text-3xl md:text-4xl mb-2">EcoVision</h1>
          <p className="text-neutral-400">Sistema Inteligente de Reciclagem</p>
          <p className="text-neutral-500 text-sm mt-2">
            Detecção automática de materiais com IA
          </p>
        </div>

        {/* Card de Login */}
        <Card className="bg-neutral-900 border-neutral-800 p-6 md:p-8">
          <div className="space-y-4">
            <div className="text-center mb-6">
              <h2 className="text-white text-xl mb-2">Bem-vindo</h2>
              <p className="text-neutral-400 text-sm">
                Faça login para acessar o sistema
              </p>
            </div>

            {/* Botão Google Login */}
            <Button
              onClick={handleGoogleLogin}
              disabled={loading}
              className="w-full bg-white hover:bg-neutral-100 text-neutral-900 border border-neutral-300"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-neutral-400 border-t-neutral-900 rounded-full animate-spin mr-2" />
                  Conectando...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    />
                  </svg>
                  Continuar com Google
                </>
              )}
            </Button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-neutral-800"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-neutral-900 text-neutral-500">ou</span>
              </div>
            </div>

            {/* Botão Modo Demo */}
            <Button
              onClick={handleDemoMode}
              variant="outline"
              className="w-full bg-neutral-800 border-neutral-700 text-white hover:bg-neutral-700"
            >
              <Play className="w-4 h-4 mr-2" />
              Modo Demonstração
            </Button>

            <p className="text-neutral-500 text-xs text-center mt-4">
              O modo demonstração permite testar o sistema sem autenticação
            </p>
          </div>
        </Card>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
          <div className="p-4">
            <div className="text-3xl mb-2">🎯</div>
            <p className="text-white text-sm">Detecção em Tempo Real</p>
            <p className="text-neutral-500 text-xs mt-1">YOLO + ESP32</p>
          </div>
          <div className="p-4">
            <div className="text-3xl mb-2">♻️</div>
            <p className="text-white text-sm">4 Tipos de Material</p>
            <p className="text-neutral-500 text-xs mt-1">Plástico, Metal, Papel, Vidro</p>
          </div>
          <div className="p-4">
            <div className="text-3xl mb-2">⚡</div>
            <p className="text-white text-sm">Separação Automática</p>
            <p className="text-neutral-500 text-xs mt-1">Servo controlado por IA</p>
          </div>
        </div>
      </div>
    </div>
  );
}
