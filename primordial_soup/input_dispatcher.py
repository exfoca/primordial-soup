# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Roteamento de eventos de input para handlers de painel.

Este modulo e o unico ponto que traduz pygame.event em acoes de
dominio. Ele NAO chama rendering; apenas retorna DispatchResult, que
diz ao loop grafico se deve redesenhar ou encerrar.

Ordem de roteamento (importante):

    QUIT
      -> abre modal de saida (nao encerra direto)

    modal ativo?
      -> modal handler

    tecla global?
      -> executa (SPACE, =, F11, ESC)

    tecla de ativacao de painel?
      -> foca painel

    active_panel != world?
      -> painel handler (Tab, Shift+Tab, <-, ->, Enter, ESC)

    senao
      -> no-op

O dispatcher e stateful apenas em relacao a ui_state. Nao guarda
referencia a rendering, simulation nem controls.
"""

from __future__ import annotations

from typing import Callable

import pygame

from . import ui_state
from . import panels
from .panels import DispatchResult, Flow, ItemKind


# --- Teclas globais ---
#
# _STRUCTURAL_KEYS: comandos cujo significado pertence ao proprio
# dispatcher (pausa, single step, fullscreen, escape). Nao podem ser
# sobrescritos por register_global_action: um accelerator nessas
# teclas ficaria inalcancavel.
_STRUCTURAL_KEYS = frozenset({
    pygame.K_SPACE,
    pygame.K_EQUALS,
    pygame.K_PLUS,
    pygame.K_F11,
    pygame.K_ESCAPE,
})

# Tabela de accelerators registrados pelo bootstrap grafico. Chaves
# devem ser exclusivas entre si e fora de _STRUCTURAL_KEYS.
_GLOBAL_ACTIONS: dict[int, "Callable[[], DispatchResult]"] = {}


def register_global_action(key: int, handler) -> None:
    """Registra um accelerator global.

    Rejeita teclas estruturais: SPACE, =, +, F11 e ESC tem significado
    fixo no dispatcher e um accelerator nessas teclas seria
    inalcancavel.
    """
    if key in _STRUCTURAL_KEYS:
        raise ValueError(
            f"key {key!r} e estrutural e nao pode receber accelerator"
        )
    _GLOBAL_ACTIONS[key] = handler


# Teclas de ativacao de painel. Mapeadas para PANEL_* de ui_state.
# Populado em _panel_activation_keys() para evitar import cycle.
def _panel_activation_keys() -> dict[int, str]:
    return {
        panel.activation_key: panel.id
        for panel in panels.PANELS.values()
    }


def _first_interactive_cursor(panel: panels.Panel) -> str | None:
    """Cursor inicial de um painel: primeiro item interativo, ou None."""
    return panel.default_cursor_id()


def _move_cursor(panel: panels.Panel, direction: int) -> None:
    """Avanca (direction=+1) ou retrocede (-1) o cursor do painel.

    Wrap circular. No-op se o painel nao tem itens interativos.
    """
    interactive = panel.interactive_indices()
    if not interactive:
        return

    current_id = ui_state.panel_cursors.get(panel.id)
    if current_id is None:
        # Sem cursor previo: entra no primeiro (ou ultimo, se direction<0).
        ui_state.panel_cursors[panel.id] = panel.items[
            interactive[0] if direction > 0 else interactive[-1]
        ].id
        return

    # Posicao atual na lista de interativos.
    current_idx_in_items = next(
        (i for i, item in enumerate(panel.items) if item.id == current_id),
        None,
    )
    if current_idx_in_items is None:
        # Cursor aponta para item que sumiu; reseta.
        ui_state.panel_cursors[panel.id] = panel.items[interactive[0]].id
        return

    try:
        pos = interactive.index(current_idx_in_items)
    except ValueError:
        pos = 0

    new_pos = (pos + direction) % len(interactive)
    ui_state.panel_cursors[panel.id] = panel.items[interactive[new_pos]].id


def _activate_item(panel: panels.Panel, item: panels.Item) -> DispatchResult:
    """Enter: dispara o handler do item com direction=0."""
    if item.handler is None:
        return DispatchResult.continue_(redraw=False)
    return item.handler(panel, item, 0)


def _adjust_item(
    panel: panels.Panel, item: panels.Item, direction: int
) -> DispatchResult:
    """<- ->: ajusta o valor do item.

    Somente VALUE e ENUM respondem a setas. TOGGLE e ACTION sao no-op
    em setas; Enter e o caminho canonico.
    """
    if item.kind not in (ItemKind.VALUE, ItemKind.ENUM):
        return DispatchResult.continue_(redraw=False)
    if item.handler is None:
        return DispatchResult.continue_(redraw=False)
    return item.handler(panel, item, direction)


# --- Roteamento de teclado ---


def _handle_global_key(key: int) -> DispatchResult | None:
    """Trata teclas globais. Retorna None se a tecla nao for global.

    Ordem: comandos estruturais primeiro, accelerators registrados
    depois. Nao usa `simulation.step` diretamente para evitar import
    cycle; o handler real e injetado via register_step_handler().
    """
    if key == pygame.K_ESCAPE:
        return _handle_escape()
    if key == pygame.K_SPACE:
        return _handle_space()
    if key in (pygame.K_EQUALS, pygame.K_PLUS):
        return _handle_one_tick()
    if key == pygame.K_F11:
        return _handle_fullscreen()

    handler = _GLOBAL_ACTIONS.get(key)
    if handler is not None:
        return handler()
    return None


# Handlers injetados. O dispatcher nao importa rendering nem
# simulation: o loop grafico registra o que for necessario.
_STEP_HANDLER = None
_SPACE_HANDLER = None
_FULLSCREEN_HANDLER = None
_ESCAPE_HANDLER = None
_MOUSE_HANDLER = None
_RESIZE_HANDLER = None
_WHEEL_HANDLER = None


def register_step_handler(fn) -> None:
    global _STEP_HANDLER
    _STEP_HANDLER = fn


def register_space_handler(fn) -> None:
    global _SPACE_HANDLER
    _SPACE_HANDLER = fn


def register_fullscreen_handler(fn) -> None:
    global _FULLSCREEN_HANDLER
    _FULLSCREEN_HANDLER = fn


def register_escape_handler(fn) -> None:
    global _ESCAPE_HANDLER
    _ESCAPE_HANDLER = fn


def register_mouse_handler(fn) -> None:
    """fn(pos: tuple[int, int]) -> DispatchResult."""
    global _MOUSE_HANDLER
    _MOUSE_HANDLER = fn


def register_resize_handler(fn) -> None:
    """fn(width: int, height: int) -> DispatchResult."""
    global _RESIZE_HANDLER
    _RESIZE_HANDLER = fn


def register_wheel_handler(fn) -> None:
    """fn(notches: int, pos: tuple[int, int]) -> DispatchResult.

    Capturar pygame.mouse.get_pos() e responsabilidade do dispatcher;
    decidir o que fazer com a posicao (qual painel rolar, se a posicao
    pertence a lateral) e politica do adapter.
    """
    global _WHEEL_HANDLER
    _WHEEL_HANDLER = fn


def _handle_space() -> DispatchResult:
    if _SPACE_HANDLER is None:
        return DispatchResult.continue_(redraw=False)
    return _SPACE_HANDLER()


def _handle_one_tick() -> DispatchResult:
    if _STEP_HANDLER is None:
        return DispatchResult.continue_(redraw=False)
    return _STEP_HANDLER()


def _handle_fullscreen() -> DispatchResult:
    if _FULLSCREEN_HANDLER is None:
        return DispatchResult.continue_(redraw=False)
    return _FULLSCREEN_HANDLER()


def _handle_escape() -> DispatchResult:
    """ESC hierarquico (esboco; comportamento completo na Fase 9).

    Fase 1: se ha painel focado, volta para world. Se ja esta em
    world, no-op (a Fase 9 troca isso por abrir o modal de saida).
    """
    if _ESCAPE_HANDLER is not None:
        return _ESCAPE_HANDLER()
    if ui_state.active_panel != ui_state.PANEL_WORLD:
        ui_state.set_active_panel(ui_state.PANEL_WORLD)
        return DispatchResult.continue_(redraw=True)
    return DispatchResult.continue_(redraw=False)


# --- Entry point ---


def process_events() -> DispatchResult:
    """Processa a fila inteira de eventos do pygame e devolve o
    resultado agregado.

    Nao retornar cedo em redraw=True: a fila inteira e consumida em
    ordem, acumulando o bit. Sair no primeiro redraw descartaria os
    eventos seguintes que pygame.event.get() ja removeu da fila —
    perda silenciosa de teclas em bursts rapidos. So Flow.EXIT
    interrompe, e sem rollback: eventos anteriores ja produziram
    efeito.
    """
    redraw = False
    for event in pygame.event.get():
        result = _dispatch_event(event)
        if result.flow is Flow.EXIT:
            return result
        redraw |= result.redraw
    return DispatchResult.continue_(redraw=redraw)


def _dispatch_event(event: pygame.event.Event) -> DispatchResult:
    """Roteia um unico evento. Primeiro branch depois de QUIT: modal
    (Fase 9). Hoje o modal nao existe, entao cai direto para mouse e
    teclado.
    """
    if event.type == pygame.QUIT:
        # Fase 9 substitui por modal de saida. Ate la: EXIT direto,
        # mantendo o comportamento legado sem regressao.
        return DispatchResult.exit_()

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _handle_mouse(event.pos)

    if event.type == pygame.MOUSEWHEEL:
        return _handle_wheel(event.y)

    if event.type == pygame.VIDEORESIZE:
        return _handle_resize(event.w, event.h)

    if event.type != pygame.KEYDOWN:
        return DispatchResult.continue_(redraw=False)

    return _handle_keydown(event.key, event.mod)


def _handle_keydown(key: int, mod: int) -> DispatchResult:
    # Fase 1: modal ainda nao existe. O ramo abaixo fica pronto para
    # a Fase 9.
    if ui_state.active_modal is not None:
        return DispatchResult.continue_(redraw=False)

    # Globais.
    result = _handle_global_key(key)
    if result is not None:
        return result

    # Ativacao de painel.
    activation = _panel_activation_keys()
    if key in activation:
        panel_id = activation[key]
        ui_state.set_active_panel(panel_id)
        panel = panels.PANELS.get(panel_id)
        if panel is not None and ui_state.panel_cursors.get(panel.id) is None:
            ui_state.panel_cursors[panel.id] = _first_interactive_cursor(panel)
        return DispatchResult.continue_(redraw=True)

    # Handlers do painel ativo.
    if ui_state.active_panel != ui_state.PANEL_WORLD:
        panel = panels.PANELS.get(ui_state.active_panel)
        if panel is not None:
            return _handle_panel_key(panel, key, mod)

    return DispatchResult.continue_(redraw=False)


def _panel_order() -> list[str]:
    """Ordem canonica de ciclagem por Tab, derivada do registry.

    Exclui PANEL_WORLD, que e o estado "sem painel focado". Se um
    painel novo for registrado, Tab passa a inclui-lo sem alteracao
    aqui.
    """
    return [
        pid for pid in panels.PANELS.keys()
        if pid != ui_state.PANEL_WORLD
    ]


def _cycle_panel(direction: int) -> DispatchResult:
    """Avanca (direction=+1) ou retrocede (-1) o painel focado.

    Wrap circular. Se o painel corrente nao esta no registry (ex:
    world), entra pelo primeiro (ou ultimo, se direction<0). Resolve
    o cursor do painel destino se ele ainda nao foi navegado, mesma
    logica do ramo de ativacao por tecla.
    """
    order = _panel_order()
    if not order:
        return DispatchResult.continue_(redraw=False)

    current = ui_state.active_panel
    if current in order:
        idx = order.index(current)
        next_id = order[(idx + direction) % len(order)]
    else:
        next_id = order[0] if direction > 0 else order[-1]

    ui_state.set_active_panel(next_id)
    panel = panels.PANELS.get(next_id)
    if panel is not None and ui_state.panel_cursors.get(panel.id) is None:
        ui_state.panel_cursors[panel.id] = _first_interactive_cursor(panel)
    return DispatchResult.continue_(redraw=True)


def _handle_panel_key(panel: panels.Panel, key: int, mod: int) -> DispatchResult:
    if key == pygame.K_TAB:
        # event.mod em vez de pygame.key.get_mods(): o modificador
        # fica associado ao evento efetivamente processado, e nao ao
        # estado global do teclado no instante da consulta. Isso
        # torna o comportamento deterministico em bursts e testavel
        # sem depender do subsistema de input do pygame.
        shift = mod & pygame.KMOD_SHIFT
        return _cycle_panel(-1 if shift else +1)

    if key == pygame.K_DOWN:
        _move_cursor(panel, +1)
        return DispatchResult.continue_(redraw=True)

    if key == pygame.K_UP:
        _move_cursor(panel, -1)
        return DispatchResult.continue_(redraw=True)

    if key == pygame.K_RETURN:
        cursor_id = ui_state.panel_cursors.get(panel.id)
        item = panel.find_item(cursor_id)
        if item is None:
            return DispatchResult.continue_(redraw=False)
        return _activate_item(panel, item)

    if key == pygame.K_LEFT:
        cursor_id = ui_state.panel_cursors.get(panel.id)
        item = panel.find_item(cursor_id)
        if item is None:
            return DispatchResult.continue_(redraw=False)
        return _adjust_item(panel, item, -1)

    if key == pygame.K_RIGHT:
        cursor_id = ui_state.panel_cursors.get(panel.id)
        item = panel.find_item(cursor_id)
        if item is None:
            return DispatchResult.continue_(redraw=False)
        return _adjust_item(panel, item, +1)

    return DispatchResult.continue_(redraw=False)


def _handle_mouse(pos: tuple[int, int]) -> DispatchResult:
    """Clique do mouse. Delega ao adapter registrado, se houver."""
    if _MOUSE_HANDLER is None:
        return DispatchResult.continue_(redraw=False)
    return _MOUSE_HANDLER(pos)


def _handle_wheel(notches: int) -> DispatchResult:
    """Roda do mouse. Captura a posicao e delega ao adapter.

    MOUSEWHEEL nao carrega posicao; pygame.mouse.get_pos() e a unica
    via. Capturar aqui mantem o adapter focado em politica de UI.
    """
    if _WHEEL_HANDLER is None:
        return DispatchResult.continue_(redraw=False)
    return _WHEEL_HANDLER(notches, pygame.mouse.get_pos())


def _handle_resize(width: int, height: int) -> DispatchResult:
    """Resize da janela. Delega ao adapter, se houver.

    Nao chama set_mode(): em Pygame 2 a display Surface ja foi
    redimensionada quando VIDEORESIZE dispara. O adapter so
    recalcula geometria derivada.
    """
    if _RESIZE_HANDLER is None:
        return DispatchResult.continue_(redraw=False)
    return _RESIZE_HANDLER(width, height)
