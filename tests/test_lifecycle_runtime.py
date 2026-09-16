"""Fechamento HOT das regras behavior/lifecycle de RuntimeRules."""

import numpy as np
import pytest

from primordial_soup import bootstrap
from primordial_soup import config as cfg
from primordial_soup import ecology
from primordial_soup import evolution
from primordial_soup import layout
from primordial_soup import state
from primordial_soup import world
from primordial_soup.state import agents
from primordial_soup.world import INDEX_HP, INDEX_X, INDEX_Y


def _valid_test_nests():
    """Geometria deterministica de ninhos valida para o schema v23."""
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


def _empty_zones():
    return np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
        dtype=bool,
    )


def _valid_test_zone_centers():
    """Centros de zona determinísticos, sem consumir RNG."""
    center = (
        layout.LAYOUT.world_width - cfg.ZONE_RADIUS - 1,
        layout.LAYOUT.world_height - cfg.ZONE_RADIUS - 1,
    )
    return tuple(
        center
        for _ in range(cfg.NUMBER_OF_ZONES)
    )


def _install_checkpoint_geometry():
    """Instala geometry valida sob o schema v23 sem consumir RNG.

    zone_centers e a autoridade geometrica; zones e derivada por
    world.build_zone_mask().
    """
    centers = _valid_test_zone_centers()
    state.zone_centers = centers
    state.zones = world.build_zone_mask(centers)
    state.nests = _valid_test_nests()


@pytest.fixture
def lifecycle_world():
    """Tres linhagens com dois individuos em lockstep e sem zonas."""
    original_rules = state.runtime_rules
    state.reset_counters()
    world.seed_lineages()

    n = 2
    for ag in agents:
        ag["pool"] = np.zeros((n, cfg.GENOME_SIZE), dtype=np.float32)
    world.place_initially()
    for ag in agents:
        ag["agents"] = ag["agents"][:n].copy()
        ag["ids"] = ag["ids"][:n].copy()

    positions = (
        ((10, 10), (11, 10)),
        ((30, 30), (31, 30)),
        ((50, 50), (51, 50)),
    )
    for ag, lineage_positions in zip(agents, positions):
        for row, (x, y) in zip(ag["agents"], lineage_positions):
            row[INDEX_X] = x
            row[INDEX_Y] = y
            row[INDEX_HP] = 1000.0

    state.zones = None
    state.zone_centers = None
    state.nests = None
    world.fill_fields()

    yield

    state.set_runtime_rules(original_rules)
    state.reset_counters()
    state.zones = None
    state.zone_centers = None
    state.nests = None
    agents.clear()


def test_low_hp_threshold_is_hot_in_internal_state():
    matrix = np.zeros((2, world.AGENT_COLUMNS), dtype=np.float32)
    matrix[:, INDEX_HP] = (1000.0, 3000.0)

    _, low = evolution_senses_internal(matrix, 2000)
    assert low.tolist() == [1.0, 0.0]

    _, low = evolution_senses_internal(matrix, 3500)
    assert low.tolist() == [1.0, 1.0]


def evolution_senses_internal(matrix, threshold):
    from primordial_soup.senses import _internal_state_batch

    return _internal_state_batch(matrix, low_hp_threshold=threshold)


def test_sense_batch_requires_threshold_only_with_real_matrix(lifecycle_world):
    from primordial_soup import senses

    matrix = agents[0]["agents"]
    xs = matrix[:, INDEX_X].astype(np.int64)
    ys = matrix[:, INDEX_Y].astype(np.int64)

    with pytest.raises(ValueError):
        senses.sense_batch(xs, ys, matrix, index=0)

    result = senses.sense_batch(
        xs,
        ys,
        matrix,
        index=0,
        low_hp_threshold=2000,
    )
    assert result.shape == (2, cfg.NETWORK_INPUTS)
    assert matrix[:, world.INDEX_LOW_HP].tolist() == [1.0, 1.0]

    # Compatibilidade: sem matrix, threshold nao e necessario.
    assert senses.sense(10, 10).shape == (cfg.NETWORK_INPUTS,)


def _install_controlled_decision(monkeypatch):
    """Isola evaluate_and_move para testar apenas regra -> decisao."""
    from primordial_soup import brain, movement, senses

    captured = {"threshold": None, "choices": None}

    def fake_sense_batch(xs, ys, matrix=None, index=None, *, low_hp_threshold=None):
        captured["threshold"] = low_hp_threshold
        return np.zeros((len(xs), cfg.NETWORK_INPUTS), dtype=np.float32)

    def fake_evaluate_batch(inputs, weights, previous_hidden_state=None):
        n = inputs.shape[0]
        return (
            np.zeros((n, cfg.POSSIBLE_MOVES), dtype=np.float32),
            np.zeros((n, cfg.HIDDEN_NEURONS), dtype=np.float32),
        )

    def fake_move_batch(matrix, choices):
        captured["choices"] = choices.copy()

    monkeypatch.setattr(senses, "sense_batch", fake_sense_batch)
    monkeypatch.setattr(brain, "evaluate_batch", fake_evaluate_batch)
    monkeypatch.setattr(movement, "move_batch", fake_move_batch)
    return captured


