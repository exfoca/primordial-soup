# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
import csv
import math
import numbers
import os
import pickle
import random
import numpy as np

from . import config as cfg
from . import layout
from . import state
from . import i18n
from .state import agents
from .world import (
    AGENT_COLUMNS,
    INDEX_X,
    INDEX_Y,
    seed_lineages,
)


# Resolucao de path por slot


def save_path(slot: str | None = None) -> str:
    """Path do .pkl para o slot dado, ou o slot ativo se None."""
    slot = slot or state.active_save_slot
    return cfg.SAVE_SLOT_TEMPLATE.format(slot=slot)


def metrics_path(slot: str | None = None) -> str:
    """Path do _metricas.csv para o slot dado, ou o slot ativo."""
    slot = slot or state.active_save_slot
    return cfg.METRICS_SLOT_TEMPLATE.format(slot=slot)


# Compatibilidade de chaves
#
# O formato canonico do savegame usa chaves em portugues. `_read_key`
# aceita a grafia em ingles como fallback (para arquivos legados ou
# editados a mao), mas a chave canonica e sempre a portuguesa e DEVE
# ser a escrita por `save()`.
#
# Nada neste modulo e traduzido em runtime. As chaves do savegame, o
# cabecalho do CSV e os nomes de metrica sao identificadores canonicos
# e DEVEM permanecer estaveis. So as mensagens de log impressas
# durante save/load sao traduzidas (ver i18n.t("log.*")).


# Sentinelas privadas do parser.
#
# _INVALID: valor presente mas nao conversivel para o tipo alvo.
#           Rejeicao imediata de load() com log e return False.
# _MISSING: chave ausente no dict. Permite ao chamador decidir o
#           default apropriado.
#
# Ambos sao objetos unicos e privados, detalhe interno do parser.
_INVALID = object()
_MISSING = object()


# Limite superior do int64. Usado por _coerce_int_array e pelo parsing
# de proximo_id para garantir que os IDs cabem no dtype armazenado em
# state.agents[i]["ids"] (int64).
_INT64_MAX = 2**63 - 1


def _coerce_int(value):
    """Converte `value` para int sem perda, ou retorna _INVALID.

    Contrato:
        aceita   int, np.integer, float integral finito, str de int
        rejeita  bool, None, NaN, inf, float nao integral,
                 str de float ("3.0", "3.7"), str nao numerica,
                 qualquer outro tipo

    A checagem de bool vem ANTES de numbers.Integral porque
    isinstance(True, numbers.Integral) e True em Python (bool e
    subclasse de int), mas True/False nao sao inteiros validos no
    dominio do savegame: e erro de payload.

    Conversao lossless: 3.7 e rejeitado, nao truncado para 3. Nao
    impoe limite int64 — isso e do chamador quando o campo participa
    do dominio de IDs.
    """
    if isinstance(value, bool):
        return _INVALID

    if isinstance(value, numbers.Integral):
        return int(value)

    if isinstance(value, numbers.Real):
        numeric = float(value)
        if not math.isfinite(numeric) or not numeric.is_integer():
            return _INVALID
        return int(value)

    if isinstance(value, str):
        try:
            return int(value)
        except (TypeError, ValueError, OverflowError):
            return _INVALID

    return _INVALID


def _parse_int_field(
    record: dict,
    pt_key: str,
    en_key: str,
    *,
    default=_MISSING,
    minimum: int | None = None,
    maximum: int | None = None,
):
    """Le, coage e valida um campo inteiro escalar do payload.

    Retorna o int validado, ou `default` (que pode ser `_MISSING`), ou
    `_INVALID`. Nunca levanta. O chamador so precisa comparar com
    `_INVALID`.

    Contrato:
      - ausente (nenhum dos dois aliases): retorna `default`. Com
        `default=_MISSING` (o padrao), um campo obrigatorio sem
        chave cai em `_INVALID`.
      - presente mas nao coerccivel para int: `_INVALID`. Usa
        `_coerce_int`, que ja distingue `None`, `bool`, NaN/inf,
        floats nao-integrais, strings nao-numericas.
      - coerccivel mas fora de [minimum, maximum] (quando
        fornecidos): `_INVALID`. Sem clamp.

    Aliases PT/EN preservados via `_read_key_strict`: uma chave
    presente com valor `None` e "presente", nao "ausente", e cai em
    `_coerce_int(None) == _INVALID`. Distincao que o loader explora
    em outros campos e que este helper mantem.
    """
    raw = _read_key(record, pt_key, en_key)
    if raw is _MISSING:
        # Campo obrigatorio: ausencia e indistinguivel de invalidez
        # no contrato do helper. Com default=_MISSING (o padrao),
        # ausencia cai em _INVALID. Com default concreto, ausencia
        # cai no default (caminho de campo opcional, hoje nao usado
        # no loader v11 estrito).
        return _INVALID if default is _MISSING else default
    value = _coerce_int(raw)
    if value is _INVALID:
        return _INVALID
    if minimum is not None and value < minimum:
        return _INVALID
    if maximum is not None and value > maximum:
        return _INVALID
    return value


