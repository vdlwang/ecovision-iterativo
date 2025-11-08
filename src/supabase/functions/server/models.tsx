// ==================== CLASSES DO SISTEMA ECOVISION ====================

/**
 * Classe Camera - Gerencia captura de vídeo e imagens
 */
export class Camera {
  fps: number;
  cap: any; // VideoCapture equivalente
  resolucao: [number, number];
  
  constructor(fps: number = 30, resolucao: [number, number] = [640, 480]) {
    this.fps = fps;
    this.resolucao = resolucao;
    this.cap = null;
  }

  iniciarStream(source: number = 0): void {
    console.log(`Iniciando stream da câmera ${source} com resolução ${this.resolucao}`);
    // Simulação - em produção, conectaria com hardware real
    this.cap = { active: true, source };
  }

  capturarImagem(): any {
    if (!this.is_ativa()) {
      throw new Error("Câmera não está ativa");
    }
    // Retorna frame simulado
    return { timestamp: new Date(), data: "frame_data" };
  }

  pararStream(): void {
    if (this.cap) {
      console.log("Parando stream da câmera");
      this.cap = null;
    }
  }

  is_ativa(): boolean {
    return this.cap !== null && this.cap.active;
  }
}

/**
 * Classe Usuario - Gerencia informação do usuário autenticado
 */
export class Usuario {
  id: string;
  name: string;
  email: string;
  autenticado: boolean;

  constructor(id: string, name: string, email: string, autenticado: boolean = false) {
    this.id = id;
    this.name = name;
    this.email = email;
    this.autenticado = autenticado;
  }

  to_dict(): Record<string, any> {
    return {
      id: this.id,
      name: this.name,
      email: this.email,
      autenticado: this.autenticado
    };
  }
}

/**
 * Classe OutputData - Representa resultado de uma detecção
 */
export class OutputData {
  classePrevista: string;
  confianca: number;

  constructor(classePrevista: string, confianca: number) {
    this.classePrevista = classePrevista;
    this.confianca = confianca;
  }

  getClasse(): string {
    return this.classePrevista;
  }

  getConfianca(): number {
    return this.confianca;
  }
}

/**
 * Interface IAtuador - Define contrato para controle de hardware
 */
export interface IAtuador {
  ligarEsteira(): void;
  desligarEsteira(): void;
  abrirCancela(cancelaId: number): void;
  fecharCancela(cancelaId: number): void;
}

/**
 * Classe ControladorSerial - Implementa controle via porta serial
 */
export class ControladorSerial implements IAtuador {
  portaSerial: string;
  baudRate: number;
  ser: any;

  constructor(portaSerial: string, baudRate: number = 9600) {
    this.portaSerial = portaSerial;
    this.baudRate = baudRate;
    this.ser = null;
  }

  conectar(): boolean {
    try {
      console.log(`Conectando à porta serial ${this.portaSerial} @ ${this.baudRate} baud`);
      // Simulação - em produção, usaria biblioteca serial real
      this.ser = { connected: true, port: this.portaSerial };
      return true;
    } catch (error) {
      console.error("Erro ao conectar porta serial:", error);
      return false;
    }
  }

  enviarComando(comando: string): void {
    if (!this.ser || !this.ser.connected) {
      throw new Error("Porta serial não conectada");
    }
    console.log(`Enviando comando: ${comando}`);
    // Simulação do envio de comando
  }

  ligarEsteira(): void {
    this.enviarComando("LIGAR_ESTEIRA");
  }

  desligarEsteira(): void {
    this.enviarComando("DESLIGAR_ESTEIRA");
  }

  abrirCancela(cancelaId: number): void {
    this.enviarComando(`ABRIR_CANCELA_${cancelaId}`);
  }

  fecharCancela(cancelaId: number): void {
    this.enviarComando(`FECHAR_CANCELA_${cancelaId}`);
  }
}

/**
 * Classe Esteira - Representa a esteira rolante
 */
export class Esteira {
  status: string;
  velocidade: number;
  controlador: ControladorSerial;

  constructor(controlador: ControladorSerial, velocidade: number = 50) {
    this.status = "desligada";
    this.velocidade = velocidade;
    this.controlador = controlador;
  }

  ligar(): void {
    this.controlador.ligarEsteira();
    this.status = "ligada";
    console.log(`Esteira ligada a ${this.velocidade}% de velocidade`);
  }

  desligar(): void {
    this.controlador.desligarEsteira();
    this.status = "desligada";
    console.log("Esteira desligada");
  }
}

/**
 * Classe Cancela - Representa uma cancela de separação
 */
export class Cancela {
  cancela_id: number;
  status: string;
  controlador: ControladorSerial;

