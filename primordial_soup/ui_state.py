# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Estado transitorio da interface grafica.

Separado de state.py de proposito: state.py representa o MUNDO, este
modulo representa a NAVEGACAO da aplicacao grafica sobre ele. Nada
daqui vai para o savegame; nada daqui influencia a simulacao.

Em particular, este modulo NAO e importado por simulation.py,
evolution.py, brain.py, senses.py, genetics.py, world.py, movement.py
nem persistence.py. Ele existe apenas para a camada de apresentacao.
"""

from __future__ import annotations
from dataclasses import dataclass, field


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
floating_hud_visible: bool = True

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
# Patch 2. UI-only: nunca vai para state.py nem para persistence.
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
    """Restaura o estado de UI para o default.

    Chamado apenas em testes e no bootstrap da aplicacao. Nao e
    chamado por recreate() nem por reset_counters(): a navegacao do
    usuario sobrevive a uma nova run.
    """
    global active_panel, last_panel, active_modal, modal_cursor
    global panel_before_modal, pause_before_modal
    global floating_hud_visible
    active_panel = PANEL_WORLD
    last_panel = PANEL_INSPECTION
    active_modal = None
    modal_cursor = 0
    panel_before_modal = PANEL_WORLD
    pause_before_modal = False
    floating_hud_visible = True
    for key in panel_cursors:
        panel_cursors[key] = None
    for key in panel_scroll_offsets:
        panel_scroll_offsets[key] = 0
