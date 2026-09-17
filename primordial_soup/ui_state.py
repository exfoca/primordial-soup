# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Estado transitorio da interface grafica.

Separado de state.py de proposito: state.py representa o MUNDO, este
modulo representa a APRESENTACAO/NAVEGACAO da aplicacao grafica
sobre ele. Nada daqui vai para o savegame; nada daqui influencia a
simulacao.

Fronteira arquitetural:

  - O simulation core (simulation.step, evolution, ecology,
    senses, brain, genetics, world, movement, persistence) NAO
    depende de ui_state.

  - O composition root grafico (simulation.run) faz import lazy de
    ui_state para conectar apresentacao, exatamente como ja faz para
    rendering, panels_defs, audio e feedback.

Este modulo continua sem dependencia inversa: nao importa state.py
nem simulation.py.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field

from . import config as cfg


# Identificadores canonicos de paineis. Usados como chave em
# panel_cursors e como valor de active_panel.
PANEL_WORLD = "world"
PANEL_INSPECTION = "inspection"
PANEL_CONFIGURATION = "configuration"
PANEL_METRICS = "metrics"
PANEL_SESSION = "session"
PANEL_TOOLS = "tools"

ALL_PANELS = (
    PANEL_WORLD,
    PANEL_INSPECTION,
    PANEL_CONFIGURATION,
    PANEL_METRICS,
    PANEL_SESSION,
    PANEL_TOOLS,
)


# Painel atualmente focado. "world" significa: nenhum painel recebe
# navegacao contextual; teclas de ativacao e comandos globais ainda
# funcionam.
active_panel: str = PANEL_WORLD

# Visibilidade dos elementos flutuantes sobre o mundo (Telemetry HUD,
# Command Dock, RPS tip). A lateral direita NAO participa: ela ocupa
# faixa estrutural reservada. Preferencia de UI, como language:
# sobrevive a R/new world, mas nao vai para savegame.
floating_hud_visible: bool = (
    cfg.CONFIG_SNAPSHOT.operator.default_floating_hud_visible
)

# Ultimo painel real que recebeu foco. Enquanto active_panel for
# "world", o rendering desenha ESTE painel no viewport, porem sem
# foco interativo (sem cursor ativo, sem borda destacada).
# Atualizado por set_active_panel().
last_panel: str = PANEL_INSPECTION


# Cursor de cada painel, por id de item. Persiste entre trocas de foco
# para que voltar a um painel restaure a ultima posicao do usuario.
# Valor None = painel ainda nao navegado; o dispatcher cai no primeiro
# item interativo.
panel_cursors: dict[str, str | None] = {
    PANEL_INSPECTION: None,
    PANEL_CONFIGURATION: None,
    PANEL_METRICS: None,
    PANEL_SESSION: None,
    PANEL_TOOLS: None,
}

# Offset vertical (em pixels) de cada painel. So o rendering escreve
# aqui; so o rendering le para desenhar. O input de wheel entra no
# UI-only: nunca vai para state.py nem para persistence.
panel_scroll_offsets: dict[str, int] = {
    PANEL_INSPECTION: 0,
    PANEL_CONFIGURATION: 0,
    PANEL_METRICS: 0,
    PANEL_SESSION: 0,
    PANEL_TOOLS: 0,
}


# Modal ativo (nome canonico) ou None. Enquanto houver modal, somente
# ele recebe input; paineis e mundo ficam bloqueados.
active_modal: str | None = None

# Item selecionado dentro do modal ativo.
modal_cursor: int = 0

# Contexto preservado para restauracao ao cancelar o modal.
panel_before_modal: str = PANEL_WORLD
pause_before_modal: bool = False


# --- Notificacao transitoria ------------------------------------------
#
# Feedback curto de acoes do operador (save, load, etc.), exibido no
# footer da sidebar. NAO e parte da simulacao: usa relogio monotono,
# nao tick_count. Enquanto a simulacao esta pausada, o loop grafico
# ainda chama expire_notice_if_needed() a cada iteracao para a notice
# sumir no prazo; sem isso ela congelaria com a simulacao pausada.