  constructor(cancela_id: number, controlador: ControladorSerial) {
    this.cancela_id = cancela_id;
    this.status = "fechada";
    this.controlador = controlador;
  }

  abrir(): void {
    this.controlador.abrirCancela(this.cancela_id);
    this.status = "aberta";
    console.log(`Cancela ${this.cancela_id} aberta`);
  }

  fechar(): void {
    this.controlador.fecharCancela(this.cancela_id);
    this.status = "fechada";
    console.log(`Cancela ${this.cancela_id} fechada`);
  }
}

/**
 * Classe RegistroProcessamento - Representa um registro no banco de dados
 */
export class RegistroProcessamento {
  id: number;
  material: string;
  precisao: number;
  cancela_id: number;
  data: Date;

  constructor(
    id: number,
    material: string,
    precisao: number,
    cancela_id: number,
    data: Date = new Date()
  ) {
    this.id = id;
    this.material = material;
    this.precisao = precisao;
    this.cancela_id = cancela_id;
    this.data = data;
  }

  toJSON() {
    return {
      id: this.id,
      material: this.material,
      precisao: this.precisao,
      cancela_id: this.cancela_id,
      data: this.data.toISOString()
    };
  }
}

/**
 * Classe BancoDeDados - Gerencia persistência de dados
 */
export class BancoDeDados {
  private kvStore: any;

  constructor(kvStore: any) {
    this.kvStore = kvStore;
  }

  async registrarProcessamento(
    material: string,
    precisao: number,
    cancelaId: number
  ): Promise<void> {
    const id = Date.now();
    const registro = new RegistroProcessamento(id, material, precisao, cancelaId);
    
    await this.kvStore.set(`processamento_${id}`, registro.toJSON());
    console.log(`Processamento registrado: ${material} com ${precisao}% na cancela ${cancelaId}`);
  }

  async consultarItensProcessados(data: Date): Promise<number> {
    const prefix = "processamento_";
    const registros = await this.kvStore.getByPrefix(prefix);
    
    // Filtra por data
    const filtrados = registros.filter((r: any) => {
      const dataReg = new Date(r.data);
      return dataReg.toDateString() === data.toDateString();
    });
    
    return filtrados.length;
  }

  async consultarMateriais(data: Date): Promise<Record<string, number>> {
    const prefix = "processamento_";
    const registros = await this.kvStore.getByPrefix(prefix);
    
    const materiais: Record<string, number> = {};
    
    registros.forEach((r: any) => {
      const dataReg = new Date(r.data);
      if (dataReg.toDateString() === data.toDateString()) {
        materiais[r.material] = (materiais[r.material] || 0) + 1;
      }
    });
    
    return materiais;
  }

  async consultarPerformanceCancelas(data: Date): Promise<Record<string, number>> {
    const prefix = "processamento_";
    const registros = await this.kvStore.getByPrefix(prefix);
    
    const performance: Record<string, number> = {};
    
    registros.forEach((r: any) => {
      const dataReg = new Date(r.data);
      if (dataReg.toDateString() === data.toDateString()) {
        const key = `cancela_${r.cancela_id}`;
        performance[key] = (performance[key] || 0) + 1;
      }
    });
    
    return performance;
  }

  async consultarPrecisaoMedia(data: Date): Promise<number> {
    const prefix = "processamento_";
    const registros = await this.kvStore.getByPrefix(prefix);
    
    const filtrados = registros.filter((r: any) => {
      const dataReg = new Date(r.data);
      return dataReg.toDateString() === data.toDateString();
    });
    
    if (filtrados.length === 0) return 0;
    
    const soma = filtrados.reduce((acc: number, r: any) => acc + r.precisao, 0);
    return soma / filtrados.length;
  }
}

/**
 * Classe ModeloIA - Gerencia modelo YOLO e decisões de acionamento
 */
export class ModeloIA {
  nome: string;
  versao: string;
  ativo: boolean;
  limiteMinAccuracy: number;
  model: any; // YOLO model
  db: BancoDeDados;
  atuador: IAtuador;

  constructor(
    nome: string,
    versao: string,
    limiteMinAccuracy: number,
    db: BancoDeDados,
    atuador: IAtuador
  ) {
    this.nome = nome;
    this.versao = versao;
    this.ativo = false;
    this.limiteMinAccuracy = limiteMinAccuracy;
    this.model = null;
    this.db = db;
    this.atuador = atuador;
  }

  ativar(): void {
    this.ativo = true;
    console.log(`Modelo ${this.nome} ${this.versao} ativado`);
  }

  desativar(): void {
    this.ativo = false;
    console.log(`Modelo ${this.nome} ${this.versao} desativado`);
  }

