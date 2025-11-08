import { Hono } from "npm:hono";
import { cors } from "npm:hono/cors";
import { logger } from "npm:hono/logger";
import * as kv from "./kv_store.tsx";
import {
  BancoDeDados,
  Dashboard,
  ModeloIA,
  ControladorSerial,
  Esteira,
  Cancela,
  Camera,
  Autenticacao,
  OutputData
} from "./models.tsx";

const app = new Hono();

// Inicializa as instâncias do sistema
const db = new BancoDeDados(kv);
const dashboard = new Dashboard(db);
const controlador = new ControladorSerial(Deno.env.get("SERIAL_PORT") || "/dev/ttyUSB0", 9600);
const esteira = new Esteira(controlador, 50);
const cancelas = [
  new Cancela(1, controlador),
  new Cancela(2, controlador),
  new Cancela(3, controlador)
];
const camera = new Camera(30, [1920, 1080]);
const autenticacao = new Autenticacao(Deno.env.get("GOOGLE_CLIENT_ID") || "");
const modeloIA = new ModeloIA("YOLO", "v8n", 85, db, controlador);

// Inicializa conexão serial se configurada
try {
  controlador.conectar();
  console.log("Controlador serial inicializado com sucesso");
} catch (error) {
  console.log("Executando em modo simulação (serial não disponível):", error);
}

// Enable logger
app.use('*', logger(console.log));

// Enable CORS for all routes and methods
app.use(
  "/*",
  cors({
    origin: "*",
    allowHeaders: ["Content-Type", "Authorization"],
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    exposeHeaders: ["Content-Length"],
    maxAge: 600,
  }),
);

// Health check endpoint
app.get("/make-server-ea835390/health", (c) => {
  return c.json({ status: "ok", message: "EcoVision server is running" });
});

