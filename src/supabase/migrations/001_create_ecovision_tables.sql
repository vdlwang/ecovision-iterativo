-- ==================== ECOVISION DATABASE SCHEMA ====================
-- Criação das tabelas principais do sistema EcoVision
-- Data: 2025-11-08
-- Versão: 1.0.0

-- ==================== EXTENSÕES ====================

-- Habilita UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==================== TABELA: PROFILES ====================
-- Perfil do usuário com dados adicionais

CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    avatar_url TEXT,
    phone VARCHAR(20),
    company VARCHAR(255),
    role VARCHAR(100),
    preferences JSONB DEFAULT '{}'::jsonb,
    total_sessions INTEGER DEFAULT 0,
    last_session_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_profiles_updated_at ON public.profiles(updated_at DESC);

-- RLS (Row Level Security)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Políticas RLS
CREATE POLICY "Users can view own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON public.profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Comentários
COMMENT ON TABLE public.profiles IS 'Dados adicionais do perfil do usuário';
COMMENT ON COLUMN public.profiles.preferences IS 'Configurações do usuário em JSON: theme, notifications, default_model';
COMMENT ON COLUMN public.profiles.total_sessions IS 'Contador de sessões do usuário';

-- ==================== TABELA: USER_SESSIONS ====================
-- Rastreamento de sessões do usuário

CREATE TABLE IF NOT EXISTS public.user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    ip_address VARCHAR(45),
    user_agent TEXT,
    device_info JSONB DEFAULT '{}'::jsonb,
    inferences_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_session_end CHECK (ended_at IS NULL OR ended_at > started_at),
    CONSTRAINT check_inferences_count CHECK (inferences_count >= 0)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON public.user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON public.user_sessions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON public.user_sessions(session_token);

-- RLS
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own sessions" ON public.user_sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own sessions" ON public.user_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own sessions" ON public.user_sessions
    FOR UPDATE USING (auth.uid() = user_id);

-- Comentários
COMMENT ON TABLE public.user_sessions IS 'Rastreamento de sessões dos usuários';
COMMENT ON COLUMN public.user_sessions.device_info IS 'Informações do dispositivo em JSON: browser, os, screen';
COMMENT ON COLUMN public.user_sessions.duration_seconds IS 'Duração da sessão em segundos (calculado por trigger)';

-- ==================== TABELA: INFERENCES ====================
-- Registro de cada inferência realizada pelo modelo IA

