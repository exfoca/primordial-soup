"""Testes do dispatcher de input (Fase 5).

Cobrem o contrato endurecido de process_events():
  - a fila inteira e consumida em ordem;
  - redraw e acumulado (OR), nao sobrescrito pelo ultimo evento;
  - somente Flow.EXIT interrompe, sem rollback dos eventos anteriores;
  - Shift+Tab usa event.mod;
  - ativacao de painel inicializa o cursor;
  - ESC em painel volta para world;
  - o loop grafico honra redraw mesmo pausado.

Estilo de teste: monkeypatch de pygame.event.get() devolve a lista
desejada. Sem parametro `events` na API de producao — o seam de
teste e o proprio pygame.event.get(), que e onde o dispatcher le.
"""

import pygame
import pytest

from primordial_soup import input_dispatcher
from primordial_soup import ui_state
from primordial_soup.panels import Flow
from primordial_soup import panels as panels_module


@pytest.fixture(autouse=True)
def _reset_ui():
    """Limpa ui_state entre testes e popula um painel fake minimo.

    ui_state e modulo-global. Testes que tocam active_panel ou
    panel_cursors precisam partir de um estado conhecido. Sem isso,
    a ordem de execucao dos testes muda o resultado.
    """
    ui_state.reset()
    panels_module.PANELS.clear()
    # Painel fake para testes que ativam painel por tecla.
    fake = panels_module.Panel(
        id=ui_state.PANEL_INSPECTION,
        activation_key=pygame.K_i,
        title_key="panel.title",
        items=[
            panels_module.Item("a", panels_module.ItemKind.ACTION, "a"),
            panels_module.Item("b", panels_module.ItemKind.ACTION, "b"),
        ],
    )
    panels_module.PANELS[fake.id] = fake
    yield
    ui_state.reset()
    panels_module.PANELS.clear()


def _event(type_, **kwargs) -> pygame.event.Event:
    return pygame.event.Event(type_, **kwargs)


def _set_queue(monkeypatch, events):
    monkeypatch.setattr(pygame.event, "get", lambda: list(events))


# ---------------------------------------------------------------------------
# Fila inteira
# ---------------------------------------------------------------------------


def test_dispatcher_processes_all_queued_events(monkeypatch):
    """Dois eventos na fila: ambos sao processados em ordem."""
    calls = []

    def fake_global(key, mod):
        calls.append(key)
        # Devolve CONTINUE sem redraw para nao interferir no teste.
        return input_dispatcher.DispatchResult.continue_(redraw=False)

    monkeypatch.setattr(input_dispatcher, "_handle_global_key", fake_global)
    _set_queue(monkeypatch, [
        _event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0),
        _event(pygame.KEYDOWN, key=pygame.K_EQUALS, mod=0),
    ])

    result = input_dispatcher.process_events()

    assert calls == [pygame.K_SPACE, pygame.K_EQUALS]
    assert result.flow is Flow.CONTINUE


def test_dispatcher_accumulates_redraw(monkeypatch):
    """Sequencia False -> True -> False: resultado final deve ser True.

    Este cenario distingue OR acumulado de "ultimo evento vence".
    Uma implementacao que devolvesse simplesmente o redraw do ultimo
    evento passaria com False -> True, mas falha aqui.
    """
    redraws = iter([False, True, False])

    def fake_global(key, mod):
        return input_dispatcher.DispatchResult.continue_(redraw=next(redraws))

    monkeypatch.setattr(input_dispatcher, "_handle_global_key", fake_global)
    _set_queue(monkeypatch, [
        _event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0),
        _event(pygame.KEYDOWN, key=pygame.K_EQUALS, mod=0),
        _event(pygame.KEYDOWN, key=pygame.K_F11, mod=0),
    ])

    result = input_dispatcher.process_events()

    assert result.redraw is True


# ---------------------------------------------------------------------------
# EXIT tem precedencia, sem rollback
# ---------------------------------------------------------------------------