def test_evaluate_and_move_propagates_runtime_low_hp_threshold(
    lifecycle_world, monkeypatch
):
    captured = _install_controlled_decision(monkeypatch)
    state.update_runtime_rules(low_hp_threshold=3500)
    monkeypatch.setattr(cfg, "LOW_HP_THRESHOLD", 1)

    evolution.evaluate_and_move(0)

    assert captured["threshold"] == 3500


def test_stay_still_impulse_is_hot_and_independent_from_cfg(
    lifecycle_world, monkeypatch
):
    captured = _install_controlled_decision(monkeypatch)

    state.update_runtime_rules(stay_still_impulse=1.0)
    monkeypatch.setattr(cfg, "STAY_STILL_IMPULSE", -100.0)
    evolution.evaluate_and_move(0)
    assert np.all(captured["choices"] == cfg.STAY_STILL_INDEX)

    state.update_runtime_rules(stay_still_impulse=-1.0)
    monkeypatch.setattr(cfg, "STAY_STILL_IMPULSE", 100.0)
    evolution.evaluate_and_move(0)
    assert np.all(captured["choices"] != cfg.STAY_STILL_INDEX)


@pytest.mark.parametrize(
    "runtime_threshold,cfg_threshold,expected_hp",
    [
        (10, 0, [15.0]),
        (0, 10, [5.0, 15.0]),
    ],
)
def test_death_threshold_is_hot_and_independent_from_cfg(
    lifecycle_world,
    monkeypatch,
    runtime_threshold,
    cfg_threshold,
    expected_hp,
):
    matrix = agents[0]["agents"]
    matrix[:, INDEX_HP] = (5.0, 15.0)
    world.fill_fields()

    state.update_runtime_rules(
        base_decay_per_tick=0,
        death_hp_threshold=runtime_threshold,
    )
    monkeypatch.setattr(cfg, "DIE_WHEN_HP_LESS_OR_EQUAL", cfg_threshold)

    # Os dois individuos estao em posicoes separadas e nao ha outra
    # linhagem na mesma celula. Com base_decay=0 e overcrowding no
    # default, os unicos efeitos sao os de mortalidade deterministica
    # pelo death_hp_threshold configurado em runtime.
    resolution = ecology.compute_ecology_resolution()
    ecology.apply_ecology_resolution(resolution)

    assert agents[0]["agents"][:, INDEX_HP].tolist() == expected_hp


def test_fresh_bootstrap_restores_lifecycle_defaults(monkeypatch):
    """Bootstrap zera os tres campos behavior/lifecycle ao default.

    Monkeypatch apenas nas dependencias do modulo bootstrap (autoridade
    real), nao em simulacao nem controls. O entry point pode ser
    simulation.bootstrap_new_world() (e o mesmo objeto), mas o custo e
    reduzido substituindo operacoes pesadas no namespace de bootstrap.
    """
    from primordial_soup import simulation

    original = state.runtime_rules
    saved_agents = list(agents)
    saved_zones = state.zones
    saved_zone_centers = state.zone_centers
    saved_nests = state.nests
    try:
        agents.clear()
        state.update_runtime_rules(
            low_hp_threshold=3500,
            stay_still_impulse=-0.5,
            death_hp_threshold=500,
        )
        sentinel_zone_centers = _valid_test_zone_centers()
        sentinel_zones = world.build_zone_mask(sentinel_zone_centers)
        sentinel_nests = _valid_test_nests()
        monkeypatch.setattr(bootstrap, "seed_lineages", lambda: None)
        monkeypatch.setattr(bootstrap, "place_initially", lambda: None)
        monkeypatch.setattr(bootstrap, "fill_fields", lambda: None)
        monkeypatch.setattr(
            bootstrap,
            "generate_zones",
            lambda: (sentinel_zones, sentinel_zone_centers),
        )
        monkeypatch.setattr(
            bootstrap, "generate_nests", lambda zones: sentinel_nests
        )
        monkeypatch.setattr(
            bootstrap,
            "random_population",
            lambda n: np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32),
        )

        simulation.bootstrap_new_world()

        assert state.runtime_rules.low_hp_threshold == int(cfg.LOW_HP_THRESHOLD)
        assert state.runtime_rules.stay_still_impulse == float(
            cfg.STAY_STILL_IMPULSE
        )
        assert state.runtime_rules.death_hp_threshold == int(
            cfg.DIE_WHEN_HP_LESS_OR_EQUAL
        )
        assert state.zones is sentinel_zones
        assert state.zone_centers == sentinel_zone_centers
        assert state.nests == sentinel_nests
    finally:
        agents[:] = saved_agents
        state.set_runtime_rules(original)
        state.zones = saved_zones
        state.zone_centers = saved_zone_centers
        state.nests = saved_nests