def _coerce_int_array(value, ndim: int | None = None):
    """Converte `value` para ndarray int64 com IDs validos, ou None.

    Contrato de ID:
        finite          (sem NaN, sem inf)
        integral        (3.0 sim, 3.7 nao — sem truncamento)
        >= 1            (IDs comecam em 1; 0 e negativos rejeitados)
        <= INT64_MAX    (cabe no dtype armazenado)

    Aceita listas, tuplas, ndarrays. Rejeita None, bool, floats
    nao-integrais, strings de float ("3.0"), strings nao-numericas e
    qualquer shape cujo ndim nao bata com `ndim` (se fornecido).

    O `ndim` check e feito ANTES da validacao elemento a elemento,
    porque uma lista de listas como [[1,2],[3,4]] tem ndim 2 mesmo
    que todos os elementos sejam validos — rejeitar cedo evita
    percorrer o array inteiro para nada.

    Implementacao: mantem o array como dtype=object ate a validacao
    e delega cada elemento ao contrato lossless de _coerce_int(). Isso
    garante que:

      - bool misturado com int ([True, 2, 3]) seja rejeitado: o
        np.asarray() com dtype explicito NAO homogeniza tipos antes
        da validacao, entao o True chega intacto ao _coerce_int().

      - strings de float ("3.0", "3.7") sejam rejeitadas: _coerce_int()
        so aceita strings que int() parseia, e int("3.0") levanta
        ValueError.

      - inteiros grandes (2**53 + 1) sobrevivam intactos: nao ha
        funil float64 no caminho, entao o valor exato e preservado.

    Custo: iteracao Python elemento a elemento. Irrelevante em
    contexto: o loader valida poucos IDs por linhagem.
    """
    if value is None:
        return None

    # Array de entrada como object: preserva o tipo de cada elemento
    # (bool, int, float, str) ate a validacao. dtype=object impede o
    # NumPy de homogenizar [True, 2, 3] para int64 e perder o bool.
    try:
        raw = np.asarray(value, dtype=object)
    except (TypeError, ValueError, OverflowError):
        return None

    if ndim is not None and raw.ndim != ndim:
        return None

    arr = np.empty(raw.shape, dtype=np.int64)

    for index, item in np.ndenumerate(raw):
        parsed = _coerce_int(item)

        if parsed is _INVALID:
            return None

        if not (1 <= parsed <= _INT64_MAX):
            return None

        arr[index] = parsed

    return arr


def _read_key(record: dict, pt_key: str, en_key: str, default=_MISSING):
    """Le uma chave aceitando PT (canonica) e EN (fallback legado).

    Retorna o valor quando ao menos uma das grafias esta no dict —
    MESMO se o valor for None. Retorna `default` quando nenhuma esta
    presente. O default padrao e `_MISSING`, que preserva a distincao
    entre "ausente" e "presente com valor None":

        ausente              -> retorna `default` (por padrao _MISSING)
        presente com None    -> retorna None
        presente com valor X -> retorna X

    Saves canonicos sao sempre escritos em portugues (ver `save`), mas
    aceitamos a grafia em ingles no load para saves legados
    continuarem carregando. Codigo novo deve sempre passar a chave PT
    primeiro.

    Chamadores que precisam distinguir ausente de presente-None
    comparam o retorno com `_MISSING`. Chamadores que so querem um
    default simples passam `default=<valor>`. Chamadores que precisam
    aceitar `None` como valor legitimo (ex: `zonas`) passam
    `default=None` explicitamente.
    """
    if pt_key in record:
        return record[pt_key]
    if en_key in record:
        return record[en_key]
    return default


# Migracao de formato


def _validate_save_compatibility(data: dict) -> dict | None:
    """Valida compatibilidade estrita com a versao atual do savegame.

    NAO migra. NAO normaliza. NAO reconstroi. Sob o contrato v11
    estrito, esta funcao apenas decide se o payload pode ou nao ser
    carregado; qualquer payload compativel ja e byte-a-byte o
    contrato atual.

    Recebe o dict cru do pickle e retorna o mesmo dict quando
    compativel, ou None quando irrecuperavel.

    Regras v11:
      - `versao` ausente       -> rejeita.
      - `versao` invalida      -> rejeita.
      - `versao` != atual      -> rejeita (nem mais novo, nem mais
        antigo; politica P1: mudancas semanticas em topologia,
        recombinacao, mutacao ou selecao nao podem ser migradas sem
        sintetizar estado que nunca existiu).
      - `arquitetura` ausente  -> rejeita.
      - `arquitetura` != atual -> rejeita.
      - `genoma` ausente       -> rejeita.
      - `genoma` != atual      -> rejeita.

    Aceita chaves em portugues (canonico) e em ingles (grafia
    historica), mas ambas precisam estar presentes E corretas. A
    tolerancia de idioma e apenas lexical; a semantica e estrita.

    NOTA: sob A1, `nascimentos` / `mortes` / `zonas` / `zonas_ativas`
    / `efeito_hp_zonas` / `reproduction_*` / `rng_*` passaram a ser
    campos obrigatorios do schema v11. Eles nao sao validados aqui
    (a funcao so cuida dos metadados de versao); cada um tem sua
    checagem em load(). Esta funcao apenas garante que o payload se
    identifica como exatamente v11 antes que load() comece a tocar
    no restante.
    """
    raw_version = _read_key(data, "versao", "version")
    if raw_version is _MISSING:
        # Metadado obrigatorio ausente: rejeita. Usa None para nao
        # deixar _MISSING vazar para a interpolacao da mensagem.
        print(i18n.t("log.load_invalid_version", v=None))
        return None

    version = _coerce_int(raw_version)
    if version is _INVALID:
        print(i18n.t("log.load_invalid_version", v=raw_version))
        return None

    if version > cfg.SAVE_VERSION:
        print(i18n.t("log.load_newer", v=version, cur=cfg.SAVE_VERSION))
        return None

    if version < cfg.SAVE_VERSION:
        print(i18n.t("log.load_incompatible", v=version, cur=cfg.SAVE_VERSION))
        return None

    # Version == SAVE_VERSION a partir daqui.

    raw_arch = _read_key(data, "arquitetura", "architecture")
    if raw_arch is _MISSING:
        print(
            i18n.t(
                "log.load_arch_mismatch",
                a=None,
                cur=cfg.ARCHITECTURE_VERSION,
            )
        )
        return None
    if raw_arch != cfg.ARCHITECTURE_VERSION:
        print(
            i18n.t(
                "log.load_arch_mismatch",
                a=raw_arch,
                cur=cfg.ARCHITECTURE_VERSION,
            )
        )
        return None

    raw_genome = _read_key(data, "genoma", "genome")
    if raw_genome is _MISSING:
        print(
            i18n.t(
                "log.load_genome_mismatch",
                g=None,
                cur=cfg.GENOME_VERSION,
            )
        )
        return None
    if raw_genome != cfg.GENOME_VERSION:
        print(
            i18n.t(
                "log.load_genome_mismatch",
                g=raw_genome,
                cur=cfg.GENOME_VERSION,
            )
        )
        return None

    return data


