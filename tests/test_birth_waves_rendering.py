"""Regressao do hotfix Birth Waves.

Protege o bug NameError que existia no commit 338cf9c:

    _draw_birth_waves() referenciava
    _BIRTH_WAVE_TRAILING_RING_SCALE, mas a constante nunca foi
    declarada em rendering.py, e as tres constantes visuais antigas
    ainda estavam no modulo. Resultado em runtime:

        NameError: name '_BIRTH_WAVE_TRAILING_RING_SCALE' is not
        defined

O teste forca ring_index == 1 a ser processado, que foi exatamente
o ramo onde o runtime quebrou. Tambem confirma os valores finais
da calibracao visual e a hierarquia
_BIRTH_WAVE_COLOR_SCALE < _NEST_COLOR_SCALE.

Todos os docstrings deste arquivo sao intencionalmente ASCII puro.
"""

import numpy as np
import pytest

from primordial_soup import config as cfg
from primordial_soup import layout
from primordial_soup import rendering
from primordial_soup import state
from primordial_soup import ui_state
from primordial_soup import world
from primordial_soup.state import agents


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _valid_nests():
    """Geometria deterministica de ninhos valida (tres discos sem
    overlap), compativel com o contrato de rendering._draw_nests().
    """
    radius = cfg.NEST_RADIUS
    y = radius + 1
    stride = 2 * radius + 1
    return (
        (radius + 1, y),
        (radius + 1 + stride, y),
        (radius + 1 + 2 * stride, y),
    )


@pytest.fixture
def rendering_state():
    """Estado minimo para exercitar _draw_birth_waves sem pygame.

    Salva e restaura agents, zones, nests, inspected e birth_waves.
    Nao chama rendering.init() nem abre janela.
    """
    saved_agents = list(agents)
    saved_zones = state.zones
    saved_zones_active = state.zones_active
    saved_nests = state.nests
    saved_inspected = state.inspected_critter_id

    agents.clear()
    world.seed_lineages()

    state.zones = np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
        dtype=bool,
    )
    state.zones_active = False
    state.nests = _valid_nests()
    state.inspected_critter_id = None
    ui_state.clear_birth_waves()

    yield

    agents[:] = saved_agents
    state.zones = saved_zones
    state.zones_active = saved_zones_active
    state.nests = saved_nests
    state.inspected_critter_id = saved_inspected
    ui_state.clear_birth_waves()


def _empty_image():
    return np.zeros(
        (layout.LAYOUT.world_width, layout.LAYOUT.world_height, 3),
        dtype=np.uint8,
    )


# ---------------------------------------------------------------------------
# Contrato dos parametros visuais finais
# ---------------------------------------------------------------------------


def test_final_birth_wave_parameters():
    """Os quatro parametros visuais batem com a calibracao final.

    Estes asserts sao legitimamente por valor: representam uma
    calibracao visual deliberadamente especificada no hotfix.
    """
    assert rendering._BIRTH_WAVE_COLOR_SCALE == 0.30
    assert rendering._BIRTH_WAVE_RING_COUNT == 2
    assert rendering._BIRTH_WAVE_MAX_RADIUS_MULTIPLIER == 1.5
    assert rendering._BIRTH_WAVE_TRAILING_RING_SCALE == 0.55


def test_birth_wave_intensity_below_nest_ring():
    """Hierarquia visual: critter > nest ring > birth wave.

    O nest ring permanente usa _NEST_COLOR_SCALE; a Birth Wave
    precisa ficar abaixo dele para nao competir.
    """
    assert (
        rendering._BIRTH_WAVE_COLOR_SCALE
        < rendering._NEST_COLOR_SCALE
    )


def test_ui_state_duration_unchanged():
    """Duracao permanece 1.25 s. Nao faz parte deste hotfix."""
    assert ui_state.BIRTH_WAVE_DURATION_SECONDS == 1.25


# ---------------------------------------------------------------------------
# Regressao do NameError: ring_index == 1 precisa ser processado
# ---------------------------------------------------------------------------


