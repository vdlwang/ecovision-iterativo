import { ReactNode, useEffect, useRef, useState } from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Slider } from './ui/slider';
import { Lock, ScanEye } from 'lucide-react';

// Estado de um controle da câmera lido pelo backend; valor null no automático
export interface EstadoAjuste {
  auto: boolean;
  valor: number | null;
}

export type ModoAjuste = 'auto' | 'travar' | 'manual';

// Arrastando o slider, no máximo um pedido a cada tanto (cada um grava o config.json)
const INTERVALO_MS = 150;
// Passos do slider em escala logarítmica
const PASSOS_LOG = 1000;

interface Props {
  titulo: string;
  rotulo: string;
  estado: EstadoAjuste | null;
  desabilitado: boolean;
  min: number;
  max: number;
  // Escala logarítmica no slider (exposição: os valores úteis ficam embaixo)
  log?: boolean;
  // Complemento do badge com o valor fixo (ex.: o ganho)
  detalheFixo?: string;
  ajuda: string;
  onPedir: (modo: ModoAjuste, valor?: number) => void;
  // Controles a mais no card, abaixo do slider (ex.: o ganho na exposição)
  children?: ReactNode;
}

/**
 * Card de um controle da câmera (foco, exposição): Travar desliga o automático
 * no valor em que ele está, Automático o religa, e o slider põe o valor à mão.
 */
export function AjusteCamera({ titulo, rotulo, estado, desabilitado, min, max, log = false,
                               detalheFixo, ajuda, onPedir, children }: Props) {
  return (
    <Card className="bg-neutral-900 border-neutral-800 p-4 md:p-6">
      <h3 className="text-white mb-3 md:mb-4 text-base md:text-lg">{titulo}</h3>

      <div className="space-y-4">
        <div className="flex items-center justify-between p-3 md:p-4 bg-neutral-800 rounded-lg">
          <span className="text-neutral-300 text-sm md:text-base">{rotulo}</span>
          <Badge className={!estado ? 'bg-neutral-600' : estado.auto ? 'bg-blue-600' : 'bg-green-600'}>
            {!estado ? 'N/A' : estado.auto ? 'Automático'
              : `Fixo em ${Math.round(estado.valor ?? 0)}${detalheFixo ? ` · ${detalheFixo}` : ''}`}
          </Badge>
        </div>

        <div className="grid grid-cols-2 gap-2 md:gap-3">
          <Button
            onClick={() => onPedir('travar')}
            disabled={desabilitado || !estado?.auto}
            className="bg-green-600 hover:bg-green-700 text-white text-sm md:text-base"
          >
            <Lock className="w-3 h-3 md:w-4 md:h-4 mr-2" />
            Travar
          </Button>
          <Button
            onClick={() => onPedir('auto')}
            disabled={desabilitado || estado?.auto}
            variant="outline"
            className="bg-neutral-800 border-neutral-700 text-white hover:bg-neutral-700 text-sm md:text-base"
          >
            <ScanEye className="w-3 h-3 md:w-4 md:h-4 mr-2" />
            Automático
          </Button>
        </div>

        <SliderAjuste
          rotulo="Ajuste manual"
          atual={estado?.valor ?? null}
          desabilitado={desabilitado}
          min={min}
          max={max}
          log={log}
          ajuda={ajuda}
          onMudar={(v) => onPedir('manual', v)}
        />
        {children}
      </div>
    </Card>
  );
}

interface PropsSlider {
  rotulo: string;
  // Valor lido do backend; null mantém o slider onde está
  atual: number | null;
  desabilitado: boolean;
  min: number;
  max: number;
  log?: boolean;
  ajuda: string;
  onMudar: (valor: number) => void;
}

/**
 * Slider de um valor da câmera: segue o backend a cada quadro (volta ao lido
 * se a câmera arredondou ou recusou), menos enquanto é arrastado; arrastando,
 * pede no máximo um ajuste a cada INTERVALO_MS, e o valor final ao soltar.
 */
export function SliderAjuste({ rotulo, atual, desabilitado, min, max, log = false, ajuda,
                               onMudar }: PropsSlider) {
  // Posição 0..PASSOS_LOG (log) ou o próprio valor (linear)
  const paraSlider = (v: number) => log
    ? Math.round(PASSOS_LOG * Math.log(Math.min(Math.max(v, min), max) / min) / Math.log(max / min))
    : v;
  const doSlider = (p: number) => log
    ? Math.round(min * Math.pow(max / min, p / PASSOS_LOG))
    : p;

  const [valor, setValor] = useState(min);
  const arrastando = useRef(false);
  const ultimoEnvio = useRef(0);
  useEffect(() => {
    if (atual != null && !arrastando.current) setValor(atual);
  }, [atual]);

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-neutral-400">
        <span>{rotulo}</span>
        <span>{Math.round(valor)}</span>
      </div>
      <Slider
        min={log ? 0 : min}
        max={log ? PASSOS_LOG : max}
        step={1}
        value={[paraSlider(valor)]}
        disabled={desabilitado}
        onValueChange={([p]) => {
          const v = doSlider(p);
          arrastando.current = true;
          setValor(v);
          const agora = Date.now();
          if (agora - ultimoEnvio.current >= INTERVALO_MS) {
            ultimoEnvio.current = agora;
            onMudar(v);
          }
        }}
        onValueCommit={([p]) => {
          arrastando.current = false;
          onMudar(doSlider(p));
        }}
      />
      <p className="text-neutral-500 text-xs">{ajuda}</p>
    </div>
  );
}