# Exportacao de metricas


def _export_metrics_csv(path: str) -> None:
    """Escreve o historico de metricas avancadas em CSV.

    Formato:
        tick,metrica,valores
        0,populacao,200;200;200
        10,populacao,195;198;200
        10,taxa_de_mutacao,5

    Metricas escalares tem um valor; metricas por linhagem tem N
    valores separados por ';'. O CSV e reescrito a cada save; sem
    historico, o arquivo nao e criado.

    Os nomes de metrica sao as chaves canonicas em portugues de
    cfg.ADVANCED_METRICS. O cabecalho e os nomes NAO sao traduzidos:
    fazem parte do contrato do formato.
    """
    has_data = any(series for series in state.metrics_history.values())
    if not has_data:
        return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["tick", "metrica", "valores"])
        for name in cfg.ADVANCED_METRICS:
            for tick, values in state.metrics_history[name]:
                text = ";".join(f"{v:.6g}" for v in values)
                writer.writerow([tick, name, text])


# Validacao de identidade


def _validate_identity(
    ids_per_lineage: list[np.ndarray],
    next_id: int,
) -> bool:
    """Valida a invariante estrutural de identidade.

    Por linhagem: dtype int64 e todos os IDs > 0.
    Global: nenhum ID duplicado, next_id > 0, next_id > max(ids).

    Nao valida len(ids) == len(agents) == len(pool): isso e feito no
    loop de carregamento, onde agents e pool estao disponiveis.
    """
    for ids in ids_per_lineage:
        if ids.dtype != np.int64:
            print(f"[load] ids dtype invalido: {ids.dtype}, esperado int64.")
            return False
        if ids.size and int(ids.min()) <= 0:
            print("[load] ids contem valor <= 0.")
            return False

    if not ids_per_lineage:
        if next_id <= 0:
            print("[load] proximo_id invalido.")
            return False
        return True

    non_empty = [ids for ids in ids_per_lineage if ids.size]
    if not non_empty:
        if next_id <= 0:
            print("[load] proximo_id invalido.")
            return False
        return True

    all_ids = np.concatenate(non_empty)
    if np.unique(all_ids).size != all_ids.size:
        print("[load] ids duplicados entre linhagens.")
        return False
    if next_id <= 0:
        print("[load] proximo_id invalido.")
        return False
    if next_id <= int(all_ids.max()):
        print(
            f"[load] proximo_id ({next_id}) <= max(ids) "
            f"({int(all_ids.max())}); risco de colisao."
        )
        return False
    return True


# Save


