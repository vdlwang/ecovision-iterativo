import { ControladorSerial } from "./Atuador.tsx";

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
