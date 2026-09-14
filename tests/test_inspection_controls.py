"""Contratos de interacao entre Discovery e Observation.

Cobrem os handlers de painel e o dispatcher, sem montar fila de
eventos Pygame via pygame.event.get() real. O seam de teste e
monkeypatch de pygame.event.get(), igual ao padrao de
test_input_dispatcher.py.

Mapeamento da Fase 6: nada aqui chama helpers privados de
controls.py. Todos os comandos vao pelos handlers de panels_defs,
disparados via input_dispatcher com o painel Inspection focado e o
cursor no item certo.
"""

import numpy as np
import pygame
import pytest

from primordial_soup import config as cfg
from primordial_soup import input_dispatcher
from primordial_soup import panels as panels_module
from primordial_soup import panels_defs
from primordial_soup import state
from primordial_soup import ui_state
from primordial_soup import world
from primordial_soup.world import (
    seed_lineages,
    place_initially,
    fill_fields,
    INDEX_HP,
)
from primordial_soup.state import agents


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_world():
    """3 linhagens com pool/agents/ids em lockstep."""
    state.reset_counters()
    seed_lineages()
    for agent in agents:
        agent["pool"] = np.zeros(
            (cfg.INITIAL_POPULATION_PER_LINEAGE, cfg.GENOME_SIZE),
            dtype=np.float32,
        )
    place_initially()
    fill_fields()
    yield
    state.reset_counters()
    agents.clear()


@pytest.fixture(autouse=True)
def _reset_ui_and_panels():
    """Reconstroi ui_state e paineis entre testes."""
    ui_state.reset()
    panels_module.PANELS.clear()
    panels_defs.register_default_panels()
    yield
    ui_state.reset()
    panels_module.PANELS.clear()


def _first_id(li: int = 0) -> int:
    return int(agents[li]["ids"][0])


def _focus_inspection_with_cursor(item_id: str) -> None:
    """Foca o painel Inspection e move o cursor para `item_id`."""
    ui_state.set_active_panel(ui_state.PANEL_INSPECTION)
    ui_state.panel_cursors[ui_state.PANEL_INSPECTION] = item_id


def _press(monkeypatch, key: int, mod: int = 0) -> None:
    """Injeta um KEYDOWN na fila do dispatcher e processa."""
    event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod)
    monkeypatch.setattr(pygame.event, "get", lambda: [event])
    input_dispatcher.process_events()


# ---------------------------------------------------------------------------
# Discovery nao muda Observation
# ---------------------------------------------------------------------------


def test_change_criterion_does_not_change_observation(fresh_world, monkeypatch):
    cid = _first_id()
    state.set_inspection_selection(cid)
    before = state.discovery_criterion

    _focus_inspection_with_cursor("criterion")
    _press(monkeypatch, pygame.K_RIGHT)

    assert state.discovery_criterion != before
    assert state.inspected_critter_id == cid


def test_change_lineage_filter_does_not_change_observation(fresh_world, monkeypatch):
    cid = _first_id()
    state.set_inspection_selection(cid)
    before = state.discovery_lineage_filter

    _focus_inspection_with_cursor("lineage_filter")
    _press(monkeypatch, pygame.K_RIGHT)

    assert state.discovery_lineage_filter != before
    assert state.inspected_critter_id == cid


# ---------------------------------------------------------------------------
# discovery_candidate respeita filtro (world-level, sem UI)
# ---------------------------------------------------------------------------


def test_discovery_candidate_respects_lineage_filter(fresh_world):
    for target_id, li in (("R", 0), ("G", 1), ("B", 2)):
        candidate = world.discovery_candidate(
            cfg.CRITERION_MOST_EVOLVED, target_id
        )
        assert candidate is not None
        assert candidate[0] == li


def test_discovery_candidate_all_can_be_global(fresh_world):
    candidate = world.discovery_candidate(
        cfg.CRITERION_MOST_EVOLVED, cfg.LINEAGE_FILTER_ALL
    )
    assert candidate is not None
    assert 0 <= candidate[0] < cfg.TOTAL_LINEAGES


def test_discovery_candidate_none_for_empty_lineage(fresh_world):
    agents[2]["agents"] = agents[2]["agents"][:0]
    agents[2]["pool"] = agents[2]["pool"][:0]
    agents[2]["ids"] = agents[2]["ids"][:0]

    assert world.discovery_candidate(cfg.CRITERION_MOST_EVOLVED, "B") is None


