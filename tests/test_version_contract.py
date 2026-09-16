# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Contrato de Single Source of Truth da versao da aplicacao.

Protege a arquitetura estabelecida no Patch 5:

    primordial_soup/_version.py
            |
            | __version__
            |
            +--> primordial_soup.__version__   (reexport)
            |
            +--> config.WORLD_VERSION          (alias)
            |
            +--> CLI --version / -v
            |
            +--> setuptools dynamic attr

Todos os testes derivam o valor canonico de
primordial_soup._version.__version__; nenhum hardcoda "0.6.0".
Isso garante que uma release futura (ex: 0.6.0 -> 0.6.1) altera
apenas _version.py, sem tocar em nenhum teste.

Docstrings e comentarios sao ASCII puro para manter consistencia
com o estilo dominante da suite.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

import primordial_soup
from primordial_soup import config as cfg
from primordial_soup._version import __version__ as canonical_version
from primordial_soup.cli import build_parser


_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"
_CANONICAL_MODULE = (
    _REPO_ROOT / "primordial_soup" / "_version.py"
)


# ---------------------------------------------------------------------------
# Reexport publico
# ---------------------------------------------------------------------------


def test_public_version_reexports_canonical_version() -> None:
    """primordial_soup.__version__ reexporta _version.__version__."""
    assert primordial_soup.__version__ == canonical_version


# ---------------------------------------------------------------------------
# Alias semantico em config
# ---------------------------------------------------------------------------


def test_world_version_aliases_canonical_version() -> None:
    """config.WORLD_VERSION e alias de _version.__version__."""
    assert cfg.WORLD_VERSION == canonical_version


# ---------------------------------------------------------------------------
# pyproject: dynamic version via setuptools attr
# ---------------------------------------------------------------------------


def test_pyproject_declares_dynamic_version_from_canonical_module() -> None:
    """pyproject remove version estatica e aponta setuptools para o
    modulo canonico."""
    with _PYPROJECT.open("rb") as file:
        data = tomllib.load(file)

    project = data["project"]

    assert "version" not in project, (
        "pyproject nao pode declarar version estatica em [project]"
    )
    assert project["dynamic"] == ["version"], (
        "pyproject deve declarar dynamic = [\"version\"]"
    )

    dynamic_version = (
        data["tool"]["setuptools"]["dynamic"]["version"]
    )
    assert dynamic_version == {
        "attr": "primordial_soup._version.__version__"
    }, (
        "setuptools deve resolver a versao via attr canonico"
    )


# ---------------------------------------------------------------------------
# CLI --version / -v
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag", ["--version", "-v"])
def test_cli_version_uses_canonical_version(
    flag: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI emite exatamente 'primordial_soup <canonical>\n'."""
    parser = build_parser()

    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args([flag])

    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert captured.out == (
        f"primordial_soup {canonical_version}\n"
    )
    assert captured.err == ""


# ---------------------------------------------------------------------------
# Ausencia de duplicatas executaveis do literal
# ---------------------------------------------------------------------------


def test_application_version_literal_has_no_duplicate_in_runtime_sources() -> None:
    """Nenhum literal "X.Y.Z" da versao existe fora de _version.py
    em sources executaveis ou em pyproject.toml.

    Escopo: primordial_soup/**/*.py (exceto _version.py) e
    pyproject.toml. Exclui README.md, docs/* e tests/*: documentacao
    sera reconciliada no Patch 6; testes sao justamente os guardioes
    deste contrato e nao contem o literal.
    """
    quoted_forms = (
        f'"{canonical_version}"',
        f"'{canonical_version}'",
    )

    duplicates: list[str] = []

    for path in (
        _REPO_ROOT / "primordial_soup"
    ).rglob("*.py"):
        if path == _CANONICAL_MODULE:
            continue
        text = path.read_text(encoding="utf-8")
        if any(form in text for form in quoted_forms):
            duplicates.append(
                str(path.relative_to(_REPO_ROOT))
            )

    pyproject_text = _PYPROJECT.read_text(encoding="utf-8")
    if any(
        form in pyproject_text
        for form in quoted_forms
    ):
        duplicates.append("pyproject.toml")

    assert duplicates == [], (
        "application version literal duplicated outside "
        f"_version.py: {duplicates}"
    )


# ---------------------------------------------------------------------------
# _version.py nao depende de metadata instalada
# ---------------------------------------------------------------------------


def test_canonical_version_module_has_no_installed_metadata_dependency() -> None:
    """_version.py e folha: sem importlib.metadata, sem fallback,
    sem leitura de ambiente ou Git.

    Protege a decisao arquitetural do Patch 5: a direcao da verdade
    e source -> package metadata; nao o contrario.
    """
    text = _CANONICAL_MODULE.read_text(encoding="utf-8")

    forbidden = (
        "importlib.metadata",
        "PackageNotFoundError",
        "metadata.version",
    )
    for fragment in forbidden:
        assert fragment not in text, (
            f"_version.py nao pode referenciar {fragment!r}"
        )
