import { OutputData } from "./OutputData.tsx";
import { BancoDeDados } from "./BancoDeDados.tsx";
import { IAtuador } from "./Atuador.tsx";

/**
 * Classe ModeloIA - Gerencia modelo YOLO e decisões de acionamento
 */
export class ModeloIA {
  nome: string;
  versao: string;
  ativo: boolean;
  limiteMinAccuracy: number;
  model: any;
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
    this.model = { loaded: true, path: caminho, version: this.versao };
  }

  preverFrame(frame: any): OutputData {
    if (!this.ativo || !this.model) {
      throw new Error("Modelo não está ativo");
    }
    
    const classes = ["papel", "metal", "plastico", "vidro"];
    const classePrevista = classes[Math.floor(Math.random() * classes.length)];
    const confianca = Math.random() * 40 + 60;
    
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
    if (pred.getConfianca() < this.limiteMinAccuracy) {
      return false;
    }
    
    const materialCancela = cancelaData[cancelaId];
    return materialCancela === pred.getClasse();
  }

  async executarAcionamento(cancelaId: number): Promise<void> {
    try {
      this.atuador.abrirCancela(cancelaId);
      await new Promise(resolve => setTimeout(resolve, 2000));
      this.atuador.fecharCancela(cancelaId);
      console.log(`Acionamento da cancela ${cancelaId} concluído`);
    } catch (error) {
      console.error(`Erro ao acionar cancela ${cancelaId}:`, error);
      throw error;
    }
  }
}
