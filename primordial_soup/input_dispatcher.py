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
# dispatcher (pausa, single step, fullscreen, escape). Sao reservados
# INDEPENDENTEMENTE de modificador: Ctrl+F11 continua sendo estrutural
# e nao pode virar accelerator. Um accelerator nessas teclas ficaria
# inalcancavel porque o dispatcher as resolve primeiro.
_STRUCTURAL_KEYS = frozenset({
    pygame.K_SPACE,
    pygame.K_EQUALS,
    pygame.K_PLUS,
    pygame.K_F11,
    pygame.K_ESCAPE,
})

# Modificadores que participam da identidade de um accelerator.
# CapsLock, NumLock e afins sao IGNORADOS: Ctrl+S continua sendo
# reconhecido com NumLock ativo.
_RELEVANT_MODIFIERS = (
    pygame.KMOD_CTRL
    | pygame.KMOD_SHIFT
    | pygame.KMOD_ALT
    | pygame.KMOD_META
)


def _normalize_modifiers(mod: int) -> int:
    """Mascara canonica de modificadores para identidade de accelerator.

    Produz uma identidade SEMANTICA: Ctrl e Ctrl, nao importa se o
    lado fisico foi esquerdo ou direito. O mesmo para Shift, Alt e
    Meta/GUI. pygame.KMOD_LCTRL e pygame.KMOD_RCTRL sao bits
    distintos (assim como LSHIFT/RSHIFT, LALT/RALT, LMETA/RMETA), e
    sem esta canonicalizacao um accelerator registrado com
    pygame.KMOD_CTRL (que inclui ambos os lados) nao bateria com um
    evento cujo mod contivesse apenas KMOD_LCTRL isolado.

    Na pratica pygame.KMOD_CTRL e o OR de LCTRL e RCTRL, entao
    `mod & KMOD_CTRL` ja aceitaria ambos. A canonicalizacao explicita
    aqui e defensiva: documenta a intencao, sobrevive a mudancas de
    constante no pygame, e produz uma mascara que nao distingue lado
    nenhum.

    Bits de lock (CapsLock, NumLock) e qualquer outro bit nao
    pertencente ao conjunto semantico sao descartados.
    """
    normalized = 0
    if mod & pygame.KMOD_CTRL:
        normalized |= pygame.KMOD_CTRL
    if mod & pygame.KMOD_SHIFT:
        normalized |= pygame.KMOD_SHIFT
    if mod & pygame.KMOD_ALT:
        normalized |= pygame.KMOD_ALT
    if mod & pygame.KMOD_META:
        normalized |= pygame.KMOD_META
    return normalized


# Tabela de accelerators registrados pelo bootstrap grafico. A chave e
# (key, normalized_modifiers). Chaves devem ser exclusivas entre si e
# a key nunca pode ser estrutural.
_GLOBAL_ACTIONS: dict[
    tuple[int, int], "Callable[[], DispatchResult]"
] = {}


def register_global_action(key: int, handler, modifiers: int = 0) -> None:
    """Registra um accelerator global.

    `modifiers` e a mascara pygame.KMOD_* aplicavel ao evento. Apenas
    CTRL, SHIFT, ALT e META participam da identidade; o resto e
    ignorado por _normalize_modifiers.

    Rejeita teclas estruturais (SPACE, =, +, F11, ESC)
    INDEPENDENTEMENTE do valor de modifiers: o dispatcher resolve
    estruturais antes dos accelerators, entao um accelerator nessas
    teclas seria inalcancavel mesmo com modificador.
    """
    if key in _STRUCTURAL_KEYS:
        raise ValueError(
            f"key {key!r} e estrutural e nao pode receber accelerator"
        )
    _GLOBAL_ACTIONS[(int(key), _normalize_modifiers(modifiers))] = handler


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


