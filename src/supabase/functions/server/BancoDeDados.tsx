import { RegistroProcessamento } from "./RegistroProcessamento.tsx";

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