CREATE TABLE IF NOT EXISTS public.inferences (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES public.user_sessions(id) ON DELETE SET NULL,
    material_detected VARCHAR(50) NOT NULL,
    confidence DECIMAL(5,2) NOT NULL,
    gate_number INTEGER NOT NULL,
    gate_activated BOOLEAN DEFAULT FALSE,
    model_version VARCHAR(20),
    processing_time_ms INTEGER,
    image_url TEXT,
    bounding_box JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_confidence CHECK (confidence >= 0 AND confidence <= 100),
    CONSTRAINT check_gate_number CHECK (gate_number IN (1, 2, 3)),
    CONSTRAINT check_material CHECK (material_detected IN ('papel', 'metal', 'plastico', 'vidro'))
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_inferences_user_timestamp ON public.inferences(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_inferences_session_id ON public.inferences(session_id);
CREATE INDEX IF NOT EXISTS idx_inferences_material ON public.inferences(material_detected);
CREATE INDEX IF NOT EXISTS idx_inferences_timestamp ON public.inferences(timestamp DESC);

-- RLS
ALTER TABLE public.inferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own inferences" ON public.inferences
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own inferences" ON public.inferences
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Comentários
COMMENT ON TABLE public.inferences IS 'Registro de cada detecção realizada pelo modelo IA';
COMMENT ON COLUMN public.inferences.confidence IS 'Confiança da detecção de 0.00 a 100.00';
COMMENT ON COLUMN public.inferences.bounding_box IS 'Coordenadas do bounding box em JSON: {x, y, width, height}';
COMMENT ON COLUMN public.inferences.processing_time_ms IS 'Tempo de processamento da inferência em milissegundos';

-- ==================== TABELA: SYSTEM_CONFIG ====================
-- Configurações do sistema por usuário

CREATE TABLE IF NOT EXISTS public.system_config (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    gate_1_material VARCHAR(50),
    gate_2_material VARCHAR(50),
    gate_3_material VARCHAR(50),
    min_confidence INTEGER DEFAULT 85,
    model_version VARCHAR(20) DEFAULT 'YOLOv8n',
    auto_start BOOLEAN DEFAULT FALSE,
    notification_enabled BOOLEAN DEFAULT TRUE,
    config_data JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_min_confidence CHECK (min_confidence >= 50 AND min_confidence <= 100),
    CONSTRAINT check_model_version CHECK (model_version IN ('YOLOv8n', 'YOLOv8s', 'YOLOv8m')),
    CONSTRAINT unique_active_config UNIQUE (user_id, is_active)
);

-- Índice
CREATE INDEX IF NOT EXISTS idx_config_user_active ON public.system_config(user_id, is_active);

-- RLS
ALTER TABLE public.system_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own config" ON public.system_config
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own config" ON public.system_config
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own config" ON public.system_config
    FOR UPDATE USING (auth.uid() = user_id);

-- Comentários
COMMENT ON TABLE public.system_config IS 'Configurações do sistema por usuário';
COMMENT ON COLUMN public.system_config.min_confidence IS 'Confiança mínima para acionamento (50-100)';
COMMENT ON COLUMN public.system_config.is_active IS 'Apenas uma configuração ativa por usuário';

-- ==================== TABELA: STATISTICS ====================
-- Estatísticas agregadas diárias

CREATE TABLE IF NOT EXISTS public.statistics (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES public.user_sessions(id) ON DELETE SET NULL,
    date DATE NOT NULL,
    total_inferences INTEGER DEFAULT 0,
    papel_count INTEGER DEFAULT 0,
    metal_count INTEGER DEFAULT 0,
    plastico_count INTEGER DEFAULT 0,
    vidro_count INTEGER DEFAULT 0,
    gate_1_count INTEGER DEFAULT 0,
    gate_2_count INTEGER DEFAULT 0,
    gate_3_count INTEGER DEFAULT 0,
    avg_confidence DECIMAL(5,2),
    avg_processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_user_date UNIQUE (user_id, date),
    CONSTRAINT check_avg_confidence CHECK (avg_confidence IS NULL OR (avg_confidence >= 0 AND avg_confidence <= 100))
);

-- Índices
CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_user_date ON public.statistics(user_id, date);
CREATE INDEX IF NOT EXISTS idx_stats_date ON public.statistics(date DESC);

-- RLS
ALTER TABLE public.statistics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own statistics" ON public.statistics
    FOR SELECT USING (auth.uid() = user_id);

-- Comentários
COMMENT ON TABLE public.statistics IS 'Estatísticas agregadas por usuário por dia';
COMMENT ON COLUMN public.statistics.date IS 'Data da agregação (apenas data, sem hora)';

-- ==================== TABELA: SYSTEM_LOGS ====================
-- Logs do sistema para auditoria e debugging

CREATE TABLE IF NOT EXISTS public.system_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES public.user_sessions(id) ON DELETE SET NULL,
    log_level VARCHAR(20) NOT NULL,
    log_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}'::jsonb,
    stack_trace TEXT,
    ip_address VARCHAR(45),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_log_level CHECK (log_level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    CONSTRAINT check_log_type CHECK (log_type IN ('AUTH', 'INFERENCE', 'SYSTEM', 'HARDWARE', 'API'))
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_logs_user_timestamp ON public.system_logs(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_level ON public.system_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_logs_type ON public.system_logs(log_type);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON public.system_logs(timestamp DESC);

-- RLS
ALTER TABLE public.system_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own logs" ON public.system_logs
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "System can insert logs" ON public.system_logs
    FOR INSERT WITH CHECK (true); -- Permite inserção por qualquer processo autenticado

-- Comentários
COMMENT ON TABLE public.system_logs IS 'Logs do sistema para auditoria e debugging';
COMMENT ON COLUMN public.system_logs.details IS 'Contexto adicional em JSON';
COMMENT ON COLUMN public.system_logs.log_level IS 'DEBUG, INFO, WARNING, ERROR ou CRITICAL';

-- ==================== TRIGGERS ====================

-- Trigger: Atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger em tabelas relevantes
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_config_updated_at BEFORE UPDATE ON public.system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_statistics_updated_at BEFORE UPDATE ON public.statistics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Calcular duração da sessão
CREATE OR REPLACE FUNCTION calculate_session_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ended_at IS NOT NULL AND OLD.ended_at IS NULL THEN
        NEW.duration_seconds := EXTRACT(EPOCH FROM (NEW.ended_at - NEW.started_at))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_duration BEFORE UPDATE ON public.user_sessions
    FOR EACH ROW EXECUTE FUNCTION calculate_session_duration();

-- Trigger: Incrementar contador de sessões no perfil
CREATE OR REPLACE FUNCTION increment_session_counter()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ended_at IS NOT NULL AND OLD.ended_at IS NULL THEN
        UPDATE public.profiles
        SET total_sessions = total_sessions + 1,
            last_session_at = NEW.ended_at
        WHERE id = NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_increment_counter AFTER UPDATE ON public.user_sessions
    FOR EACH ROW EXECUTE FUNCTION increment_session_counter();

-- Trigger: Criar perfil automaticamente após registro
CREATE OR REPLACE FUNCTION create_profile_for_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, avatar_url)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'name', NEW.raw_user_meta_data->>'full_name'),
        NEW.raw_user_meta_data->>'avatar_url'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_create_profile AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION create_profile_for_user();

-- ==================== VIEWS ====================

-- View: Dashboard do usuário
CREATE OR REPLACE VIEW public.v_user_dashboard AS
SELECT
    u.id,
    p.full_name,
    p.total_sessions,
    COUNT(DISTINCT CASE WHEN s.ended_at IS NULL THEN s.id END) as active_sessions,
    COUNT(i.id) as total_inferences,
    AVG(i.confidence) as avg_confidence
FROM auth.users u
JOIN public.profiles p ON u.id = p.id
LEFT JOIN public.user_sessions s ON u.id = s.user_id
LEFT JOIN public.inferences i ON u.id = i.user_id
GROUP BY u.id, p.full_name, p.total_sessions;

COMMENT ON VIEW public.v_user_dashboard IS 'Visão geral do dashboard do usuário';

-- View: Resumo de sessão
CREATE OR REPLACE VIEW public.v_session_summary AS
SELECT
    s.id,
    s.user_id,
    s.started_at,
    s.ended_at,
    s.duration_seconds,
    COUNT(i.id) as inferences_count,
    AVG(i.confidence) as avg_confidence,
    SUM(CASE WHEN i.gate_activated THEN 1 ELSE 0 END) as activations_count
FROM public.user_sessions s
LEFT JOIN public.inferences i ON s.id = i.session_id
GROUP BY s.id;

COMMENT ON VIEW public.v_session_summary IS 'Resumo estatístico de cada sessão';

-- View: Estatísticas por material
CREATE OR REPLACE VIEW public.v_material_stats AS
SELECT
    user_id,
    material_detected,
    DATE(timestamp) as date,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    MIN(confidence) as min_confidence,
    MAX(confidence) as max_confidence
FROM public.inferences
GROUP BY user_id, material_detected, DATE(timestamp);

COMMENT ON VIEW public.v_material_stats IS 'Estatísticas agregadas por material detectado';

-- ==================== DADOS INICIAIS ====================

-- Nenhum dado inicial necessário
-- As tabelas serão populadas automaticamente pelo sistema

-- ==================== VERIFICAÇÕES ====================

-- Verificar se todas as tabelas foram criadas
DO $$
BEGIN
    ASSERT (SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('profiles', 'user_sessions', 'inferences', 
                               'system_config', 'statistics', 'system_logs')) = 6,
    'Nem todas as tabelas foram criadas!';
    
    RAISE NOTICE 'Migração concluída com sucesso! Todas as 6 tabelas foram criadas.';
END $$;
