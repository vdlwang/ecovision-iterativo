# 🎥 Troubleshooting de Câmera - EcoVision

## ❌ Erro: "Permissão de câmera negada"

### Causa
Você clicou em "Bloquear" quando o navegador pediu permissão, ou a permissão foi bloqueada anteriormente.

### Solução Passo a Passo

#### Chrome/Edge:
```
1. Clique no ícone de cadeado 🔒 ao lado da URL
2. Clique em "Configurações do site"
3. Encontre "Câmera"
4. Mude de "Bloquear" para "Permitir"
5. Recarregue a página (F5)
6. Clique em "Iniciar Sistema"
7. ✅ Deve funcionar agora!
```

#### Firefox:
```
1. Clique no ícone de cadeado 🔒 ao lado da URL
2. Clique em "Mais informações"
3. Vá em "Permissões"
4. Encontre "Usar a câmera"
5. Desmarque "Usar padrão" e marque "Permitir"
6. Recarregue a página (F5)
7. Clique em "Iniciar Sistema"
8. ✅ Deve funcionar agora!
```

#### Safari:
```
1. Vá em Safari > Preferências
2. Clique em "Sites"
3. Selecione "Câmera" na barra lateral
4. Encontre seu site na lista
5. Mude para "Permitir"
6. Recarregue a página (F5)
7. Clique em "Iniciar Sistema"
8. ✅ Deve funcionar agora!
```

---

## ❌ Erro: "Nenhuma câmera encontrada"

### Possíveis Causas:
1. Webcam não está conectada
2. Drivers da câmera não instalados
3. Outra aplicação está usando a câmera
4. Câmera desabilitada no sistema

### Solução:

#### 1. Verificar Conexão:
```
- Webcam USB: Verifique se está conectada
- Notebook: Certifique-se que câmera integrada não está desabilitada
- Teste em outro app (Zoom, Skype, etc)
```

#### 2. Verificar Drivers (Windows):
```
1. Pressione Win + X
2. Selecione "Gerenciador de Dispositivos"
3. Expanda "Câmeras" ou "Dispositivos de imagem"
4. Veja se há algum ícone de erro (⚠️)
5. Se houver, clique direito > "Atualizar driver"
```

#### 3. Fechar Outras Aplicações:
```
Aplicações que podem estar usando a câmera:
- Zoom
- Skype
- Microsoft Teams
- Discord
- OBS Studio
- Outros navegadores

Feche TODAS antes de usar o EcoVision
```

#### 4. Verificar Configurações do Sistema:

**Windows 10/11:**
```
1. Configurações > Privacidade > Câmera
2. Certifique-se que "Permitir acesso à câmera" está ATIVADO
3. Certifique-se que navegador tem permissão
```

**macOS:**
```
1. Preferências do Sistema > Segurança e Privacidade
2. Clique em "Câmera"
3. Certifique-se que seu navegador está marcado
```

**Linux:**
```bash
# Verificar se câmera está sendo detectada
ls -l /dev/video*

# Deve mostrar algo como /dev/video0

# Se não aparecer nada:
sudo apt install v4l-utils
v4l2-ctl --list-devices
```

---

## ⚠️ Erro: "Este recurso só funciona via HTTPS ou localhost"

### Causa:
Navegadores modernos **bloqueiam** acesso à câmera em sites HTTP (não seguros), exceto `localhost`.

### Solução:

#### Desenvolvimento (Local):
```
✅ Use: http://localhost:5000
✅ Use: http://127.0.0.1:5000
❌ NÃO use: http://192.168.x.x:5000 (IP da rede local)
```

#### Produção:
```
✅ SEMPRE use HTTPS
❌ HTTP não funciona (navegador bloqueia)

Deploy em:
- Vercel (HTTPS automático)
- Netlify (HTTPS automático)
- Render (HTTPS automático)
```

---

## 🐛 Erro: "NotReadableError" ou "TrackStartError"

### Causa:
Câmera em uso por outro aplicativo ou driver corrompido.

### Solução:
```
1. Feche TODAS as aplicações de vídeo
2. Feche TODOS os navegadores
3. Reinicie o computador
4. Abra apenas o EcoVision
5. Tente novamente
```

Se persistir:
```
Windows:
1. Gerenciador de Dispositivos
2. Clique direito na câmera
3. "Desinstalar dispositivo"
4. Reinicie o computador
5. Windows reinstalará automaticamente
```

---

## 🔧 Erro: Câmera funciona mas fica preta

### Causa:
Configuração de resolução não suportada ou baixa luminosidade.

### Solução:
```
1. Certifique-se que há luz suficiente
2. Limpe a lente da câmera
3. Teste em outro app para confirmar funcionamento
4. Verifique console do navegador (F12) para erros
```

---

## 📱 Problemas no Celular

### Câmera não abre no celular:

#### Android (Chrome):
```
1. Configurações do Chrome
2. Configurações do site
3. Câmera > Permitir
4. Recarregue a página
```

#### iOS (Safari):
```
1. Configurações > Safari
2. Câmera > Permitir
3. Recarregue a página

IMPORTANTE: iOS bloqueia getUserMedia em apps standalone
Use sempre pelo navegador Safari
```

### Câmera abre mas usa a frontal:

```
Normal! Celulares têm múltiplas câmeras.

O EcoVision usa facingMode: "environment" (câmera traseira)
Se não houver câmera traseira, usa a frontal automaticamente.

Para forçar câmera traseira, configure físicamente o celular.
```

---

## 🔍 Debug Avançado

### Verificar getUserMedia no Console:

```javascript
// Abra console do navegador (F12)
// Cole este código:

navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => {
    console.log('✅ Câmera funcionando!', stream);
    stream.getTracks().forEach(track => track.stop());
  })
  .catch(err => {
    console.error('❌ Erro:', err.name, err.message);
  });
```

### Verificar Dispositivos Disponíveis:

```javascript
// Abra console do navegador (F12)
// Cole este código:

navigator.mediaDevices.enumerateDevices()
  .then(devices => {
    const cameras = devices.filter(d => d.kind === 'videoinput');
    console.log(`📹 ${cameras.length} câmera(s) encontrada(s):`);
    cameras.forEach((cam, i) => {
      console.log(`${i + 1}. ${cam.label || 'Câmera sem nome'}`);
    });
  });
```

---

## 🌐 Problemas Específicos do Playground Figma

### Erro no Playground:

```
CAUSA: O Playground do Figma roda em iframe com restrições de segurança.
Pode bloquear acesso à câmera por política de CORS/CSP.

SOLUÇÃO:
✅ Execute localmente: ./run_dev.sh
✅ Deploy em Vercel/Netlify
❌ NÃO espere que funcione 100% no playground
```

---

## 📊 Checklist de Diagnóstico

Use este checklist para diagnosticar problemas:

```
Hardware:
[ ] Webcam está conectada fisicamente
[ ] LED da câmera acende (se houver)
[ ] Câmera funciona em outro app (Zoom, etc)

Sistema Operacional:
[ ] Permissões de câmera estão habilitadas
[ ] Drivers estão instalados e atualizados
[ ] Nenhuma outra app está usando a câmera

Navegador:
[ ] Navegador moderno (Chrome 63+, Firefox 68+, Safari 11+)
[ ] Site está em HTTPS ou localhost
[ ] Permissão de câmera está em "Permitir"
[ ] JavaScript está habilitado

Rede:
[ ] Conexão com internet está funcionando
[ ] Firewall não está bloqueando

EcoVision:
[ ] Sistema está "Iniciado" (botão verde)
[ ] Console do navegador não mostra erros (F12)
[ ] Servidor Python está rodando (inference_server.py)
```

---

## 🆘 Ainda Não Funciona?

### 1. Teste Básico de Câmera:

Abra este HTML simples para testar se o problema é do navegador:

```html
<!DOCTYPE html>
<html>
<head><title>Teste Câmera</title></head>
<body>
  <h1>Teste de Câmera</h1>
  <video id="video" autoplay style="width:640px"></video>
  <script>
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        document.getElementById('video').srcObject = stream;
        alert('✅ Câmera funcionando!');
      })
      .catch(err => {
        alert('❌ Erro: ' + err.name + ' - ' + err.message);
      });
  </script>
</body>
</html>
```

Se **ESTE teste funcionar**, o problema é no EcoVision (abra issue no GitHub).
Se **NÃO funcionar**, o problema é no navegador/sistema.

### 2. Coletar Informações:

Quando abrir issue, inclua:

```
- Sistema Operacional: (Windows 11, macOS 13, Ubuntu 22.04, etc)
- Navegador: (Chrome 120, Firefox 115, Safari 17, etc)
- Tipo de câmera: (Integrada, USB Logitech C920, etc)
- Erro exato: (copie do console F12)
- Já funcionou antes?: (Sim/Não)
- Funciona em outro app?: (Zoom, Skype, etc)
```

### 3. Reportar Bug:

Se confirmou que é bug do EcoVision:
- GitHub Issues: https://github.com/seu-usuario/ecovision/issues
- Inclua TODAS as informações acima
- Anexe screenshot do console (F12)
- Anexe screenshot da aba Network (F12)

---

<div align="center">

**🎥 EcoVision Camera Troubleshooting**

Na maioria dos casos, o problema é permissão bloqueada.  
Siga o guia do seu navegador no topo deste documento!

---

**[🏠 Voltar](./README.md)** | **[📖 Documentação](./DOCS_INDEX.md)** | **[🐛 Issues](https://github.com/seu-usuario/ecovision/issues)**

</div>
