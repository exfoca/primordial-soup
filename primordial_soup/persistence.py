# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

from __future__ import annotations
import csv
import math
import numbers
import os
import pickle
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
    generate_zones,
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


def _read_key_strict(record: dict, pt_key: str, en_key: str):
    """Le uma chave aceitando PT (canonica) e EN (fallback legado).

    Retorna o valor quando ao menos uma das grafias esta no dict —
    MESMO se o valor for None. Retorna _MISSING quando nenhuma esta
    presente.

    Diferente de _read_key, distingue chave ausente de valor None.
    Isso e o que permite aplicar a politica:
        ausente        -> default (decidido pelo chamador)
        presente None  -> _coerce_int(None) == _INVALID -> rejeita
        presente X     -> tenta converter; se _INVALID, rejeita
    """
    if pt_key in record:
        return record[pt_key]
    if en_key in record:
        return record[en_key]
    return _MISSING


def _read_key(record: dict, pt_key: str, en_key: str, default=None):
    """Le uma chave aceitando a grafia em portugues (canonica) e em
    ingles.

    Saves canonicos sao sempre escritos em portugues (ver `save`), mas
    aceitamos a grafia em ingles no load para saves legados
    continuarem carregando. Codigo novo deve sempre passar a chave PT
    primeiro.

    Retorna `default` apenas se NENHUMA das chaves estiver presente.
    Uma chave presente com valor None e retornada como None (valor
    legitimo em alguns campos, ex: `zonas`).
    """
    if pt_key in record:
        return record[pt_key]
    if en_key in record:
        return record[en_key]
    return default


# Migracao de formato


def _migrate(data: dict) -> dict | None:
    """Ponto unico de migracao de savegames.

    Recebe o dict cru do pickle e retorna um dict compativel com a
    versao atual, ou None se irrecuperavel.

    Regras:
      - `versao` ausente   -> assume 1 (save pre-versionamento).
      - `versao` > atual   -> rejeita (save de versao futura).
      - `versao` < atual   -> rejeita (mudanca semantica em topologia,
        recombinacao, mutacao ou selecao; sintetizar pesos aleatorios
        produziria comparacoes invalidas entre runs — politica P1).
      - `arquitetura`/`genoma` ausentes -> assume valores atuais.
      - Zonas sao opcionais; se ausentes, regenera ou None.

    Aceita chaves em portugues e em ingles.

    NOTA: `nascimentos` / `mortes` NAO fazem parte do contrato de
    versao. Ausencia num save antigo e estado legitimo (nao sabemos
    quantos nascimentos/mortes ocorreram antes do save existir), e
    `load()` usa default 0. SAVE_VERSION deliberadamente NAO e
    incrementado por eles — mesmo raciocinio de `zonas_ativas`.
    """
    raw_version = _read_key_strict(data, "versao", "version")
    if raw_version is _MISSING:
        version = 1
    else:
        version = _coerce_int(raw_version)
        if version is _INVALID:
            print(i18n.t("log.load_invalid_version", v=raw_version))
            return None

    if version > cfg.SAVE_VERSION:
        print(i18n.t("log.load_newer", v=version, cur=cfg.SAVE_VERSION))
        return None

    if version < 1:
        print(i18n.t("log.load_invalid_version", v=version))
        return None

    architecture = _read_key(
        data, "arquitetura", "architecture", cfg.ARCHITECTURE_VERSION
    )
    genome = _read_key(data, "genoma", "genome", cfg.GENOME_VERSION)

    if version < cfg.SAVE_VERSION:
        print(i18n.t("log.load_incompatible", v=version, cur=cfg.SAVE_VERSION))
        return None

    if architecture != cfg.ARCHITECTURE_VERSION:
        print(
            i18n.t(
                "log.load_arch_mismatch",
                a=architecture,
                cur=cfg.ARCHITECTURE_VERSION,
            )
        )
        return None

    if genome != cfg.GENOME_VERSION:
        print(
            i18n.t(
                "log.load_genome_mismatch",
                g=genome,
                cur=cfg.GENOME_VERSION,
            )
        )
        return None

    data["versao"] = cfg.SAVE_VERSION
    data["arquitetura"] = cfg.ARCHITECTURE_VERSION
    data["genoma"] = cfg.GENOME_VERSION
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


