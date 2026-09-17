# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Contrato estrutural neutro do modelo neural e genetico."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


VISION_CHANNELS: Final = 3
INTERNAL_STATE_INPUTS: Final = 4
POSSIBLE_MOVES: Final = 9
STAY_STILL_INDEX: Final = 4

MIN_GENE_VALUE: Final = -2.0
MAX_GENE_VALUE: Final = 2.0
GENE_VALUE_SPAN: Final = MAX_GENE_VALUE - MIN_GENE_VALUE


@dataclass(frozen=True, slots=True)
class NeuralLayout:
    """Dimensoes derivadas da arquitetura neural vigente."""

    vision_side: int
    vision_inputs: int
    network_inputs: int
    input_hidden_weights: int
    hidden1_hidden2_weights: int
    hidden2_output_weights: int
    hidden_biases: int
    hidden_biases_2: int
    recurrence_weights: int
    genome_size: int


def derive_neural_layout(
    *,
    vision_radius: int,
    hidden_neurons: int,
    hidden_neurons_2: int,
) -> NeuralLayout:
    """Deriva as dimensoes neurais sem validar configuracao declarativa."""
    vision_side = 2 * vision_radius + 1
    vision_inputs = vision_side**2 * VISION_CHANNELS
    network_inputs = vision_inputs + INTERNAL_STATE_INPUTS

    input_hidden_weights = network_inputs * hidden_neurons
    hidden1_hidden2_weights = hidden_neurons * hidden_neurons_2
    hidden2_output_weights = hidden_neurons_2 * POSSIBLE_MOVES
    hidden_biases = hidden_neurons
    hidden_biases_2 = hidden_neurons_2
    recurrence_weights = hidden_neurons * hidden_neurons
    genome_size = (
        input_hidden_weights
        + hidden1_hidden2_weights
        + hidden2_output_weights
        + hidden_biases
        + hidden_biases_2
        + recurrence_weights
    )

    return NeuralLayout(
        vision_side=vision_side,
        vision_inputs=vision_inputs,
        network_inputs=network_inputs,
        input_hidden_weights=input_hidden_weights,
        hidden1_hidden2_weights=hidden1_hidden2_weights,
        hidden2_output_weights=hidden2_output_weights,
        hidden_biases=hidden_biases,
        hidden_biases_2=hidden_biases_2,
        recurrence_weights=recurrence_weights,
        genome_size=genome_size,
    )