  carregarModelo(caminho: string): void {
    console.log(`Carregando modelo de ${caminho}`);
    // Simulação - em produção, carregaria modelo YOLO real
    this.model = { loaded: true, path: caminho, version: this.versao };
  }

  preverFrame(frame: any): OutputData {
    if (!this.ativo || !this.model) {
      throw new Error("Modelo não está ativo");
    }
    
    // Simulação de predição
    const classes = ["papel", "metal", "plastico", "vidro"];
    const classePrevista = classes[Math.floor(Math.random() * classes.length)];
    const confianca = Math.random() * 40 + 60; // 60-100%
    
    return new OutputData(classePrevista, confianca);
  }

  calibrarLimite(limite: number): void {
    if (limite < 0 || limite > 100) {
      throw new Error("Limite deve estar entre 0 e 100");
    }
    this.limiteMinAccuracy = limite;
    console.log(`Limite de acurácia ajustado para ${limite}%`);
  }

  decidirAcionamento(
    pred: OutputData,
    cancelaData: Record<number, string>,
    cancelaId: number
  ): boolean {
    // Verifica se a confiança está acima do limite
    if (pred.getConfianca() < this.limiteMinAccuracy) {
      return false;
    }
    
    // Verifica se a cancela está configurada para este material
    const materialCancela = cancelaData[cancelaId];
    return materialCancela === pred.getClasse();
  }

  async executarAcionamento(cancelaId: number): Promise<void> {
    try {
      this.atuador.abrirCancela(cancelaId);
      
      // Aguarda 2 segundos
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      this.atuador.fecharCancela(cancelaId);
      console.log(`Acionamento da cancela ${cancelaId} concluído`);
    } catch (error) {
      console.error(`Erro ao acionar cancela ${cancelaId}:`, error);
      throw error;
    }
  }
}

/**
 * Classe Dashboard - Gerencia visualização de dados
 */
export class Dashboard {
  db: BancoDeDados;

  constructor(db: BancoDeDados) {
    this.db = db;
  }

  async coletarVisaoGeral(): Promise<Record<string, any>> {
    const hoje = new Date();
    
    const [
      totalProcessados,
      materiais,
      performanceCancelas,
      precisaoMedia
    ] = await Promise.all([
      this.db.consultarItensProcessados(hoje),
      this.db.consultarMateriais(hoje),
      this.db.consultarPerformanceCancelas(hoje),
      this.db.consultarPrecisaoMedia(hoje)
    ]);
    
    return {
      totalProcessados,
      materiais,
      performanceCancelas,
      precisaoMedia,
      data: hoje.toISOString()
    };
  }

  exibirStatusGeral(): Record<string, any> {
    return {
      sistema: "EcoVision",
      versao: "1.0.0",
      status: "operacional",
      timestamp: new Date().toISOString()
    };
  }

  async exibirMateriaisReciclados(data: Date): Promise<Record<string, number>> {
    return await this.db.consultarMateriais(data);
  }

  async exibirPerformanceCancelas(data: Date): Promise<Record<string, number>> {
    return await this.db.consultarPerformanceCancelas(data);
  }
}

/**
 * Classe Autenticacao - Gerencia autenticação de usuários
 */
export class Autenticacao {
  google_client_id: string;
  private _sessions: Map<string, Record<string, any>>;

  constructor(google_client_id: string) {
    this.google_client_id = google_client_id;
    this._sessions = new Map();
  }

  loginComGoogle(tokenGoogle: string): Record<string, any> {
    // Simulação - em produção, validaria o token com Google OAuth
    console.log("Processando login com Google...");
    
    const usuario = {
      id: `user_${Date.now()}`,
      name: "Usuário Demo",
      email: "demo@ecovision.com",
      autenticado: true
    };
    
    const sessionId = `session_${Date.now()}`;
    this._sessions.set(sessionId, usuario);
    
    return { sessionId, usuario };
  }

  logout(usuario: Usuario): void {
    // Remove sessão do usuário
    for (const [sessionId, sessionData] of this._sessions.entries()) {
      if (sessionData.id === usuario.id) {
        this._sessions.delete(sessionId);
        console.log(`Logout realizado para usuário ${usuario.email}`);
        return;
      }
    }
  }

  logout_try(email: string): void {
    // Tenta fazer logout por email
    for (const [sessionId, sessionData] of this._sessions.entries()) {
      if (sessionData.email === email) {
        this._sessions.delete(sessionId);
        console.log(`Logout realizado para ${email}`);
        return;
      }
    }
    console.log(`Nenhuma sessão encontrada para ${email}`);
  }

  is_autenticado(email: string): boolean {
    for (const sessionData of this._sessions.values()) {
      if (sessionData.email === email && sessionData.autenticado) {
        return true;
      }
    }
    return false;
  }
}
