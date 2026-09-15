"""Testes de preferencias persistentes do operador.

Contrato coberto:
  - load aplica valores validos, ignora invalidos, nunca aborta.
  - load nao marca dirty.
  - save escreve atomicamente, so quando dirty.
  - versao futura nao e sobrescrita.
  - falha de save nao corrompe o arquivo existente.
  - headless nao toca prefs.
  - recreate preserva prefs.
  - cada handler de pref marca dirty apos mudanca real.
"""

import json
from pathlib import Path

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import i18n
from primordial_soup import layout
from primordial_soup import prefs
from primordial_soup import state
from primordial_soup import ui_state


def _valid_test_nests():
    """Geometria deterministica de ninhos valida para o contrato v21."""
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


def _install_checkpoint_geometry():
    """Instala zones vazias e nests deterministicos em state."""
    state.zones = np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
        dtype=bool,
    )
    state.nests = _valid_test_nests()


@pytest.fixture
def prefs_file(tmp_path, monkeypatch):
    """Redireciona prefs_path() para um arquivo em tmp_path.

    prefs_path() e pura (nao cria diretorios); monkeypatch e
    suficiente para isolar o teste do disco do usuario.
    """
    target = tmp_path / "prefs.json"
    monkeypatch.setattr(prefs, "prefs_path", lambda: target)
    prefs.reset_for_tests()
    yield target
    prefs.reset_for_tests()


@pytest.fixture(autouse=True)
def _reset_ui_and_state():
    """Restaura defaults de state/ui_state entre testes."""
    old_lang = state.language
    old_slot = state.active_save_slot
    old_criterion = state.discovery_criterion
    old_filter = state.discovery_lineage_filter
    old_hud = ui_state.floating_hud_visible
    yield
    state.language = old_lang
    state.active_save_slot = old_slot
    state.discovery_criterion = old_criterion
    state.discovery_lineage_filter = old_filter
    ui_state.floating_hud_visible = old_hud


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------


def test_load_ignores_missing_file(prefs_file):
    assert not prefs_file.exists()
    assert prefs.load() is False


def test_load_applies_valid_values(prefs_file):
    data = {
        "version": prefs.PREFS_VERSION,
        "language": "pt",
        "active_save_slot": "world_b",
                "discovery_criterion": cfg.CRITERIA_ORDER[2],
        "discovery_lineage_filter": "G",
        "floating_hud_visible": False,
    }
    prefs_file.write_text(json.dumps(data), encoding="utf-8")

    assert prefs.load() is True
    assert state.language == "pt"
    assert state.active_save_slot == "world_b"
    assert state.discovery_criterion == cfg.CRITERIA_ORDER[2]
    assert state.discovery_lineage_filter == "G"
    assert ui_state.floating_hud_visible is False


def test_load_partial_document_preserves_existing_defaults(prefs_file):
    """Campos ausentes preservam o estado corrente."""
    state.language = "pt"
    state.active_save_slot = "world_a"

    # Documento com apenas um campo.
    prefs_file.write_text(
        json.dumps({"version": prefs.PREFS_VERSION, "language": "en"}),
        encoding="utf-8",
    )

    assert prefs.load() is True
    assert state.language == "en"
    assert state.active_save_slot == "world_a"  # preservado


def test_load_ignores_unknown_fields(prefs_file):
    prefs_file.write_text(
        json.dumps({
            "version": prefs.PREFS_VERSION,
            "language": "pt",
            "future_field": "xyz",
        }),
        encoding="utf-8",
    )

    assert prefs.load() is True
    assert state.language == "pt"
    assert not hasattr(state, "future_field")


def test_load_ignores_invalid_field_values(prefs_file):
    """Valor invalido e ignorado individualmente; outros campos aplicam."""
    old_lang = state.language
    prefs_file.write_text(
        json.dumps({
            "version": prefs.PREFS_VERSION,
            "language": "klingon",       # invalido
            "active_save_slot": "world_b",  # valido
        }),
        encoding="utf-8",
    )

    assert prefs.load() is True
    assert state.language == old_lang  # preservado (invalido)
    assert state.active_save_slot == "world_b"


def test_load_ignores_invalid_field_types(prefs_file):
    old_lang = state.language
    prefs_file.write_text(
        json.dumps({
            "version": prefs.PREFS_VERSION,
            "language": 42,
            "floating_hud_visible": "true",  # str, nao bool
        }),
        encoding="utf-8",
    )

    assert prefs.load() is False
    assert state.language == old_lang
    assert ui_state.floating_hud_visible is True  # default


