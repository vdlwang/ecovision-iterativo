"""
Lógica de detecção sem dependências de hardware nem do YOLO: mapeamento
TACO -> material, filtro das caixas e decisão de disparar o servo.
Testada em backend/tests/.
"""

# Cooldown fixo entre detecções enviadas (em segundos)
DETECTION_COOLDOWN = 1.5

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

def deteccoes_do_quadro(names, cls_ids, confs, xyxy, conf_minima):
    """
    Converte as caixas de um quadro do YOLO em detecções
    {class, material, confidence, bbox}, descartando as abaixo de conf_minima.
    """
    detections = []
    for cls_id, conf, (x1, y1, x2, y2) in zip(cls_ids, confs, xyxy):
        confidence = float(conf)
        if confidence < conf_minima:
            continue
        class_name = names[int(cls_id)].lower()
        detections.append({
            'class': class_name,
            'material': map_taco_to_material(class_name),
            'confidence': confidence,
            'bbox': [float(x1), float(y1), float(x2), float(y2)]
        })
    return detections

def angulo_a_disparar(det, altura, config, ocupado, desde_ultimo_disparo):
    """
    Devolve o ângulo do servo se a detecção deve disparar agora, ou None.
    Dispara se:
    1) o material tem ângulo configurado
    2) o centro Y da caixa está na faixa da ROI
    3) não estamos processando um item agora
    4) já passou o cooldown desde a última detecção enviada
    """
    angulo = config['class_to_angle'].get(det['material'])
    if angulo is None:
        return None
    x1, y1, x2, y2 = det['bbox']
    cy_norm = (y1 + y2) / 2.0 / altura
    if not config['roi_y_min'] <= cy_norm <= config['roi_y_max']:
        return None
    if ocupado or desde_ultimo_disparo < DETECTION_COOLDOWN:
        return None
    return angulo
