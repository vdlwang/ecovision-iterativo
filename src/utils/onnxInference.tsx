// EcoVision ONNX Inference Service - Browser-based YOLOv8 Inference
import * as ort from 'onnxruntime-web';

interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface Detection {
  class_name: string;
  material: string;
  confidence: number;
  bounding_box: BoundingBox;
}

interface InferenceResult {
  success: boolean;
  detections: Detection[];
  processing_time_ms: number;
  error?: string;
}

// Mapeamento de classes YOLO para materiais
const CLASS_TO_MATERIAL: Record<number, string> = {
  0: 'papel',      // Papel/Papelão
  1: 'metal',      // Metal
  2: 'plastico',   // Plástico
  3: 'vidro'       // Vidro
};

const MATERIAL_NAMES: Record<string, string> = {
  papel: 'Papel/Papelão',
  metal: 'Metal',
  plastico: 'Plástico',
  vidro: 'Vidro'
};

class ONNXInferenceService {
  private session: ort.InferenceSession | null = null;
  private modelLoaded: boolean = false;
  private modelVersion: string = 'v1';
  private inputSize: number = 640; // YOLOv8 default input size

  /**
   * Carrega o modelo ONNX
   * @param modelPath Caminho para o arquivo .onnx (ex: '/models/yolov8n.onnx')
   */
  async loadModel(modelPath: string): Promise<void> {
    try {
      console.log(`[ONNX] Carregando modelo: ${modelPath}...`);
      
      // Configura o ambiente ONNX Runtime com múltiplos fallbacks para WASM
      // Tenta carregar do CDN unpkg primeiro, depois jsDelivr
      ort.env.wasm.numThreads = 1; // Use single thread para compatibilidade
      ort.env.wasm.simd = false; // Desabilita SIMD para maior compatibilidade
      
      // Tenta carregar do unpkg (mais confiável)
      try {
        ort.env.wasm.wasmPaths = 'https://unpkg.com/onnxruntime-web@1.16.3/dist/';
        console.log('[ONNX] Tentando carregar WASM de unpkg.com...');
      } catch {
        console.log('[ONNX] Fallback: usando jsDelivr...');
        ort.env.wasm.wasmPaths = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.16.3/dist/';
      }
      
      this.session = await ort.InferenceSession.create(modelPath, {
        executionProviders: ['wasm'],
        graphOptimizationLevel: 'all'
      });
      
      this.modelLoaded = true;
      console.log('[ONNX] ✅ Modelo carregado com sucesso');
    } catch (error) {
      console.error('[ONNX] ❌ Erro ao carregar modelo:', error);
      console.warn('[ONNX] ℹ️ O modelo ONNX não está disponível. O sistema funcionará em modo servidor/mock.');
      console.warn('[ONNX] ℹ️ Para usar inferência local, certifique-se de:');
      console.warn('[ONNX]   1. Ter o arquivo /models/yolov8n.onnx no servidor');
      console.warn('[ONNX]   2. Estar em uma rede que permite acesso aos CDNs (unpkg.com ou jsdelivr.net)');
      throw new Error(`Falha ao carregar modelo ONNX: ${error}`);
    }
  }

  /**
   * Pré-processa a imagem para o formato esperado pelo YOLO
   */
  private preprocessImage(imageData: ImageData): Float32Array {
    const { width, height, data } = imageData;
    const input = new Float32Array(3 * this.inputSize * this.inputSize);
    
    // Redimensiona e normaliza a imagem
    for (let c = 0; c < 3; c++) {
      for (let y = 0; y < this.inputSize; y++) {
        for (let x = 0; x < this.inputSize; x++) {
          // Calcula posição na imagem original (redimensionamento simples)
          const srcX = Math.floor(x * width / this.inputSize);
          const srcY = Math.floor(y * height / this.inputSize);
          const srcIdx = (srcY * width + srcX) * 4;
          
          // Normaliza pixel (0-255 -> 0-1)
          const pixelValue = data[srcIdx + c] / 255.0;
          
          // Armazena no formato CHW (channels, height, width)
          const dstIdx = c * this.inputSize * this.inputSize + y * this.inputSize + x;
          input[dstIdx] = pixelValue;
        }
      }
    }
    
    return input;
  }

