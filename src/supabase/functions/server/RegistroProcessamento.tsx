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
