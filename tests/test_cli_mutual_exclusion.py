"""Testes do contrato de exclusao mutua entre --new e --load.

Cobrem a propriedade definida no Patch 4: a fonte do mundo e uma so.
Passar as duas flags deve falhar no argparse, antes de qualquer
alteracao de estado ou escrita em disco.

Testes chamam build_parser().parse_args([...]) diretamente, sem
subprocess. Isso e rapido, deterministico, nao depende de instalacao
e exercita exatamente o parser. O que subprocess testaria e o
empacotamento (`python -m primordial_soup`), que e ortogonal a este
patch.

O contrato verificado e estritamente estrutural:

    combinacao invalida
    -> parse falha
    -> SystemExit(2)

Nao validamos texto de mensagem: mudancas de formatacao do argparse,
versao do Python ou ordem de argumentos tornariam o teste fragil sem
ganho diagnostico proporcional.

Todos os docstrings e comentarios deste arquivo sao intencionalmente
ASCII puro, seguindo o estilo de nomenclatura interna do projeto.
"""

import pytest

from primordial_soup.cli import build_parser


_REJECT_CASES = [
    pytest.param(
        ["--new", "-l", "world_a", "-d", "1000"],
        id="new_entao_load",
    ),
    pytest.param(
        ["-l", "world_a", "--new", "-d", "1000"],
        id="load_entao_new",
    ),
    pytest.param(
        ["--new", "-l", "world_a"],
        id="new_e_load_sem_duration",
    ),
    pytest.param(
        ["-l", "world_a", "--new"],
        id="load_e_new_sem_duration",
    ),
    pytest.param(
        ["--new", "--load", "world_a", "-d", "1000", "-s", "world_b"],
        id="new_load_com_save",
    ),
    pytest.param(
        ["--new", "-l", "world_a", "--seed", "42"],
        id="new_load_com_seed",
    ),
]


@pytest.mark.parametrize("argv", _REJECT_CASES)
def test_new_and_load_are_mutually_exclusive(argv):
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(argv)
    assert exc_info.value.code == 2, (
        "combinacao --new + --load deveria causar SystemExit(2), "
        f"recebeu codigo {exc_info.value.code!r}."
    )


_ACCEPT_CASES = [
    pytest.param([], id="sem_flags_modo_grafico"),
    pytest.param(["--new"], id="new_sozinho"),
    pytest.param(["-l", "world_a"], id="load_sozinho"),
    pytest.param(["--new", "-d", "1000"], id="new_com_duration"),
    pytest.param(
        ["--new", "-d", "1000", "-s", "world_a"],
        id="new_com_duration_e_save",
    ),
    pytest.param(
        ["-l", "world_a", "-d", "1000"],
        id="load_com_duration",
    ),
    pytest.param(
        ["-l", "world_a", "-d", "1000", "-s", "world_b"],
        id="load_com_duration_e_save",
    ),
    pytest.param(
        ["--new", "-d", "1000", "--seed", "42"],
        id="new_com_duration_e_seed",
    ),
    pytest.param(
        ["-l", "world_a", "-d", "1000", "--seed", "42"],
        id="load_com_duration_e_seed",
    ),
    pytest.param(
        ["--new", "-d", "1000", "-s", "world_a", "--seed", "42", "-q"],
        id="new_completo",
    ),
    pytest.param(
        ["-l", "world_a", "-d", "1000", "-s", "world_b", "--seed", "42", "-q"],
        id="load_completo",
    ),
]


@pytest.mark.parametrize("argv", _ACCEPT_CASES)
def test_valid_combinations_parse(argv):
    parser = build_parser()
    args = parser.parse_args(argv)

    # Confirma que --new e --load continuam sendo atributos do
    # namespace. O grupo so restringe a COEXISTENCIA, nao remove os
    # campos.
    assert hasattr(args, "new")
    assert hasattr(args, "load")

    # E confirma que nao ha combinacao invalida bem-sucedida por
    # engano.
    assert not (args.new and args.load is not None), (
        f"combinacao --new + --load passou pelo parser: {argv!r}."
    )