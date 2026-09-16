# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Interface de linha de comando do Primordial Soup.

Dois modos:

  Grafico (default): sem flags, ou so flags que o loop grafico
  entende. Abre janela pygame e roda a simulacao interativa normal.
  E o que `python -m primordial_soup` sempre fez, sem mudanca.

  Headless: qualquer uma de -l/--load, -d/--duration, -s/--save,
  --new, --seed. Roda N ticks sem janela, salva e sai. Para
  experimentos em lote, smoke tests de CI e sweeps reproduziveis.

Notas de design:

  - pygame e importado SO no ramo grafico de main().
    `import primordial_soup.cli` nunca deve puxar pygame, para um
    chamador headless importar o CLI sem display.

  - O formato de savegame e identico nos dois modos: run_headless
    delega a persistence.save() exatamente como o loop grafico. Um
    save gerado headless carrega no jogo grafico e vice-versa
    (sujeito a restricao de resolucao documentada em
    persistence.load: a mascara de zonas esta amarrada ao tamanho
    derivado do mundo).

  - O seed fixa AS DUAS fontes aleatorias da simulacao: `random` da
    stdlib (usada por world.generate_zones) e o RNG global legado do
    NumPy (usado por genetics e evolution). Seed em so uma tornaria
    um sweep com --seed nao-reproduzivel.

  - As mensagens do CLI sao hardcoded em ingles. O CLI e interface
    de baixo nivel para scripts e CI, nao superficie de usuario; seu
    idioma nao segue state.language. Os logs da propria simulacao
    (log.save_ok, log.tick_summary, ...) seguem i18n normalmente.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from . import config as cfg


def _non_negative_int(text: str) -> int:
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError(
            f"duration must be >= 0 (got {value})"
        )
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="primordial_soup",
        description=(
            "Primordial Soup — artificial life simulation. "
            "With no arguments, opens the graphical window. "
            "With any headless flag (-l/-d/-s/--new/--seed), runs "
            "without a window, saves, and exits."
        ),
    )
    # --load e --new sao mutuamente exclusivos: a fonte do mundo e
    # uma so. Sem required=True, porque o modo grafico (sem flags)
    # continua valido e nem --new nem --load e obrigatorio
    # individualmente. O grupo so proibe a COEXISTENCIA.
    world_source = parser.add_mutually_exclusive_group()
    world_source.add_argument(
        "-l", "--load",
        metavar="SLOT",
        help=(
            "load save slot SLOT before running. If the load fails, "
            "the process aborts WITHOUT saving (a failed load must "
            "never silently overwrite the save it was asked to "
            "continue from). Cannot be combined with --new."
        ),
    )
    parser.add_argument(
        "-d", "--duration",
        type=_non_negative_int,
        metavar="N",
        help=(
            "run N ticks headless and exit. N=0 is valid: load, "
            "save, exit (useful to canonicalise a save or export "
            "its metrics CSV). Requires -l or --new."
        ),
    )
    parser.add_argument(
        "-s", "--save",
        metavar="SLOT",
        help=(
            "save slot at the end. Default: the slot given to -l, "
            f"or \'{cfg.DEFAULT_SAVE_SLOT}\' if -l was not given."
        ),
    )
    world_source.add_argument(
        "--new",
        action="store_true",
        help="start a fresh run, ignoring -l. Cannot be combined with -l/--load.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        metavar="N",
        help=(
            "seed the RNG for reproducibility. With --new, seeds "
            "before world construction. With --load, the checkpoint "
            "is restored first (including its RNG state), then the "
            "seed overwrites it deliberately, producing a divergent "
            "stochastic future from the same starting point. A "
            "failed load applies no seed."
        ),
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help=(
            "suppress periodic per-tick logs (the final save "
            "summary is still printed)."
        ),
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def is_headless(args: argparse.Namespace) -> bool:
    """True se alguma flag headless-only foi passada.

    Uma flag basta: -d sozinho ja significa "rodar N ticks sem
    janela", e nao ha caso de uso legitimo para -d no modo grafico
    (gravar um GIF de N ticks exige renderizar cada frame, o que o
    loop grafico ja faz).
    """
    return any([
        args.load is not None,
        args.duration is not None,
        args.save is not None,
        args.new,
        args.seed is not None,
    ])


def _resolve_save_slot(args: argparse.Namespace) -> str:
    """Slot para salvar, conforme a precedencia documentada."""
    if args.save is not None:
        return args.save
    if args.load is not None:
        return args.load
    return cfg.DEFAULT_SAVE_SLOT


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not is_headless(args):
        # Ramo grafico. pygame e importado AQUI, nao no nivel do
        # modulo, para `import primordial_soup.cli` ser seguro em
        # ambiente headless.
        from .simulation import run

        run()
        return 0

    # Ramo headless. -d exige -l ou --new: "rodar N ticks" e sem
    # sentido sem estado inicial explicito, e um default silencioso
    # (bootstrap de mundo novo) surpreenderia quem esqueceu a flag.
    # Falha ruidosamente em vez disso.
    if args.duration is not None and args.load is None and not args.new:
        print(
            "error: -d/--duration requires -l/--load or --new. "
            "Use `--new -d N` for a fresh run, or `-l SLOT -d N` "
            "to continue from an existing save.",
            file=sys.stderr,
        )
        return 2

    from .simulation import run_headless

    return run_headless(
        load_slot=args.load,
        ticks=args.duration,
        save_slot=_resolve_save_slot(args),
        fresh=args.new,
        quiet=args.quiet,
        seed=args.seed,
    )