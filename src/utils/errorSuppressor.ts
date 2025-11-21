// Supressão global de erros não tratados
if (typeof window !== 'undefined') {
  // Suprime erros do WebSocket
  const originalError = window.console.error;
  window.console.error = (...args: any[]) => {
    const message = args[0]?.toString() || '';
    
    // Lista de padrões a ignorar
    const ignorePatterns = [
      'WebSocket',
      'ws://',
      'wss://',
      'isTrusted',
      'supabase',
      'edge_functions',
      'status 544',
      'XHR',
      'deploy'
    ];
    
    // Verifica se deve ignorar
    if (ignorePatterns.some(pattern => message.toLowerCase().includes(pattern.toLowerCase()))) {
      return; // Silencia
    }
    
    // Mantém outros erros
    originalError.apply(console, args);
  };

  // Suprime avisos do WebSocket
  const originalWarn = window.console.warn;
  window.console.warn = (...args: any[]) => {
    const message = args[0]?.toString() || '';
    
    if (message.includes('WebSocket') || message.includes('ws://')) {
      return; // Silencia
    }
    
    originalWarn.apply(console, args);
  };

  // Captura erros não tratados
  window.addEventListener('error', (event) => {
    const message = event.message?.toLowerCase() || '';
    
    if (
      message.includes('websocket') ||
      message.includes('supabase') ||
      message.includes('544')
    ) {
      event.preventDefault();
      event.stopPropagation();
      return false;
    }
  });

  // Captura rejeições de promises não tratadas
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason?.toString()?.toLowerCase() || '';
    
    if (
      reason.includes('websocket') ||
      reason.includes('supabase') ||
      reason.includes('544')
    ) {
      event.preventDefault();
      return false;
    }
  });
}

export {};