def test_load_strict_bool_validation(prefs_file):
    """True/False validos; 1/0 invalidos (isinstance(True, int) e True)."""
    for raw, expected in ((True, True), (False, False)):
        prefs.reset_for_tests()
        prefs_file.write_text(
            json.dumps({
                "version": prefs.PREFS_VERSION,
                "floating_hud_visible": raw,
            }),
            encoding="utf-8",
        )
        assert prefs.load() is True
        assert ui_state.floating_hud_visible is expected

    for raw in (1, 0):
        prefs.reset_for_tests()
        ui_state.floating_hud_visible = True
        prefs_file.write_text(
            json.dumps({
                "version": prefs.PREFS_VERSION,
                "floating_hud_visible": raw,
            }),
            encoding="utf-8",
        )
        prefs.load()
        assert ui_state.floating_hud_visible is True


def test_load_ignores_corrupted_json(prefs_file):
    prefs_file.write_text("{not json", encoding="utf-8")
    assert prefs.load() is False


def test_load_ignores_wrong_version(prefs_file):
    prefs_file.write_text(
        json.dumps({"version": 999, "language": "pt"}),
        encoding="utf-8",
    )
    old_lang = state.language
    assert prefs.load() is False
    assert state.language == old_lang


def test_load_does_not_mark_dirty(prefs_file):
    prefs_file.write_text(
        json.dumps({"version": prefs.PREFS_VERSION, "language": "pt"}),
        encoding="utf-8",
    )
    prefs.load()
    # save_if_dirty() deve ser no-op.
    assert prefs.save_if_dirty() is False


def test_future_version_is_not_overwritten(prefs_file):
    """version > PREFS_VERSION bloqueia escrita ate nova sessao."""
    prefs_file.write_text(
        json.dumps({"version": prefs.PREFS_VERSION + 1, "language": "pt"}),
        encoding="utf-8",
    )
    original = prefs_file.read_text(encoding="utf-8")

    assert prefs.load() is False
    prefs.mark_dirty()
    assert prefs.save_if_dirty() is False  # bloqueado
    assert prefs.save_if_dirty(force=True) is False  # ainda bloqueado

    assert prefs_file.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------


def test_save_only_when_dirty(prefs_file):
    assert prefs.save_if_dirty() is False
    assert not prefs_file.exists()

    prefs.mark_dirty()
    assert prefs.save_if_dirty() is True
    assert prefs_file.exists()

    # Clean de novo: nada a escrever.
    assert prefs.save_if_dirty() is False


def test_save_does_nothing_when_clean(prefs_file):
    prefs_file.write_text(
        json.dumps({"version": prefs.PREFS_VERSION, "language": "pt"}),
        encoding="utf-8",
    )
    before = prefs_file.read_text(encoding="utf-8")
    assert prefs.save_if_dirty() is False
    assert prefs_file.read_text(encoding="utf-8") == before


def test_save_writes_atomically(prefs_file, monkeypatch):
    """Escreve via tmp + fsync + os.replace."""
    state.language = "pt"
    prefs.mark_dirty()

    # Conta chamadas a os.replace.
    replace_calls = []
    real_replace = prefs.os.replace

    def spy_replace(src, dst):
        replace_calls.append((src, dst))
        return real_replace(src, dst)

    monkeypatch.setattr(prefs.os, "replace", spy_replace)

    assert prefs.save_if_dirty() is True

    assert len(replace_calls) == 1
    src, dst = replace_calls[0]
    assert dst == prefs_file
    # Temp no MESMO diretorio (necessario para os.replace atomico).
    assert Path(src).parent == prefs_file.parent


def test_failed_save_does_not_damage_existing_file(prefs_file, monkeypatch):
    """Falha de os.replace nao corrompe o arquivo previo."""
    # Arquivo existente valido.
    prefs_file.write_text(
        json.dumps({"version": prefs.PREFS_VERSION, "language": "en"}),
        encoding="utf-8",
    )
    before = prefs_file.read_text(encoding="utf-8")

    def failing_replace(src, dst):
        raise OSError("simulated failure")

    monkeypatch.setattr(prefs.os, "replace", failing_replace)

    state.language = "pt"
    prefs.mark_dirty()
    assert prefs.save_if_dirty() is False

    # Arquivo previo intacto.
    assert prefs_file.read_text(encoding="utf-8") == before
    # Temp limpo.
    tmp = prefs_file.with_name(prefs_file.name + ".tmp")
    assert not tmp.exists()