def test_exit_has_precedence(monkeypatch):
    """[SPACE, Enter-no-modal, F11]: modal confirma EXIT, F11 nao roda.

    Contrato estrutural do dispatcher: Flow.EXIT interrompe a fila
    sem rollback; eventos posteriores na fila nao sao processados.

    O gatilho de EXIT hoje e Enter com o modal confirm_exit aberto
    (Patch 2). QUIT nao encerra direto mais: abre o mesmo modal.
    Este teste dispara EXIT pelo caminho canonico.

    Nota: com modal ativo, SPACE e engolido por _handle_modal_event
    (no-op), entao space_calls permanece vazio. O ponto do teste e
    a precedencia de EXIT sobre eventos posteriores, nao o efeito
    de SPACE.
    """
    # Registramos handlers espioes para detectar execucoes indevidas.
    space_calls = []

    def fake_space():
        space_calls.append(True)
        return input_dispatcher.DispatchResult.continue_(redraw=False)

    input_dispatcher.register_space_handler(fake_space)

    f11_calls = []

    def fake_f11():
        f11_calls.append(True)
        return input_dispatcher.DispatchResult.continue_(redraw=False)

    input_dispatcher.register_fullscreen_handler(fake_f11)

    # Abre o modal ANTES de enfileirar eventos, para o Enter ser
    # roteado pelo _handle_modal_event.
    ui_state.open_modal("confirm_exit", paused_before=True)

    _set_queue(monkeypatch, [
        _event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0),
        _event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0),
        _event(pygame.KEYDOWN, key=pygame.K_F11, mod=0),
    ])

    result = input_dispatcher.process_events()

    assert result.flow is Flow.EXIT
    assert f11_calls == [], "F11 nao deveria rodar apos EXIT"
    # SPACE foi engolido pelo modal; nenhum dos dois handlers deve
    # ter disparado.
    assert space_calls == [], "SPACE com modal ativo deve ser no-op"

    # Cleanup: registradores sao globais no modulo.
    input_dispatcher.register_space_handler(lambda: None)
    input_dispatcher.register_fullscreen_handler(lambda: None)
    ui_state.reset()


# ---------------------------------------------------------------------------
# Shift+Tab e navegacao
# ---------------------------------------------------------------------------


def test_up_moves_cursor_backward(monkeypatch):
    """↑ retrocede o cursor dentro do painel focado.

    Nota historica: este teste se chamava
    test_shift_tab_moves_cursor_backward e usava Shift+Tab. Tab e
    Shift+Tab ciclam PAINEIS (via _cycle_panel); quem move o cursor
    DENTRO do painel e ↑/↓ (via _move_cursor). O teste antigo
    assumia o modelo errado.
    """
    ui_state.set_active_panel(ui_state.PANEL_INSPECTION)
    # Cursor inicial no segundo item.
    ui_state.panel_cursors[ui_state.PANEL_INSPECTION] = "b"

    _set_queue(monkeypatch, [
        _event(pygame.KEYDOWN, key=pygame.K_UP, mod=0),
    ])

    input_dispatcher.process_events()

    # Retrocedeu de "b" para "a".
    assert ui_state.panel_cursors[ui_state.PANEL_INSPECTION] == "a"


def test_shift_tab_cycles_panels_not_items(monkeypatch):
    """Shift+Tab cicla paineis, nao itens dentro de um painel.

    Registra o contrato real do dispatcher: Tab/Shift+Tab passam
    por _cycle_panel, que troca o painel focado. O cursor do painel
    de origem e preservado, nao alterado.
    """
    from primordial_soup import panels as panels_module

    # Registra um segundo painel para o ciclo ter destino.
    second = panels_module.Panel(
        id=ui_state.PANEL_CONFIGURATION,
        activation_key=pygame.K_c,
        title_key="panel.title",
        items=[
            panels_module.Item("x", panels_module.ItemKind.ACTION, "x"),
        ],
    )
    panels_module.PANELS[second.id] = second

    ui_state.set_active_panel(ui_state.PANEL_INSPECTION)
    ui_state.panel_cursors[ui_state.PANEL_INSPECTION] = "b"
    ui_state.panel_cursors[ui_state.PANEL_CONFIGURATION] = None

    _set_queue(monkeypatch, [
        _event(pygame.KEYDOWN, key=pygame.K_TAB, mod=pygame.KMOD_SHIFT),
    ])

    input_dispatcher.process_events()

    # Painel mudou (cursor de Inspection preservado, cursor do novo
    # painel inicializado).
    assert ui_state.panel_cursors[ui_state.PANEL_INSPECTION] == "b"
    assert ui_state.active_panel != ui_state.PANEL_INSPECTION


