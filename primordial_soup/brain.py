# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
import numpy as np

from . import config as cfg


# Ativacoes — trocaveis via cfg.HIDDEN_ACTIVATION / HIDDEN_ACTIVATION_2


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _tanh(x: np.ndarray) -> np.ndarray:
    return np.tanh(x)


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


_ACTIVATIONS = {
    "sigmoid": _sigmoid,
    "tanh": _tanh,
    "relu": _relu,
}


def _activation(name: str):
    try:
        return _ACTIVATIONS[name]
    except KeyError:
        raise ValueError(
            f"Unknown activation: {name!r}. Options: {sorted(_ACTIVATIONS)}"
        )


def _hidden_activation():
    return _activation(cfg.HIDDEN_ACTIVATION)


def _hidden_activation_2():
    return _activation(cfg.HIDDEN_ACTIVATION_2)


def _output_activation():
    """Retorna a ativacao aplicada a camada de saida.

    "linear" e a identidade (default, comportamento identico ao
    codigo anterior sem ativacao). Qualquer outro nome precisa estar
    em _ACTIVATIONS.
    """
    if cfg.OUTPUT_ACTIVATION == "linear":
        return lambda x: x
    return _activation(cfg.OUTPUT_ACTIVATION)


def split_weights(weights: np.ndarray):
    """Separa um genoma plano em (W1, W2, W3, b1, b2, R).

    Layout do genoma:
        [ W1 (E×O1) | W2 (O1×O2) | W3 (O2×M) | b1 (O1) | b2 (O2) | R (O1×O1) ]

    Aceita genoma unico [G] ou batch [N, G]. Sempre retorna em batch;
    squeezed se a entrada for 1D.
    """
    weights = np.asarray(weights)
    single = weights.ndim == 1
    if single:
        weights = weights[None, :]

    n = weights.shape[0]
    e = cfg.NETWORK_INPUTS
    o1 = cfg.HIDDEN_NEURONS
    o2 = cfg.HIDDEN_NEURONS_2
    m = cfg.POSSIBLE_MOVES

    # Offsets cumulativos
    w1_start = 0
    w1_end = w1_start + cfg.INPUT_HIDDEN_WEIGHTS
    w2_start = w1_end
    w2_end = w2_start + cfg.HIDDEN1_HIDDEN2_WEIGHTS
    w3_start = w2_end
    w3_end = w3_start + cfg.HIDDEN2_OUTPUT_WEIGHTS
    b1_start = w3_end
    b1_end = b1_start + cfg.HIDDEN_BIASES
    b2_start = b1_end
    b2_end = b2_start + cfg.HIDDEN_BIASES_2
    r_start = b2_end
    r_end = r_start + cfg.RECURRENCE_WEIGHTS

    w1 = weights[:, w1_start:w1_end].reshape(n, o1, e)
    w2 = weights[:, w2_start:w2_end].reshape(n, o2, o1)
    w3 = weights[:, w3_start:w3_end].reshape(n, m, o2)
    b1 = weights[:, b1_start:b1_end]
    b2 = weights[:, b2_start:b2_end]
    r = weights[:, r_start:r_end].reshape(n, o1, o1)

    if single:
        return w1[0], w2[0], w3[0], b1[0], b2[0], r[0]
    return w1, w2, w3, b1, b2, r


def evaluate(
    inputs: np.ndarray,
    weights: np.ndarray,
    previous_hidden_state: np.ndarray | None = None,
) -> np.ndarray:
    """Avalia um unico bicho SEM hidden state previo (recorrencia
    zerada).

    Compatibilidade com codigo antigo. Retorna apenas os outputs.
    """
    outputs, _ = evaluate_batch(
        inputs[None, :], weights[None, :], previous_hidden_state=previous_hidden_state
    )
    return outputs[0]


def evaluate_batch(
    inputs: np.ndarray,
    weights: np.ndarray,
    previous_hidden_state: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Avalia N bichos com duas camadas ocultas + recorrencia na 1.

    inputs:                 [N, NETWORK_INPUTS]
    weights:                [N, GENOME_SIZE]
    previous_hidden_state:  [N, HIDDEN_NEURONS] ou None (tratado como 0)

    Retorna:
        outputs: [N, POSSIBLE_MOVES]
        hidden1: [N, HIDDEN_NEURONS]  (hidden state do tick atual,
                                       persistido para o proximo)
    """
    w1, w2, w3, b1, b2, r = split_weights(weights)

    # Contrato de dtype. O hot path inteiro e float32: metade da
    # memoria, metade da banda, e precisao mais que suficiente para
    # HP (10.000), posicao (600) e pesos (-2..+2). Se qualquer um
    # destes for float64, o @ abaixo roda em dupla precisao silencioso
    # e o throughput CAI PELA METADE sem erro nem aviso.
    #
    # Python remove asserts sob -O, entao em producao eles nao custam
    # nada. Em debug sao ~4 leituras de atributo por chamada.
    assert w1.dtype == np.float32, f"w1 must be float32, got {w1.dtype}"
    assert w2.dtype == np.float32, f"w2 must be float32, got {w2.dtype}"
    assert w3.dtype == np.float32, f"w3 must be float32, got {w3.dtype}"
    assert inputs.dtype == np.float32, (
        f"inputs must be float32, got {inputs.dtype}"
    )

    # Camada 1: input -> hidden1 (com recorrencia).
    #
    # @ em vez de np.einsum: matematicamente identicos para esta
    # forma, mas @ usa BLAS (gemm/gemv) enquanto einsum cai num loop
    # em C para o caso batched matvec. Nos builds testados, @ e 15-25%
    # mais rapido, e a fase neural e 70-80% de um tick.
    #
    # inputs[..., None] promove [N, e] para [N, e, 1]; o matmul com
    # w1 [N, o1, e] da [N, o1, 1]; [..., 0] volta para [N, o1]. Sem
    # transpose: N e o eixo lider de ambos os operandos.
    pre1 = (w1 @ inputs[..., None])[..., 0] + b1  # [N, o1]
    if previous_hidden_state is not None:
        previous = np.asarray(previous_hidden_state, dtype=np.float32)
        pre1 = pre1 + (r @ previous[..., None])[..., 0]
    hidden1 = _hidden_activation()(pre1)

    # Camada 2: hidden1 -> hidden2 (sem recorrencia). Mesma troca
    # por @: einsum("npo,no->np", w2, hidden1) ==
    # (w2 @ hidden1[..., None])[..., 0].
    pre2 = (w2 @ hidden1[..., None])[..., 0] + b2  # [N, o2]
    hidden2 = _hidden_activation_2()(pre2)

    # Saida: hidden2 -> output, seguida da ativacao configurada.
    # OUTPUT_ACTIVATION == "linear" faz isto ser a identidade (igual
    # ao codigo anterior). Mesma troca por @:
    # einsum("nmp,np->nm", w3, hidden2) ==
    # (w3 @ hidden2[..., None])[..., 0].
    outputs = _output_activation()((w3 @ hidden2[..., None])[..., 0])

    return outputs, hidden1
