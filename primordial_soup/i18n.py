# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Internacionalizacao para todas as strings visiveis ao usuario.

Chaves canonicas sao neutras de idioma (ex: "hud.tick_speed").
Valores sao por idioma. Ingles e o default e o fallback.

NAO traduzido aqui (deliberado):
  - Identificadores canonicos de persistencia, que podem ter grafias
    historicas em portugues ou ingles (ver persistence.py).
  - Cabecalhos do CSV e chaves de metrica (identificadores canonicos;
    ver config.py).
  - IDs de linhagem "R", "G", "B" (identificadores, nao exibicao).
  - Nomes de coluna do agente / constantes de indice (internos).
  - Nomes de arquivo e templates de slot definidos pela camada de persistencia.

Valores canonicos de config NAO sao alterados nem localizados
internamente. Quando um valor canonico e exibido ao usuario, a
camada de apresentacao pode mapea-lo para uma representacao
localizada (ver hud.value.mutation_mode.* e hud.value.environment.*).
A distincao e:

    canonical value != display value

Nunca:

    mutation_mode = "duas_escalas"  # valor localizado, nao canonico

apenas porque a interface esta em portugues.

O idioma de exibicao e preferencia do usuario. NAO e parte do estado
da simulacao e NAO e resetado por state.reset_counters().
"""

from __future__ import annotations

from . import state
from .config_schema import get_field_spec

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # --- HUD: global block ---
        "hud.on": "ON",
        "hud.off": "OFF",
        # --- Command Dock ---
        "command.group.simulation": "SIM",
        "command.group.panels": "PANELS",
        "command.group.navigation": "NAV",
        "command.group.quick": "QUICK",

        "command.pause": "pause",
        "command.step": "step",
        "command.new_world": "new",
        "command.fullscreen": "fullscreen",
        "command.back_quit": "back/quit",

        "command.inspect": "inspect",
        "command.configuration": "config",
        "command.metrics": "metrics",
        "command.session": "session",
        "command.tools": "tools",

        "command.select": "select",
        "command.change": "change",
        "command.panel": "panel",
        "command.activate": "activate",
        "command.observe": "observe",

        "command.hide_hud": "hide HUD",
        "command.save": "save",
        "command.load": "load",
        "command.slot": "slot",
        "command.zones": "zones",
        "command.record": "record",
        # --- Telemetry HUD: labels atomicos ---
        "hud.label.tick": "TICK",
        "hud.label.speed": "SPEED",
        "hud.label.zoom": "ZOOM",
        "hud.label.births": "BIRTHS",
        "hud.label.deaths": "DEATHS",
        "hud.label.slot": "SLOT",
        "hud.label.mutation": "MUT",
        "hud.label.mode": "MODE",
        "hud.label.local": "LOCAL",
        "hud.label.global": "GLOBAL",
        "hud.label.environment": "ENV",
        "hud.label.zones": "ZONES",
        "hud.label.zone_hp": "ZONE HP",
        "hud.label.reproduction": "REPRO",
        "hud.label.weights": "WEIGHTS",
        "hud.value.mutation_mode.surgical": "surgical",
        "hud.value.mutation_mode.two_scales": "two scales",
        "hud.value.environment.zonas": "zones",
        "hud.value.reproduction_criterion.composite": "CMP",
        "hud.value.reproduction_criterion.longevity": "LONG",
        "hud.reproduction_gates":
            "age>={age} hp<{hp} score>={score:.2f} enc>={enc}",
        "hud.zone_summary_on": "{n}x r={r} ON",
        "hud.zone_summary_off": "{n}x r={r} OFF",
        "hud.zone_summary_none": "none",
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
        # --- Notificacoes transitorias (sidebar footer) ---
        "notice.save_ok": "Game saved — slot {slot}",
        "notice.save_fail": "Save failed — slot {slot}",
        "notice.load_ok": "Game loaded — slot {slot}",
        "notice.load_fail": "Load failed — slot {slot}",
        "notice.no_candidate": "No candidate for current filter",
        # --- Modal de confirmacao de saida ---
        "modal.exit.title": "Leave the simulation?",
        "modal.exit.confirm": "Enter   Exit",
        "modal.exit.cancel": "Esc     Cancel",
        # --- Panel titles ---
        "panel.inspection.title": "INSPECTION",
        "panel.configuration.title": "CONFIGURATION",
        "panel.metrics.title": "METRICS",
        "panel.session.title": "SESSION",
        "panel.tools.title": "TOOLS",
        # --- Panel items ---
        "panel.configuration.genetics": "GENETICS",
        "panel.configuration.ecology": "ECOLOGY",
        "panel.configuration.reproduction": "REPRODUCTION",
        "panel.configuration.selection": "SELECTION",
        "item.reproduction_interval": "Reproduction interval",
        "item.reproduction_min_age": "Minimum age",
        "item.reproduction_hp_gate": "HP gate",
        "item.reproduction_min_encounters": "Minimum encounters",
        "item.reproduction_parent_hp_bonus": "Parent HP reward",
        "item.reproduction_criterion": "Selection criterion",
        "item.reproduction_pool_fraction": "Parent pool",
        "item.reproduction_attempts_divisor": "Attempts divisor",
        "item.reproduction_min_score": "Minimum score",
        "item.longevity_weight": "Longevity weight",
        "item.exploration_weight": "Exploration weight",
        "item.interaction_weight": "Interaction weight",
        "item.reproduction_weight": "Reproduction weight",
        "reproduction_criterion.composite": "composite",
        "reproduction_criterion.longevity": "longevity",
        "item.criterion": "Criterion",
        "item.base_decay": "Base decay",
        "item.low_hp_threshold": "Low-HP threshold",
        "item.death_hp_threshold": "Death threshold",
        "item.predation_transfer": "Predation transfer",
        "item.overcrowding_factor": "Overcrowding factor",
        "item.lineage_filter": "Lineage filter",
        "item.discovery_candidate": "Candidate",
        "item.clear_observation": "Clear observation",
        "item.speed": "Simulation speed",
        "item.crossover_mode": "Crossover mode",
        "item.crossover_probability": "Crossover probability",
        "item.block_size": "Block size",
        "item.mutation_mode": "Mutation mode",
        "crossover_mode.blocks": "blocks",
        "crossover_mode.uniform": "uniform",
        "crossover_mode.two_points": "two points",
        "item.mutation_rate": "Mutation rate",
        "item.local_scale": "Local mutation scale",
        "item.local_scale_sigma": "Local sigma",
        "item.global_probability": "Global probability",
        "item.global_scale_fraction": "Global mutation scale",
        "item.global_scale_sigma": "Global sigma",
        "item.stay_still_impulse": "Stay-still impulse",
        "item.zones": "Environmental zones",
        "item.zone_hp_effect": "Zone HP effect",
        "item.heal_all": "Heal all critters",
        "item.save_slot": "Save slot",
        "item.save": "Save now",
        "item.load": "Load",
        "item.new_world": "New world",
        "item.language": "Language",
        "item.music": "Music",
        "item.sfx": "Sound effects",
        "item.recording": "Recording",
        "item.print_state": "Print state",
        # --- Footers ---
        "footer.inspection": "↑↓ navigate | ←→ change | Enter observe | Tab panel | Esc world",
        "footer.configuration": "↑↓ navigate | ←→ change | Tab panel | Enter activate | Esc world",
        "footer.metrics": "Wheel scroll | Tab panel | Esc world",
        "footer.session": "↑↓ navigate | ←→ change | Tab panel | Enter activate | Esc world",
        "footer.tools": "↑↓ navigate | ←→ change | Tab panel | Enter activate | Esc world",
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
        "chart.metric_title": "{label}",
        "chart.x_axis": "tick",
        "chart.scalar_label": "value",
        # --- Metric labels (keys are canonical PT) ---
        "metric.populacao": "population",
        "metric.hp_medio": "average hp",
        "metric.maior_tempo_de_vida": "longest lifetime",
        "metric.geracao_maxima": "max generation",
        "metric.score_composto_medio": "average composite score",
        "metric.taxa_de_mutacao": "mutation rate (%)",
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
        "panel.vision_unavailable_dead": "vision unavailable after death",
        # --- Heatmaps ---
        "heatmap.w1": "W1 (input->hidden1)",
        "heatmap.w2": "W2 (hidden1->hidden2)",
        "heatmap.w3": "W3 (hidden2->output)",
        "heatmap.b1": "b1 (hidden1 biases)",
        "heatmap.b2": "b2 (hidden2 biases)",
        "heatmap.r": "R (recurrence)",
        # --- Console logs ---
        "log.recreate": "[recreate] population reset, tick=0",
        "log.load_lineage_count": "[load] save has {saved} lineages, expected {expected}.",
        "log.load_lineage_shape": "[load] lineage {id}: pool={pool} agents={agents} ids={ids} (expected {expected}).",
        "log.inspection_no_match": "[inspection] no match for criterion={criterion} lineage={lineage}",
        "log.inspection_observe": "[inspection] observing {desc}",
        "log.heal_all": "[heal] {n} critters restored to full HP",
        "log.lang": "[lang] {v}",
        "log.load_not_found": "[load] {path} not found.",
        "log.save_slot": "[slot] {slot}",
        "log.load_corrupted": "[load] {path} corrupted or unreadable ({e}). Ignoring.",
        "log.load_invalid_dict": "[load] {path} does not contain a valid save dictionary.",
        "log.load_newer": "[load] save v{v} is newer than supported (v{cur}). Update the code or use another save.",
        "log.load_invalid_version": "[load] save with invalid version ({v}). Ignoring.",
        "log.load_incompatible": "[load] save v{v} is incompatible with v{cur}. Start a new run.",
        "log.load_arch_mismatch": "[load] save architecture={a!r} incompatible with architecture {cur!r}. Ignoring.",
        "log.load_genome_mismatch": "[load] save genome={g!r} incompatible with genome {cur!r}. Ignoring.",
        "log.load_zones_shape_mismatch": "[load] zones mask has shape {saved}, but the current screen derives {current}. Save was made on a different resolution; reopen the game at that resolution or start a new run.",
        "log.load_empty_pool": "[load] empty pool for lineage {id}; ignoring.",
        "log.load_ok": "[load] {path} v{v} ({arch}/{gen}) loaded: tick={t} pools={p}",
        "log.save_ok": "[save] {path} v{v} ({arch}/{gen}) saved: pools={p} tick={t}",
        "log.save_metrics_ok": "[save] metrics exported: {path}",
        "log.save_metrics_fail": "[save] failed to export metrics ({e})",
        "log.tick_summary": "tick={t} lifetimes={lt} generations={g} pop={p} mut={m}% mode={modo} local={l}% global={gg}%@{gf}% genes={genes}",
        "log.print_state": "tick={t} lifetimes={lt} generations={g} pop={p} speed={s}x mut={m}% mode={modo} local={l}% global={gg}%@{gf}% genes={genes} environment={a} zones={z} slot={slot}",
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
        "hud.on": "ON",
        "hud.off": "OFF",
        # --- Command Dock ---
        "command.group.simulation": "SIM",
        "command.group.panels": "PAINÉIS",
        "command.group.navigation": "NAV",
        "command.group.quick": "RÁPIDAS",

        "command.pause": "pausa",
        "command.step": "step",
        "command.new_world": "novo",
        "command.fullscreen": "tela cheia",
        "command.back_quit": "volta/sai",

        "command.inspect": "inspeção",
        "command.configuration": "config",
        "command.metrics": "métricas",
        "command.session": "sessão",
        "command.tools": "ferramentas",

        "command.select": "seleciona",
        "command.change": "altera",
        "command.panel": "painel",
        "command.activate": "ativa",
        "command.observe": "observa",

        "command.hide_hud": "ocultar HUD",
        "command.save": "salva",
        "command.load": "carrega",
        "command.slot": "slot",
        "command.zones": "zonas",
        "command.record": "grava",
        # --- Telemetry HUD: labels atomicos ---
        "hud.label.tick": "PASSO",
        "hud.label.speed": "VEL",
        "hud.label.zoom": "ZOOM",
        "hud.label.births": "NASC",
        "hud.label.deaths": "MORTES",
        "hud.label.slot": "SALV.",
        "hud.label.mutation": "MUT",
        "hud.label.mode": "MODO",
        "hud.label.local": "LOCAL",
        "hud.label.global": "GLOBAL",
        "hud.label.environment": "AMB",
        "hud.label.zones": "ZONAS",
        "hud.label.zone_hp": "HP ZONA",
        "hud.label.reproduction": "REPRO",
        "hud.label.weights": "PESOS",
        "hud.value.mutation_mode.surgical": "cirurgica",
        "hud.value.mutation_mode.two_scales": "duas escalas",
        "hud.value.environment.zonas": "zonas",
        "hud.value.reproduction_criterion.composite": "CMP",
        "hud.value.reproduction_criterion.longevity": "LONG",
        "hud.reproduction_gates":
            "idade>={age} hp<{hp} pont>={score:.2f} enc>={enc}",
        "hud.zone_summary_on": "{n}x r={r} ATIVAS",
        "hud.zone_summary_off": "{n}x r={r} INATIVAS",
        "hud.zone_summary_none": "nenhuma",
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
        # --- Notificacoes transitorias ---
        "notice.save_ok": "Jogo salvo — slot {slot}",
        "notice.save_fail": "Falha ao salvar — slot {slot}",
        "notice.load_ok": "Jogo carregado — slot {slot}",
        "notice.load_fail": "Falha ao carregar — slot {slot}",
        "notice.no_candidate": "Nenhum candidato para o filtro atual",
        # --- Modal de confirmacao de saida ---
        "modal.exit.title": "Sair da simulação?",
        "modal.exit.confirm": "Enter   Sair",
        "modal.exit.cancel": "Esc     Cancelar",
        # --- Titulos dos Paineis ---
        "panel.inspection.title": "INSPEÇÃO",
        "panel.configuration.title": "CONFIGURAÇÃO",
        "panel.metrics.title": "MÉTRICAS",
        "panel.session.title": "SESSÃO",
        "panel.tools.title": "FERRAMENTAS",
        # --- Itens dos Paineis ---
        "panel.configuration.genetics": "GENÉTICA",
        "panel.configuration.ecology": "ECOLOGIA",
        "panel.configuration.reproduction": "REPRODUÇÃO",
        "panel.configuration.selection": "SELEÇÃO",
        "item.reproduction_interval": "Intervalo reprodutivo",
        "item.reproduction_min_age": "Idade mínima",
        "item.reproduction_hp_gate": "Gate de HP",
        "item.reproduction_min_encounters": "Encontros mínimos",
        "item.reproduction_parent_hp_bonus": "Recompensa de HP dos pais",
        "item.reproduction_criterion": "Critério de seleção",
        "item.reproduction_pool_fraction": "Pool de pais",
        "item.reproduction_attempts_divisor": "Divisor de tentativas",
        "item.reproduction_min_score": "Score mínimo",
        "item.longevity_weight": "Peso de longevidade",
        "item.exploration_weight": "Peso de exploração",
        "item.interaction_weight": "Peso de interação",
        "item.reproduction_weight": "Peso de reprodução",
        "reproduction_criterion.composite": "composto",
        "reproduction_criterion.longevity": "longevidade",
        "item.criterion": "Critério",
        "item.base_decay": "Decaimento basal",
        "item.low_hp_threshold": "Limite de HP baixo",
        "item.death_hp_threshold": "Limite de morte",
        "item.predation_transfer": "Transferência por predação",
        "item.overcrowding_factor": "Fator de superlotação",
        "item.lineage_filter": "Filtro de linhagem",
        "item.discovery_candidate": "Candidato",
        "item.clear_observation": "Limpar observação",
        "item.speed": "Velocidade da simulação",
        "item.crossover_mode": "Modo de crossover",
        "item.crossover_probability": "Probabilidade de crossover",
        "item.block_size": "Tamanho do bloco",
        "item.mutation_mode": "Modo de mutação",
        "crossover_mode.blocks": "blocos",
        "crossover_mode.uniform": "uniforme",
        "crossover_mode.two_points": "dois pontos",
        "item.mutation_rate": "Taxa de mutação",
        "item.local_scale": "Escala local de mutação",
        "item.local_scale_sigma": "Sigma local",
        "item.global_probability": "Probabilidade global",
        "item.global_scale_fraction": "Escala global de mutação",
        "item.global_scale_sigma": "Sigma global",
        "item.stay_still_impulse": "Impulso para ficar parado",
        "item.zones": "Zonas ambientais",
        "item.zone_hp_effect": "Efeito de HP das zonas",
        "item.heal_all": "Curar todos os bichos",
        "item.save_slot": "Slot de save",
        "item.save": "Salvar agora",
        "item.load": "Carregar",
        "item.new_world": "Novo mundo",
        "item.language": "Idioma",
        "item.music": "Música",
        "item.sfx": "Efeitos sonoros",
        "item.recording": "Gravação",
        "item.print_state": "Imprimir estado",
        # --- Rodapes ---
        "footer.inspection": "↑↓ navega | ←→ altera | Enter observar | Tab painel | Esc mundo",
        "footer.configuration": "↑↓ navega | ←→ altera | Tab painel | Enter ativa | Esc mundo",
        "footer.metrics": "Wheel scroll | Tab painel | Esc mundo",
        "footer.session": "↑↓ navega | ←→ altera | Tab painel | Enter ativa | Esc mundo",
        "footer.tools": "↑↓ navega | ←→ altera | Tab painel | Enter ativa | Esc mundo",
        # --- HUD: recording indicator ---
        "hud.recording_on": "● GRAV",
        # --- HUD: lineage table column labels ---
        "col.id": "id",
        "col.hp": "hp",
        "col.lt": "temp",
        "col.gen": "ger",
        "col.pop": "pop",
        "col.score": "pont",
        # --- Charts ---
        "chart.population_title": "população por linhagem",
        "chart.metric_title": "{label}",
        "chart.x_axis": "tick",
        "chart.scalar_label": "valor",
        # --- Metric labels ---
        "metric.populacao": "população",
        "metric.hp_medio": "hp médio",
        "metric.maior_tempo_de_vida": "maior tempo de vida",
        "metric.geracao_maxima": "geração máxima",
        "metric.score_composto_medio": "score composto médio",
        "metric.taxa_de_mutacao": "taxa de mutação (%)",
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
        "panel.vision_unavailable_dead": "visão indisponível após a morte",
        # --- Heatmaps ---
        "heatmap.w1": "W1 (entrada->oculta1)",
        "heatmap.w2": "W2 (oculta1->oculta2)",
        "heatmap.w3": "W3 (oculta2->saida)",
        "heatmap.b1": "b1 (vieses oculta1)",
        "heatmap.b2": "b2 (vieses oculta2)",
        "heatmap.r": "R (recorrência)",
        # --- Console logs ---
        "log.recreate": "[recreate] população reiniciada, tick=0",
        "log.load_lineage_count": "[load] save tem {saved} linhagens, esperado {expected}.",
        "log.load_lineage_shape": "[load] linhagem {id}: pool={pool} agents={agents} ids={ids} (esperado {expected}).",
        "log.inspection_no_match": "[inspecao] sem correspondencia para criterio={criterion} linhagem={lineage}",
        "log.inspection_observe": "[inspecao] observando {desc}",
        "log.heal_all": "[cura] {n} bichos restaurados ao HP cheio",
        "log.lang": "[idioma] {v}",
        "log.load_not_found": "[load] {path} não encontrado.",
        "log.save_slot": "[slot] {slot}",
        "log.load_corrupted": "[load] {path} corrompido ou ilegível ({e}). Ignorando.",
        "log.load_invalid_dict": "[load] {path} não contém um dicionário de save válido.",
        "log.load_newer": "[load] save v{v} é mais novo que o suportado (v{cur}). Atualize o código ou use outro save.",
        "log.load_invalid_version": "[load] save com versão inválida ({v}). Ignorando.",
        "log.load_incompatible": "[load] save v{v} é incompatível com v{cur}. Recomece uma run nova.",
        "log.load_arch_mismatch": "[load] save arquitetura={a!r} incompatível com arquitetura {cur!r}. Ignorando.",
        "log.load_genome_mismatch": "[load] save genoma={g!r} incompatível com genoma {cur!r}. Ignorando.",
        "log.load_zones_shape_mismatch": "[load] mascara de zonas tem shape {saved}, mas a tela atual deriva {current}. O save foi feito em outra resolucao; reabra o jogo naquela resolucao ou comece uma run nova.",
        "log.load_empty_pool": "[load] pool vazio para linhagem {id}; ignorando.",
        "log.load_ok": "[load] {path} v{v} ({arch}/{gen}) carregado: tick={t} pops={p}",
        "log.save_ok": "[save] {path} v{v} ({arch}/{gen}) salvo: pops={p} tick={t}",
        "log.save_metrics_ok": "[save] métricas exportadas: {path}",
        "log.save_metrics_fail": "[save] falha ao exportar métricas ({e})",
        "log.tick_summary": "tick={t} lifetimes={lt} geracoes={g} pop={p} mut={m}% modo={modo} local={l}% global={gg}%@{gf}% genes={genes}",
        "log.print_state": "tick={t} lifetimes={lt} geracoes={g} pop={p} speed={s}x mut={m}% modo={modo} local={l}% global={gg}%@{gf}% genes={genes} ambiente={a} zonas={z} slot={slot}",
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
_LANGUAGE_CHOICES = get_field_spec("DEFAULT_LANGUAGE").constraints.choices
if not isinstance(_LANGUAGE_CHOICES, tuple):
    raise RuntimeError("DEFAULT_LANGUAGE deve declarar choices estaticos no schema.")
AVAILABLE_LANGUAGES = _LANGUAGE_CHOICES
if set(TRANSLATIONS) != set(AVAILABLE_LANGUAGES):
    raise RuntimeError(
        "TRANSLATIONS deve cobrir exatamente os idiomas declarados no schema."
    )


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