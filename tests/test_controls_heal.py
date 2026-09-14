"""Heal All continua acessivel via painel Configuration.

Protege contra regressao conceitual: remover o binding global de H
nao pode remover a acao nem o item de painel. Heal All permanece
exclusivamente pelo Configuration.
"""

import numpy as np
import pygame
import pytest

from primordial_soup import config as cfg
from primordial_soup import controls
from primordial_soup import input_dispatcher
from primordial_soup import panels as panels_module
from primordial_soup import panels_defs
from primordial_soup import state
from primordial_soup import ui_state
from primordial_soup.world import seed_lineages, place_initially
from primordial_soup.state import agents


@pytest.fixture
def fresh_world():
    state.reset_counters()
    seed_lineages()
    for agent in agents:
        agent["pool"] = np.zeros(
            (cfg.INITIAL_POPULATION_PER_LINEAGE, cfg.GENOME_SIZE),
            dtype=np.float32,
        )
    place_initially()
    yield
    state.reset_counters()
    agents.clear()


@pytest.fixture(autouse=True)
def _reset_ui_and_panels():
    ui_state.reset()
    panels_module.PANELS.clear()
    panels_defs.register_default_panels()
    yield
    ui_state.reset()
    panels_module.PANELS.clear()


def test_action_heal_all_still_exists():
    """A acao de dominio continua existindo."""
    assert hasattr(controls, "action_heal_all")


def test_configuration_panel_has_heal_all_item(fresh_world):
    """O painel Configuration tem o item heal_all com handler."""
    panel = panels_module.PANELS[ui_state.PANEL_CONFIGURATION]
    item = panel.find_item("heal_all")
    assert item is not None
    assert item.handler is not None
    assert item.kind is panels_module.ItemKind.ACTION


def test_heal_all_via_panel_changes_hp(fresh_world, monkeypatch):
    """Enter no item heal_all restaura HP de todos os bichos."""
    # Zera HP de todos.
    for agent in agents:
        agent["agents"][:, 0] = 0.5  # INDEX_HP = 0

    ui_state.set_active_panel(ui_state.PANEL_CONFIGURATION)
    ui_state.panel_cursors[ui_state.PANEL_CONFIGURATION] = "heal_all"

    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0)
    monkeypatch.setattr(pygame.event, "get", lambda: [event])
    input_dispatcher.process_events()

    for agent in agents:
        assert (agent["agents"][:, 0] == float(cfg.INITIAL_HP)).all()


def test_h_is_not_heal_binding():
    """H nao esta registrado como Heal All em _GLOBAL_ACTIONS.

    Este teste e independente do bootstrap grafico: verifica o
    registry diretamente. O bootstrap limpa o registry no inicio de
    cada processo; testes que rodam sem bootstrap veem o registry
    vazio, o que tambem e valido.
    """
    handler = input_dispatcher._GLOBAL_ACTIONS.get(pygame.K_h)
    assert handler is None or handler is not controls.action_heal_all, (
        "H nao pode estar registrado como Heal All"
    )
