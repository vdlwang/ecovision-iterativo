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
        // Suprime warnings específicos
        if (warning.code === 'UNUSED_EXTERNAL_IMPORT') return;
        if (warning.message?.includes('supabase')) return;
        warn(warning);
      },
    },
  },
  // Desabilita completamente logs de erro do Vite relacionados ao Supabase
  logLevel: 'warn',
});