// Salvar configurações do sistema
app.post("/make-server-ea835390/config", async (c) => {
  try {
    const { gateConfigs, minAccuracy, modelVersion } = await c.req.json();
    
    // Atualiza configurações do modelo IA
    if (minAccuracy !== undefined) {
      modeloIA.calibrarLimite(minAccuracy);
    }
    
    if (modelVersion !== undefined) {
      modeloIA.versao = modelVersion.toLowerCase().replace("yolov8", "v8");
    }
    
    await kv.set("system_config", {
      gateConfigs,
      minAccuracy,
      modelVersion,
      updatedAt: new Date().toISOString()
    });
    
    console.log("Configuração atualizada - Cancelas:", gateConfigs, "Confiança:", minAccuracy, "Modelo:", modelVersion);
    
    return c.json({ success: true, message: "Configuração salva com sucesso" });
  } catch (error) {
    console.error("Erro ao salvar configuração:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Obter configurações do sistema
app.get("/make-server-ea835390/config", async (c) => {
  try {
    const config = await kv.get("system_config");
    return c.json({ success: true, config });
  } catch (error) {
    console.error("Erro ao obter configuração:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Salvar detecções
app.post("/make-server-ea835390/detections", async (c) => {
  try {
    const detection = await c.req.json();
    const detectionId = `detection_${Date.now()}`;
    
    await kv.set(detectionId, {
      ...detection,
      createdAt: new Date().toISOString()
    });
    
    return c.json({ success: true, id: detectionId });
  } catch (error) {
    console.error("Erro ao salvar detecção:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Obter estatísticas
app.get("/make-server-ea835390/stats", async (c) => {
  try {
    const detections = await kv.getByPrefix("detection_");
    
    // Processa estatísticas
    const stats = {
      total: detections.length,
      byMaterial: {} as Record<string, number>,
      byGate: {} as Record<number, number>
    };
    
    detections.forEach((d: any) => {
      if (d.material) {
        stats.byMaterial[d.material] = (stats.byMaterial[d.material] || 0) + 1;
      }
      if (d.gateAssigned) {
        stats.byGate[d.gateAssigned] = (stats.byGate[d.gateAssigned] || 0) + 1;
      }
    });
    
    return c.json({ success: true, stats });
  } catch (error) {
    console.error("Erro ao obter estatísticas:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Salvar logs
app.post("/make-server-ea835390/logs", async (c) => {
  try {
    const log = await c.req.json();
    const logId = `log_${Date.now()}`;
    
    await kv.set(logId, {
      ...log,
      createdAt: new Date().toISOString()
    });
    
    return c.json({ success: true, id: logId });
  } catch (error) {
    console.error("Erro ao salvar log:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Obter logs
app.get("/make-server-ea835390/logs", async (c) => {
  try {
    const logs = await kv.getByPrefix("log_");
    return c.json({ success: true, logs });
  } catch (error) {
    console.error("Erro ao obter logs:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// ==================== ENDPOINTS BASEADOS NAS CLASSES ====================

// Controle da Esteira
app.post("/make-server-ea835390/esteira/ligar", (c) => {
  try {
    esteira.ligar();
    return c.json({ success: true, status: esteira.status });
  } catch (error) {
    console.error("Erro ao ligar esteira:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.post("/make-server-ea835390/esteira/desligar", (c) => {
  try {
    esteira.desligar();
    return c.json({ success: true, status: esteira.status });
  } catch (error) {
    console.error("Erro ao desligar esteira:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Controle das Cancelas
app.post("/make-server-ea835390/cancela/:id/abrir", (c) => {
  try {
    const id = parseInt(c.req.param("id"));
    const cancela = cancelas.find(c => c.cancela_id === id);
    
    if (!cancela) {
      return c.json({ success: false, error: "Cancela não encontrada" }, 404);
    }
    
    cancela.abrir();
    return c.json({ success: true, status: cancela.status });
  } catch (error) {
    console.error("Erro ao abrir cancela:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.post("/make-server-ea835390/cancela/:id/fechar", (c) => {
  try {
    const id = parseInt(c.req.param("id"));
    const cancela = cancelas.find(c => c.cancela_id === id);
    
    if (!cancela) {
      return c.json({ success: false, error: "Cancela não encontrada" }, 404);
    }
    
    cancela.fechar();
    return c.json({ success: true, status: cancela.status });
  } catch (error) {
    console.error("Erro ao fechar cancela:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Controle da Câmera
app.post("/make-server-ea835390/camera/iniciar", (c) => {
  try {
    camera.iniciarStream(0);
    return c.json({ success: true, ativa: camera.is_ativa() });
  } catch (error) {
    console.error("Erro ao iniciar câmera:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.post("/make-server-ea835390/camera/parar", (c) => {
  try {
    camera.pararStream();
    return c.json({ success: true, ativa: camera.is_ativa() });
  } catch (error) {
    console.error("Erro ao parar câmera:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.get("/make-server-ea835390/camera/capturar", (c) => {
  try {
    const frame = camera.capturarImagem();
    return c.json({ success: true, frame });
  } catch (error) {
    console.error("Erro ao capturar imagem:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Controle do Modelo IA
app.post("/make-server-ea835390/modelo/ativar", (c) => {
  try {
    modeloIA.ativar();
    return c.json({ success: true, ativo: modeloIA.ativo });
  } catch (error) {
    console.error("Erro ao ativar modelo:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.post("/make-server-ea835390/modelo/desativar", (c) => {
  try {
    modeloIA.desativar();
    return c.json({ success: true, ativo: modeloIA.ativo });
  } catch (error) {
    console.error("Erro ao desativar modelo:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.post("/make-server-ea835390/modelo/calibrar", async (c) => {
  try {
    const { limite } = await c.req.json();
    modeloIA.calibrarLimite(limite);
    return c.json({ success: true, limiteAtual: modeloIA.limiteMinAccuracy });
  } catch (error) {
    console.error("Erro ao calibrar modelo:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.post("/make-server-ea835390/modelo/processar", async (c) => {
  try {
    const { frame, gateConfigs } = await c.req.json();
    
    // Faz predição
    const predicao = modeloIA.preverFrame(frame);
    
    console.log(`Detecção: ${predicao.getClasse()} com ${predicao.getConfianca().toFixed(1)}% de confiança`);
    
    // Decide acionamento para cada cancela
    const acionamentos = [];
    for (let i = 1; i <= 3; i++) {
      const deveAcionar = modeloIA.decidirAcionamento(predicao, gateConfigs, i);
      if (deveAcionar) {
        console.log(`Acionando cancela ${i} para material ${predicao.getClasse()}`);
        await modeloIA.executarAcionamento(i);
        await db.registrarProcessamento(
          predicao.getClasse(),
          predicao.getConfianca(),
          i
        );
        acionamentos.push(i);
      }
    }
    
    return c.json({
      success: true,
      predicao: {
        classe: predicao.getClasse(),
        confianca: predicao.getConfianca()
      },
      acionamentos
    });
  } catch (error) {
    console.error("Erro ao processar frame:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Dashboard
app.get("/make-server-ea835390/dashboard/visao-geral", async (c) => {
  try {
    const dados = await dashboard.coletarVisaoGeral();
    return c.json({ success: true, dados });
  } catch (error) {
    console.error("Erro ao obter visão geral:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.get("/make-server-ea835390/dashboard/status", (c) => {
  try {
    const status = dashboard.exibirStatusGeral();
    return c.json({ success: true, status });
  } catch (error) {
    console.error("Erro ao obter status:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.get("/make-server-ea835390/dashboard/materiais", async (c) => {
  try {
    const data = new Date();
    const materiais = await dashboard.exibirMateriaisReciclados(data);
    return c.json({ success: true, materiais });
  } catch (error) {
    console.error("Erro ao obter materiais:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.get("/make-server-ea835390/dashboard/performance-cancelas", async (c) => {
  try {
    const data = new Date();
    const performance = await dashboard.exibirPerformanceCancelas(data);
    return c.json({ success: true, performance });
  } catch (error) {
    console.error("Erro ao obter performance:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Autenticação
app.post("/make-server-ea835390/auth/login", async (c) => {
  try {
    const { token } = await c.req.json();
    const resultado = autenticacao.loginComGoogle(token);
    return c.json({ success: true, ...resultado });
  } catch (error) {
    console.error("Erro ao fazer login:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.post("/make-server-ea835390/auth/logout", async (c) => {
  try {
    const { email } = await c.req.json();
    autenticacao.logout_try(email);
    return c.json({ success: true, message: "Logout realizado" });
  } catch (error) {
    console.error("Erro ao fazer logout:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

app.get("/make-server-ea835390/auth/verificar/:email", (c) => {
  try {
    const email = c.req.param("email");
    const autenticado = autenticacao.is_autenticado(email);
    return c.json({ success: true, autenticado });
  } catch (error) {
    console.error("Erro ao verificar autenticação:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// ==================== NOVOS ENDPOINTS PARA SISTEMA COMPLETO ====================

// Endpoint para comunicação serial (ESP32)
app.post("/make-server-ea835390/serial/send", async (c) => {
  try {
    const { esteira, cancela } = await c.req.json();
    
    console.log(`[SERIAL] Enviando comando - Esteira: ${esteira ? 'ON' : 'OFF'}, Cancela: ${cancela}`);
    
    // Monta comando serial:
    // Bit 0: Esteira (0 = desligada, 1 = ligada)
    // Bits 1-2: Cancela (00 = nenhuma, 01 = cancela 1, 10 = cancela 2, 11 = cancela 3)
    let command = esteira ? 0b1 : 0b0; // Bit da esteira
    
    if (cancela) {
      const cancelaBits = cancela & 0b11; // Limita a 2 bits
      command |= (cancelaBits << 1); // Desloca cancela para bits 1-2
    }
    
    try {
      // Envia comando via serial
      const output = controlador.enviarComando(command);
      console.log(`[SERIAL] Comando enviado: ${command.toString(2).padStart(3, '0')} (binário) - Resposta: ${output.codigo}`);
      
      return c.json({
        success: true,
        command,
        binary: command.toString(2).padStart(3, '0'),
        output
      });
    } catch (serialError) {
      console.log('[SERIAL] Porta serial não disponível, modo simulação');
      return c.json({
        success: true,
        command,
        binary: command.toString(2).padStart(3, '0'),
        mode: 'simulation'
      });
    }
  } catch (error) {
    console.error("[SERIAL] Erro ao enviar comando:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Salvar detecção no banco de dados por usuário
app.post("/make-server-ea835390/detections/save", async (c) => {
  try {
    const { userId, material, confidence, gateAssigned, timestamp } = await c.req.json();
    
    const detectionId = `detection_${userId}_${Date.now()}`;
    
    await kv.set(detectionId, {
      userId,
      material,
      confidence,
      gateAssigned,
      timestamp,
      createdAt: new Date().toISOString()
    });
    
    console.log(`[BD] Detecção salva: ${material} (${confidence.toFixed(1)}%) - Usuário: ${userId}`);
    
    return c.json({ success: true, id: detectionId });
  } catch (error) {
    console.error("[BD] Erro ao salvar detecção:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Estatísticas do dashboard por usuário
app.get("/make-server-ea835390/dashboard/stats", async (c) => {
  try {
    const userId = c.req.query('userId');
    
    if (!userId) {
      return c.json({ success: false, error: "userId é obrigatório" }, 400);
    }
    
    console.log(`[DASHBOARD] Buscando estatísticas para usuário ${userId}`);
    
    // Busca todas as detecções do usuário
    const allDetections = await kv.getByPrefix(`detection_${userId}_`);
    
    const stats = {
      totalProcessed: allDetections.length,
      totalSeparated: allDetections.filter((d: any) => d.gateAssigned !== null).length,
      totalRejected: allDetections.filter((d: any) => d.gateAssigned === null).length,
      materialCounts: {
        papel: allDetections.filter((d: any) => d.material === 'papel').length,
        metal: allDetections.filter((d: any) => d.material === 'metal').length,
        plastico: allDetections.filter((d: any) => d.material === 'plastico').length,
        vidro: allDetections.filter((d: any) => d.material === 'vidro').length
      },
      gateCounts: {
        1: allDetections.filter((d: any) => d.gateAssigned === 1).length,
        2: allDetections.filter((d: any) => d.gateAssigned === 2).length,
        3: allDetections.filter((d: any) => d.gateAssigned === 3).length
      },
      efficiency: allDetections.length > 0 
        ? Math.round((allDetections.filter((d: any) => d.gateAssigned !== null).length / allDetections.length) * 100)
        : 0,
      uptime: 95 // Simulado por enquanto
    };
    
    console.log(`[DASHBOARD] Estatísticas: ${stats.totalProcessed} processados, ${stats.totalSeparated} separados`);
    
    return c.json({ success: true, stats });
  } catch (error) {
    console.error("[DASHBOARD] Erro ao obter estatísticas:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Estatísticas do perfil do usuário
app.get("/make-server-ea835390/user/stats", async (c) => {
  try {
    const userId = c.req.query('userId');
    
    if (!userId) {
      return c.json({ success: false, error: "userId é obrigatório" }, 400);
    }
    
    console.log(`[PERFIL] Buscando estatísticas para usuário ${userId}`);
    
    const allDetections = await kv.getByPrefix(`detection_${userId}_`);
    
    // Busca configurações mais usadas
    const configKey = `user_${userId}_favorite_config`;
    const favoriteConfig = await kv.get(configKey);
    
    const stats = {
      totalSessions: 0, // TODO: Implementar contagem de sessões
      totalDetections: allDetections.length,
      totalProcessed: allDetections.length,
      lastSession: allDetections.length > 0 
        ? allDetections[allDetections.length - 1].timestamp
        : null,
      favoriteConfiguration: favoriteConfig || null
    };
    
    return c.json({ success: true, stats });
  } catch (error) {
    console.error("[PERFIL] Erro ao obter estatísticas do usuário:", error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

Deno.serve(app.fetch);