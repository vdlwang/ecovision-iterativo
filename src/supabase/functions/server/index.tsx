import { Hono } from "npm:hono";
import { cors } from "npm:hono/cors";
import { logger } from "npm:hono/logger";
import { createClient } from "npm:@supabase/supabase-js@2";

const app = new Hono();

// Cria cliente Supabase com service role para acesso admin
const supabase = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
);

// URL do servidor de inferência Python
const INFERENCE_SERVER_URL = Deno.env.get('INFERENCE_SERVER_URL') || 'http://localhost:8000';

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

// ==================== HELPER FUNCTIONS ====================

/**
 * Extrai user_id do token JWT
 */
async function getUserFromToken(authHeader: string | null) {
  if (!authHeader?.startsWith('Bearer ')) {
    console.error('[AUTH] Header de autorização ausente ou inválido');
    return null;
  }
  
  const token = authHeader.substring(7);
  
  // Validar se o token não está vazio
  if (!token || token.trim() === '') {
    console.error('[AUTH] Token vazio ou inválido');
    return null;
  }
  
  // Log para debug (primeiros 30 caracteres apenas)
  console.log(`[AUTH] Token recebido (início): ${token.substring(0, 30)}...`);
  
  // MODO DEMO: Token especial para desenvolvimento/testes
  if (token === 'DEMO_MODE_TOKEN_ecovision_2024') {
    console.log('[DEMO] ✅ Token demo reconhecido! Usando usuário demo');
    return {
      id: 'demo-user-ecovision-2024',
      email: 'demo@ecovision.com',
      aud: 'authenticated',
      role: 'authenticated'
    };
  }
  
  console.log('[AUTH] Token não é demo, tentando validar com Supabase OAuth...');
  
  try {
    // Criar cliente Supabase com o token do usuário
    const userSupabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      {
        global: {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      }
    );
    
    const { data: { user }, error } = await userSupabase.auth.getUser();
    
    if (error || !user) {
      // Não logar erro se o token parece ser uma key pública (termina com números/letras aleatórios)
      // Isso evita spam de logs quando não há autenticação OAuth configurada
      const isAnonKey = token.length > 100 && token.includes('eyJ');
      if (!isAnonKey) {
        console.error('[AUTH] Erro ao obter usuário:', error?.message || 'Usuário não encontrado');
      }
      return null;
    }
    
    console.log(`[AUTH] Usuário autenticado via OAuth: ${user.email}`);
    return user;
  } catch (err) {
    console.error('[AUTH] Exceção ao validar token:', err);
    return null;
  }
}

/**
 * Obtém ou cria sessão ativa do usuário
 */
async function getOrCreateSession(userId: string, userAgent: string | null) {
  // Busca sessão ativa (sem ended_at)
  const { data: activeSessions, error: searchError } = await supabase
    .from('user_sessions')
    .select('*')
    .eq('user_id', userId)
    .is('ended_at', null)
    .order('started_at', { ascending: false })
    .limit(1);
  
  if (searchError) {
    console.error('Erro ao buscar sessão:', searchError);
    throw searchError;
  }
  
  // Se existe sessão ativa, retorna ela
  if (activeSessions && activeSessions.length > 0) {
    return activeSessions[0];
  }
  
  // Cria nova sessão
  const { data: newSession, error: createError } = await supabase
    .from('user_sessions')
    .insert({
      user_id: userId,
      session_token: crypto.randomUUID(),
      user_agent: userAgent,
      device_info: {}
    })
    .select()
    .single();
  
  if (createError) {
    console.error('Erro ao criar sessão:', createError);
    throw createError;
  }
  
  return newSession;
}

// ==================== ENDPOINTS ====================

// Health check
app.get("/make-server-ea835390/health", (c) => {
  return c.json({ 
    status: "ok", 
    message: "EcoVision server is running",
    timestamp: new Date().toISOString()
  });
});

