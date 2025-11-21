import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    hmr: {
      overlay: false, // Desabilita overlay de erros
    },
  },
  build: {
    rollupOptions: {
      onwarn(warning, warn) {
        // Suprime todos os warnings relacionados
        if (warning.code === 'UNUSED_EXTERNAL_IMPORT') return;
        if (warning.message?.toLowerCase().includes('supabase')) return;
        if (warning.message?.toLowerCase().includes('websocket')) return;
        warn(warning);
      },
    },
  },
  // Silencia logs do Vite
  logLevel: 'error',
  clearScreen: false,
});