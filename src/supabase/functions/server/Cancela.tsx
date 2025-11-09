import { ControladorSerial } from "./Atuador.tsx";

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
