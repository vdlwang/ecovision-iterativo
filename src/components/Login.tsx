import { useState } from "react";
import { Button } from "./ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Leaf, Chrome, TestTube } from "lucide-react";
import { getSupabaseClient } from "../utils/supabase/client";

const supabase = getSupabaseClient();

export function Login({ onDemoMode }: { onDemoMode?: () => void }) {
  const [isLoading, setIsLoading] = useState(false);

  const handleGoogleLogin = async () => {
    setIsLoading(true);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: window.location.origin,
        }
      });
      
      if (error) {
        console.error("Erro ao fazer login:", error);
        alert("Erro ao fazer login com Google. Por favor, configure o Google OAuth no Supabase ou use o Modo Demo.");
      }
    } catch (error) {
      console.error("Erro inesperado:", error);
      alert("Erro inesperado. Por favor, tente novamente.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoMode = () => {
    if (onDemoMode) {
      onDemoMode();
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-md border-2 border-recycling-primary/20">
        <CardHeader className="text-center space-y-4">
          <div className="flex justify-center">
            <div className="w-20 h-20 bg-recycling-primary rounded-full flex items-center justify-center">
              <Leaf className="w-12 h-12 text-white" />
            </div>
          </div>
          <CardTitle className="text-recycling-primary-darker">
            EcoVision
          </CardTitle>
          <CardDescription>
            Sistema de Controle Inteligente para Centro de Reciclagem
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center text-sm text-muted-foreground mb-4">
            Faça login para acessar o sistema de monitoramento e controle da esteira de reciclagem
          </div>
          
          <Button
            onClick={handleGoogleLogin}
            disabled={isLoading}
            className="w-full bg-white hover:bg-gray-50 text-gray-800 border-2 border-gray-300"
            size="lg"
          >
            {isLoading ? (
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                Conectando...
              </div>
            ) : (
              <div className="flex items-center gap-3">
                <Chrome className="w-5 h-5" />
                Entrar com Google
              </div>
            )}
          </Button>

          <div className="relative my-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-2 text-muted-foreground">Ou</span>
            </div>
          </div>

          <Button
            onClick={handleDemoMode}
            variant="outline"
            className="w-full border-2 border-recycling-primary/30 text-recycling-primary hover:bg-recycling-primary/10"
            size="lg"
          >
            <div className="flex items-center gap-3">
              <TestTube className="w-5 h-5" />
              Entrar em Modo Demo
            </div>
          </Button>

          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-xs text-blue-800 font-semibold mb-2">
              📋 Para configurar o login com Google:
            </p>
            <ol className="text-xs text-blue-700 space-y-1 ml-4 list-decimal">
              <li>Acesse o Dashboard do Supabase</li>
              <li>Vá em Authentication → Providers</li>
              <li>Ative o Google OAuth</li>
              <li>Configure as credenciais do Google Cloud</li>
            </ol>
            <p className="text-xs text-blue-600 mt-2 italic">
              Enquanto isso, use o Modo Demo para testar o sistema!
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
