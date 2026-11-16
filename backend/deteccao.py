"""
Lógica de detecção sem dependências de hardware nem do YOLO: mapeamento
TACO -> material, filtro das caixas e decisão de disparar o servo.
Testada em backend/tests/.

O disparo é por objeto (T15): o YOLO roda com rastreamento (ByteTrack), cada
caixa traz o ID da trilha, e DisparosPorTrilha dispara o servo uma vez por
trilha, quando o centro dela está na faixa de acionamento ou a atravessou
desde o quadro anterior, com o material votado ao longo da trilha.
"""

# Trilha não vista há mais que isto é esquecida (s)
ESQUECER_TRILHA_S = 5.0
# Um ID novo que aparece até REIDENTIFICAR_S depois de uma trilha disparada
# sumir, sobrepondo a última caixa dela (IoU >= IOU_REIDENTIFICAR), é tido
# como o mesmo objeto (o rastreador o perdeu e o achou de novo com outro ID)
REIDENTIFICAR_S = 1.0
IOU_REIDENTIFICAR = 0.3

# ==== Mapeamento TACO -> material genérico ====
PLASTIC = "plastic"
METAL   = "metal"
GLASS   = "glass"
PAPER   = "paper"
OTHER   = "other"  # opcional

# Dicionário: nome da classe TACO (lowercase) -> grupo de material
taco_to_material = {
    # --- Metal ---
    "aluminium foil": METAL,
    "battery": METAL,
    "aluminium blister pack": METAL,
    "metal bottle cap": METAL,
    "food can": METAL,
    "aerosol": METAL,
    "drink can": METAL,
    "metal lid": METAL,
    "scrap metal": METAL,
    "pop tab": METAL,

    # --- Glass ---
    "glass bottle": GLASS,
    "broken glass": GLASS,
    "glass cup": GLASS,
    "glass jar": GLASS,

    # --- Paper / papel ---
    "toilet tube": PAPER,
    "other carton": PAPER,
    "egg carton": PAPER,
    "drink carton": PAPER,          # Tetrapak: aqui tratado como papel
    "corrugated carton": PAPER,
    "meal carton": PAPER,
    "pizza box": PAPER,
    "paper cup": PAPER,
    "magazine paper": PAPER,
    "tissues": PAPER,
    "wrapping paper": PAPER,
    "normal paper": PAPER,
    "paper bag": PAPER,
    "plastified paper bag": PAPER,
    "paper straw": PAPER,

    # --- Plastic / plástico ---
    "other plastic bottle": PLASTIC,
    "clear plastic bottle": PLASTIC,
    "plastic bottle cap": PLASTIC,
    "disposable plastic cup": PLASTIC,
    "foam cup": PLASTIC,             # isopor
    "other plastic cup": PLASTIC,
    "plastic lid": PLASTIC,
    "other plastic": PLASTIC,
    "plastic film": PLASTIC,
    "six pack rings": PLASTIC,
    "garbage bag": PLASTIC,
    "other plastic wrapper": PLASTIC,
    "single-use carrier bag": PLASTIC,
    "polypropylene bag": PLASTIC,
    "crisp packet": PLASTIC,         # embalagem metalizada
    "spread tub": PLASTIC,
    "tupperware": PLASTIC,
    "disposable food container": PLASTIC,
    "foam food container": PLASTIC,
    "other plastic container": PLASTIC,
    "plastic gloves": PLASTIC,
    "plastic utensils": PLASTIC,
    "squeezable tube": PLASTIC,
    "plastic straw": PLASTIC,
    "styrofoam piece": PLASTIC,
    "rope & strings": PLASTIC,       # assumindo corda sintética

    # --- Outros / não mapeados nos 4 grupos ---
    "food waste": OTHER,
    "shoe": OTHER,
    "unlabeled litter": OTHER,
    "cigarette": OTHER,
    "carded blister pack": OTHER,    # cartão + bolha plástica: material misto
}

def map_taco_to_material(class_name: str) -> str:
    """
    Recebe o nome da classe TACO (como vem do YOLO) e
    devolve 'plastic', 'metal', 'glass', 'paper' ou 'other'.
    """
    key = class_name.strip().lower()
    return taco_to_material.get(key, OTHER)

def deteccoes_do_quadro(names, cls_ids, confs, xyxy, conf_minima, ids=None):
    """
    Converte as caixas de um quadro do YOLO em detecções
    {class, material, confidence, bbox, id}, descartando as abaixo de
    conf_minima. id é o da trilha do rastreador (None sem rastreamento).
    """
    if ids is None:
        ids = [None] * len(confs)
    detections = []
    for cls_id, conf, (x1, y1, x2, y2), id_trilha in zip(cls_ids, confs, xyxy, ids):
        confidence = float(conf)
        if confidence < conf_minima:
            continue
        class_name = names[int(cls_id)].lower()
        detections.append({
            'class': class_name,
            'material': map_taco_to_material(class_name),
            'confidence': confidence,
            'bbox': [float(x1), float(y1), float(x2), float(y2)],
            'id': None if id_trilha is None else int(id_trilha),
        })
    return detections

