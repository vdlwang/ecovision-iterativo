from motor import EstadoMotor, MENSAGEM_BOOT


def test_comeca_desligado():
    m = EstadoMotor()
    assert m.ligado is False
    assert m.ligado_desde is None


def test_liga_e_desliga_quando_enviado():
    m = EstadoMotor()
    m.comando(True, enviado=True, agora=10.0)
    assert m.ligado and m.ligado_desde == 10.0
    m.comando(False, enviado=True, agora=20.0)
    assert not m.ligado and m.ligado_desde is None


def test_comando_nao_enviado_nao_muda_estado():
    # modo demo ou falha de escrita: send_line devolve False
    m = EstadoMotor()
    m.comando(True, enviado=False, agora=10.0)
    assert not m.ligado and m.ligado_desde is None
    m.comando(True, enviado=True, agora=11.0)
    m.comando(False, enviado=False, agora=12.0)
    assert m.ligado and m.ligado_desde == 11.0


def test_ligar_de_novo_mantem_instante():
    m = EstadoMotor()
    m.comando(True, enviado=True, agora=10.0)
    m.comando(True, enviado=True, agora=15.0)
    assert m.ligado_desde == 10.0


def test_reset_do_esp32_desliga():
    m = EstadoMotor()
    m.comando(True, enviado=True, agora=10.0)
    assert m.linha_recebida(MENSAGEM_BOOT + "\r") is True
    assert not m.ligado and m.ligado_desde is None


def test_outras_linhas_nao_mudam_estado():
    m = EstadoMotor()
    m.comando(True, enviado=True, agora=10.0)
    for linha in ("PONG", "Servo movido para 50 graus", "ERR: comando desconhecido", ""):
        assert m.linha_recebida(linha) is False
    assert m.ligado and m.ligado_desde == 10.0
