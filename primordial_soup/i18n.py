# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Internacionalizacao para todas as strings visiveis ao usuario.

Chaves canonicas sao neutras de idioma (ex: "hud.tick_speed").
Valores sao por idioma. Ingles e o default e o fallback.

NAO traduzido aqui (deliberado):
  - Chaves do savegame (sempre portugues; ver persistence.py).
  - Cabecalhos do CSV e chaves de metrica (sempre portugues; ver
    config.py).
  - Valores canonicos de config lidos pelo codigo (ver config.py).
  - IDs de linhagem "R", "G", "B" (identificadores, nao exibicao).
  - Nomes de coluna do agente / constantes de indice (internos).
  - Nomes de arquivo (genome_pool.pkl, _metricas.csv).

O idioma de exibicao e preferencia do usuario. NAO e parte do estado
da simulacao e NAO e resetado por state.reset_counters().
"""

from __future__ import annotations
from . import state

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # --- HUD: global block ---
        "hud.tick_speed": "tick={tick}  speed={speed}x",
        "hud.births_deaths": "births={births}  deaths={deaths}",
        "hud.mutation": "mut={mut}%{mut_marker}  mode={mode}  local={local}%{local_marker}  global={gp}%@{gf}%",
        "hud.selection": "selection={crit}  L/E/I/R={w1}/{w2}/{w3}/{w4}",
        "hud.environment": "env={env}  {zones}",
        "hud.save_slot": "slot: {slot}",
        "hud.zones_none": "none",
        "hud.zones_fmt": "{n}x r={r} ({bonus}hp)",
        "hud.zones_off_suffix": "{base} [off]",
        "hud.zones_damage": "DANGER",
        "hud.zones_zkey": "  [Z]",
        "hud.metric_prefix": "metric (M): {label}",
        "hud.inspection_prefix": "inspection (i): {state}",
        "hud.on": "ON",
        "hud.off": "OFF",
        # --- HUD: controls block ---
        "hud.section_sim": "── simulation ─────────────────────────",
        "hud.controls_1": "SPACE pause  = step  R recreate  ESC quit",
        "hud.controls_2": "S save  L load  N slot  P print",
        "hud.section_tune": "── adjust ────────────────────────────",
        "hud.controls_3": "U mut  O local  E zone HP  then up/down",
        "hud.controls_4": ", . speed  Z zones on/off",
        "hud.zone_hp_param": "zone HP effect={v}",
        "hud.repro_gates": "repro: age>={age} hp<{hp} score>={score} enc>={enc}",
        "hud.active_marker": " ◄",
        "hud.section_analysis": "── analysis ──────────────────────────",
        "hud.controls_5": "M metric  I inspect  click observes",
        "hud.controls_6": "← → criterion  Tab lineage",
        "hud.controls_7": "Enter observes candidate  F11 fullscreen",
        "hud.controls_8": "H reset hp  T language  G record GIF",
        # --- Inspection criteria and lineage filter ---
        "criterion.most_evolved": "most evolved",
        "criterion.oldest": "oldest",
        "criterion.youngest": "youngest",
        "criterion.most_offspring": "most offspring",
        "criterion.most_encounters": "most encounters",
        "criterion.most_explored": "most explored",
        "criterion.highest_hp": "highest hp",
        "criterion.lowest_hp": "lowest hp",
        "criterion.highest_generation": "highest generation",
        "criterion.best_score": "best score",
        "lineage_filter.all": "all",
        "lineage_filter.R": "R",
        "lineage_filter.G": "G",
        "lineage_filter.B": "B",
        "panel.discovery_title": "DISCOVERY",
        "panel.observation_title": "OBSERVING",
        "panel.candidate_label": "candidate:",
        "panel.no_candidate": "no candidate",
        "panel.enter_hint": "Enter = observe",
        "panel.hint_navigation": "←→ criterion | Tab lineage",
        "panel.hint_actions": "Enter observe | click choose | I exit",
        # --- HUD: recording indicator ---
        "hud.recording_on": "● REC",
        # --- HUD: lineage table column labels ---
        "col.id": "id",
        "col.hp": "hp",
        "col.lt": "lt",
        "col.gen": "gen",
        "col.pop": "pop",
        "col.score": "score",
        # --- Charts ---
        "chart.population_title": "population per lineage",
        "chart.metric_title": "metric: {label}  (M cycles)",
        "chart.x_axis": "tick",
        "chart.scalar_label": "value",
        # --- Metric labels (keys are canonical PT) ---
        "metric.populacao": "population",
        "metric.hp_medio": "average hp",
        "metric.maior_tempo_de_vida": "longest lifetime",
        "metric.geracao_maxima": "max generation",
        "metric.score_composto_medio": "average composite score",
        "metric.taxa_de_mutacao": "mutation rate (%)",
        # --- RPS tip ---
        "rps.enemy": "  -> enemy: ",
        "rps.ally": "  |  ally: ",
        # --- Inspection panel ---
        "panel.title": "INSPECTION",
        "panel.no_selection": "no critter observed",
        "panel.stale_selection": "selected critter no longer exists",
        "panel.lineage": "lineage:",
        "panel.id": "id:",
        "panel.status": "status:",
        "panel.status_alive": "ALIVE",
        "panel.status_dead": "DEAD — tick {tick}",
        "panel.hp": "hp:",
        "panel.time": "time:",
        "panel.generation": "generation:",
        "panel.offspring": "offspring:",
        "panel.encounters": "encounters:",
        "panel.score": "score:",
        "panel.last_action": "last action:",
        "panel.position": "position:",
        "panel.vision_title": "vision 11x11 (center {x},{y})",
        # --- Heatmaps ---
        "heatmap.w1": "W1 (input->hidden1)",
        "heatmap.w2": "W2 (hidden1->hidden2)",
        "heatmap.w3": "W3 (hidden2->output)",
        "heatmap.b1": "b1 (hidden1 biases)",
        "heatmap.b2": "b2 (hidden2 biases)",
        "heatmap.r": "R (recurrence)",
        # --- Console logs ---
        "log.recreate": "[recreate] population reset, tick=0",
        "log.inspection_on": "[inspection] ON — {desc}",
        "log.inspection_on_empty": "[inspection] ON (no living critters)",
        "log.inspection_on_auto": "[inspection] ON — auto-selected {desc}",
        "log.inspection_off": "[inspection] OFF",
        "log.inspection_select": "[inspection] {desc}",
        "log.inspection_miss": "[inspection] nobody at ({x},{y}) radius={r}",
        "log.load_lineage_count": "[load] save has {saved} lineages, expected {expected}.",
        "log.load_lineage_shape": "[load] lineage {id}: pool={pool} agents={agents} ids={ids} (expected {expected}).",
        "log.stale_selection": "(stale selection)",
        "log.selection_desc": "lineage={id} id={i} score={s} gen={g} time={t} pos=({x},{y})",
        "log.selection_desc_dead": "id={id} (dead; observation frozen)",
        "log.inspection_no_match": "[inspection] no match for criterion={criterion} lineage={lineage}",
        "log.inspection_observe": "[inspection] observing {desc}",
        "log.heal_all": "[heal] {n} critters restored to full HP",
        "log.metric_cycle": "[metric] {name}",
        "log.mut": "[mut] {v}%",
        "log.local_scale": "[local scale] {v}%",
        "log.zone_hp_effect": "[zone hp effect] {v}",
        "log.param_selected": "[param] {name} active (up/down to adjust)",
        "log.param_name.mutation": "mutation rate",
        "log.param_name.local_scale": "local scale",
        "log.param_name.zone_hp_effect": "zone HP effect",
        "log.speed": "[speed] {v} tick(s)/frame",
        "log.lang": "[lang] {v}",
        "log.load_not_found": "[load] {path} not found.",
        "log.load_legacy_fallback": "[load] {slot_path} not found; falling back to legacy {legacy}.",
        "log.save_slot": "[slot] {slot}",
        "log.load_corrupted": "[load] {path} corrupted or unreadable ({e}). Ignoring.",
        "log.load_invalid_dict": "[load] {path} does not contain a valid save dictionary.",
        "log.load_newer": "[load] save v{v} is newer than supported (v{cur}). Update the code or use another save.",
        "log.load_invalid_version": "[load] save with invalid version ({v}). Ignoring.",
        "log.load_incompatible": "[load] save v{v} is incompatible with v{cur}. Start a new run.",
        "log.load_arch_mismatch": "[load] save architecture={a!r} incompatible with architecture {cur!r}. Ignoring.",
        "log.load_genome_mismatch": "[load] save genome={g!r} incompatible with genome {cur!r}. Ignoring.",
        "log.load_zones_missing": "[load] zones missing from save; generated new ones.",
        "log.load_zones_shape_mismatch": "[load] zones mask has shape {saved}, but the current screen derives {current}. Save was made on a different resolution; reopen the game at that resolution or start a new run.",
        "log.load_empty_pool": "[load] empty pool for lineage {id}; ignoring.",
        "log.load_ok": "[load] {path} v{v} ({arch}/{gen}) loaded: tick={t} pools={p}",
        "log.save_ok": "[save] {path} v{v} ({arch}/{gen}) saved: pools={p} tick={t}",
        "log.save_metrics_ok": "[save] metrics exported: {path}",
        "log.save_metrics_fail": "[save] failed to export metrics ({e})",
        "log.tick_summary": "tick={t} lifetimes={lt} generations={g} pop={p} mut={m}% mode={modo} local={l}% global={gg}%@{gf}% genes={genes}",
        "log.print_state": "tick={t} lifetimes={lt} generations={g} pop={p} speed={s}x mut={m}% mode={modo} local={l}% global={gg}%@{gf}% genes={genes} environment={a} zones={z} metric={met} inspection={i} slot={slot}",
        # --- Recording logs ---
        "log.recording_start": "[recording] ON -> {path}  ({fps} fps, max {max} frames, scale {scale})",
        "log.recording_ok": "[recording] {path} saved: {n} frames @ {fps} fps ({kb} KB)",
        "log.recording_empty": "[recording] stopped with no frames captured.",
        "log.recording_full": "[recording] frame budget reached ({max}); stopping.",
        "log.recording_save_fail": "[recording] failed to write GIF ({e}).",
        "log.recording_no_pillow": "[recording] Pillow is not installed. Install it with: pip install Pillow",
    },
    "pt": {
        # --- HUD: global block ---
        "hud.tick_speed": "tick={tick}  speed={speed}x",
        "hud.births_deaths": "nasc={births}  mortes={deaths}",
        "hud.mutation": "mut={mut}%{mut_marker}  modo={mode}  local={local}%{local_marker}  global={gp}%@{gf}%",
        "hud.selection": "selection={crit}  L/E/I/R={w1}/{w2}/{w3}/{w4}",
        "hud.environment": "env={env}  {zones}",
        "hud.save_slot": "slot: {slot}",
        "hud.zones_none": "nenhum",
        "hud.zones_fmt": "{n}x r={r} ({bonus}hp)",
        "hud.zones_off_suffix": "{base} [off]",
        "hud.zones_damage": "PERIGO",
        "hud.zones_zkey": "  [Z]",
        "hud.metric_prefix": "métrica (M): {label}",
        "hud.inspection_prefix": "inspeção (i): {state}",
        "hud.on": "ON",
        "hud.off": "OFF",
        # --- HUD: controls block ---
        "hud.section_sim": "── simulação ─────────────────────────",
        "hud.controls_1": "SPACE pausa  = step  R recria  ESC sai",
        "hud.controls_2": "S salva  L carrega  N slot  P imprime",
        "hud.section_tune": "── ajuste ────────────────────────────",
        "hud.controls_3": "U mut  O local  E efeito HP zonas  depois ↑/↓",
        "hud.controls_4": ", . velocidade  Z zonas on/off",
        "hud.zone_hp_param": "efeito HP zonas={v}",
        "hud.repro_gates": "repro: idade>={age} hp<{hp} score>={score} enc>={enc}",
        "hud.active_marker": " ◄",
        "hud.section_analysis": "── análise ───────────────────────────",
        "hud.controls_5": "M métrica  I inspeção  clique observa",
        "hud.controls_6": "← → critério  Tab linhagem",
        "hud.controls_7": "Enter observa candidato  F11 tela cheia",
        "hud.controls_8": "H resetar hp  T idioma  G grava GIF",
        # --- Critérios de inspeção e filtro de linhagem ---
        "criterion.most_evolved": "mais evoluído",
        "criterion.oldest": "mais velho",
        "criterion.youngest": "mais novo",
        "criterion.most_offspring": "mais filhos",
        "criterion.most_encounters": "mais encontros",
        "criterion.most_explored": "mais explorou",
        "criterion.highest_hp": "maior hp",
        "criterion.lowest_hp": "menor hp",
        "criterion.highest_generation": "maior geração",
        "criterion.best_score": "melhor score",
        "lineage_filter.all": "todas",
        "lineage_filter.R": "R",
        "lineage_filter.G": "G",
        "lineage_filter.B": "B",
        "panel.discovery_title": "DESCOBERTA",
        "panel.observation_title": "OBSERVANDO",
        "panel.candidate_label": "candidato:",
        "panel.no_candidate": "nenhum candidato",
        "panel.enter_hint": "Enter = observar",
        "panel.hint_navigation": "←→ critério | Tab linhagem",
        "panel.hint_actions": "Enter observar | clique escolher | I sair",
        # --- HUD: recording indicator ---
        "hud.recording_on": "● GRAV",
        # --- HUD: lineage table column labels ---
        "col.id": "id",
        "col.hp": "hp",
        "col.lt": "temp",
        "col.gen": "ger",
        "col.pop": "pop",
        "col.score": "score",
        # --- Charts ---
        "chart.population_title": "população por linhagem",
        "chart.metric_title": "métrica: {label}  (M cicla)",
        "chart.x_axis": "tick",
        "chart.scalar_label": "valor",
        # --- Metric labels ---
        "metric.populacao": "população",
        "metric.hp_medio": "hp médio",
        "metric.maior_tempo_de_vida": "maior tempo de vida",
        "metric.geracao_maxima": "geração máxima",
        "metric.score_composto_medio": "score composto médio",
        "metric.taxa_de_mutacao": "taxa de mutação (%)",
        # --- RPS tip ---
        "rps.enemy": "  →  inimigo: ",
        "rps.ally": "  |  aliado: ",
        # --- Inspection panel ---
        "panel.title": "INSPEÇÃO",
        "panel.no_selection": "nenhum bicho observado",
        "panel.stale_selection": "bicho selecionado não existe mais",
        "panel.lineage": "linhagem:",
        "panel.id": "id:",
        "panel.status": "status:",
        "panel.status_alive": "VIVO",
        "panel.status_dead": "MORTO — tick {tick}",
        "panel.hp": "hp:",
        "panel.time": "tempo:",
        "panel.generation": "geração:",
        "panel.offspring": "filhos:",
        "panel.encounters": "encontros:",
        "panel.score": "score:",
        "panel.last_action": "última ação:",
        "panel.position": "posição:",
        "panel.vision_title": "visão 11x11 (centro {x},{y})",
        # --- Heatmaps ---
        "heatmap.w1": "W1 (entrada->oculta1)",
        "heatmap.w2": "W2 (oculta1->oculta2)",
        "heatmap.w3": "W3 (oculta2->saida)",
        "heatmap.b1": "b1 (vieses oculta1)",
        "heatmap.b2": "b2 (vieses oculta2)",
        "heatmap.r": "R (recorrência)",
        # --- Console logs ---
        "log.recreate": "[recreate] população reiniciada, tick=0",
        "log.inspection_on": "[inspecao] ON — {desc}",
        "log.inspection_on_empty": "[inspecao] ON (nenhum agente vivo)",
        "log.inspection_on_auto": "[inspecao] ON — auto-selecionado {desc}",
        "log.inspection_off": "[inspecao] OFF",
        "log.inspection_select": "[inspecao] {desc}",
        "log.inspection_miss": "[inspecao] ninguém em ({x},{y}) raio={r}",
        "log.load_lineage_count": "[load] save tem {saved} linhagens, esperado {expected}.",
        "log.load_lineage_shape": "[load] linhagem {id}: pool={pool} agents={agents} ids={ids} (esperado {expected}).",
        "log.stale_selection": "(seleção obsoleta)",
        "log.selection_desc": "linhagem={id} id={i} score={s} ger={g} tempo={t} pos=({x},{y})",
        "log.selection_desc_dead": "id={id} (morto; observacao congelada)",
        "log.inspection_no_match": "[inspecao] sem correspondencia para criterio={criterion} linhagem={lineage}",
        "log.inspection_observe": "[inspecao] observando {desc}",
        "log.heal_all": "[cura] {n} bichos restaurados ao HP cheio",
        "log.metric_cycle": "[metrica] {name}",
        "log.mut": "[mut] {v}%",
        "log.local_scale": "[escala local] {v}%",
        "log.zone_hp_effect": "[efeito HP das zonas] {v}",
        "log.param_selected": "[param] {name} ativo (↑/↓ para ajustar)",
        "log.param_name.mutation": "taxa de mutacao",
        "log.param_name.local_scale": "escala local",
        "log.param_name.zone_hp_effect": "efeito HP das zonas",
        "log.speed": "[speed] {v} tick(s)/frame",
        "log.lang": "[idioma] {v}",
        "log.load_not_found": "[load] {path} não encontrado.",
        "log.load_legacy_fallback": "[load] {slot_path} não encontrado; usando o legado {legacy}.",
        "log.save_slot": "[slot] {slot}",
        "log.load_corrupted": "[load] {path} corrompido ou ilegível ({e}). Ignorando.",
        "log.load_invalid_dict": "[load] {path} não contém um dicionário de save válido.",
        "log.load_newer": "[load] save v{v} é mais novo que o suportado (v{cur}). Atualize o código ou use outro save.",
        "log.load_invalid_version": "[load] save com versão inválida ({v}). Ignorando.",
        "log.load_incompatible": "[load] save v{v} é incompatível com v{cur}. Recomece uma run nova.",
        "log.load_arch_mismatch": "[load] save arquitetura={a!r} incompatível com arquitetura {cur!r}. Ignorando.",
        "log.load_genome_mismatch": "[load] save genoma={g!r} incompatível com genoma {cur!r}. Ignorando.",
        "log.load_zones_missing": "[load] zonas ausentes no save; geradas novas.",
        "log.load_zones_shape_mismatch": "[load] mascara de zonas tem shape {saved}, mas a tela atual deriva {current}. O save foi feito em outra resolucao; reabra o jogo naquela resolucao ou comece uma run nova.",
        "log.load_empty_pool": "[load] pool vazio para linhagem {id}; ignorando.",
        "log.load_ok": "[load] {path} v{v} ({arch}/{gen}) carregado: tick={t} pops={p}",
        "log.save_ok": "[save] {path} v{v} ({arch}/{gen}) salvo: pops={p} tick={t}",
        "log.save_metrics_ok": "[save] métricas exportadas: {path}",
        "log.save_metrics_fail": "[save] falha ao exportar métricas ({e})",
        "log.tick_summary": "tick={t} lifetimes={lt} geracoes={g} pop={p} mut={m}% modo={modo} local={l}% global={gg}%@{gf}% genes={genes}",
        "log.print_state": "tick={t} lifetimes={lt} geracoes={g} pop={p} speed={s}x mut={m}% modo={modo} local={l}% global={gg}%@{gf}% genes={genes} ambiente={a} zonas={z} metrica={met} inspecao={i} slot={slot}",
        # --- Recording logs ---
        "log.recording_start": "[gravacao] ON -> {path}  ({fps} fps, max {max} frames, escala {scale})",
        "log.recording_ok": "[gravacao] {path} salvo: {n} frames @ {fps} fps ({kb} KB)",
        "log.recording_empty": "[gravacao] parada sem frames capturados.",
        "log.recording_full": "[gravacao] limite de frames atingido ({max}); parando.",
        "log.recording_save_fail": "[gravacao] falha ao escrever o GIF ({e}).",
        "log.recording_no_pillow": "[gravacao] Pillow nao esta instalado. Instale com: pip install Pillow",
    },
}

DEFAULT_LANGUAGE = "en"
AVAILABLE_LANGUAGES = tuple(TRANSLATIONS.keys())


def t(key: str, **kwargs) -> str:
    """Traduz uma chave para o idioma atual.

    Cai para o idioma default se a chave faltar no idioma atual e
    para a propria chave se faltar em todos. `kwargs` sao
    interpolados com str.format().
    """
    lang = getattr(state, "language", DEFAULT_LANGUAGE)
    if lang not in TRANSLATIONS:
        lang = DEFAULT_LANGUAGE
    table = TRANSLATIONS[lang]
    template = table.get(key) or TRANSLATIONS[DEFAULT_LANGUAGE].get(key) or key
    if kwargs:
        return template.format(**kwargs)
    return template


def cycle_language() -> str:
    """Avança para o proximo idioma disponivel e retorna o codigo."""
    lang = getattr(state, "language", DEFAULT_LANGUAGE)
    if lang not in AVAILABLE_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    idx = AVAILABLE_LANGUAGES.index(lang)
    new_lang = AVAILABLE_LANGUAGES[(idx + 1) % len(AVAILABLE_LANGUAGES)]
    state.language = new_lang
    return new_lang