NOTICE_SUCCESS = "success"
NOTICE_ERROR = "error"
NOTICE_INFO = "info"

_NOTICE_KINDS = frozenset({NOTICE_SUCCESS, NOTICE_ERROR, NOTICE_INFO})


@dataclass(slots=True)
class TransientNotice:
    """Notificacao transitória exibida no footer da sidebar.

    message:    texto ja localizado (i18n.t ja foi chamado)
    kind:       NOTICE_SUCCESS | NOTICE_ERROR | NOTICE_INFO
    expires_at: time.monotonic() em que a notice deixa de ser exibida
    """
    message: str
    kind: str
    expires_at: float


# Notice ativa ou None.
notice: TransientNotice | None = None

# Duracao default, em segundos. Valor unico, sem exposicao por config:
# a granularidade e "curta o bastante para nao poluir, longa o
# bastante para ser lida".
NOTICE_DEFAULT_DURATION: float = 2.5


def set_active_panel(panel_id: str) -> None:
    """Foca um painel. Atualiza last_panel se for painel real.

    Passar PANEL_WORLD desfoca o painel atual sem trocar last_panel:
    o viewport continua mostrando o ultimo painel, sem foco.
    """
    global active_panel, last_panel
    if panel_id != PANEL_WORLD:
        last_panel = panel_id
    active_panel = panel_id


def toggle_floating_hud() -> bool:
    """Alterna visibilidade dos elementos flutuantes sobre o mundo.

    Retorna o novo estado. Callers que so querem o efeito ignoram o
    retorno; testes e consumidores futuros usam.
    """
    global floating_hud_visible
    floating_hud_visible = not floating_hud_visible
    return floating_hud_visible


def reset() -> None:
    """Restaura o estado de UI para seus baselines declarativos.

    Chamado apenas em testes e no bootstrap da aplicacao. Nao e
    chamado por recreate() nem por reset_counters(): a navegacao do
    usuario sobrevive a uma nova run.
    """
    global active_panel, last_panel, active_modal, modal_cursor
    global panel_before_modal, pause_before_modal
    global floating_hud_visible, notice
    active_panel = PANEL_WORLD
    last_panel = PANEL_INSPECTION
    active_modal = None
    modal_cursor = 0
    panel_before_modal = PANEL_WORLD
    pause_before_modal = False
    floating_hud_visible = (
        cfg.CONFIG_SNAPSHOT.operator.default_floating_hud_visible
    )
    notice = None
    for key in panel_cursors:
        panel_cursors[key] = None
    for key in panel_scroll_offsets:
        panel_scroll_offsets[key] = 0
    clear_birth_waves()


# --- Birth Waves ------------------------------------------------------
#
# Apresentacao pura: nasce do fato "houve descendentes da linhagem L
# neste tick" reportado por simulation.step(). Nao altera o mundo, nao
# vai para o save, nao consome RNG. A duracao e wall-clock porque a
# velocidade da simulacao nao deve alterar a percepcao da animacao.

BIRTH_WAVE_DURATION_SECONDS: float = 1.25


@dataclass(frozen=True, slots=True)
class BirthWave:
    """Onda de nascimento ancorada em um ninho.

    Guarda apenas identidade da linhagem + instante de inicio. Centro,
    raio e cor sao derivados pelo rendering a partir de state.nests e
    cfg.LINEAGES; nao duplicamos esses dados aqui.
    """
    lineage_index: int
    started_at: float


birth_waves: list[BirthWave] = []


def add_birth_wave(
    lineage_index: int,
    *,
    started_at: float | None = None,
) -> None:
    """Registra uma onda para `lineage_index`.

    `started_at=None` usa time.monotonic(). O argumento explicito
    existe apenas para testes deterministicos; nao ha caminho de
    producao que o utilize.

    Valida minimamente `lineage_index` como int Python estrito e
    nao-negativo. O limite superior pertence a camada que conhece
    cfg.TOTAL_LINEAGES; aqui nao importamos config.py.
    """
    if type(lineage_index) is not int or lineage_index < 0:
        raise ValueError(
            "add_birth_wave: lineage_index deve ser int Python "
            f"estrito e nao-negativo; recebido {lineage_index!r}."
        )
    timestamp = (
        time.monotonic()
        if started_at is None
        else float(started_at)
    )
    birth_waves.append(
        BirthWave(
            lineage_index=lineage_index,
            started_at=timestamp,
        )
    )


