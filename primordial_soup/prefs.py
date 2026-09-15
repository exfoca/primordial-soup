# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Preferencias persistentes do operador.

Separado do savegame do mundo por design:

    .pkl    checkpoint do MUNDO (populacao, genomas, RNGs, scheduler)
    prefs   preferencias do OPERADOR (idioma, slot, metrica, HUD)

Invariantes arquiteturais:
    1. PREFS nao altera fisica da simulacao.
    2. SAVEGAME nao restaura nem sobrescreve PREFS.
    3. HEADLESS nao le nem escreve PREFS.

Escrita automatica: handlers marcam dirty; simulation.run() chama
save_if_dirty() a cada frame e no shutdown.
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path

from . import config as cfg
from . import state
from . import ui_state


PREFS_VERSION = 1
PREFS_FILENAME = "prefs.json"


# --- Localizacao --------------------------------------------------------

def _prefs_dir() -> Path:
    """Diretorio de configuracao por usuario, por plataforma.

    Nunca retorna CWD: um arquivo de prefs no diretorio de execucao
    produziria arquivos diferentes conforme o cwd, sem o usuario
    perceber.
    """
    if sys.platform.startswith("linux") or sys.platform.startswith("freebsd"):
        base = os.environ.get("XDG_CONFIG_HOME", "").strip()
        if not base:
            base = str(Path.home() / ".config")
        return Path(base) / "primordial_soup"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "primordial_soup"
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", "").strip()
        if not base:
            base = str(Path.home())
        return Path(base) / "primordial_soup"
    return Path.home() / ".config" / "primordial_soup"


def prefs_path() -> Path:
    """Resolve o caminho do arquivo. Nao cria diretorios."""
    return _prefs_dir() / PREFS_FILENAME


# --- Validadores por campo ---------------------------------------------

def _validate_language(value):
    from . import i18n
    if isinstance(value, str) and value in i18n.AVAILABLE_LANGUAGES:
        return value
    return None


def _validate_save_slot(value):
    if isinstance(value, str) and value:
        return value
    return None


def _validate_criterion(value):
    if isinstance(value, str) and value in cfg.CRITERIA_ORDER:
        return value
    return None


def _validate_lineage_filter(value):
    if isinstance(value, str) and value in cfg.LINEAGE_FILTER_ORDER:
        return value
    return None


def _validate_bool(value):
    # bool estrito: isinstance(True, int) e True em Python, entao
    # checar isinstance(value, bool) antes de qualquer coercao.
    if isinstance(value, bool):
        return value
    return None


# Mapeamento campo -> (getter, setter, validador).
# getter/setter acessam state ou ui_state conforme o caso.
_FIELDS = {
    "language": (
        lambda: state.language,
        lambda v: setattr(state, "language", v),
        _validate_language,
    ),
    "active_save_slot": (
        lambda: state.active_save_slot,
        lambda v: setattr(state, "active_save_slot", v),
        _validate_save_slot,
    ),
    "discovery_criterion": (
        lambda: state.discovery_criterion,
        lambda v: setattr(state, "discovery_criterion", v),
        _validate_criterion,
    ),
    "discovery_lineage_filter": (
        lambda: state.discovery_lineage_filter,
        lambda v: setattr(state, "discovery_lineage_filter", v),
        _validate_lineage_filter,
    ),
    "floating_hud_visible": (
        lambda: ui_state.floating_hud_visible,
        lambda v: setattr(ui_state, "floating_hud_visible", v),
        _validate_bool,
    ),
}


def _current_prefs() -> dict:
    data = {"version": PREFS_VERSION}
    for field, (getter, _setter, _validator) in _FIELDS.items():
        data[field] = getter()
    return data


# --- Estado interno ------------------------------------------------------

_dirty: bool = False
_write_allowed: bool = True
_save_failure_suppressed: bool = False


def mark_dirty() -> None:
    """Registra que ha uma diferenca persistivel.

    Reset _save_failure_suppressed: uma nova mutacao reabre a
    possibilidade de escrita, mesmo que a tentativa anterior tenha
    falhado.
    """
    global _dirty, _save_failure_suppressed
    _dirty = True
    _save_failure_suppressed = False


# --- Load ----------------------------------------------------------------

def load() -> bool:
    """Aplica prefs do disco. Nunca aborta o boot.

    Retorna True se ao menos um campo foi aplicado. Falhas (arquivo
    ausente, JSON corrompido, versao incompativel) retornam False e
    deixam os defaults intactos.

    Nao marca dirty: o estado carregado e o estado corrente.
    """
    global _write_allowed

    _write_allowed = True

    path = prefs_path()
    if not path.exists():
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[prefs] {path} corrompido ({e!r}); usando defaults.")
        return False

    if not isinstance(data, dict):
        print(f"[prefs] {path} nao contem um objeto JSON; usando defaults.")
        return False

    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool):
        print(f"[prefs] {path} sem version valida; usando defaults.")
        return False

    if version > PREFS_VERSION:
        print(
            f"[prefs] {path} version={version} > {PREFS_VERSION}; "
            f"ignorando e protegendo contra sobrescrita."
        )
        _write_allowed = False
        return False

    if version < PREFS_VERSION:
        print(
            f"[prefs] {path} version={version} < {PREFS_VERSION}; "
            f"sem migracao disponivel, usando defaults."
        )
        return False

    applied = False
    for field, (_getter, setter, validator) in _FIELDS.items():
        if field not in data:
            continue
        validated = validator(data[field])
        if validated is None:
            continue
        setter(validated)
        applied = True

    return applied


# --- Save ----------------------------------------------------------------

def save_if_dirty(force: bool = False) -> bool:
    """Escreve prefs no disco se algo mudou.

    force=True ignora _save_failure_suppressed (retry no shutdown),
    mas nunca _write_allowed: versao futura permanece protegida.

    Escrita atomica: temp no mesmo diretorio, fsync, os.replace.
    fsync apenas no arquivo (nao no diretorio pai): durabilidade do
    rename nao e requisito aqui.
    """
    global _dirty, _save_failure_suppressed

    if not _dirty:
        return False
    if not _write_allowed:
        return False
    if _save_failure_suppressed and not force:
        return False

    path = prefs_path()
    tmp_path = path.with_name(path.name + ".tmp")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(_current_prefs(), f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except OSError as e:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        _save_failure_suppressed = True
        print(f"[prefs] falha ao gravar {path} ({e!r}); prefs nao persistidas.")
        return False

    _dirty = False
    _save_failure_suppressed = False
    return True


# --- Test helper ---------------------------------------------------------

def reset_for_tests() -> None:
    """Restaura o estado interno. Path continua via monkeypatch."""
    global _dirty, _write_allowed, _save_failure_suppressed
    _dirty = False
    _write_allowed = True
    _save_failure_suppressed = False