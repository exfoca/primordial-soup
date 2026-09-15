"""Teste do contrato de run_headless quanto a ticks.

Protege a propriedade definida no Patch 5:

    ticks=None  -> 0 ticks, sim.step() nunca e executado
    ticks=0     -> 0 ticks, sim.step() nunca e executado
    ticks=N>0   -> exatamente N ticks, sim.step() roda N vezes

O teste e propositalmente mais forte que "tick_count == 0": ele
monkeypatcha simulation.step para falhar se for chamado. Assim, o
contrato "nenhum tick roda" e provado por AUSENCIA de chamada, nao
por inferencia sobre o contador.

Nao refatoramos producao para tornar este teste possivel. O
monkeypatch cobre exatamente o ponto que queremos proteger.

Todos os docstrings e comentarios deste arquivo sao intencionalmente
ASCII puro, seguindo o estilo de nomenclatura interna do projeto.
"""

import numpy as np
import pytest

from primordial_soup import simulation
from primordial_soup import state


@pytest.fixture
def forbid_step(monkeypatch):
    """Faz simulation.step explodir se for chamado.

    Retorna um contador mutavel para o teste verificar quantas vezes
    foi chamado (deve ser 0).
    """
    calls = {"n": 0}

    def _forbidden():
        calls["n"] += 1
        raise AssertionError(
            "simulation.step foi chamado apesar de ticks=0/None."
        )

    monkeypatch.setattr(simulation, "step", _forbidden)
    return calls


def test_run_headless_ticks_none_runs_zero(monkeypatch, forbid_step):
    """ticks=None -> nenhuma chamada a step()."""
    # Evita qualquer escrita real em disco: save_slot=None pula
    # persistence.save() inteiramente.
    rc = simulation.run_headless(
        load_slot=None,
        ticks=None,
        save_slot=None,
        fresh=True,
        quiet=True,
        seed=42,
    )
    assert rc == 0
    assert forbid_step["n"] == 0, (
        f"ticks=None deveria rodar 0 ticks; "
        f"step() foi chamado {forbid_step['n']} vezes."
    )


def test_run_headless_ticks_zero_runs_zero(monkeypatch, forbid_step):
    """ticks=0 -> nenhuma chamada a step()."""
    rc = simulation.run_headless(
        load_slot=None,
        ticks=0,
        save_slot=None,
        fresh=True,
        quiet=True,
        seed=42,
    )
    assert rc == 0
    assert forbid_step["n"] == 0, (
        f"ticks=0 deveria rodar 0 ticks; "
        f"step() foi chamado {forbid_step['n']} vezes."
    )


def test_run_headless_ticks_positive_runs_exactly_n(monkeypatch):
    """ticks=N>0 -> step() chamado exatamente N vezes.

    Nao usa forbid_step; conta chamadas com um stub que nao levanta.
    """
    calls = {"n": 0}

    def _count_only():
        calls["n"] += 1

    monkeypatch.setattr(simulation, "step", _count_only)

    rc = simulation.run_headless(
        load_slot=None,
        ticks=7,
        save_slot=None,
        fresh=True,
        quiet=True,
        seed=42,
    )
    assert rc == 0
    assert calls["n"] == 7, (
        f"ticks=7 deveria rodar exatamente 7 ticks; "
        f"step() foi chamado {calls['n']} vezes."
    )