def save(path: str | None = None) -> bool:
    """Escreve o payload no formato canonico em portugues.

    Retorna True se o .pkl foi gravado com sucesso; False caso
    contrario. O CSV de metricas e sidecar analitico: falha nele
    gera warning, mas nao invalida o checkpoint.

    Escrita atomica: o payload e gravado num arquivo temporario no
    mesmo diretorio e movido com os.replace(). Disco cheio, processo
    interrompido ou erro de serializacao nao corrompem um save
    anteriormente valido — o alvo so e substituido quando o
    temporario esta completo.

    `path` default = slot ativo (state.active_save_slot) via
    save_path(). O CSV de metricas companheiro vai para
    metrics_path() do mesmo slot: os dois templates sao independentes,
    nao derivamos um do outro.

    As chaves do savegame sao sempre as canonicas em portugues.
    Strings de exibicao (HUD, charts) sao traduzidas em render time e
    nunca tocam o savegame.

    Sob o contrato v11, todos os campos do payload sao obrigatorios.
    Ausencia de qualquer um deles e rejeicao no load, nao fallback:
    um checkpoint so e continuacao exata se todo o estado de
    continuacao estiver presente. Os campos cuja ausencia era tratada
    como estado legitimo em versoes anteriores ("zonas_ativas",
    "nascimentos", "mortes", "efeito_hp_zonas") passaram a ser
    obrigatorios em v11. Ver _validate_save_compatibility e load().
    """
    if path is None:
        path = save_path()

    data = {
        "versao": cfg.SAVE_VERSION,
        "arquitetura": cfg.ARCHITECTURE_VERSION,
        "genoma": cfg.GENOME_VERSION,
        "mutation": state.mutation_rate,
        "mutategen": state.mutated_genes,
        "escala_local": state.local_scale_fraction,
        "tick": state.tick_count,
        # Contador global de identidade. Obrigatorio em v11; o load
        # rejeita se ausente ou inconsistente com os ids salvos.
        "proximo_id": state.next_critter_id,
        # Contadores cumulativos de nascimento/morte. Opcionais no
        # load (default 0); ausentes em saves pre-contador, estado
        # legitimo.
        "nascimentos": state.births,
        "mortes": state.deaths,
        # --- v11: estado exato de continuacao ---------------------
        #
        # Fase do scheduler reprodutivo. Sem esses dois campos, um
        # save/load nao reproduz a mesma sequencia de turnos: o
        # scheduler resumiria do estado em memoria, nao do estado
        # persistido.
        #
        # Chaves em ingles (reproduction_cooldown / reproduction_turn),
        # consistente com mutation / mutategen / escala_local / tick
        # / proximo_id. O save ja mistura PT e EN sem cerimonia; a
        # consistencia real e "chave estavel", nao "chave em PT".
        "reproduction_cooldown": state.reproduction_cooldown,
        "reproduction_turn": state.reproduction_turn,
        # Estado dos dois RNGs globais. Cru: o objeto devolvido por
        # random.getstate() / np.random.get_state() vai direto para o
        # pickle, sem conversao. O payload do mundo em si continua no
        # formato historico (list[list[float]]); o RNG state e opaco
        # por natureza, nunca sera lido por humano nem por ferramenta
        # externa, e o pickle do NumPy lida com o ndarray aninhado
        # sem esforco.
        "rng_python_state": random.getstate(),
        "rng_numpy_state": np.random.get_state(),
        # --- fim v11 ----------------------------------------------
        "modificadores_ambientais": cfg.ENVIRONMENTAL_MODIFIERS,
        "zonas": state.zones,
        "zonas_ativas": state.zones_active,
        # Efeito de HP das zonas em runtime. Opcional no load
        # (default cfg.HP_EFFECT_IN_ZONE); ausente em saves
        # pre-chave, estado legitimo. NAO faz parte do contrato de
        # SAVE_VERSION.
        "efeito_hp_zonas": state.zone_hp_effect,
        "linhagens": [
            {
                "id": ag["id"],
                "cor": ag["color"],
                # pool e ndarray [N, GENOME_SIZE] float32 em
                # memoria, mas o savegame mantem o formato historico
                # list[list[float]]: .tolist() produz os mesmos bytes
                # do caminho antigo com lista de arrays. Saves antigos
                # carregam sem mudanca.
                "pools": ag["pool"].tolist(),
                # agents e ndarray [N, AGENT_COLUMNS]; o savegame
                # mantem o formato historico list[list[float]].
                "agentes": ag["agents"].tolist(),
                # Identidade estavel. Chave canonica "ids".
                "ids": ag["ids"].tolist(),
            }
            for ag in agents
        ],
    }
    # Escrita atomica: grava em .tmp ao lado do alvo e renomeia.
    # os.replace e atomico em POSIX e Windows para o mesmo volume.
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "wb") as f:
            pickle.dump(data, f)
        os.replace(tmp_path, path)
    except (OSError, pickle.PicklingError) as e:
        # Limpa o temporario se ele ficou pela metade.
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        print(f"[save] falha ao gravar {path}: {e!r}")
        return False

    print(
        i18n.t(
            "log.save_ok",
            path=path,
            v=cfg.SAVE_VERSION,
            arch=cfg.ARCHITECTURE_VERSION,
            gen=cfg.GENOME_VERSION,
            p=[len(ag["pool"]) for ag in agents],
            t=state.tick_count,
        )
    )

    # CSV de metricas companheiro. O template de metricas do slot e
    # independente do template do .pkl: NAO derive um do outro com
    # splitext. O sufixo (_metricas.csv) faz parte do contrato do
    # formato (ver cfg.METRICS_CSV_SUFFIX).
    #
    # Se um path explicito foi passado (save ad-hoc, nao via slot
    # ativo), mantem o CSV ao lado usando o sufixo historico.
    explicit = path != save_path()
    csv_path = (
        os.path.splitext(path)[0] + cfg.METRICS_CSV_SUFFIX
        if explicit
        else metrics_path()
    )
    try:
        _export_metrics_csv(csv_path)
        print(i18n.t("log.save_metrics_ok", path=csv_path))
    except OSError as e:
        print(i18n.t("log.save_metrics_fail", e=repr(e)))

    return True


# Load