// Teste de autenticação
app.get("/make-server-ea835390/auth-test", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    
    if (!authHeader) {
      return c.json({ 
        success: false, 
        error: 'Header Authorization ausente',
        hint: 'Certifique-se de incluir: Authorization: Bearer {token}'
      }, 401);
    }
    
    const user = await getUserFromToken(authHeader);
    
    if (!user) {
      return c.json({ 
        success: false, 
        error: 'Token inválido ou expirado',
        hint: 'Faça logout e login novamente para obter um novo token'
      }, 401);
    }
    
    return c.json({ 
      success: true, 
      message: 'Autenticação funcionando corretamente',
      user: {
        id: user.id,
        email: user.email
      },
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('[AUTH-TEST] Erro:', error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// ==================== CONFIGURAÇÕES ====================

// Salvar configuração
app.post("/make-server-ea835390/config", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    const user = await getUserFromToken(authHeader);
    
    if (!user) {
      return c.json({ success: false, error: 'Não autorizado' }, 401);
    }
    
    const { gateConfigs, minAccuracy, modelVersion } = await c.req.json();
    
    // MODO DEMO: Apenas retorna sucesso sem salvar no banco
    if (user.id === 'demo-user-ecovision-2024') {
      console.log('[CONFIG] Modo demo - configuração não será salva permanentemente');
      return c.json({ 
        success: true, 
        config: {
          gate_1_material: gateConfigs?.['1'] || null,
          gate_2_material: gateConfigs?.['2'] || null,
          gate_3_material: gateConfigs?.['3'] || null,
          min_confidence: minAccuracy || 85,
          model_version: modelVersion || 'YOLOv8n',
          is_active: true
        }
      });
    }
    
    // Desativa configurações antigas
    await supabase
      .from('system_config')
      .update({ is_active: false })
      .eq('user_id', user.id)
      .eq('is_active', true);
    
    // Cria nova configuração
    const { data, error } = await supabase
      .from('system_config')
      .insert({
        user_id: user.id,
        gate_1_material: gateConfigs?.['1'] || null,
        gate_2_material: gateConfigs?.['2'] || null,
        gate_3_material: gateConfigs?.['3'] || null,
        min_confidence: minAccuracy || 85,
        model_version: modelVersion || 'YOLOv8n',
        is_active: true
      })
      .select()
      .single();
    
    if (error) {
      console.error('Erro ao salvar config:', error);
      return c.json({ success: false, error: error.message }, 500);
    }
    
    console.log('Config salva:', data);
    return c.json({ success: true, config: data });
    
  } catch (error) {
    console.error('Erro ao salvar configuração:', error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Obter configuração ativa
app.get("/make-server-ea835390/config", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    const user = await getUserFromToken(authHeader);
    
    if (!user) {
      return c.json({ success: false, error: 'Não autorizado' }, 401);
    }
    
    // MODO DEMO: Retorna valores padrão
    if (user.id === 'demo-user-ecovision-2024') {
      console.log('[CONFIG] Modo demo - retornando configuração padrão');
      return c.json({ 
        success: true, 
        config: {
          gate_1_material: null,
          gate_2_material: null,
          gate_3_material: null,
          min_confidence: 85,
          model_version: 'YOLOv8n'
        }
      });
    }
    
    const { data, error } = await supabase
      .from('system_config')
      .select('*')
      .eq('user_id', user.id)
      .eq('is_active', true)
      .single();
    
    if (error && error.code !== 'PGRST116') { // PGRST116 = no rows
      console.error('Erro ao obter config:', error);
      return c.json({ success: false, error: error.message }, 500);
    }
    
    // Se não tem config, retorna valores padrão
    if (!data) {
      return c.json({ 
        success: true, 
        config: {
          gate_1_material: null,
          gate_2_material: null,
          gate_3_material: null,
          min_confidence: 85,
          model_version: 'YOLOv8n'
        }
      });
    }
    
    return c.json({ success: true, config: data });
    
  } catch (error) {
    console.error('Erro ao obter configuração:', error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// ==================== INFERÊNCIA ====================

// Processar imagem (fazer inferência)
app.post("/make-server-ea835390/inference", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    
    if (!authHeader) {
      console.error('[INFERENCE] Header Authorization ausente');
      return c.json({ success: false, error: 'Token de autenticação não fornecido' }, 401);
    }
    
    const user = await getUserFromToken(authHeader);
    
    if (!user) {
      console.error('[INFERENCE] Falha na autenticação do usuário');
      return c.json({ success: false, error: 'Token de autenticação inválido ou expirado. Faça login novamente.' }, 401);
    }
    
    console.log(`[INFERENCE] Usuário autenticado: ${user.id}`);
    
    const { image_base64, model_version, min_confidence } = await c.req.json();
    
    // Chama servidor de inferência Python
    const inferenceResponse = await fetch(`${INFERENCE_SERVER_URL}/inference`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64,
        model_version: model_version || 'YOLOv8n',
        min_confidence: (min_confidence || 85) / 100 // Converte para 0-1
      })
    });
    
    if (!inferenceResponse.ok) {
      const errorText = await inferenceResponse.text();
      console.error('Erro na inferência:', errorText);
      return c.json({ 
        success: false, 
        error: 'Servidor de inferência indisponível. Execute: python inference_server.py' 
      }, 500);
    }
    
    const inferenceData = await inferenceResponse.json();
    
    // Se não há detecções, retorna sem salvar
    if (!inferenceData.detections || inferenceData.detections.length === 0) {
      return c.json({ 
        success: true, 
        detections: [],
        processing_time_ms: inferenceData.processing_time_ms
      });
    }
    
    // Obtém configuração ativa para saber qual cancela acionar
    const { data: config } = await supabase
      .from('system_config')
      .select('*')
      .eq('user_id', user.id)
      .eq('is_active', true)
      .single();
    
    // Obtém ou cria sessão
    const session = await getOrCreateSession(user.id, c.req.header('User-Agent'));
    
    // Salva cada detecção no banco
    const detectionsToSave = [];
    
    for (const detection of inferenceData.detections) {
      // Determina qual cancela acionar baseado no material
      let gateNumber = 1; // Padrão
      let gateActivated = false;
      
      if (config) {
        if (detection.material === config.gate_1_material) {
          gateNumber = 1;
          gateActivated = detection.confidence >= (config.min_confidence || 85);
        } else if (detection.material === config.gate_2_material) {
          gateNumber = 2;
          gateActivated = detection.confidence >= (config.min_confidence || 85);
        } else if (detection.material === config.gate_3_material) {
          gateNumber = 3;
          gateActivated = detection.confidence >= (config.min_confidence || 85);
        }
      }
      
      detectionsToSave.push({
        user_id: user.id,
        session_id: session.id,
        material_detected: detection.material,
        confidence: detection.confidence,
        gate_number: gateNumber,
        gate_activated: gateActivated,
        model_version: inferenceData.model_version,
        processing_time_ms: inferenceData.processing_time_ms,
        bounding_box: detection.bounding_box
      });
    }
    
    // Insere todas as detecções
    const { data: savedDetections, error: saveError } = await supabase
      .from('inferences')
      .insert(detectionsToSave)
      .select();
    
    if (saveError) {
      console.error('Erro ao salvar detecções:', saveError);
      // Não falha a requisição, apenas loga o erro
    }
    
    // Atualiza contador de inferências na sessão
    await supabase
      .from('user_sessions')
      .update({ 
        inferences_count: session.inferences_count + detectionsToSave.length 
      })
      .eq('id', session.id);
    
    return c.json({ 
      success: true, 
      detections: inferenceData.detections,
      processing_time_ms: inferenceData.processing_time_ms,
      saved_to_database: !!savedDetections
    });
    
  } catch (error) {
    console.error('Erro ao processar inferência:', error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// ==================== ESTATÍSTICAS ====================

// Obter estatísticas do dashboard
app.get("/make-server-ea835390/stats", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    const user = await getUserFromToken(authHeader);
    
    if (!user) {
      console.error('[STATS] Usuário não autorizado');
      return c.json({ success: false, error: 'Não autorizado' }, 401);
    }
    
    console.log(`[STATS] Buscando estatísticas para usuário: ${user.email}`);
    
    // MODO DEMO: Retorna dados mockados
    if (user.id === 'demo-user-ecovision-2024') {
      console.log('[STATS] Modo demo detectado - retornando dados mockados');
      return c.json({ 
        success: true, 
        stats: {
          total: 0,
          byMaterial: {
            papel: 0,
            metal: 0,
            plastico: 0,
            vidro: 0
          },
          byGate: {
            '1': 0,
            '2': 0,
            '3': 0
          },
          avgConfidence: 0,
          recentDetections: [],
          totalSessions: 0
        }
      });
    }
    
    // Total de inferências
    const { count: totalInferences } = await supabase
      .from('inferences')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id);
    
    // Inferências por material
    const { data: byMaterial } = await supabase
      .from('inferences')
      .select('material_detected')
      .eq('user_id', user.id);
    
    const materialCounts = {
      papel: 0,
      metal: 0,
      plastico: 0,
      vidro: 0
    };
    
    byMaterial?.forEach(item => {
      if (item.material_detected in materialCounts) {
        materialCounts[item.material_detected]++;
      }
    });
    
    // Inferências por cancela
    const { data: byGate } = await supabase
      .from('inferences')
      .select('gate_number')
      .eq('user_id', user.id);
    
    const gateCounts = { '1': 0, '2': 0, '3': 0 };
    
    byGate?.forEach(item => {
      if (item.gate_number in gateCounts) {
        gateCounts[item.gate_number]++;
      }
    });
    
    // Confiança média
    const { data: confidenceData } = await supabase
      .from('inferences')
      .select('confidence')
      .eq('user_id', user.id);
    
    const avgConfidence = confidenceData && confidenceData.length > 0
      ? confidenceData.reduce((sum, item) => sum + item.confidence, 0) / confidenceData.length
      : 0;
    
    // Últimas 10 detecções
    const { data: recentDetections } = await supabase
      .from('inferences')
      .select('*')
      .eq('user_id', user.id)
      .order('timestamp', { ascending: false })
      .limit(10);
    
    // Sessões
    const { count: totalSessions } = await supabase
      .from('user_sessions')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id);
    
    return c.json({ 
      success: true, 
      stats: {
        total: totalInferences || 0,
        byMaterial: materialCounts,
        byGate: gateCounts,
        avgConfidence: Math.round(avgConfidence * 100) / 100,
        recentDetections: recentDetections || [],
        totalSessions: totalSessions || 0
      }
    });
    
  } catch (error) {
    console.error('[STATS] Erro ao obter estatísticas:', error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Estatísticas por período
app.get("/make-server-ea835390/stats/period", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    const user = await getUserFromToken(authHeader);
    
    if (!user) {
      return c.json({ success: false, error: 'Não autorizado' }, 401);
    }
    
    const days = parseInt(c.req.query('days') || '7');
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);
    
    // Busca estatísticas agregadas
    const { data: dailyStats } = await supabase
      .from('statistics')
      .select('*')
      .eq('user_id', user.id)
      .gte('date', startDate.toISOString().split('T')[0])
      .order('date', { ascending: true });
    
    return c.json({ 
      success: true, 
      stats: dailyStats || []
    });
    
  } catch (error) {
    console.error('Erro ao obter estatísticas por período:', error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// ==================== SESSÕES ====================

// Encerrar sessão atual
app.post("/make-server-ea835390/session/end", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    const user = await getUserFromToken(authHeader);
    
    if (!user) {
      return c.json({ success: false, error: 'Não autorizado' }, 401);
    }
    
    // Busca sessão ativa
    const { data: sessions } = await supabase
      .from('user_sessions')
      .select('*')
      .eq('user_id', user.id)
      .is('ended_at', null)
      .order('started_at', { ascending: false })
      .limit(1);
    
    if (!sessions || sessions.length === 0) {
      return c.json({ success: true, message: 'Nenhuma sessão ativa' });
    }
    
    // Encerra sessão
    const { error } = await supabase
      .from('user_sessions')
      .update({ ended_at: new Date().toISOString() })
      .eq('id', sessions[0].id);
    
    if (error) {
      console.error('Erro ao encerrar sessão:', error);
      return c.json({ success: false, error: error.message }, 500);
    }
    
    return c.json({ success: true, message: 'Sessão encerrada' });
    
  } catch (error) {
    console.error('Erro ao encerrar sessão:', error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// ==================== LOGS ====================

// Salvar log
app.post("/make-server-ea835390/logs", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    const user = await getUserFromToken(authHeader);
    
    const { log_level, log_type, message, details } = await c.req.json();
    
    const { error } = await supabase
      .from('system_logs')
      .insert({
        user_id: user?.id || null,
        log_level: log_level || 'INFO',
        log_type: log_type || 'SYSTEM',
        message,
        details: details || {}
      });
    
    if (error) {
      console.error('Erro ao salvar log:', error);
      return c.json({ success: false, error: error.message }, 500);
    }
    
    return c.json({ success: true });
    
  } catch (error) {
    console.error('Erro ao salvar log:', error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Obter logs
app.get("/make-server-ea835390/logs", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    const user = await getUserFromToken(authHeader);
    
    if (!user) {
      return c.json({ success: false, error: 'Não autorizado' }, 401);
    }
    
    const limit = parseInt(c.req.query('limit') || '50');
    const level = c.req.query('level');
    
    let query = supabase
      .from('system_logs')
      .select('*')
      .eq('user_id', user.id)
      .order('timestamp', { ascending: false })
      .limit(limit);
    
    if (level) {
      query = query.eq('log_level', level);
    }
    
    const { data, error } = await query;
    
    if (error) {
      console.error('Erro ao obter logs:', error);
      return c.json({ success: false, error: error.message }, 500);
    }
    
    return c.json({ success: true, logs: data || [] });
    
  } catch (error) {
    console.error('Erro ao obter logs:', error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// ==================== PERFIL DO USUÁRIO ====================

// Obter estatísticas do usuário para o perfil
app.get("/make-server-ea835390/user/stats", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    const user = await getUserFromToken(authHeader);
    
    if (!user) {
      console.error('[USER/STATS] Não autorizado');
      return c.json({ success: false, error: 'Não autorizado' }, 401);
    }
    
    console.log(`[USER/STATS] Buscando estatísticas do usuário ${user.email}`);
    
    // MODO DEMO: Retorna dados mockados
    if (user.id === 'demo-user-ecovision-2024') {
      console.log('[USER/STATS] Modo demo detectado - retornando dados mockados');
      return c.json({ 
        success: true, 
        stats: {
          totalSessions: 0,
          totalDetections: 0,
          totalProcessed: 0,
          lastSession: null,
          favoriteConfiguration: null
        }
      });
    }
    
    // Total de sessões
    const { count: totalSessions } = await supabase
      .from('user_sessions')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id);
    
    // Total de detecções
    const { count: totalDetections } = await supabase
      .from('inferences')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id);
    
    // Itens processados (detecções com cancela acionada)
    const { count: totalProcessed } = await supabase
      .from('inferences')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id)
      .eq('gate_activated', true);
    
    // Última sessão
    const { data: lastSessionData } = await supabase
      .from('user_sessions')
      .select('started_at')
      .eq('user_id', user.id)
      .order('started_at', { ascending: false })
      .limit(1);
    
    const lastSession = lastSessionData && lastSessionData.length > 0 
      ? lastSessionData[0].started_at 
      : null;
    
    // Configuração favorita (mais usada)
    const { data: configurations } = await supabase
      .from('configurations')
      .select('*')
      .eq('user_id', user.id)
      .order('updated_at', { ascending: false })
      .limit(1);
    
    const favoriteConfiguration = configurations && configurations.length > 0
      ? {
          cancela1: configurations[0].cancela1_material,
          cancela2: configurations[0].cancela2_material,
          cancela3: configurations[0].cancela3_material,
          minAccuracy: configurations[0].min_confidence,
          modelVersion: configurations[0].model_version
        }
      : null;
    
    const stats = {
      totalSessions: totalSessions || 0,
      totalDetections: totalDetections || 0,
      totalProcessed: totalProcessed || 0,
      lastSession,
      favoriteConfiguration
    };
    
    console.log(`[USER/STATS] Estatísticas carregadas: ${totalSessions} sessões, ${totalDetections} detecções`);
    
    return c.json({ 
      success: true, 
      stats 
    });
    
  } catch (error) {
    console.error('[USER/STATS] Erro ao buscar estatísticas:', error);
    return c.json({ success: false, error: String(error) }, 500);
  }
});

// Start the server
Deno.serve(app.fetch);