def _handle_global_key(key: int, mod: int) -> DispatchResult | None:
    """Trata teclas globais. Retorna None se a tecla nao for global.

    Ordem: comandos estruturais primeiro (independentemente de
    modificadores), accelerators registrados depois. Nao usa
    `simulation.step` diretamente para evitar import cycle; o handler
    real e injetado via register_step_handler().
    """
    if key == pygame.K_ESCAPE:
        return _handle_escape()
    if key == pygame.K_SPACE:
        return _handle_space()
    if key in (pygame.K_EQUALS, pygame.K_PLUS):
        return _handle_one_tick()
    if key == pygame.K_F11:
        return _handle_fullscreen()

    handler = _GLOBAL_ACTIONS.get((int(key), _normalize_modifiers(mod)))
    if handler is not None:
        return handler()
    return None


# Handlers injetados. O dispatcher nao importa rendering nem
# simulation: o loop grafico registra o que for necessario.
#
# ESC nao possui adapter: e politica estrutural do dispatcher
# (_handle_escape), porque envolve o modal confirm_exit, que e
# estado de UI. Permitir um adapter externo reabriria a
# possibilidade de a semantica do modal ser ignorada.
_STEP_HANDLER = None
_SPACE_HANDLER = None
_FULLSCREEN_HANDLER = None
_MOUSE_HANDLER = None
_RESIZE_HANDLER = None
_WHEEL_HANDLER = None
_TAB_HIT_TEST = None


def register_step_handler(fn) -> None:
    global _STEP_HANDLER
    _STEP_HANDLER = fn


def register_space_handler(fn) -> None:
    global _SPACE_HANDLER
    _SPACE_HANDLER = fn


def register_fullscreen_handler(fn) -> None:
    global _FULLSCREEN_HANDLER
    _FULLSCREEN_HANDLER = fn


def register_mouse_handler(fn) -> None:
    """fn(pos: tuple[int, int]) -> DispatchResult."""
    global _MOUSE_HANDLER
    _MOUSE_HANDLER = fn


def register_resize_handler(fn) -> None:
    """fn(width: int, height: int) -> DispatchResult."""
    global _RESIZE_HANDLER
    _RESIZE_HANDLER = fn


def register_wheel_handler(fn) -> None:
    """fn(
        notches: int,
        pos: tuple[int, int],
        modifiers: int,
    ) -> DispatchResult.

    Capturar pygame.mouse.get_pos() e pygame.key.get_mods() e
    responsabilidade do dispatcher: ambos pertencem ao estado bruto da
    entrada Pygame. Decidir o que fazer com a posicao e com os
    modificadores (rolar painel, aplicar zoom, ignorar) e politica do
    adapter.

    Os modificadores sao passados SEM normalizacao. O wheel so precisa
    testar presenca de Ctrl (pygame.KMOD_CTRL); outras teclas de lock
    (CapsLock, NumLock) nao interferem no teste de bit.
    """
    global _WHEEL_HANDLER
    _WHEEL_HANDLER = fn


def register_tab_hit_test_handler(fn) -> None:
    """fn(pos: tuple[int, int]) -> str | None.

    Registra o hit-test das tabs da sidebar. O dispatcher NAO conhece
    coordenadas graficas: a autoridade geometrica e o rendering, via
    rendering.panel_tab_at().

    Contrato:
        pos dentro de uma tab valida -> panel_id
        caso contrario               -> None

    O hook e consumido por _handle_mouse: se retornar um panel_id, o
    dispatcher foca aquele painel e NAO delega o clique ao world
    mouse handler. Se retornar None, o clique segue para o adapter do
    mundo. Isso mantem a autoridade geometrica das tabs em rendering
    (via panel_tab_at) sem o dispatcher conhecer coordenadas.
    """
    global _TAB_HIT_TEST
    _TAB_HIT_TEST = fn


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
    """ESC hierarquico. Sem adapter externo.

    Contrato estrutural do dispatcher:
      - active_panel != world -> volta para world.
      - active_panel == world -> abre modal confirm_exit.

    ESC nunca encerra o processo diretamente. A confirmacao explicita
    protege contra saida acidental. O mesmo caminho e usado por
    pygame.QUIT (ver _dispatch_event).
    """
    if ui_state.active_panel != ui_state.PANEL_WORLD:
        ui_state.set_active_panel(ui_state.PANEL_WORLD)
        return DispatchResult.continue_(redraw=True)
    return _request_exit()


