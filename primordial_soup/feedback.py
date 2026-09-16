# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Fronteira semantica de feedback da aplicacao.

Este modulo representa acontecimentos cosmeticos da aplicacao sem
conhecer sua representacao concreta (som, visual, log). Ele nao
importa pygame, nao conhece audio.py, nao conhece nomes de arquivos
WAV e nao depende de state, ui_state nem RuntimeRules.

Apenas stdlib.

O contrato e deliberadamente minimo: um enum de eventos canonicos,
um unico sink opcional e tres funcoes (register_sink, clear_sink,
emit). Nao e um event bus, nao e extensivel, nao e fila, nao possui
multiplos listeners. Se o desenho precisar mudar, o cambio deve ser
explicito, nao "descoberto" por generalizacao silenciosa.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Callable


class FeedbackEvent(StrEnum):
    """Eventos canonicos de feedback.

    O nome BIRTH_ACTIVITY e deliberado: o contrato futuro sera "um ou
    mais nascimentos observados em um batch grafico => um evento",
    nao necessariamente um nascimento individual.
    """
    MENU_MOVE = "menu_move"
    MENU_CHANGE = "menu_change"
    WORLD_GENERATED = "world_generated"
    SAVE_OK = "save_ok"
    LOAD_OK = "load_ok"
    BIRTH_ACTIVITY = "birth_activity"


FeedbackSink = Callable[[FeedbackEvent], None]


_sink: FeedbackSink | None = None


def register_sink(sink: FeedbackSink) -> None:
    """Substitui o sink atual pelo recebido.

    Composicao unica, sem lista de listeners. Registrar o mesmo sink
    novamente e permitido e nao cria duplicacao.
    """
    global _sink
    _sink = sink


def clear_sink() -> None:
    """Remove o sink atual. Idempotente."""
    global _sink
    _sink = None


def emit(event: FeedbackEvent) -> None:
    """Emite um evento para o sink, se houver.

    Sem sink: retorna imediatamente.
    Com sink: chama sink(event).

    Se o sink levantar qualquer Exception, o sink e limpo
    imediatamente, um unico aviso e impresso e a excecao NAO
    propaga. Isso impede que um sink defeituoso derrube a aplicacao
    ou gere uma tempestade de logs: apos a primeira falha o proprio
    sink deixa de existir.
    """
    global _sink
    sink = _sink
    if sink is None:
        return
    try:
        sink(event)
    except Exception as exc:
        _sink = None
        print(f"[feedback] sink disabled after failure: {exc!r}")
