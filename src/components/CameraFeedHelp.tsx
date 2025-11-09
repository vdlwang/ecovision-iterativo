// Camera Permission Help Component
export function CameraFeedHelp() {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
      <h4 className="font-semibold text-blue-900 text-sm mb-2">💡 Como resolver problemas de câmera:</h4>
      <ul className="text-xs text-blue-800 space-y-1.5 list-disc list-inside">
        <li>Verifique se você está acessando via <strong>HTTPS</strong> ou <strong>localhost</strong></li>
        <li>Clique no ícone de <strong>cadeado/câmera</strong> ao lado da URL no navegador</li>
        <li>Selecione "<strong>Permitir</strong>" para câmera nas configurações do site</li>
        <li>Recarregue a página após alterar as permissões</li>
        <li>Se estiver usando Chrome, vá em Configurações → Privacidade → Configurações de site → Câmera</li>
        <li>Em dispositivos móveis, verifique as permissões do navegador nas configurações do sistema</li>
      </ul>
    </div>
  );
}
