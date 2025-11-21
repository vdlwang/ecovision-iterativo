import { Component, ReactNode } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-neutral-950 flex items-center justify-center p-4">
          <Card className="bg-neutral-900 border-neutral-800 p-8 max-w-md w-full">
            <div className="text-center">
              <div className="text-6xl mb-4">⚠️</div>
              <h2 className="text-white text-xl mb-2">Algo deu errado</h2>
              <p className="text-neutral-400 text-sm mb-6">
                {this.state.error?.message || 'Erro desconhecido'}
              </p>
              <Button
                onClick={() => window.location.reload()}
                className="bg-green-600 hover:bg-green-700 text-white w-full"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Recarregar Página
              </Button>
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
