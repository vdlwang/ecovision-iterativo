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