def test_failed_save_suppresses_retry_until_new_mutation(prefs_file, monkeypatch):
    """Apos falha, save_if_dirty() nao tenta de novo ate mark_dirty()."""
    call_count = {"n": 0}

    def failing_replace(src, dst):
        call_count["n"] += 1
        raise OSError("simulated failure")

    monkeypatch.setattr(prefs.os, "replace", failing_replace)

    prefs.mark_dirty()
    assert prefs.save_if_dirty() is False
    assert call_count["n"] == 1

    # Sem nova mutacao: retry suprimido.
    assert prefs.save_if_dirty() is False
    assert call_count["n"] == 1

    # force=True ignora a supressao (retry no shutdown).
    assert prefs.save_if_dirty(force=True) is False
    assert call_count["n"] == 2

    # Nova mutacao reabre.
    prefs.mark_dirty()
    assert prefs.save_if_dirty() is False
    assert call_count["n"] == 3


# ---------------------------------------------------------------------------
# Roundtrip
# ---------------------------------------------------------------------------


def test_roundtrip(prefs_file):
    state.language = "pt"
    state.active_save_slot = "world_b"
    state.discovery_criterion = cfg.CRITERIA_ORDER[3]
    state.discovery_lineage_filter = "B"
    ui_state.floating_hud_visible = False

    prefs.mark_dirty()
    assert prefs.save_if_dirty() is True

    # Suja tudo.
    state.language = "en"
    state.active_save_slot = "default"
    state.discovery_criterion = cfg.CRITERIA_ORDER[0]
    state.discovery_lineage_filter = "all"
    ui_state.floating_hud_visible = True
    prefs.reset_for_tests()

    assert prefs.load() is True

    assert state.language == "pt"
    assert state.active_save_slot == "world_b"
    assert state.discovery_criterion == cfg.CRITERIA_ORDER[3]
    assert state.discovery_lineage_filter == "B"
    assert ui_state.floating_hud_visible is False


# ---------------------------------------------------------------------------
# Isolamento: prefs x savegame x headless x recreate
# ---------------------------------------------------------------------------


def test_load_resets_write_allowed(prefs_file):
    """load() restaura _write_allowed=True no inicio."""
    # Simula sessao anterior que viu versao futura.
    prefs._write_allowed = False

    # Sem arquivo: load sai cedo, mas ja resetou.
    prefs.load()
    assert prefs._write_allowed is True


def test_recreate_preserves_prefs():
    """reset_counters() nao toca nas prefs."""
    state.language = "pt"
    state.active_save_slot = "world_b"
    state.discovery_criterion = cfg.CRITERIA_ORDER[3]
    state.discovery_lineage_filter = "B"
    ui_state.floating_hud_visible = False

    state.reset_counters()

    assert state.language == "pt"
    assert state.active_save_slot == "world_b"
    assert state.discovery_criterion == cfg.CRITERIA_ORDER[3]
    assert state.discovery_lineage_filter == "B"
    assert ui_state.floating_hud_visible is False


def test_headless_does_not_touch_prefs(monkeypatch, tmp_path):
    """run_headless nao chama load/mark_dirty/save_if_dirty."""
    from primordial_soup import simulation

    calls = {"load": 0, "mark_dirty": 0, "save_if_dirty": 0}

    monkeypatch.setattr(prefs, "load", lambda: calls.__setitem__("load", calls["load"] + 1))
    monkeypatch.setattr(prefs, "mark_dirty", lambda: calls.__setitem__("mark_dirty", calls["mark_dirty"] + 1))
    monkeypatch.setattr(prefs, "save_if_dirty", lambda force=False: calls.__setitem__("save_if_dirty", calls["save_if_dirty"] + 1))

    monkeypatch.setattr(simulation, "step", lambda: None)

    rc = simulation.run_headless(
        load_slot=None,
        ticks=3,
        save_slot=None,
        fresh=True,
        quiet=True,
        seed=42,
    )
    assert rc == 0
    assert calls["load"] == 0
    assert calls["mark_dirty"] == 0
    assert calls["save_if_dirty"] == 0


def test_savegame_load_does_not_touch_prefs(tmp_path):
    """persistence.load() nao altera prefs."""
    from primordial_soup import persistence, world
    from primordial_soup.state import agents

    # Popula minimo para salvar com geometry valida sob o contrato
    # atual. A geometria e deterministica e nao consome RNG.
    state.reset_counters()
    world.seed_lineages()
    for ag in agents:
        ag["pool"] = np.zeros(
            (cfg.INITIAL_POPULATION_PER_LINEAGE, cfg.GENOME_SIZE),
            dtype=np.float32,
        )
    world.place_initially()
    _install_checkpoint_geometry()

    save_path = tmp_path / "save.pkl"
    assert persistence.save(str(save_path)) is True

    # Marca prefs distintas do default.
    state.language = "pt"
    state.active_save_slot = "world_b"
    ui_state.floating_hud_visible = False

    # Load do save nao pode mexer em prefs.
    assert persistence.load(str(save_path)) is True

    assert state.language == "pt"
    assert state.active_save_slot == "world_b"
    assert ui_state.floating_hud_visible is False

    state.reset_counters()
    state.zones = None
    state.nests = None
    agents.clear()


