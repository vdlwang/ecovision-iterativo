import { Badge } from './ui/badge';

// Estado da conexão com o backend, igual em todos os painéis
export function BadgeBackend({ connected }: { connected: boolean }) {
  return (
    <Badge variant="outline" className={`${connected ? 'bg-green-600/20 text-green-600 border-green-600/30' : 'bg-red-600/20 text-red-600 border-red-600/30'}`}>
      {connected ? 'Backend Conectado' : 'Backend Offline'}
    </Badge>
  );
}
