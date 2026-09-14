"""Chaves do Telemetry HUD existem em todos os idiomas.

Protege contra adicionar label em EN sem adicionar em PT (ou
vice-versa): o fallback silencioso de i18n mascararia o problema
(exibiria EN num layout PT).
"""

import pytest

from primordial_soup import i18n


_REQUIRED_KEYS = (
    # Telemetry HUD
    "hud.label.tick",
    "hud.label.speed",
    "hud.label.births",
    "hud.label.deaths",
    "hud.label.slot",
    "hud.label.mutation",
    "hud.label.mode",
    "hud.label.local",
    "hud.label.global",
    "hud.label.environment",
    "hud.label.zones",
    "hud.label.zone_hp",
    "hud.label.reproduction",
    "hud.label.weights",
    "hud.zone_summary_on",
    "hud.zone_summary_off",
    "hud.zone_summary_none",
    # Command Dock
    "command.group.simulation",
    "command.group.panels",
    "command.group.navigation",
    "command.group.quick",
    "command.pause",
    "command.step",
    "command.new_world",
    "command.fullscreen",
    "command.back_quit",
    "command.inspect",
    "command.configuration",
    "command.metrics",
    "command.session",
    "command.tools",
    "command.select",
    "command.change",
    "command.panel",
    "command.activate",
    "command.observe",
    "command.hide_hud",
    "command.load",
    "command.slot",
    "command.zones",
    "command.record",
    # Apresentacao de valores canonicos e gates de reproducao.
    "hud.value.mutation_mode.surgical",
    "hud.value.mutation_mode.two_scales",
    "hud.value.environment.zonas",
    "hud.reproduction_gates",
)

# Chaves que NAO devem mais existir apos o Patch 3: o HUD textual
# antigo foi removido em favor do Command Dock.
_REMOVED_KEYS = (
    "hud.section_sim",
    "hud.controls_1",
    "hud.section_panels",
    "hud.controls_2",
    "hud.section_navigation",
    "hud.controls_3",
    "hud.section_quick",
    "hud.controls_4",
    "hud.section_observation",
    "hud.controls_5",
    "hud.tick_speed",
    "hud.births_deaths",
    "hud.mutation",
    "hud.selection",
    "hud.environment",
    "hud.save_slot",
    "hud.zone_hp_param",
    "hud.repro_gates",
    "hud.metric_prefix",
    "hud.zones_none",
    "hud.zones_fmt",
    "hud.zones_off_suffix",
    "hud.zones_damage",
    "hud.zones_zkey",
)


@pytest.mark.parametrize("lang", i18n.AVAILABLE_LANGUAGES)
@pytest.mark.parametrize("key", _REQUIRED_KEYS)
def test_required_keys_present_in_all_languages(lang, key):
    assert key in i18n.TRANSLATIONS[lang], (
        f"chave {key!r} ausente no idioma {lang!r}"
    )


@pytest.mark.parametrize("lang", i18n.AVAILABLE_LANGUAGES)
@pytest.mark.parametrize("key", _REMOVED_KEYS)
def test_removed_keys_are_gone(lang, key):
    """Chaves do HUD textual antigo devem ter sido removidas.

    Protege contra reintroduzir o HUD em cards por engano, ou deixar
    strings mortas ocupando espaco no i18n.
    """
    assert key not in i18n.TRANSLATIONS[lang], (
        f"chave {key!r} deveria ter sido removida de {lang!r}"
    )


# ---------------------------------------------------------------------------
# Regressao de conteudo: os termos principais batem com o idioma.
# ---------------------------------------------------------------------------
#
# test_required_keys_present_in_all_languages so garante presenca, nao
# correcao semantica. Foi assim que NASC vazou para EN e SPEED ficou em
# PT. Este teste fixa strings deliberadamente: seu proposito E verificar
# conteudo de traducao, nao comportamento do dominio.
def test_hud_labels_regression_terms():
    en = i18n.TRANSLATIONS["en"]
    pt = i18n.TRANSLATIONS["pt"]

    assert en["hud.label.births"] == "BIRTHS"
    assert en["hud.label.deaths"] == "DEATHS"
    assert en["hud.label.zones"] == "ZONES"
    assert en["hud.label.weights"] == "WEIGHTS"
    assert en["hud.label.zone_hp"] == "ZONE HP"
    assert en["hud.label.speed"] == "SPEED"
    assert en["hud.label.mode"] == "MODE"

    assert pt["hud.label.speed"] == "VEL"
    assert pt["hud.label.mode"] == "MODO"
    assert pt["hud.label.zones"] == "ZONAS"
    assert pt["hud.label.weights"] == "PESOS"
    assert pt["hud.label.tick"] == "PASSO"
    assert pt["hud.label.slot"] == "SALV."

    # Apresentacao de valores canonicos: PT traduz, dominio nao muda.
    assert pt["hud.value.mutation_mode.two_scales"] == "duas escalas"
    assert en["hud.value.mutation_mode.two_scales"] == "two scales"
    assert pt["hud.value.environment.zonas"] == "zonas"
    assert en["hud.value.environment.zonas"] == "zones"


def test_lineage_header_is_dynamic():
    """_lineage_header_text() reage a state.language em runtime.

    Protege contra reintroduzir uma constante localizada em import-time,
    que congelaria o cabecalho da tabela de linhagens no idioma do boot.
    """
    from primordial_soup import rendering, state

    old_lang = state.language
    try:
        state.language = "en"
        en = rendering._lineage_header_text()

        state.language = "pt"
        pt = rendering._lineage_header_text()

        assert en != pt
        assert "score" in en
        assert "pont" in pt
    finally:
        state.language = old_lang