def clear_birth_waves() -> None:
    """Remove todas as waves. Muta a colecao in-place para preservar
    identidade para consumidores que mantem referencia."""
    birth_waves.clear()


def get_birth_waves() -> tuple[BirthWave, ...]:
    """Copia imutavel das waves ativas. Rendering consome por aqui
    em vez de tocar a lista global."""
    return tuple(birth_waves)


def birth_wave_progress(
    wave: BirthWave,
    *,
    now: float | None = None,
) -> float:
    """Progresso [0.0, 1.0] da wave.

    clamp em ambos os extremos: valores negativos (clock retrocedido
    ou wave do futuro, o que nao deveria ocorrer em producao) sao
    0.0; progresso acima de 1.0 e clampado em 1.0.
    """
    current = time.monotonic() if now is None else float(now)
    elapsed = max(0.0, current - wave.started_at)
    progress = elapsed / BIRTH_WAVE_DURATION_SECONDS
    return min(1.0, progress)


def expire_birth_waves_if_needed(
    *,
    now: float | None = None,
) -> bool:
    """Remove waves expiradas (progress >= 1.0).

    Retorna True se ao menos uma wave foi removida. Muta in-place
    para preservar a identidade da lista.
    """
    current = time.monotonic() if now is None else float(now)
    survivors = [
        wave
        for wave in birth_waves
        if birth_wave_progress(wave, now=current) < 1.0
    ]
    if len(survivors) == len(birth_waves):
        return False
    birth_waves[:] = survivors
    return True


def has_birth_waves() -> bool:
    """Consulta pura: existe ao menos uma wave? Nao expira nada."""
    return bool(birth_waves)


# --- Modal helpers ----------------------------------------------------


def open_modal(name: str, paused_before: bool) -> None:
    """Abre um modal, preservando o contexto anterior.

    paused_before: valor de state.paused ANTES de abrir. Quem chama
    decide pausar; ui_state apenas guarda o valor para restaurar ao
    cancelar. ui_state NAO importa state.py (essa e a fronteira: o
    operador de composicao passa o valor).
    """
    global active_modal, modal_cursor
    global panel_before_modal, pause_before_modal
    active_modal = name
    modal_cursor = 0
    panel_before_modal = active_panel
    pause_before_modal = paused_before


def close_modal() -> bool:
    """Fecha o modal ativo e restaura o contexto anterior.

    Retorna o valor de pause_before_modal para o chamador aplicar em
    state.paused. ui_state NAO escreve em state.py.

    No-op se nao ha modal; retorna o pause_before_modal atual (que
    sera o default False, sem efeito pratico).
    """
    global active_modal
    if active_modal is None:
        return pause_before_modal
    active_modal = None
    return pause_before_modal


# --- Notice helpers ---------------------------------------------------


def show_notice(
    message: str,
    kind: str = NOTICE_SUCCESS,
    duration: float = NOTICE_DEFAULT_DURATION,
) -> None:
    """Registra uma notificacao transitoria.

    Substitui qualquer notice anterior. Usa time.monotonic() para a
    expiracao: a notice vive no tempo da interface, nao no tempo da
    simulacao (tick_count pode estar congelado em pause).
    """
    global notice
    if kind not in _NOTICE_KINDS:
        kind = NOTICE_INFO
    notice = TransientNotice(
        message=message,
        kind=kind,
        expires_at=time.monotonic() + float(duration),
    )


def clear_notice() -> None:
    global notice
    notice = None


def expire_notice_if_needed() -> bool:
    """Remove a notice se ja expirou. Retorna True se removeu.

    Chamado pelo loop grafico a cada iteracao (inclusive pausado),
    para a notice nao ficar congelada quando a simulacao esta parada.
    """
    global notice
    if notice is None:
        return False
    if time.monotonic() >= notice.expires_at:
        notice = None
        return True
    return False