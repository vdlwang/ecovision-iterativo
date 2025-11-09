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
