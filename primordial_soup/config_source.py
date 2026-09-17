# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Resolucao canonica da fonte declarativa de configuracao."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Final, Mapping

from .config_errors import ConfigError


PACKAGED_CONFIG_PATH: Final = Path(__file__).resolve().with_name(".env")
CONFIG_OVERRIDE_ENV: Final = "PRIMORDIAL_SOUP_CONFIG"


@dataclass(frozen=True, slots=True)
class ConfigPaths:
    """Paths efetivos de leitura/escrita selecionados para este processo."""

    read_path: Path
    write_path: Path
    using_packaged_default: bool


def _user_config_path(
    *,
    environ: Mapping[str, str],
    home: Path,
    platform: str,
) -> Path:
    """Deriva o destino gravavel sem tocar no filesystem."""
    if platform == "win32":
        appdata = environ.get("APPDATA", "")
        base = Path(appdata).expanduser() if appdata.strip() else home / "AppData" / "Roaming"
        return base / "PrimordialSoup" / ".env"

    if platform == "darwin":
        return home / "Library" / "Application Support" / "PrimordialSoup" / ".env"

    xdg_config_home = environ.get("XDG_CONFIG_HOME", "")
    base = (
        Path(xdg_config_home).expanduser()
        if xdg_config_home.strip()
        else home / ".config"
    )
    return base / "primordial-soup" / ".env"


def resolve_config_paths(
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    platform: str | None = None,
) -> ConfigPaths:
    """Resolve override, configuracao do usuario e baseline empacotado."""
    effective_environ = os.environ if environ is None else environ
    effective_home = Path.home() if home is None else Path(home)
    effective_platform = sys.platform if platform is None else platform

    if CONFIG_OVERRIDE_ENV in effective_environ:
        raw_override = effective_environ[CONFIG_OVERRIDE_ENV]
        if not raw_override.strip():
            raise ConfigError(
                f"{CONFIG_OVERRIDE_ENV}: path de configuracao nao pode ser vazio."
            )
        override_path = Path(raw_override.strip()).expanduser()
        if not override_path.is_absolute():
            override_path = Path.cwd() / override_path
        override_path = override_path.resolve()
        return ConfigPaths(
            read_path=override_path,
            write_path=override_path,
            using_packaged_default=False,
        )

    user_path = _user_config_path(
        environ=effective_environ,
        home=effective_home,
        platform=effective_platform,
    )
    if user_path.exists():
        return ConfigPaths(
            read_path=user_path,
            write_path=user_path,
            using_packaged_default=False,
        )

    return ConfigPaths(
        read_path=PACKAGED_CONFIG_PATH,
        write_path=user_path,
        using_packaged_default=True,
    )


CONFIG_PATHS: Final = resolve_config_paths()
CONFIG_PATH: Final = CONFIG_PATHS.read_path
CONFIG_WRITE_PATH: Final = CONFIG_PATHS.write_path