def _request_exit() -> DispatchResult:
    """Abre o modal confirm_exit, pausando e guardando o pause anterior.

    NAO altera state.paused diretamente: ui_state guarda o valor de
    pausa anterior para restauracao em cancelamento, e a composicao
    efetiva de state.paused fica com o loop grafico. Aqui fazemos o
    minimo para a UI: pedir pausa enquanto o modal esta aberto.
    """
    from . import state as _state
    if ui_state.active_modal is not None:
        # Modal ja ativo: no-op. Nao reempilha nem troca contexto.
        return DispatchResult.continue_(redraw=False)
    ui_state.open_modal("confirm_exit", paused_before=_state.paused)
    _state.paused = True
    return DispatchResult.continue_(redraw=True)


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
    """Roteia um unico evento.

    Ordem:
      1. QUIT -> mesmo _request_exit() do ESC-no-mundo.
      2. modal ativo -> branch dedicado do modal; todo o resto e
         bloqueado (mouse, scroll, resize, teclado).
      3. mouse / wheel / resize.
      4. KEYDOWN -> _handle_keydown.
    """
    if event.type == pygame.QUIT:
        # X da janela e ESC-no-mundo representam o mesmo pedido de
        # saida. Ambos abrem o modal de confirmacao, nao encerram
        # direto.
        return _request_exit()

    if ui_state.active_modal is not None:
        return _handle_modal_event(event)

    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _handle_mouse(event.pos)

    if event.type == pygame.MOUSEWHEEL:
        return _handle_wheel(event.y)

    if event.type == pygame.VIDEORESIZE:
        return _handle_resize(event.w, event.h)

    if event.type != pygame.KEYDOWN:
        return DispatchResult.continue_(redraw=False)

    return _handle_keydown(event.key, event.mod)


def _handle_modal_event(event: pygame.event.Event) -> DispatchResult:
    """Input com modal ativo.

    Contrato minimo: Enter confirma a saida (Flow.EXIT), ESC cancela
    (fecha o modal e restaura state.paused ao valor anterior).

    Todo o resto e no-op. Nao ha roteamento para paineis, mouse,
    scroll, resize, accelerators nem mundo enquanto o modal existe.
    Em particular, ESC dentro do modal NAO reabre o modal nem delega
    a _handle_escape: a politica de ESC aqui e cancelar.
    """
    if event.type != pygame.KEYDOWN:
        return DispatchResult.continue_(redraw=False)

    if ui_state.active_modal == "confirm_exit":
        if event.key == pygame.K_RETURN:
            return DispatchResult.exit_()
        if event.key == pygame.K_ESCAPE:
            return _cancel_modal()
    return DispatchResult.continue_(redraw=False)


def _cancel_modal() -> DispatchResult:
    """Fecha o modal ativo e restaura paused ao valor guardado."""
    from . import state as _state
    previous_paused = ui_state.close_modal()
    _state.paused = previous_paused
    return DispatchResult.continue_(redraw=True)


def _focus_panel(panel_id: str) -> DispatchResult:
    """Foca um painel e inicializa o cursor se necessario.

    Helper compartilhado por ativacao via tecla de painel (em
    _handle_keydown) e por clique em tab (em _handle_mouse). Concentra
    o contrato:

        - valida que o painel existe no registry;
        - set_active_panel(panel_id);
        - se o cursor ainda for None, inicializa com o primeiro item
          interativo;
        - solicita redraw.

    Painel inexistente cai em no-op redraw=False: o chamador nao
    deve passar id invalido, mas falhar silenciosamente aqui e mais
    seguro que levantar no meio do processamento de eventos.
    """
    panel = panels.PANELS.get(panel_id)
    if panel is None:
        return DispatchResult.continue_(redraw=False)
    ui_state.set_active_panel(panel_id)
    if ui_state.panel_cursors.get(panel.id) is None:
        ui_state.panel_cursors[panel.id] = _first_interactive_cursor(panel)
    return DispatchResult.continue_(redraw=True)


