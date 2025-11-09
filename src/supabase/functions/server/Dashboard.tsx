import { BancoDeDados } from "./BancoDeDados.tsx";

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
