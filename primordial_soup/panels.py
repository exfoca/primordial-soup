# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Abstracao de painel, item e resultado de dispatch.

Este modulo define a GRAMATICA da interface, nao a implementacao de
cada painel. Os paineis concretos (Inspection, Configuration, Metrics,
Session, Tools) sao registrados em PANELS e construidos a partir dos
tipos definidos aqui.

Contrato de handler:

    handler(panel: Panel, item: Item) -> DispatchResult

O handler NUNCA chama rendering.draw() diretamente. Se a acao muda o
que deve ser exibido, retorna redraw=True. O loop grafico decide
quando desenhar.

O handler NUNCA le ui_state diretamente. O cursor e o painel ativo
sao responsabilidade do dispatcher.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable


class Flow(Enum):
    """Resultado de fluxo de um evento processado."""
    CONTINUE = auto()
    EXIT = auto()


class ItemKind(Enum):
    """Tipo de item interativo.

    VALUE      valor continuo; <- -> ajustam
    ENUM       valor discreto de uma lista; <- -> ciclam
    TOGGLE     booleano; Enter alterna
    ACTION     executa algo; Enter dispara
    READ_ONLY  exibido, nao recebe foco
    SECTION    separador visual, nao recebe foco
    """
    VALUE = auto()
    ENUM = auto()
    TOGGLE = auto()
    ACTION = auto()
    READ_ONLY = auto()
    SECTION = auto()


# Itens que participam da navegacao por Tab.
_INTERACTIVE_KINDS = frozenset({
    ItemKind.VALUE,
    ItemKind.ENUM,
    ItemKind.TOGGLE,
    ItemKind.ACTION,
})


@dataclass(frozen=True, slots=True)
class DispatchResult:
    """Resultado de processar um evento.

    flow:    CONTINUE (a aplicacao segue) ou EXIT (encerrar)
    redraw:  se o loop grafico deve redesenhar antes do proximo evento
    """
    flow: Flow = Flow.CONTINUE
    redraw: bool = False

    @classmethod
    def continue_(cls, redraw: bool = False) -> "DispatchResult":
        return cls(Flow.CONTINUE, redraw)

    @classmethod
    def exit_(cls) -> "DispatchResult":
        return cls(Flow.EXIT, False)


# Handler: recebe painel, item e direction.
#
# direction:
#    0  -> Enter (ativacao)
#   -1  -> seta esquerda
#   +1  -> seta direita
#
# Handlers de ACTION e TOGGLE ignoram direction. Handlers de VALUE e
# ENUM usam. Handlers de READ_ONLY e SECTION nunca sao chamados.
Handler = Callable[["Panel", "Item", int], DispatchResult]


@dataclass(slots=True)
class Item:
    """Item de um painel.

    id:          chave estavel, usada como valor de panel_cursors
    kind:        ItemKind
    label_key:   chave i18n do rotulo
    value_fn:    retorna a string de valor exibida a direita, ou None
                 para itens sem valor (ACTION, SECTION)
    handler:     chamado em Enter ou em <- -> dependendo do kind
                 - VALUE:   handler(panel, item, direction) ja embutido
                            pelo dispatcher; aqui o handler e o ajuste
                 - ENUM:    idem
                 - TOGGLE:  handler chamado em Enter
                 - ACTION:  handler chamado em Enter
                 - outros:  handler ignorado
    """
    id: str
    kind: ItemKind
    label_key: str
    value_fn: Callable[[], str] | None = None
    handler: Handler | None = None

    @property
    def is_interactive(self) -> bool:
        return self.kind in _INTERACTIVE_KINDS


@dataclass(slots=True)
class Panel:
    """Painel registrado.

    id:              chave canonica (PANEL_* de ui_state)
    activation_key:  pygame.K_* que foca o painel
    title_key:       chave i18n do titulo
    items:           lista de Item, na ordem de Tab
    footer_key:      chave i18n do rodape contextual (opcional)
    """
    id: str
    activation_key: int
    title_key: str
    items: list[Item] = field(default_factory=list)
    footer_key: str | None = None

    def interactive_indices(self) -> list[int]:
        """Indices dos itens que participam de Tab, na ordem."""
        return [i for i, item in enumerate(self.items) if item.is_interactive]

    def default_cursor_id(self) -> str | None:
        """Primeiro item interativo, ou None se o painel nao tem nenhum."""
        for item in self.items:
            if item.is_interactive:
                return item.id
        return None

    def find_item(self, item_id: str | None) -> Item | None:
        """Item pelo id, ou None."""
        if item_id is None:
            return None
        for item in self.items:
            if item.id == item_id:
                return item
        return None


# Registry global, populado no final deste arquivo pelos paineis
# concretos. O dispatcher consulta PANELS para resolver ativacao.
PANELS: dict[str, Panel] = {}


def register(panel: Panel) -> Panel:
    """Registra um painel. Chamado no final deste arquivo."""
    PANELS[panel.id] = panel
    return panel