def load(path: str | None = None) -> bool:
    """Carrega do slot ativo (ou de um path explicito).

    Se `path` for None, tenta o arquivo do slot ativo primeiro. Se
    nao existir E o slot ativo for o default, tenta o PATH legado
    single-file (cfg.GENOME_FILE) como fallback, com aviso impresso.
    E fallback de NOME DE ARQUIVO, nao promessa de compatibilidade de
    formato: v10 rejeita qualquer save com `versao` abaixo de
    SAVE_VERSION (politica P1), entao um arquivo legado encontrado
    sera rejeitado no check de versao, nao carregado em silencio. O
    fallback e limitado ao slot default.

    Contrato v11 estrito: um save valido contem exatamente
    cfg.TOTAL_LINEAGES linhagens, cada uma com tres arrays paralelos
    em lockstep, todos os metadados de versao exatamente iguais aos
    atuais, todos os escalares de estado obrigatorios, zona valida
    com shape derivado do mundo atual, toggle de zonas obrigatorio,
    efeito de HP das zonas dentro do range, scheduler reprodutivo
    presente e estados dos dois RNGs presentes e validos:
        pool.shape   == (N, GENOME_SIZE)
        agents.shape == (N, AGENT_COLUMNS)
        ids.shape    == (N,)
    onde N e o mesmo nos tres. Qualquer outro shape e inconsistencia
    estrutural e o load e rejeitado. Sem amostragem, sem truncagem,
    sem reconstrucao.

    CONTRATO TRANSACIONAL
    ---------------------
    load() e dividido em fase PARSE e fase COMMIT, com um unico
    ponto de commit entre elas. Nada em `state` e escrito durante o
    parse: cada campo vai para uma variavel local e as linhagens sao
    montadas numa lista local `loaded`. So apos todas as checagens
    passarem a fase de commit roda, incondicionalmente ate o fim.

    Consequencias:
      - Um load rejeitado deixa o runtime byte-a-byte intacto:
        escalares, zonas, zonas_active, zone_hp_effect,
        next_critter_id, agents, sessao de inspecao, historico de
        metricas.
      - generate_zones() so e chamado no caminho de commit. Isso
        importa para reprodutibilidade: um load rejeitado nao pode
        consumir draws do RNG global, ou uma run subsequente com
        --seed divergiria de uma run identica que nunca tentou o
        load rejeitado.
      - A fase de commit nao levanta para nenhuma condicao que a
        fase de parse ja validou; o assert final e backstop
        fail-loud para bug genuino, nao caminho esperado.

    Excecoes ao split parse/commit sao os dois caminhos de saida
    antecipada (arquivo nao encontrado, pickle corrompido): leem do
    disco e das partes do payload sem RNG, e imprimem mensagem.
    """
    if path is None:
        path = save_path()
        if not os.path.exists(path) and state.active_save_slot == cfg.DEFAULT_SAVE_SLOT:
            if os.path.exists(cfg.GENOME_FILE):
                print(
                    i18n.t(
                        "log.load_legacy_fallback",
                        slot_path=path,
                        legacy=cfg.GENOME_FILE,
                    )
                )
                path = cfg.GENOME_FILE

    if not os.path.exists(path):
        print(i18n.t("log.load_not_found", path=path))
        return False

    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
    except (pickle.UnpicklingError, EOFError, AttributeError, ImportError) as e:
        print(i18n.t("log.load_corrupted", path=path, e=repr(e)))
        return False

    if not isinstance(data, dict):
        print(i18n.t("log.load_invalid_dict", path=path))
        return False

    data = _validate_save_compatibility(data)
    if data is None:
        return False

    # ------------------------------------------------------------------
    # FASE PARSE — nenhuma escrita em `state` daqui ate o commit
    # point. Cada campo vai para uma variavel local; qualquer falha
    # retorna False com `state` ainda intacto.
    # ------------------------------------------------------------------

    # --- v11: scheduler reprodutivo (parse) -----------------------
    #
    # Chaves obrigatorias em v11. Ausencia e rejeicao, nao fallback:
    # em v11 o checkpoint so e continuacao exata se a fase do
    # scheduler for conhecida. Os defaults de bootstrap (cooldown=0,
    # turn=0) NAO sao usados aqui; usá-los seria inventar estado que
    # o save nao contem.
    # Obrigatorios: default=_MISSING faz chave ausente cair em
    # _INVALID, indistinguivel de valor corrompido no contrato do
    # helper. Mensagem unica cobre os dois casos.
    parsed_reproduction_cooldown = _parse_int_field(
        data,
        "reproduction_cooldown",
        "reproduction_cooldown",
        minimum=0,
        maximum=cfg.REPRODUCTION_INTERVAL,
    )
    if parsed_reproduction_cooldown is _INVALID:
        print("[load] reproduction_cooldown ausente ou invalido; save invalido.")
        return False

    # TOTAL_LINEAGES e um limite exclusivo: turn em [0, N). Passar
    # maximum=N-1 e a forma correta; usar maximum=TOTAL_LINEAGES
    # aceitaria um turno invalido.
    parsed_reproduction_turn = _parse_int_field(
        data,
        "reproduction_turn",
        "reproduction_turn",
        minimum=0,
        maximum=cfg.TOTAL_LINEAGES - 1,
    )
    if parsed_reproduction_turn is _INVALID:
        print("[load] reproduction_turn ausente ou invalido; save invalido.")
        return False

    # --- v11: RNGs (parse com probes) -----------------------------
    #
    # Validacao em probes temporarios. Os RNGs globais (random,
    # np.random) NAO sao tocados aqui: a restauracao acontece so no
    # COMMIT, depois de toda validacao ter passado. Isso preserva o
    # invariante "load rejeitado nao altera RNG global".
    raw_rng_py = _read_key(data, "rng_python_state", "rng_python_state")
    if raw_rng_py is _MISSING:
        print("[load] rng_python_state ausente; save v11 invalido.")
        return False
    try:
        probe_py = random.Random()
        probe_py.setstate(raw_rng_py)
    except (TypeError, ValueError) as e:
        print(f"[load] rng_python_state invalido ({e!r}); save v11 invalido.")
        return False
    parsed_rng_py = raw_rng_py

    raw_rng_np = _read_key(data, "rng_numpy_state", "rng_numpy_state")
    if raw_rng_np is _MISSING:
        print("[load] rng_numpy_state ausente; save v11 invalido.")
        return False
    try:
        probe_np = np.random.RandomState()
        probe_np.set_state(raw_rng_np)
    except (TypeError, ValueError) as e:
        print(f"[load] rng_numpy_state invalido ({e!r}); save v11 invalido.")
        return False
    parsed_rng_np = raw_rng_np

    # --- Campos escalares (parseados para locais) ---
    #
    # Politica (centralizada em _parse_int_field):
    #   ausente        -> default (decidido por cada campo)
    #   presente None  -> _coerce_int(None) == _INVALID -> rejeita
    #   presente X     -> coerccao lossless + range check
    #
    # Campos com default historico usam um literal ou o valor atual
    # de `state`. Campos obrigatorios usam default=_MISSING (o
    # proprio sentinel): chave ausente e rejeitada como se invalida
    # fosse, o que e o contrato certo para v11.
    #
    # Mensagens: cada campo tem um log dedicado. Os dois
    # obrigatorios (reproduction_*) usam "ausente ou invalido"
    # porque o helper nao devolve a causa fina; distinguir "ausente"
    # de "presente mas corrompido" exigiria ampliar o protocolo do
    # helper sem ganho diagnostico proporcional.
    parsed_mutation = _parse_int_field(
        data,
        "mutation",
        "mutation",
        minimum=cfg.MIN_MUTATION_RATE,
        maximum=cfg.MAX_MUTATION_RATE,
    )
    if parsed_mutation is _INVALID:
        print("[load] mutation ausente ou invalido; save invalido.")
        return False

    parsed_mutated_genes = _parse_int_field(
        data,
        "mutategen",
        "mutategen",
        minimum=cfg.MIN_MUTATED_GENES,
        maximum=cfg.MAX_MUTATED_GENES,
    )
    if parsed_mutated_genes is _INVALID:
        print("[load] mutategen ausente ou invalido; save invalido.")
        return False

    parsed_local_scale = _parse_int_field(
        data,
        "escala_local",
        "local_scale",
        minimum=cfg.MIN_LOCAL_SCALE_FRACTION,
        maximum=cfg.MAX_LOCAL_SCALE_FRACTION,
    )
    if parsed_local_scale is _INVALID:
        print("[load] escala_local ausente ou invalida; save invalido.")
        return False

    parsed_tick = _parse_int_field(
        data,
        "tick",
        "tick",
        minimum=0,
    )
    if parsed_tick is _INVALID:
        print("[load] tick ausente ou invalido; save invalido.")
        return False

    parsed_births = _parse_int_field(
        data,
        "nascimentos",
        "births",
        minimum=0,
    )
    if parsed_births is _INVALID:
        print("[load] nascimentos ausente ou invalido; save invalido.")
        return False

    parsed_deaths = _parse_int_field(
        data,
        "mortes",
        "deaths",
        minimum=0,
    )
    if parsed_deaths is _INVALID:
        print("[load] mortes ausente ou invalido; save invalido.")
        return False

    # --- Zonas (obrigatorias em v11; sem regeneracao) ---
    #
    # Sob A1, a chave `zonas` e obrigatoria e deve conter uma mascara
    # booleana valida com o shape derivado do mundo atual. Ausencia,
    # None, tipo invalido ou shape divergente rejeitam o save.
    #
    # generate_zones() NAO e chamado em nenhum caminho do load. Um
    # load rejeitado nunca consome RNG, e um load aceito restaura
    # exatamente a mascara salva. A propriedade "checkpoint =
    # continuacao exata" depende disso.
    raw_zones = _read_key(data, "zonas", "zones")
    if raw_zones is _MISSING:
        print("[load] zonas ausente; save invalido.")
        return False
    if raw_zones is None:
        print("[load] zonas nulas; save invalido.")
        return False
    try:
        zones_arr = np.asarray(raw_zones, dtype=bool)
    except (TypeError, ValueError, OverflowError):
        print("[load] zonas invalidas; save invalido.")
        return False
    expected = (
        layout.LAYOUT.world_width,
        layout.LAYOUT.world_height,
    )
    if zones_arr.shape != expected:
        # O save foi feito em outra resolucao: a mascara de zonas e
        # [WORLD_WIDTH, WORLD_HEIGHT] do monitor em que foi salvo,
        # mas o mundo em execucao deriva as dimensoes do monitor
        # ATUAL. Carregar uma mascara incompativel quebraria no
        # primeiro state.zones[xs, ys] em evolution._zone_effect.
        #
        # Rejeitamos em vez de regenerar: regenerar substituiria a
        # ecologia salva por uma nova aleatoria em silencio, pior do
        # que recusar carregar. Rejeitar mantem o save intacto em
        # disco e forca o operador a reabrir o jogo na resolucao
        # original.
        print(
            i18n.t(
                "log.load_zones_shape_mismatch",
                saved=zones_arr.shape,
                current=expected,
            )
        )
        return False
    parsed_zones: np.ndarray = zones_arr

    # --- Toggle de zonas (obrigatorio em v11) ---
    #
    # bool estrito: type(x) is bool. Nao aceita np.bool_, strings,
    # 0/1 nem qualquer coisa que bool() aceitaria por permissividade.
    # O payload canonical grava state.zones_active, que e sempre
    # bool Python; qualquer outra coisa e payload corrompido ou
    # editado a mao.
    #
    # Ausencia e rejeicao. Saves pre-toggle nao existem mais no
    # contrato v11 (que rejeita versoes anteriores).
    raw_zones_active = _read_key(data, "zonas_ativas", "zones_active")
    if raw_zones_active is _MISSING:
        print("[load] zonas_ativas ausente; save invalido.")
        return False
    if type(raw_zones_active) is bool:
        parsed_zones_active = raw_zones_active
    else:
        print(
            f"[load] zonas_ativas deve ser bool estrito, "
            f"recebido {type(raw_zones_active).__name__}; save invalido."
        )
        return False

    # --- Efeito de HP das zonas (obrigatorio em v11, com range) ---
    parsed_zone_hp_effect = _parse_int_field(
        data,
        "efeito_hp_zonas",
        "zone_hp_effect",
        minimum=cfg.MIN_ZONE_HP_EFFECT,
        maximum=cfg.MAX_ZONE_HP_EFFECT,
    )
    if parsed_zone_hp_effect is _INVALID:
        print("[load] efeito_hp_zonas ausente ou invalido; save invalido.")
        return False

    # --- Linhagens (validacao estrutural, tudo para `loaded`) ---
    lineages = _read_key(data, "linhagens", "lineages")

    if not isinstance(lineages, list):
        print(
            f"[load] 'linhagens' is not a list (got {type(lineages).__name__}). "
            "Aborting."
        )
        return False

    if len(lineages) != cfg.TOTAL_LINEAGES:
        print(
            i18n.t(
                "log.load_lineage_count",
                saved=len(lineages),
                expected=cfg.TOTAL_LINEAGES,
            )
        )
        return False

    # proximo_id e obrigatorio em v11.
    raw_next_id = _read_key(data, "proximo_id", "proximo_id")
    if raw_next_id is _MISSING or raw_next_id is None:
        print("[load] proximo_id ausente; save invalido.")
        return False
    saved_next_id = _coerce_int(raw_next_id)
    if saved_next_id is _INVALID:
        print("[load] proximo_id invalido; save invalido.")
        return False
    if not (1 <= saved_next_id <= _INT64_MAX):
        print("[load] proximo_id fora do intervalo int64 valido.")
        return False

    loaded: list[dict] = []

    for expected_index, record in enumerate(lineages):
        expected_id = cfg.LINEAGES[expected_index]["id"]
        expected_color = cfg.LINEAGES[expected_index]["color"]

        if not isinstance(record, dict):
            print(
                f"[load] linhagem {expected_index} nao e dict "
                f"({type(record).__name__}); save invalido."
            )
            return False

        record_id = record.get("id")
        if record_id != expected_id:
            print(
                f"[load] linhagem {expected_index} tem id={record_id!r}, "
                f"esperado {expected_id!r}; save invalido."
            )
            return False

        saved_ids = record.get("ids")
        if saved_ids is None:
            print(f"[load] ids ausente para linhagem {expected_id}; save invalido.")
            return False
        # Coerced, nao np.asarray cru: uma lista de strings
        # nao-numericas levantaria ValueError fora de load() e
        # quebraria o contrato "validate/reject".
        ids_arr = _coerce_int_array(saved_ids, ndim=1)
        if ids_arr is None:
            print(
                f"[load] ids invalido para linhagem {expected_id}; save invalido."
            )
            return False

        pool = _read_key(record, "pools", "pool")
        if pool is None:
            print(
                f"[load] pool ausente para linhagem {expected_id}; save invalido."
            )
            return False
        try:
            pool_arr = np.asarray(pool, dtype=np.float32)
        except (TypeError, ValueError, OverflowError):
            print(
                f"[load] pool invalido para linhagem {expected_id}; save invalido."
            )
            return False

        agents_raw = _read_key(record, "agentes", "agents")
        if agents_raw is None:
            print(
                f"[load] agents ausente para linhagem {expected_id}; save invalido."
            )
            return False
        try:
            agents_arr = np.asarray(agents_raw, dtype=np.float32)
        except (TypeError, ValueError, OverflowError):
            print(
                f"[load] agents invalido para linhagem {expected_id}; "
                f"save invalido."
            )
            return False

        if pool_arr.ndim != 2:
            print(
                i18n.t(
                    "log.load_lineage_shape",
                    id=expected_id,
                    pool=pool_arr.shape,
                    agents=agents_arr.shape,
                    ids=ids_arr.shape,
                    expected="(N, GENOME_SIZE)",
                )
            )
            return False
        n = pool_arr.shape[0]

        expected_pool_shape = (n, cfg.GENOME_SIZE)
        expected_agents_shape = (n, AGENT_COLUMNS)
        expected_ids_shape = (n,)

        if (
            pool_arr.shape != expected_pool_shape
            or agents_arr.shape != expected_agents_shape
            or ids_arr.shape != expected_ids_shape
        ):
            print(
                i18n.t(
                    "log.load_lineage_shape",
                    id=expected_id,
                    pool=pool_arr.shape,
                    agents=agents_arr.shape,
                    ids=ids_arr.shape,
                    expected=n,
                )
            )
            return False

        # Validacao de x/y antes de qualquer cast. np.asarray(...,
        # dtype=np.int64) truncaria 3.7 -> 3 silenciosamente, violando
        # o contrato de payload. Ordem:
        #   finite -> integral -> cast -> bounds -> np.add.at
        #
        # Esta validacao prova que as coordenadas sao utilizaveis
        # como indices. Depois dela, a construcao do field abaixo nao
        # pode falhar por dados do payload.
        xs_raw = agents_arr[:, INDEX_X]
        ys_raw = agents_arr[:, INDEX_Y]

        if not (np.all(np.isfinite(xs_raw)) and np.all(np.isfinite(ys_raw))):
            print(
                f"[load] x/y nao-finitos para linhagem {expected_id}; "
                f"save invalido."
            )
            return False
        if not (
            np.all(xs_raw == np.floor(xs_raw)) and np.all(ys_raw == np.floor(ys_raw))
        ):
            print(
                f"[load] x/y nao-integrais para linhagem {expected_id}; "
                f"save invalido."
            )
            return False

        xs = xs_raw.astype(np.int64)
        ys = ys_raw.astype(np.int64)

        if not (
            np.all(xs >= 0)
            and np.all(xs < layout.LAYOUT.world_width)
            and np.all(ys >= 0)
            and np.all(ys < layout.LAYOUT.world_height)
        ):
            print(
                f"[load] x/y fora do mundo para linhagem {expected_id}; "
                f"save invalido."
            )
            return False

        # Construcao local do field. Nao chamamos world.fill_fields()
        # no commit: o field e parte do payload validado, nao efeito
        # colateral. Se este bloco nao pode falhar, o commit nao pode
        # falhar.
        field = np.zeros(
            (layout.LAYOUT.world_width, layout.LAYOUT.world_height),
            dtype=np.int16,
        )
        if xs.size:
            np.add.at(field, (xs, ys), 1)

        loaded.append(
            {
                "id": expected_id,
                "color": expected_color,
                "pool": pool_arr,
                "agents": agents_arr,
                "ids": ids_arr,
                "field": field,
            }
        )

    ids_per_lineage = [lin["ids"] for lin in loaded]

    if not _validate_identity(ids_per_lineage, saved_next_id):
        return False

    # ------------------------------------------------------------------
    # COMMIT POINT — todas as checagens passaram. Daqui em diante,
    # sem return antecipado: as escritas abaixo sempre completam, e o
    # runtime termina num estado totalmente consistente. So o assert
    # final pode parar o commit, e ele dispara por bug genuino, nao
    # por input ruim.
    # ------------------------------------------------------------------

    # Garante que as linhagens existem antes de popular. O loop
    # grafico sempre chamou seed_lineages() antes de qualquer load
    # (via bootstrap_new_world / run), mas era contrato implicito que
    # o caminho grafico satisfazia por acidente e o headless nao.
    # Sem isso, `zip(agents, lineages)` itera zero vezes num processo
    # novo, load() retorna True com agents == [], e o primeiro step()
    # quebra com IndexError.
    #
    # Idempotente: se agents ja esta populado, e no-op.
    if not agents:
        seed_lineages()

    # Escalares.
    state.mutation_rate = parsed_mutation
    state.mutated_genes = parsed_mutated_genes
    state.local_scale_fraction = parsed_local_scale
    state.tick_count = parsed_tick
    state.last_print = parsed_tick
    state.births = parsed_births
    state.deaths = parsed_deaths

    # v11: scheduler reprodutivo. A fase do turno e restaurada junto
    # com o resto do estado, para a sequencia de turnos continuar
    # exatamente de onde parou.
    state.reproduction_cooldown = parsed_reproduction_cooldown
    state.reproduction_turn = parsed_reproduction_turn

    # v11: RNGs globais. So aqui, no COMMIT, os estados validados em
    # probe sao aplicados nos geradores reais. Qualquer load rejeitado
    # antes deste ponto deixa os RNGs exatamente como estavam.
    random.setstate(parsed_rng_py)
    np.random.set_state(parsed_rng_np)

    # Zonas: restauracao direta. Sob v11 estrito, `parsed_zones` ja
    # e uma mascara booleana valida com o shape esperado; nao ha
    # caminho de regeneracao, nao ha consumo de RNG no commit.
    state.zones = parsed_zones
    state.zones_active = parsed_zones_active
    state.zone_hp_effect = parsed_zone_hp_effect

    # Populacao. In-place em `agents` para preservar a identidade da
    # lista: outros modulos fazem `from .state import agents`.
    agents.clear()
    agents.extend(loaded)

    state.next_critter_id = saved_next_id

    # fill_fields() NAO e chamado aqui. O field de cada linhagem foi
    # construido na fase parse, depois de validar x/y, e ja reflete
    # exatamente a populacao carregada. Reconstruir no commit seria
    # redundante e reintroduziria trabalho dependente do payload
    # depois da fronteira transacional.
    #
    # A sessao de inspecao NUNCA e herdada de um save: o ID observado
    # pertence a run anterior. Mesmo que o save contenha um ID
    # numericamente igual, tratar como continuacao seria surpresa.
    state.set_inspection_selection(None)

    for series in state.metrics_history.values():
        series.clear()

    # Falha ruidosamente se o load produziu estado inconsistente.
    #
    # Antes deste assert, load() retornava True mesmo com agents
    # vazio (o zip() iterava zero vezes) — o chamador entao quebrava
    # no primeiro step() com um IndexError enganoso. A invariante e:
    # um load bem-sucedido deixa as linhagens populadas. Se isto
    # dispara, o save e irrecuperavel e o chamador deve abortar, nao
    # cair num mundo meio-inicializado.
    assert len(agents) == cfg.TOTAL_LINEAGES, (
        f"load() produced {len(agents)} lineages, expected "
        f"{cfg.TOTAL_LINEAGES}. This is a bug; the save is unrecoverable."
    )

    print(
        i18n.t(
            "log.load_ok",
            path=path,
            v=data["versao"],
            arch=data["arquitetura"],
            gen=data["genoma"],
            t=state.tick_count,
            p=[len(ag["pool"]) for ag in agents],
        )
    )
    return True