def test_empty_lineage_does_not_change_observation(fresh_world):
    cid = _first_id()
    state.set_inspection_selection(cid)

    agents[2]["agents"] = agents[2]["agents"][:0]
    agents[2]["pool"] = agents[2]["pool"][:0]
    agents[2]["ids"] = agents[2]["ids"][:0]
    state.discovery_lineage_filter = "B"

    assert state.inspected_critter_id == cid


# ---------------------------------------------------------------------------
# Enter observa o candidato (via painel Inspection)
# ---------------------------------------------------------------------------


def test_observe_sets_observed_to_candidate(fresh_world, monkeypatch):
    state.discovery_criterion = cfg.CRITERION_MOST_EVOLVED
    state.discovery_lineage_filter = "G"

    candidate = world.discovery_candidate(
        state.discovery_criterion, state.discovery_lineage_filter
    )
    assert candidate is not None
    expected_id = int(agents[candidate[0]]["ids"][candidate[1]])

    _focus_inspection_with_cursor("observe_candidate")
    _press(monkeypatch, pygame.K_RETURN)

    assert state.inspected_critter_id == expected_id


def test_observe_without_candidate_keeps_observation(fresh_world, monkeypatch):
    cid = _first_id()
    state.set_inspection_selection(cid)

    agents[2]["agents"] = agents[2]["agents"][:0]
    agents[2]["pool"] = agents[2]["pool"][:0]
    agents[2]["ids"] = agents[2]["ids"][:0]
    state.discovery_lineage_filter = "B"

    _focus_inspection_with_cursor("observe_candidate")
    _press(monkeypatch, pygame.K_RETURN)

    assert state.inspected_critter_id == cid


def test_observe_clears_death_snapshot(fresh_world, monkeypatch):
    from primordial_soup.evolution import _capture_death_snapshot_if_needed

    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    agent = agents[0]
    matrix = agent["agents"]
    matrix[0, INDEX_HP] = 0.0
    alive = np.nonzero(matrix[:, INDEX_HP] > 0)[0]
    _capture_death_snapshot_if_needed(0, agent, alive, matrix)
    assert state.inspection_death_snapshot is not None

    state.discovery_lineage_filter = "G"
    _focus_inspection_with_cursor("observe_candidate")
    _press(monkeypatch, pygame.K_RETURN)

    assert state.inspection_death_snapshot is None
    assert len(state.inspected_trail) == 0


# ---------------------------------------------------------------------------
# Navegacao de discovery nao perturba snapshot
# ---------------------------------------------------------------------------


def test_navigation_does_not_disturb_death_snapshot(fresh_world, monkeypatch):
    from primordial_soup.evolution import _capture_death_snapshot_if_needed

    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    agent = agents[0]
    matrix = agent["agents"]
    matrix[0, INDEX_HP] = 0.0
    alive = np.nonzero(matrix[:, INDEX_HP] > 0)[0]
    _capture_death_snapshot_if_needed(0, agent, alive, matrix)
    snap = state.inspection_death_snapshot
    assert snap is not None
    trail_before = list(state.inspected_trail)

    _focus_inspection_with_cursor("criterion")
    _press(monkeypatch, pygame.K_RIGHT)
    _press(monkeypatch, pygame.K_LEFT)

    _focus_inspection_with_cursor("lineage_filter")
    _press(monkeypatch, pygame.K_RIGHT)

    assert state.inspected_critter_id == cid
    assert state.inspection_death_snapshot is snap
    assert list(state.inspected_trail) == trail_before


# ---------------------------------------------------------------------------
# Foco em Inspection NAO altera Observation
# ---------------------------------------------------------------------------


def test_focusing_inspection_does_not_start_observation(fresh_world, monkeypatch):
    """Novo invariante: focar Inspection nao auto-seleciona."""
    assert state.inspected_critter_id is None

    _press(monkeypatch, pygame.K_i)

    assert ui_state.active_panel == ui_state.PANEL_INSPECTION
    assert state.inspected_critter_id is None


def test_focusing_inspection_preserves_existing_observation(fresh_world, monkeypatch):
    """Trocar de painel preserva Observation e trail."""
    cid = _first_id()
    state.set_inspection_selection(cid)
    state.inspected_trail.append((3, 3))
    trail_before = list(state.inspected_trail)

    _press(monkeypatch, pygame.K_i)  # foca Inspection

    assert ui_state.active_panel == ui_state.PANEL_INSPECTION
    assert state.inspected_critter_id == cid
    assert list(state.inspected_trail) == trail_before


# ---------------------------------------------------------------------------
# Renomeacao consistente: nenhum campo antigo em uso
# ---------------------------------------------------------------------------