def test_recreate_preserves_lifecycle_runtime_rules_identity(monkeypatch):
    """controls.recreate() preserva a instancia de RuntimeRules.

    Recreate delega para bootstrap.bootstrap_new_world, que zera os
    tres campos behavior/lifecycle. Monkeypatch deve mirar o modulo
    bootstrap (autoridade real), nao controls (importador fino).
    """
    from primordial_soup import controls

    original = state.runtime_rules
    saved_agents = list(agents)
    saved_zones = state.zones
    saved_zone_centers = state.zone_centers
    saved_nests = state.nests
    try:
        agents.clear()
        state.update_runtime_rules(
            low_hp_threshold=3500,
            stay_still_impulse=-0.5,
            death_hp_threshold=500,
        )
        before = state.runtime_rules
        sentinel_zone_centers = _valid_test_zone_centers()
        sentinel_zones = world.build_zone_mask(sentinel_zone_centers)
        sentinel_nests = _valid_test_nests()
        monkeypatch.setattr(bootstrap, "seed_lineages", lambda: None)
        monkeypatch.setattr(bootstrap, "place_initially", lambda: None)
        monkeypatch.setattr(bootstrap, "fill_fields", lambda: None)
        monkeypatch.setattr(
            bootstrap,
            "generate_zones",
            lambda: (sentinel_zones, sentinel_zone_centers),
        )
        monkeypatch.setattr(
            bootstrap, "generate_nests", lambda zones: sentinel_nests
        )
        monkeypatch.setattr(
            bootstrap,
            "random_population",
            lambda n: np.zeros((0, cfg.GENOME_SIZE), dtype=np.float32),
        )

        controls.recreate()

        assert state.runtime_rules is before
        assert state.zone_centers == sentinel_zone_centers
    finally:
        agents[:] = saved_agents
        state.set_runtime_rules(original)
        state.zones = saved_zones
        state.zone_centers = saved_zone_centers
        state.nests = saved_nests


# Persistence edge cases live here so the final patch does not need to rewrite
# locally customized tails of test_load_atomicity.py.
@pytest.mark.parametrize(
    "field,bad",
    [
        ("low_hp_threshold", -1),
        ("low_hp_threshold", cfg.INITIAL_HP + 1),
        ("death_hp_threshold", -1),
        ("death_hp_threshold", cfg.INITIAL_HP + 1),
        ("stay_still_impulse", float("nan")),
        ("stay_still_impulse", float("inf")),
        ("stay_still_impulse", "not-a-number"),
    ],
)
def test_v23_rejects_invalid_lifecycle_runtime_field_atomically(tmp_path, field, bad):
    import pickle

    from primordial_soup import persistence

    original = state.runtime_rules
    saved_agents = list(agents)
    saved_zones = state.zones
    saved_zone_centers = state.zone_centers
    saved_nests = state.nests
    try:
        state.reset_counters()
        world.seed_lineages()
        for ag in agents:
            ag["pool"] = np.zeros(
                (cfg.INITIAL_POPULATION_PER_LINEAGE, cfg.GENOME_SIZE),
                dtype=np.float32,
            )
        world.place_initially()
        _install_checkpoint_geometry()

        path = tmp_path / "save.pkl"
        assert persistence.save(str(path)) is True
        with open(path, "rb") as f:
            data = pickle.load(f)
        data[field] = bad
        with open(path, "wb") as f:
            pickle.dump(data, f)

        before = state.runtime_rules
        assert persistence.load(str(path)) is False
        assert state.runtime_rules is before
    finally:
        agents[:] = saved_agents
        state.set_runtime_rules(original)
        state.zones = saved_zones
        state.zone_centers = saved_zone_centers
        state.nests = saved_nests


def test_v22_is_rejected_without_migration(tmp_path):
    """v22 e predecessor direto do schema atual; sem migration."""
    import pickle

    from primordial_soup import persistence

    original = state.runtime_rules
    saved_agents = list(agents)
    saved_zones = state.zones
    saved_zone_centers = state.zone_centers
    saved_nests = state.nests
    try:
        state.reset_counters()
        world.seed_lineages()
        for ag in agents:
            ag["pool"] = np.zeros(
                (cfg.INITIAL_POPULATION_PER_LINEAGE, cfg.GENOME_SIZE),
                dtype=np.float32,
            )
        world.place_initially()
        _install_checkpoint_geometry()

        path = tmp_path / "save.pkl"
        assert persistence.save(str(path)) is True
        with open(path, "rb") as f:
            data = pickle.load(f)
        data["versao"] = 22
        with open(path, "wb") as f:
            pickle.dump(data, f)

        before = state.runtime_rules
        assert persistence.load(str(path)) is False
        assert state.runtime_rules is before
    finally:
        agents[:] = saved_agents
        state.set_runtime_rules(original)
        state.zones = saved_zones
        state.zone_centers = saved_zone_centers
        state.nests = saved_nests