def test_panel_activation_initializes_cursor(monkeypatch):
    """Ativar painel inicializa o cursor se estava None."""
    assert ui_state.panel_cursors.get(ui_state.PANEL_INSPECTION) is None

    _set_queue(monkeypatch, [
        _event(pygame.KEYDOWN, key=pygame.K_i, mod=0),
    ])

    input_dispatcher.process_events()

    assert ui_state.active_panel == ui_state.PANEL_INSPECTION
    assert ui_state.panel_cursors[ui_state.PANEL_INSPECTION] == "a"


def test_escape_panel_goes_to_world(monkeypatch):
    """ESC em painel volta para world."""
    ui_state.set_active_panel(ui_state.PANEL_INSPECTION)

    _set_queue(monkeypatch, [
        _event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0),
    ])

    result = input_dispatcher.process_events()

    assert ui_state.active_panel == ui_state.PANEL_WORLD
    assert result.flow is Flow.CONTINUE
    assert result.redraw is True


# ---------------------------------------------------------------------------
# Integracao leve com o loop grafico
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Mouse, resize, wheel, ESC com adapter, accelerators
# ---------------------------------------------------------------------------


def test_mouse_calls_registered_handler(monkeypatch):
    """MOUSEBUTTONDOWN chama o adapter registrado."""
    calls = []

    def handler(pos):
        calls.append(pos)
        return input_dispatcher.DispatchResult.continue_(redraw=True)

    input_dispatcher.register_mouse_handler(handler)
    try:
        _set_queue(monkeypatch, [
            _event(pygame.MOUSEBUTTONDOWN, button=1, pos=(123, 456)),
        ])
        result = input_dispatcher.process_events()
        assert calls == [(123, 456)]
        assert result.redraw is True
    finally:
        input_dispatcher.register_mouse_handler(None)


def test_mouse_without_handler_is_safe_noop(monkeypatch):
    """Sem adapter registrado, mouse e no-op seguro."""
    input_dispatcher.register_mouse_handler(None)
    _set_queue(monkeypatch, [
        _event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1, 1)),
    ])
    result = input_dispatcher.process_events()
    assert result.flow is Flow.CONTINUE
    assert result.redraw is False


def test_resize_calls_registered_handler(monkeypatch):
    """VIDEORESIZE chama o adapter registrado com w/h."""
    calls = []

    def handler(w, h):
        calls.append((w, h))
        return input_dispatcher.DispatchResult.continue_(redraw=True)

    input_dispatcher.register_resize_handler(handler)
    try:
        _set_queue(monkeypatch, [
            _event(pygame.VIDEORESIZE, w=1024, h=768),
        ])
        result = input_dispatcher.process_events()
        assert calls == [(1024, 768)]
        assert result.redraw is True
    finally:
        input_dispatcher.register_resize_handler(None)


def test_resize_without_handler_is_safe_noop(monkeypatch):
    """Sem adapter registrado, resize e no-op seguro."""
    input_dispatcher.register_resize_handler(None)
    _set_queue(monkeypatch, [
        _event(pygame.VIDEORESIZE, w=800, h=600),
    ])
    result = input_dispatcher.process_events()
    assert result.flow is Flow.CONTINUE
    assert result.redraw is False


def test_wheel_calls_registered_handler_with_pos_and_modifiers(
    monkeypatch
):
    """MOUSEWHEEL entrega notches + posicao atual + modificadores atuais.

    O dispatcher captura pygame.mouse.get_pos() e pygame.key.get_mods()
    porque MOUSEWHEEL nao carrega nenhum dos dois no proprio evento. A
    politica de zoom vs scroll e do adapter do mundo, nao do
    dispatcher.
    """
    calls = []

    def handler(notches, pos, modifiers):
        calls.append((notches, pos, modifiers))
        return input_dispatcher.DispatchResult.continue_(redraw=True)

    input_dispatcher.register_wheel_handler(handler)
    try:
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (7, 8))
        monkeypatch.setattr(
            pygame.key, "get_mods", lambda: pygame.KMOD_CTRL
        )
        _set_queue(monkeypatch, [
            _event(pygame.MOUSEWHEEL, y=1),
        ])
        result = input_dispatcher.process_events()
        assert calls == [(1, (7, 8), pygame.KMOD_CTRL)]
        assert result.redraw is True
    finally:
        input_dispatcher.register_wheel_handler(None)