def _handle_keydown(key: int, mod: int) -> DispatchResult:
    # Fase 1: modal ainda nao existe. O ramo abaixo fica pronto para
    # a Fase 9.
    if ui_state.active_modal is not None:
        return DispatchResult.continue_(redraw=False)

    # Globais. `mod` e repassado: accelerators com modificadores
    # (Ctrl+S salva, Ctrl+L carrega) sao resolvidos aqui via
    # _GLOBAL_ACTIONS, chaveados por (key, _normalize_modifiers(mod)).
    result = _handle_global_key(key, mod)
    if result is not None:
        return result

    # Ativacao de painel. Somente sem modificadores funcionais:
    # Ctrl+M nao pode ativar Metrics, Ctrl+S nao pode ativar Session.
    # CapsLock/NumLock nao contam (ver _normalize_modifiers).
    if _normalize_modifiers(mod) == 0:
        activation = _panel_activation_keys()
        if key in activation:
            return _focus_panel(activation[key])

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
        # Enter contextual: se o painel define enter_handler, ele
        # redefines a semantica de Enter. O handler recebe o item
        # atual (ou None) e direction=0. Contrato identico ao de
        # _activate_item, entao o caso generico continua intacto
        # quando enter_handler e None.
        if panel.enter_handler is not None:
            return panel.enter_handler(panel, item, 0)
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
    """Clique do mouse.

    Ordem:
      1. tab_hit_test: se o clique cai numa tab da sidebar, foca o
         painel correspondente e TERMINA aqui. Nao delega ao mundo.
      2. senao, o adapter do mundo (registrado pelo bootstrap) decide
         se o clique resolve para coordenada de mundo; clique no
         corpo da sidebar e no-op porque o adapter nao encontra
         coordenadas validas.

    O dispatcher NAO conhece coordenadas graficas: a autoridade
    geometrica e rendering.panel_tab_at(), registrado via
    register_tab_hit_test_handler().

    Se o hook nao estiver registrado (headless puro, testes), cai
    direto no adapter do mundo.
    """
    if _TAB_HIT_TEST is not None:
        panel_id = _TAB_HIT_TEST(pos)
        if panel_id is not None:
            return _focus_panel(panel_id)
    if _MOUSE_HANDLER is None:
        return DispatchResult.continue_(redraw=False)
    return _MOUSE_HANDLER(pos)


def _handle_wheel(notches: int) -> DispatchResult:
    """Roda do mouse. Captura posicao e modificadores, delega.

    MOUSEWHEEL nao carrega posicao nem modificadores; tanto
    pygame.mouse.get_pos() quanto pygame.key.get_mods() sao as unicas
    vias. Capturar ambos aqui mantem o adapter focado em politica de
    UI (scroll de painel vs zoom vs no-op).
    """
    if _WHEEL_HANDLER is None:
        return DispatchResult.continue_(redraw=False)
    return _WHEEL_HANDLER(
        notches,
        pygame.mouse.get_pos(),
        pygame.key.get_mods(),
    )


def _handle_resize(width: int, height: int) -> DispatchResult:
    """Resize da janela. Delega ao adapter, se houver.

    Nao chama set_mode(): em Pygame 2 a display Surface ja foi
    redimensionada quando VIDEORESIZE dispara. O adapter so
    recalcula geometria derivada.
    """
    if _RESIZE_HANDLER is None:
        return DispatchResult.continue_(redraw=False)
    return _RESIZE_HANDLER(width, height)