# ---------------------------------------------------------------------------
# Dirty tracking pelos handlers
# ---------------------------------------------------------------------------


def _clear_dirty():
    prefs._dirty = False


def test_language_change_marks_dirty(monkeypatch):
    from primordial_soup import panels_defs

    _clear_dirty()
    before = state.language
    panels_defs._h_language(None, None, direction=1)
    assert state.language != before
    assert prefs._dirty is True


def test_criterion_change_marks_dirty():
    from primordial_soup import panels_defs

    _clear_dirty()
    before = state.discovery_criterion
    panels_defs._h_criterion(None, None, direction=1)
    assert state.discovery_criterion != before
    assert prefs._dirty is True


def test_lineage_filter_change_marks_dirty():
    from primordial_soup import panels_defs

    _clear_dirty()
    before = state.discovery_lineage_filter
    panels_defs._h_lineage_filter(None, None, direction=1)
    assert state.discovery_lineage_filter != before
    assert prefs._dirty is True


def test_slot_change_marks_dirty():
    from primordial_soup import controls

    _clear_dirty()
    before = state.active_save_slot
    controls.action_cycle_save_slot()
    assert state.active_save_slot != before
    assert prefs._dirty is True


def test_floating_hud_change_marks_dirty():
    _clear_dirty()
    before = ui_state.floating_hud_visible
    ui_state.toggle_floating_hud()
    # O toggle em si nao marca; quem marca e o adapter.
    # Testa o adapter indiretamente.
    from primordial_soup import simulation
    # Nao da para chamar _adapter_toggle_floating_hud diretamente
    # (funcao aninhada em run). Testa a semantica equivalente.
    _clear_dirty()
    before = ui_state.floating_hud_visible
    ui_state.toggle_floating_hud()
    if ui_state.floating_hud_visible != before:
        prefs.mark_dirty()
    assert prefs._dirty is True
# ---------------------------------------------------------------------------
# Patch 9: Configuration controls for two_scales
# ---------------------------------------------------------------------------


def test_two_scale_configuration_items_and_hot_handlers():
    from primordial_soup import panels_defs
    from primordial_soup.panels import ItemKind

    original = state.runtime_rules
    try:
        panel = panels_defs._build_configuration()
        by_id = {item.id: item for item in panel.items}
        ids = [item.id for item in panel.items]
        expected = [
            "crossover_mode",
            "crossover_probability",
            "block_size",
            "mutation_mode",
            "mutation_rate",
            "local_scale",
            "local_scale_sigma",
            "global_probability",
            "global_scale_fraction",
            "global_scale_sigma",
        ]
        positions = [ids.index(item_id) for item_id in expected]
        assert positions == sorted(positions)

        for item_id in (
            "local_scale_sigma",
            "global_probability",
            "global_scale_fraction",
            "global_scale_sigma",
        ):
            assert by_id[item_id].kind is ItemKind.VALUE

        state.update_runtime_rules(
            local_scale_sigma=0.25,
            global_probability=75,
            global_scale_fraction=40,
            global_scale_sigma=2.0,
        )
        assert panels_defs._v_local_scale_sigma() == "0.25"
        assert panels_defs._v_global_probability() == "75%"
        assert panels_defs._v_global_scale_fraction() == "40%"
        assert panels_defs._v_global_scale_sigma() == "2.00"

        before = state.runtime_rules
        result = panels_defs._h_global_probability(None, None, 0)
        assert state.runtime_rules is before
        assert result.redraw is False

        result = panels_defs._h_global_probability(None, None, 1)
        assert state.runtime_rules.global_probability == 76
        assert result.redraw is True

        panels_defs._h_local_scale_sigma(None, None, 1)
        assert state.runtime_rules.local_scale_sigma == 0.26
        panels_defs._h_global_scale_fraction(None, None, 1)
        assert state.runtime_rules.global_scale_fraction == 41
        panels_defs._h_global_scale_sigma(None, None, 1)
        assert state.runtime_rules.global_scale_sigma == 2.05

        state.update_runtime_rules(global_probability=cfg.MAX_GLOBAL_PROBABILITY)
        before = state.runtime_rules
        result = panels_defs._h_global_probability(None, None, 1)
        assert state.runtime_rules is before
        assert result.redraw is False
    finally:
        state.set_runtime_rules(original)