def test_escape_at_world_opens_modal_not_exit(monkeypatch):
    """ESC no world abre o modal; NAO encerra o processo diretamente.

    Este teste substitui o antigo test_escape_with_adapter_uses_adapter,
    que protegia um extension point removido. O contrato atual e que
    ESC no world sempre abre confirm_exit; o Flow resultante e
    CONTINUE, nao EXIT.
    """
    ui_state.set_active_panel(ui_state.PANEL_WORLD)

    _set_queue(monkeypatch, [
        _event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0),
    ])
    result = input_dispatcher.process_events()
    assert result.flow is Flow.CONTINUE
    assert ui_state.active_modal == "confirm_exit"


def test_accelerator_executes_once_per_event(monkeypatch):
    """Accelerator registrado executa exatamente uma vez por evento."""
    calls = []

    def acc():
        calls.append(True)
        return input_dispatcher.DispatchResult.continue_(redraw=True)

    input_dispatcher.register_global_action(pygame.K_q, acc)
    try:
        _set_queue(monkeypatch, [
            _event(pygame.KEYDOWN, key=pygame.K_q, mod=0),
        ])
        input_dispatcher.process_events()
        assert calls == [True]
    finally:
        input_dispatcher._GLOBAL_ACTIONS.pop((pygame.K_q, 0), None)


def test_h_is_not_structural():
    """H nao esta em _STRUCTURAL_KEYS: e accelerator de UI, nao
    comando estrutural do dispatcher."""
    assert pygame.K_h not in input_dispatcher._STRUCTURAL_KEYS


def test_register_global_action_rejects_structural_keys():
    """register_global_action rejeita SPACE, =, +, F11, ESC.

    Rejeicao INDEPENDENTE de modifiers: Ctrl+F11 tambem e rejeitado.
    Estruturais tem significado fixo no dispatcher e sao resolvidas
    antes dos accelerators; um accelerator nessas teclas seria
    inalcancavel.
    """
    for structural in (
        pygame.K_SPACE, pygame.K_EQUALS, pygame.K_PLUS,
        pygame.K_F11, pygame.K_ESCAPE,
    ):
        with pytest.raises(ValueError):
            input_dispatcher.register_global_action(
                structural,
                lambda: input_dispatcher.DispatchResult.continue_(),
            )
        with pytest.raises(ValueError):
            input_dispatcher.register_global_action(
                structural,
                lambda: input_dispatcher.DispatchResult.continue_(),
                modifiers=pygame.KMOD_CTRL,
            )


def test_paused_redraw_is_honored_by_graphical_loop(monkeypatch):
    """Redraw solicitado pausado deve resultar em draw() uma vez.

    Integracao leve: monkeypatch de process_events para devolver
    CONTINUE(redraw=True) e depois EXIT; monkeypatch de draw para
    contar; monkeypatch de step para falhar se chamado (pausado, nao
    deve rodar).
    """
    from primordial_soup import simulation

    draw_calls = []
    step_calls = []

    monkeypatch.setattr(simulation.state, "paused", True)

    results = iter([
        panels_module.DispatchResult.continue_(redraw=True),
        panels_module.DispatchResult.exit_(),
    ])

    def fake_process_events():
        return next(results)

    def fake_draw():
        draw_calls.append(True)

    def fake_step():
        step_calls.append(True)
        raise AssertionError("step() nao deveria rodar pausado")

    def fake_shutdown():
        pass

    def fake_tick_fps():
        pass

    # Imports usados dentro de run() — precisam ser patchados no
    # modulo onde sao resolvidos (rendering, input_dispatcher).
    from primordial_soup import rendering
    monkeypatch.setattr(rendering, "draw", fake_draw)
    monkeypatch.setattr(rendering, "init", lambda: None)
    monkeypatch.setattr(rendering, "shutdown", fake_shutdown)
    monkeypatch.setattr(rendering, "tick_fps", fake_tick_fps)
    monkeypatch.setattr(input_dispatcher, "process_events", fake_process_events)
    monkeypatch.setattr(simulation, "step", fake_step)
    # bootstrap_new_world toca a populacao; evita trabalho real.
    monkeypatch.setattr(simulation, "bootstrap_new_world", lambda: None)

    # Painel registry precisa existir (register_default_panels e
    # chamado dentro de run()).
    from primordial_soup import panels_defs
    monkeypatch.setattr(panels_defs, "register_default_panels", lambda: None)

    simulation.run()

    # O draw() inicial + o draw() do redraw solicitado.
    assert len(draw_calls) == 2, (
        f"esperado 2 draw() (inicial + redraw pausado), obtido {len(draw_calls)}"
    )
    assert step_calls == [], "step() nao deveria rodar pausado"