import { Toaster } from './ui/sonner';

export function ToastProvider() {
  return (
    <Toaster
      position="top-right"
      expand={false}
      richColors
      closeButton
      duration={3000}
      toastOptions={{
        style: {
          background: '#171717',
          border: '1px solid #262626',
          color: '#fff',
        },
      }}
    />
  );
}