def test_lifecycle_configuration_items_order_and_hot_handlers():
    from primordial_soup import panels_defs
    from primordial_soup.panels import ItemKind

    original = state.runtime_rules
    try:
        panel = panels_defs._build_configuration()
        by_id = {item.id: item for item in panel.items}
        ids = [item.id for item in panel.items]

        assert (
            ids.index("global_scale_sigma")
            < ids.index("stay_still_impulse")
            < ids.index("section_ecology")
        )
        assert (
            ids.index("base_decay")
            < ids.index("low_hp_threshold")
            < ids.index("death_hp_threshold")
            < ids.index("predation_transfer")
            < ids.index("overcrowding_factor")
            < ids.index("zones")
            < ids.index("zone_hp")
        )

        for item_id in (
            "stay_still_impulse",
            "low_hp_threshold",
            "death_hp_threshold",
            "predation_transfer",
            "overcrowding_factor",
        ):
            assert by_id[item_id].kind is ItemKind.VALUE

        state.update_runtime_rules(
            stay_still_impulse=-0.5,
            low_hp_threshold=3500,
            death_hp_threshold=500,
            predation_transfer=100,
            damage_per_own_overcrowding=20,
        )
        assert panels_defs._v_stay_still_impulse() == "-0.5"
        assert panels_defs._v_low_hp_threshold() == "3500"
        assert panels_defs._v_death_hp_threshold() == "500"
        assert panels_defs._v_predation_transfer() == "100"
        assert panels_defs._v_overcrowding_factor() == "20"

        before = state.runtime_rules
        result = panels_defs._h_stay_still_impulse(None, None, 0)
        assert state.runtime_rules is before
        assert result.redraw is False

        result = panels_defs._h_stay_still_impulse(None, None, 1)
        assert state.runtime_rules.stay_still_impulse == -0.4
        assert result.redraw is True

        panels_defs._h_low_hp_threshold(None, None, 1)
        assert state.runtime_rules.low_hp_threshold == 3600
        panels_defs._h_death_hp_threshold(None, None, -1)
        assert state.runtime_rules.death_hp_threshold == 400

        panels_defs._h_predation_transfer(None, None, 1)
        assert (
            state.runtime_rules.predation_transfer
            == 100 + cfg.PREDATION_TRANSFER_STEP
        )

        panels_defs._h_overcrowding_factor(None, None, 1)
        assert (
            state.runtime_rules.damage_per_own_overcrowding
            == 20 + cfg.DAMAGE_PER_OWN_OVERCROWDING_STEP
        )

        state.update_runtime_rules(low_hp_threshold=cfg.MAX_LOW_HP_THRESHOLD)
        before = state.runtime_rules
        result = panels_defs._h_low_hp_threshold(None, None, 1)
        assert state.runtime_rules is before
        assert result.redraw is False

        state.update_runtime_rules(
            predation_transfer=cfg.MAX_PREDATION_TRANSFER,
        )
        before = state.runtime_rules
        result = panels_defs._h_predation_transfer(None, None, 1)
        assert state.runtime_rules is before
        assert result.redraw is False

        state.update_runtime_rules(
            damage_per_own_overcrowding=cfg.MAX_DAMAGE_PER_OWN_OVERCROWDING,
        )
        before = state.runtime_rules
        result = panels_defs._h_overcrowding_factor(None, None, 1)
        assert state.runtime_rules is before
        assert result.redraw is False
    finally:
        state.set_runtime_rules(original)


def test_lifecycle_ecology_i18n_labels():
    """Labels canonicos dos itens ecologicos atuais.

    Estes rotulos sao exibidos na UI. Nomes em pt/en precisam
    corresponder exatamente ao que os dicionarios publicam; um refactor
    que mude as chaves ou os valores quebra a interface.
    """
    from primordial_soup import i18n

    assert (
        i18n.TRANSLATIONS["en"]["item.predation_transfer"]
        == "Predation transfer"
    )
    assert (
        i18n.TRANSLATIONS["en"]["item.overcrowding_factor"]
        == "Overcrowding factor"
    )
    assert (
        i18n.TRANSLATIONS["pt"]["item.predation_transfer"]
        == "Transferência por predação"
    )
    assert (
        i18n.TRANSLATIONS["pt"]["item.overcrowding_factor"]
        == "Fator de superlotação"
    )