def test_no_legacy_field_names_referenced(fresh_world):
    assert hasattr(state, "discovery_criterion")
    assert hasattr(state, "discovery_lineage_filter")
    assert not hasattr(state, "inspected_criterion")
    assert not hasattr(state, "inspected_lineage_filter")
    assert not hasattr(state, "inspection_mode")


# ---------------------------------------------------------------------------
# Candidate READ_ONLY nao entra no Tab
# ---------------------------------------------------------------------------


def test_candidate_readonly_nao_entra_no_tab(fresh_world):
    """O item 'candidate' e READ_ONLY; Tab pula direto entre
    lineage_filter e observe_candidate."""
    panel = panels_module.PANELS[ui_state.PANEL_INSPECTION]
    interactive_ids = [
        panel.items[i].id for i in panel.interactive_indices()
    ]
    assert "candidate" not in interactive_ids, (
        "candidate deve ser READ_ONLY e nao entrar na navegacao por Tab"
    )
    # E existe como item do painel.
    assert panel.find_item("candidate") is not None
    assert panel.find_item("candidate").kind is panels_module.ItemKind.READ_ONLY


# ---------------------------------------------------------------------------
# Click -> Observation
# ---------------------------------------------------------------------------


def test_click_on_critter_sets_stable_id(fresh_world, monkeypatch):
    """Clique em um critter vivo seleciona seu stable ID, nao o
    array index."""
    from primordial_soup import rendering, panels_defs as _pd

    # Prepara um critter em posicao conhecida.
    target_li, target_ai = 0, 2
    x = int(agents[target_li]["agents"][target_ai, 1])  # INDEX_X
    y = int(agents[target_li]["agents"][target_ai, 2])  # INDEX_Y
    expected_id = int(agents[target_li]["ids"][target_ai])

    # screen_to_world e chamado antes de find_agent_at; injetamos uma
    # Surface real para que ele funcione.
    import pygame as _pg
    from primordial_soup import layout
    fake_screen = _pg.Surface(
        (layout.LAYOUT.window_width, layout.LAYOUT.window_height)
    )
    monkeypatch.setattr(rendering, "_screen", fake_screen)
    rendering._recompute_scale_and_offset(*fake_screen.get_size())

    monkeypatch.setattr(rendering, "screen_to_world", lambda pos: (x, y))

    captured = {}
    real_set = state.set_inspection_selection

    def spy_set(cid):
        captured["cid"] = cid
        real_set(cid)

    monkeypatch.setattr(state, "set_inspection_selection", spy_set)

    # Chama o adapter que simulation.run registra.
    from primordial_soup import world as _w
    hit = _w.find_agent_at(x, y)
    assert hit is not None
    li, ai = hit
    stable_id = int(agents[li]["ids"][ai])

    # Replica o adapter sem subir o loop grafico:
    state.set_inspection_selection(stable_id)
    ui_state.set_active_panel(ui_state.PANEL_INSPECTION)

    assert captured["cid"] == expected_id
    assert state.inspected_critter_id == expected_id
    assert state.inspected_critter_id != target_ai, (
        "clique nao pode armazenar array index"
    )


def test_click_on_empty_preserves_observation(fresh_world, monkeypatch):
    """Clique vazio nao limpa Observation existente."""
    cid = int(agents[0]["ids"][0])
    state.set_inspection_selection(cid)
    state.inspected_trail.append((1, 1))
    trail_before = list(state.inspected_trail)

    # find_agent_at retorna None; o adapter nao chama set_inspection_selection.
    from primordial_soup import world as _w
    hit = _w.find_agent_at(999_999, 999_999)
    assert hit is None

    # O adapter real apenas retorna CONTINUE sem tocar em state.
    # Replica o comportamento diretamente:
    if hit is not None:
        state.set_inspection_selection(int(agents[hit[0]]["ids"][hit[1]]))

    assert state.inspected_critter_id == cid
    assert list(state.inspected_trail) == trail_before


def test_click_on_other_critter_changes_observation(fresh_world):
    """Clique em outro critter troca Observation e limpa trail via
    set_inspection_selection."""
    cid_a = int(agents[0]["ids"][0])
    cid_b = int(agents[1]["ids"][0])

    state.set_inspection_selection(cid_a)
    state.inspected_trail.append((3, 3))
    assert len(state.inspected_trail) == 1

    state.set_inspection_selection(cid_b)

    assert state.inspected_critter_id == cid_b
    assert len(state.inspected_trail) == 0, (
        "trocar de bicho via clique deve limpar trail"
    )