  /**
   * Pós-processa as saídas do YOLO para extrair detecções
   */
  private postprocessOutput(
    output: Float32Array,
    originalWidth: number,
    originalHeight: number,
    minConfidence: number
  ): Detection[] {
    const detections: Detection[] = [];
    const numDetections = output.length / 6; // [x, y, w, h, conf, class]
    
    for (let i = 0; i < numDetections; i++) {
      const idx = i * 6;
      const confidence = output[idx + 4] * 100;
      
      // Filtra por confiança mínima
      if (confidence < minConfidence) continue;
      
      const classId = Math.round(output[idx + 5]);
      const material = CLASS_TO_MATERIAL[classId];
      
      if (!material) continue;
      
      // Converte coordenadas normalizadas para pixels
      const x = output[idx] * originalWidth;
      const y = output[idx + 1] * originalHeight;
      const width = output[idx + 2] * originalWidth;
      const height = output[idx + 3] * originalHeight;
      
      detections.push({
        class_name: MATERIAL_NAMES[material],
        material: material,
        confidence: confidence,
        bounding_box: {
          x: x - width / 2,  // YOLO retorna centro, converter para canto superior esquerdo
          y: y - height / 2,
          width: width,
          height: height
        }
      });
    }
    
    // Aplica Non-Maximum Suppression (NMS) simples
    return this.applyNMS(detections, 0.45);
  }

  /**
   * Aplica Non-Maximum Suppression para remover detecções duplicadas
   */
  private applyNMS(detections: Detection[], iouThreshold: number): Detection[] {
    const sortedDetections = [...detections].sort((a, b) => b.confidence - a.confidence);
    const keep: Detection[] = [];
    
    for (const detection of sortedDetections) {
      let shouldKeep = true;
      
      for (const keptDetection of keep) {
        const iou = this.calculateIOU(detection.bounding_box, keptDetection.bounding_box);
        if (iou > iouThreshold && detection.material === keptDetection.material) {
          shouldKeep = false;
          break;
        }
      }
      
      if (shouldKeep) {
        keep.push(detection);
      }
    }
    
    return keep;
  }

  /**
   * Calcula IoU (Intersection over Union) entre duas bounding boxes
   */
  private calculateIOU(box1: BoundingBox, box2: BoundingBox): number {
    const x1 = Math.max(box1.x, box2.x);
    const y1 = Math.max(box1.y, box2.y);
    const x2 = Math.min(box1.x + box1.width, box2.x + box2.width);
    const y2 = Math.min(box1.y + box1.height, box2.y + box2.height);
    
    if (x2 < x1 || y2 < y1) return 0;
    
    const intersection = (x2 - x1) * (y2 - y1);
    const area1 = box1.width * box1.height;
    const area2 = box2.width * box2.height;
    const union = area1 + area2 - intersection;
    
    return intersection / union;
  }

  /**
   * Executa inferência em uma imagem
   */
  async runInference(
    imageData: ImageData,
    minConfidence: number = 50
  ): Promise<InferenceResult> {
    const startTime = performance.now();
    
    try {
      if (!this.modelLoaded || !this.session) {
        return {
          success: false,
          detections: [],
          processing_time_ms: 0,
          error: 'Modelo não carregado. Aguarde o carregamento ou use o modelo no servidor.'
        };
      }
      
      // Pré-processa a imagem
      const inputTensor = this.preprocessImage(imageData);
      
      // Cria tensor de entrada
      const tensor = new ort.Tensor('float32', inputTensor, [1, 3, this.inputSize, this.inputSize]);
      
      // Executa inferência
      const feeds = { images: tensor };
      const results = await this.session.run(feeds);
      
      // Pós-processa as saídas
      const outputData = results.output0.data as Float32Array;
      const detections = this.postprocessOutput(
        outputData,
        imageData.width,
        imageData.height,
        minConfidence
      );
      
      const processingTime = performance.now() - startTime;
      
      console.log(`[ONNX] ✅ Inferência concluída: ${detections.length} detecção(ões) em ${processingTime.toFixed(1)}ms`);
      
      return {
        success: true,
        detections: detections,
        processing_time_ms: processingTime
      };
      
    } catch (error) {
      console.error('[ONNX] ❌ Erro durante inferência:', error);
      const processingTime = performance.now() - startTime;
      
      return {
        success: false,
        detections: [],
        processing_time_ms: processingTime,
        error: `Erro durante inferência: ${error}`
      };
    }
  }

  /**
   * Verifica se o modelo está carregado
   */
  isReady(): boolean {
    return this.modelLoaded;
  }

  /**
   * Descarrega o modelo da memória
   */
  async unloadModel(): Promise<void> {
    if (this.session) {
      console.log('[ONNX] Descarregando modelo...');
      this.session = null;
      this.modelLoaded = false;
    }
  }
}

// Singleton instance
export const onnxInferenceService = new ONNXInferenceService();

// Helper function para converter base64 para ImageData
export async function base64ToImageData(base64: string): Promise<ImageData> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Falha ao criar contexto 2D'));
        return;
      }
      ctx.drawImage(img, 0, 0);
      const imageData = ctx.getImageData(0, 0, img.width, img.height);
      resolve(imageData);
    };
    img.onerror = reject;
    img.src = `data:image/jpeg;base64,${base64}`;
  });
}
