/**
 * Classe Camera - Gerencia captura de vídeo e imagens
 */
export class Camera {
  fps: number;
  cap: any;
  resolucao: [number, number];
  
  constructor(fps: number = 30, resolucao: [number, number] = [640, 480]) {
    this.fps = fps;
    this.resolucao = resolucao;
    this.cap = null;
  }

  iniciarStream(source: number = 0): void {
    console.log(`Iniciando stream da câmera ${source} com resolução ${this.resolucao}`);
    this.cap = { active: true, source };
  }

  capturarImagem(): any {
    if (!this.is_ativa()) {
      throw new Error("Câmera não está ativa");
    }
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