def iou(a, b):
    """Interseção sobre união de duas caixas [x1, y1, x2, y2]."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    uniao = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / uniao if uniao > 0 else 0.0


def material_votado(votos):
    """Material com a maior soma de confiança na trilha, sem contar 'other'; None se só há 'other'."""
    validos = {m: v for m, v in votos.items() if m != OTHER}
    if not validos:
        return None
    return max(validos, key=validos.get)


def cruzou_a_faixa(cy_anterior, cy, config):
    """
    O centro (fração da altura) está na faixa ou a atravessou desde o quadro
    anterior, em qualquer sentido: a 12 fps, um objeto rápido pode pular a faixa.
    """
    baixo, alto = (cy, cy) if cy_anterior is None else sorted((cy_anterior, cy))
    return baixo <= config['roi_y_max'] and alto >= config['roi_y_min']


class DisparosPorTrilha:
    """
    Decide o disparo do servo por objeto rastreado: uma vez por trilha, quando
    ela cruza a faixa de acionamento, com o material votado (soma das
    confianças por material em todos os quadros da trilha). Ocupado (servo
    em ação) não dispara: a trilha que cruza a faixa ocupada ainda dispara se
    estiver dentro dela quando o servo liberar (como antes do T15); se não,
    vai para `perdidas_ocupado` ao sair da faixa (ou ao ser esquecida, se
    sumir dentro dela), uma vez. Detecção sem ID é ignorada.
    """

    def __init__(self):
        self.trilhas = {}
        self.perdidas_ocupado = []  # IDs esquecidos que cruzaram a faixa com o servo ocupado

    def reiniciar(self):
        """Câmera reaberta: o rastreador recomeça os IDs."""
        self.trilhas.clear()

    def _nova(self, id_trilha, bbox, agora):
        trilha = {"votos": {}, "disparada": False, "cy": None, "caixa": bbox,
                  "visto": agora, "cruzou_ocupado": False, "avisada": False, "herdou": None}
        # Mesmo objeto com ID novo: herda o disparo da trilha que sumiu
        for id_antigo, antiga in self.trilhas.items():
            if (antiga["disparada"] and antiga["visto"] < agora
                    and agora - antiga["visto"] <= REIDENTIFICAR_S
                    and iou(antiga["caixa"], bbox) >= IOU_REIDENTIFICAR):
                trilha["disparada"] = True
                trilha["herdou"] = id_antigo
                break
        self.trilhas[id_trilha] = trilha
        return trilha

    def quadro(self, deteccoes, altura, config, agora, ocupado):
        """
        Atualiza as trilhas com as detecções do quadro e devolve o disparo
        ({id, material, angulo, votos}) ou None. No máximo um por quadro: o
        servo é um só, e o disparo deixa o sistema ocupado.
        """
        disparo = None
        for det in deteccoes:
            id_trilha = det.get('id')
            if id_trilha is None:
                continue
            x1, y1, x2, y2 = det['bbox']
            trilha = self.trilhas.get(id_trilha) or self._nova(id_trilha, det['bbox'], agora)
            trilha["votos"][det['material']] = trilha["votos"].get(det['material'], 0.0) + det['confidence']
            cy = (y1 + y2) / 2.0 / altura
            # Depois de cruzar com o servo ocupado, só dispara ainda dentro da
            # faixa (não pelo intervalo desde o quadro anterior, que já a tocava)
            cruzou = cruzou_a_faixa(None if trilha["cruzou_ocupado"] else trilha["cy"], cy, config)
            trilha.update(cy=cy, caixa=det['bbox'], visto=agora)
            if (trilha["cruzou_ocupado"] and not trilha["disparada"] and not trilha["avisada"]
                    and not cruzou_a_faixa(None, cy, config)):
                # Passou da faixa sem disparar: não será separado
                trilha["avisada"] = True
                self.perdidas_ocupado.append(id_trilha)
            if not cruzou or trilha["disparada"]:
                continue
            material = material_votado(trilha["votos"])
            angulo = config['class_to_angle'].get(material) if material else None
            if angulo is None:
                continue
            if ocupado or disparo is not None:
                trilha["cruzou_ocupado"] = True
                continue
            trilha["disparada"] = True
            disparo = {"id": id_trilha, "material": material, "angulo": angulo,
                       "votos": dict(trilha["votos"])}
        self._esquecer(agora)
        return disparo

    def _esquecer(self, agora):
        for id_trilha in [i for i, t in self.trilhas.items() if agora - t["visto"] > ESQUECER_TRILHA_S]:
            trilha = self.trilhas.pop(id_trilha)
            if trilha["cruzou_ocupado"] and not trilha["disparada"] and not trilha["avisada"]:
                self.perdidas_ocupado.append(id_trilha)