def test_draw_birth_waves_processes_trailing_ring(
    rendering_state, monkeypatch
):
    """_draw_birth_waves processa ring_index == 1 sem NameError.

    Este e o teste que reproduz o bug original. Configura progress
    suficiente para que leading_radius > ring_spacing, garantindo
    que ambos os aneis sejam efetivamente desenhados.

    Com NEST_RADIUS=20:
        max_radius      = 20 * 1.5   = 30
        ring_spacing    = 20 // 4    = 5
        progress        = 0.50
        leading_radius  = round(0.5 * 30) = 15
        ring 0 radius   = 15
        ring 1 radius   = 10   -> ambos > 0

    Se _BIRTH_WAVE_TRAILING_RING_SCALE nao existir (estado do
    commit 338cf9c), a chamada levanta NameError. O teste falha
    antes de qualquer assert de pixel.

    A verificacao usa duas passagens isoladas: uma com
    _BIRTH_WAVE_RING_COUNT forcado para 1 (apenas o anel
    principal) e outra com o valor canonico (2, principal +
    trailing). A intensidade no mesmo pixel do trailing precisa
    ser ESTRITAMENTE maior na segunda passagem, provando que o
    ring_index == 1 contribuiu.
    """
    # Configura uma wave e captura seu progress de forma determinista
    # por meio do monkeypatch de birth_wave_progress.
    ui_state.add_birth_wave(0, started_at=0.0)

    monkeypatch.setattr(
        ui_state,
        "birth_wave_progress",
        lambda wave, now=None: 0.50,
    )

    # Centers: usa o ninho 0 instalado em rendering_state.
    center = state.nests[0]

    # ------------------------------------------------------------------
    # Passo 1: desenha apenas com o anel principal.
    # ------------------------------------------------------------------
    monkeypatch.setattr(rendering, "_BIRTH_WAVE_RING_COUNT", 1)
    image_leading_only = _empty_image()
    rendering._draw_birth_waves(image_leading_only)

    # ------------------------------------------------------------------
    # Passo 2: desenha com o ring count canonico (principal + trailing).
    # ------------------------------------------------------------------
    monkeypatch.setattr(rendering, "_BIRTH_WAVE_RING_COUNT", 2)
    image_with_trailing = _empty_image()
    rendering._draw_birth_waves(image_with_trailing)

    # ------------------------------------------------------------------
    # Verificacoes
    # ------------------------------------------------------------------
    # O anel principal dobra com a segunda passagem? Nao: as posicoes
    # do anel principal sao identicas nas duas imagens (o
    # ring_index == 0 sempre tem radius == leading_radius). Entao a
    # regiao do trailing ring (radius == leading - spacing) e a UNICA
    # onde a segunda imagem pode diferir.

    # Localiza pixels nao-zero em ambas as imagens.
    nonzero_leading_only = np.argwhere(image_leading_only.any(axis=2))
    nonzero_with_trailing = np.argwhere(image_with_trailing.any(axis=2))

    assert nonzero_leading_only.size > 0, (
        "anel principal nao produziu pixels; setup invalido"
    )
    assert nonzero_with_trailing.size > 0, (
        "anel trailing nao produziu pixels; "
        "trailing branch nao foi executado"
    )
    assert (
        nonzero_with_trailing.shape[0]
        > nonzero_leading_only.shape[0]
    ), (
        "imagem com ring_count=2 nao possui mais pixels que com "
        "ring_count=1; o trailing ring nao contribuiu"
    )

    # O pixel do trailing ring (qualquer um exclusivo da segunda
    # imagem) deve ter a cor derivada exata da linhagem Red, escalada
    # por _BIRTH_WAVE_COLOR_SCALE, fade e
    # _BIRTH_WAVE_TRAILING_RING_SCALE. Red possui apenas o canal R
    # positivo, entao (R > 0, G == 0, B == 0) e a cor correta.
    mask_trailing_only = (
        image_with_trailing.any(axis=2)
        & ~image_leading_only.any(axis=2)
    )
    assert mask_trailing_only.any(), (
        "nenhum pixel exclusivo do trailing ring foi desenhado"
    )
    trailing_pixels = image_with_trailing[mask_trailing_only]

    # Derivar a cor esperada para lineage 0 (Red).
    lineage_color = cfg.LINEAGES[0]["color"]
    progress = 0.50
    fade = (1.0 - progress) ** 1.5
    expected = tuple(
        int(
            round(
                channel
                * rendering._BIRTH_WAVE_COLOR_SCALE
                * fade
                * rendering._BIRTH_WAVE_TRAILING_RING_SCALE
            )
        )
        for channel in lineage_color
    )

    # A imagem inicial e zero e o mask isola pixels exclusivos do
    # trailing ring, entao a igualdade exata e apropriada. Isso prova
    # simultaneamente: trailing branch executou, escala 0.55 foi
    # aplicada, e a cor continua sendo da linhagem.
    assert np.all(
        trailing_pixels
        == np.asarray(expected, dtype=np.uint8)
    ), (
        f"cor do trailing ring divergiu: esperado {expected}, "
        f"obtido exemplos {trailing_pixels[:3].tolist()}."
    )


def test_draw_birth_waves_with_no_nests_raises(rendering_state):
    """Se ha wave ativa mas state.nests e None, o runtime esta
    inconsistente: _draw_birth_waves deve levantar, nao falhar
    silenciosamente.
    """
    ui_state.add_birth_wave(0, started_at=0.0)
    state.nests = None

    image = _empty_image()
    with pytest.raises(RuntimeError):
        rendering._draw_birth_waves(image)