def save(path: str | None = None) -> None:
    """Escreve o payload no formato canonico em portugues.

    `path` default = slot ativo (state.active_save_slot) via
    save_path(). O CSV de metricas companheiro vai para
    metrics_path() do mesmo slot: os dois templates sao independentes,
    nao derivamos um do outro.

    As chaves do savegame sao sempre as canonicas em portugues.
    Strings de exibicao (HUD, charts) sao traduzidas em render time e
    nunca tocam o savegame.

    A chave "zonas_ativas" guarda o toggle de runtime das zonas
    ambientais. Opcional no load (default True), entao saves
    pre-toggle mantem o comportamento original: zonas visiveis e
    concedendo bonus de HP. SAVE_VERSION NAO e incrementado por ela —
    ausencia e estado legitimo, nao formato incompativel.

    As chaves "nascimentos" / "mortes" guardam os contadores
    cumulativos de nascimento/morte da run. Mesma politica de
    "zonas_ativas": opcional no load (default 0), sem bump de
    SAVE_VERSION. Saves antigos que precedem esses contadores
    simplesmente carregam com ambos em 0, que e a unica resposta
    semanticamente correta — a informacao nunca foi gravada e nao
    pode ser reconstruida.

    A chave "efeito_hp_zonas" guarda o efeito de HP de runtime
    aplicado a bichos dentro de zona. Mesma politica: opcional no
    load (default cfg.HP_EFFECT_IN_ZONE), sem bump de SAVE_VERSION.
    Saves pre-chave carregam com o default do config, reproduzindo o
    comportamento original.
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
        # Contador global de identidade. Obrigatorio em v10; o load
        # rejeita se ausente ou inconsistente com os ids salvos.
        "proximo_id": state.next_critter_id,
        # Contadores cumulativos de nascimento/morte. Opcionais no
        # load (default 0); ausentes em saves pre-contador, estado
        # legitimo.
        "nascimentos": state.births,
        "mortes": state.deaths,
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
    with open(path, "wb") as f:
        pickle.dump(data, f)
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

    Contrato v10 estrito: um save valido contem exatamente
    cfg.TOTAL_LINEAGES linhagens, cada uma com tres arrays paralelos
    em lockstep:
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

    data = _migrate(data)
    if data is None:
        return False

    # ------------------------------------------------------------------
    # FASE PARSE — nenhuma escrita em `state` daqui ate o commit
    # point. Cada campo vai para uma variavel local; qualquer falha
    # retorna False com `state` ainda intacto.
    # ------------------------------------------------------------------

    # --- Campos escalares (parseados para locais) ---
    #
    # Politica (decidida em _read_key_strict + _coerce_int):
    #   ausente        -> default permitido (state atual ou literal)
    #   presente None  -> _coerce_int(None) == _INVALID -> rejeita
    #   presente X     -> _coerce_int(X); se _INVALID, rejeita
    #
    # Cumpre o contrato "chave ausente e default; presenca invalida
    # e rejeicao".
    raw_mutation = _read_key_strict(data, "mutation", "mutation")
    if raw_mutation is _MISSING:
        parsed_mutation = state.mutation_rate
    else:
        parsed_mutation = _coerce_int(raw_mutation)
        if parsed_mutation is _INVALID:
            print("[load] mutation invalido; save v10 invalido.")
            return False

    raw_mutated_genes = _read_key_strict(data, "mutategen", "mutategen")
    if raw_mutated_genes is _MISSING:
        parsed_mutated_genes = state.mutated_genes
    else:
        parsed_mutated_genes = _coerce_int(raw_mutated_genes)
        if parsed_mutated_genes is _INVALID:
            print("[load] mutategen invalido; save v10 invalido.")
            return False

    raw_local_scale = _read_key_strict(data, "escala_local", "local_scale")
    if raw_local_scale is _MISSING:
        parsed_local_scale = state.local_scale_fraction
    else:
        parsed_local_scale = _coerce_int(raw_local_scale)
        if parsed_local_scale is _INVALID:
            print("[load] escala_local invalida; save v10 invalido.")
            return False

    raw_tick = _read_key_strict(data, "tick", "tick")
    if raw_tick is _MISSING:
        parsed_tick = 0
    else:
        parsed_tick = _coerce_int(raw_tick)
        if parsed_tick is _INVALID:
            print("[load] tick invalido; save v10 invalido.")
            return False

    raw_births = _read_key_strict(data, "nascimentos", "births")
    if raw_births is _MISSING:
        parsed_births = 0
    else:
        parsed_births = _coerce_int(raw_births)
        if parsed_births is _INVALID:
            print("[load] nascimentos invalido; save v10 invalido.")
            return False

    raw_deaths = _read_key_strict(data, "mortes", "deaths")
    if raw_deaths is _MISSING:
        parsed_deaths = 0
    else:
        parsed_deaths = _coerce_int(raw_deaths)
        if parsed_deaths is _INVALID:
            print("[load] mortes invalido; save v10 invalido.")
            return False

    # --- Zonas (parseadas para local; generate_zones adiado ao commit) ---
    parsed_zones: np.ndarray | None
    zones_key_present = ("zonas" in data) or ("zones" in data)
    if zones_key_present:
        zones = _read_key(data, "zonas", "zones")
        if zones is None:
            parsed_zones = None
        else:
            try:
                zones_arr = np.asarray(zones, dtype=bool)
            except (TypeError, ValueError, OverflowError):
                print("[load] zonas invalidas; save v10 invalido.")
                return False
            expected = (
                layout.LAYOUT.world_width,
                layout.LAYOUT.world_height,
            )
            if zones_arr.shape != expected:
                # O save foi feito em outra resolucao: a mascara de
                # zonas e [WORLD_WIDTH, WORLD_HEIGHT] do monitor em
                # que foi salvo, mas o mundo em execucao deriva as
                # dimensoes do monitor ATUAL. Carregar uma mascara
                # incompativel quebraria no primeiro state.zones[xs,
                # ys] em evolution._zone_effect.
                #
                # Rejeitamos em vez de regenerar: regenerar
                # substituiria a ecologia salva por uma nova aleatoria
                # em silencio, pior do que recusar carregar. Rejeitar
                # mantem o save intacto em disco e forca o operador a
                # reabrir o jogo na resolucao original.
                print(
                    i18n.t(
                        "log.load_zones_shape_mismatch",
                        saved=zones_arr.shape,
                        current=expected,
                    )
                )
                return False
            parsed_zones = zones_arr
    else:
        # Chave ausente: adia geracao para a fase de commit, para um
        # load rejeitado nao sortear do RNG global.
        parsed_zones = None

    # --- Toggle de zonas (chave opcional, default True) ---
    parsed_zones_active = bool(_read_key(data, "zonas_ativas", "zones_active", True))

    # --- Efeito de HP das zonas (chave opcional, default cfg) ---
    raw_effect = _read_key_strict(data, "efeito_hp_zonas", "zone_hp_effect")
    if raw_effect is _MISSING:
        parsed_zone_hp_effect = int(cfg.HP_EFFECT_IN_ZONE)
    else:
        parsed_zone_hp_effect = _coerce_int(raw_effect)
        if parsed_zone_hp_effect is _INVALID:
            print("[load] efeito_hp_zonas invalido; save v10 invalido.")
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

    # proximo_id e obrigatorio em v10.
    raw_next_id = _read_key_strict(data, "proximo_id", "proximo_id")
    if raw_next_id is _MISSING or raw_next_id is None:
        print("[load] proximo_id ausente; save v10 invalido.")
        return False
    saved_next_id = _coerce_int(raw_next_id)
    if saved_next_id is _INVALID:
        print("[load] proximo_id invalido; save v10 invalido.")
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
                f"({type(record).__name__}); save v10 invalido."
            )
            return False

        record_id = record.get("id")
        if record_id != expected_id:
            print(
                f"[load] linhagem {expected_index} tem id={record_id!r}, "
                f"esperado {expected_id!r}; save v10 invalido."
            )
            return False

        saved_ids = record.get("ids")
        if saved_ids is None:
            print(f"[load] ids ausente para linhagem {expected_id}; save v10 invalido.")
            return False
        # Coerced, nao np.asarray cru: uma lista de strings
        # nao-numericas levantaria ValueError fora de load() e
        # quebraria o contrato "validate/reject".
        ids_arr = _coerce_int_array(saved_ids, ndim=1)
        if ids_arr is None:
            print(
                f"[load] ids invalido para linhagem {expected_id}; save v10 invalido."
            )
            return False

        pool = _read_key(record, "pools", "pool")
        if pool is None:
            print(
                f"[load] pool ausente para linhagem {expected_id}; save v10 invalido."
            )
            return False
        try:
            pool_arr = np.asarray(pool, dtype=np.float32)
        except (TypeError, ValueError, OverflowError):
            print(
                f"[load] pool invalido para linhagem {expected_id}; save v10 invalido."
            )
            return False

        agents_raw = _read_key(record, "agentes", "agents")
        if agents_raw is None:
            print(
                f"[load] agents ausente para linhagem {expected_id}; save v10 invalido."
            )
            return False
        try:
            agents_arr = np.asarray(agents_raw, dtype=np.float32)
        except (TypeError, ValueError, OverflowError):
            print(
                f"[load] agents invalido para linhagem {expected_id}; "
                f"save v10 invalido."
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
                f"save v10 invalido."
            )
            return False
        if not (
            np.all(xs_raw == np.floor(xs_raw)) and np.all(ys_raw == np.floor(ys_raw))
        ):
            print(
                f"[load] x/y nao-integrais para linhagem {expected_id}; "
                f"save v10 invalido."
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
                f"save v10 invalido."
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

    # Zonas. Se a chave estava ausente, gera mascara nova AQUI (so
    # no commit) para um load rejeitado nunca consumir RNG.
    if zones_key_present:
        state.zones = parsed_zones
    else:
        state.zones = generate_zones()
        if state.zones is not None:
            print(i18n.t("log.load_zones_missing"))

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
