# SPDX-License-Identifier: MIT
# Copyright (c) 2026 exfoca

"""Backend grafico de reproducao sonora.

Unico owner de pygame.mixer, dos arquivos WAV, dos volumes, dos
cooldowns internos e do estado transitorio da musica. Consumidores
falam em eventos semanticos (FeedbackEvent) e em estado da aplicacao
(sync_music running=True/False), nunca em comandos concretos do
mixer.

Contrato de import: pygame NAO e importado no nivel do modulo. A
simples execucao de `import primordial_soup.audio` nao pode carregar
pygame, inicializar o mixer nem abrir dispositivo de audio. O import
acontece exclusivamente dentro de init().

Contrato de bloqueio: durante a execucao normal nao existe
espera, polling, thread ou fila. Se nao houver capacidade de
reproduzir um som, o som e descartado.

A unica excecao deliberada e play_shutdown_sound(), executada
somente depois que Flow.EXIT ja foi decidido. Quando quit_game.wav
inicia com sucesso, essa funcao aguarda 1.5 s antes do teardown do
mixer.

Contrato de falha: falha do mixer desabilita o backend inteiro.
Falha de um WAV individual desabilita apenas aquele recurso. Falha de
game.wav desabilita apenas a musica.
"""

from __future__ import annotations

import os
import time
from typing import Any

from . import config as cfg
from .feedback import FeedbackEvent


# ---------------------------------------------------------------------------
# Estado privado do backend
# ---------------------------------------------------------------------------

_pygame: Any | None = None

_initialized = False
_disabled = False

_sounds: dict[str, Any] = {}
_last_played_at: dict[str, float] = {}

_music_enabled = (
    cfg.CONFIG_SNAPSHOT.operator.default_music_enabled
)
_sfx_enabled = (
    cfg.CONFIG_SNAPSHOT.operator.default_sfx_enabled
)

_music_available = False
_music_started = False
_music_paused = False
_music_warning_emitted = False


# ---------------------------------------------------------------------------
# Assets e mapeamento semantico
# ---------------------------------------------------------------------------

_SOUND_FILES: dict[str, str] = {
    "birth": "birth.wav",
    "generate_world": "generate_world.wav",
    "menu_move": "menu_1.wav",
    "menu_change": "menu_2.wav",
    "quit": "quit_game.wav",
}

_EVENT_TO_SOUND: dict[FeedbackEvent, str] = {
    FeedbackEvent.BIRTH_ACTIVITY: "birth",
    FeedbackEvent.WORLD_GENERATED: "generate_world",
    FeedbackEvent.MENU_MOVE: "menu_move",
    FeedbackEvent.MENU_CHANGE: "menu_change",
    FeedbackEvent.SAVE_OK: "menu_change",
    FeedbackEvent.LOAD_OK: "menu_change",
}

# Cooldowns internos. Tuning do backend, nao configuracao do universo.
_SFX_COOLDOWN_SECONDS: dict[str, float] = {
    "birth": 0.125,
    "generate_world": 0.0,
    "menu_move": 0.025,
    "menu_change": 0.025,
}

# Unica espera deliberada do subsistema: aplicada em
# play_shutdown_sound() somente quando quit_game.wav inicia com
# sucesso. Fixa por decisao; nao configuravel.
_SHUTDOWN_SOUND_DELAY_SECONDS = 1.5


def _sounds_dir() -> str:
    """Diretorio canonico dos assets de audio, relativo ao pacote."""
    return os.path.join(os.path.dirname(__file__), "sounds")


def _disable_backend(reason: Exception) -> None:
    """Desabilita o backend de audio apos falha irrecuperavel.

    Imprime um unico aviso. Nao tenta reabilitar dentro da mesma
    sessao. Chame no maximo uma vez por sessao para evitar repeticao
    de log.
    """
    global _disabled, _initialized
    _disabled = True
    _initialized = False
    print(f"[audio] disabled: {reason!r}")


def _disable_music(reason: Exception) -> None:
    """Desabilita apenas a musica, mantendo SFX operacionais.

    Imprime um unico aviso por sessao.
    """
    global _music_available, _music_started, _music_paused
    global _music_warning_emitted
    _music_available = False
    _music_started = False
    _music_paused = False
    if not _music_warning_emitted:
        _music_warning_emitted = True
        print(f"[audio] music disabled: {reason!r}")


def _mixer_available() -> bool:
    """Retorna True se o backend esta utilizavel agora.

    Valida _initialized, _disabled, _pygame e pygame.mixer.get_init().
    Se o mixer desapareceu apos a inicializacao, desabilita o backend
    e retorna False. Nunca tenta recuperar automaticamente.
    """
    if not _initialized or _disabled or _pygame is None:
        return False
    try:
        if _pygame.mixer.get_init() is None:
            _disable_backend(RuntimeError("mixer became unavailable"))
            return False
    except Exception as exc:
        _disable_backend(exc)
        return False
    return True


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def init() -> bool:
    """Inicializa o backend de audio.

    Idempotente: se ja inicializado, retorna True sem recarregar.
    Se uma tentativa anterior falhou e _disabled e True, retorna
    False sem retry.

    Retorna True se o mixer esta operacional, mesmo que assets
    individuais estejam ausentes. O significado de True e "backend
    de mixer disponivel", nao "todos os WAVs carregaram".
    """
    global _pygame, _initialized

    if _initialized and not _disabled:
        return True
    if _disabled:
        return False

    try:
        import pygame  # import lazy, unico ponto permitido
    except Exception as exc:
        _disable_backend(exc)
        return False

    _pygame = pygame

    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init()
    except Exception as exc:
        _disable_backend(exc)
        return False

    _initialized = True

    _load_sfx()
    _load_music()

    return True


def _load_sfx() -> None:
    """Carrega os SFX reconhecidos. Falha individual nao impede
    os outros nem desabilita o backend.
    """
    global _pygame
    assert _pygame is not None

    for sound_id, filename in _SOUND_FILES.items():
        path = os.path.join(_sounds_dir(), filename)
        try:
            sound = _pygame.mixer.Sound(path)
            sound.set_volume(cfg.SOUND_VOLUME_SFX)
        except Exception as exc:
            print(f"[audio] failed to load {path}: {exc!r}")
            continue
        _sounds[sound_id] = sound


def _load_music() -> None:
    """Carrega game.wav sem iniciar reproducao.

    O boot da aplicacao deve permanecer silencioso; sync_music() e
    quem inicia a musica, por transicao.
    """
    global _pygame, _music_available
    assert _pygame is not None

    music_path = os.path.join(_sounds_dir(), "game.wav")
    try:
        _pygame.mixer.music.load(music_path)
        _pygame.mixer.music.set_volume(cfg.SOUND_VOLUME_MUSIC)
    except Exception as exc:
        _music_available = False
        print(f"[audio] music unavailable: {exc!r}")
        return
    _music_available = True


def _play_sfx(sound_id: str) -> None:
    """Reproduz um SFX respeitando cooldown e politica de descarte.

    Fluxo obrigatorio:
        SFX desabilitado?    sim -> return
        backend disponivel?  nao -> return
        sound_id existe?     nao -> return
        cooldown ativo?      sim -> return
        find_channel(None)         -> return (descarte)
        channel.play(sound)  ok    -> registra monotonic()
        channel.play falha         -> desabilita backend
    """
    global _pygame
    if not _sfx_enabled:
        return
    if not _mixer_available() or _pygame is None:
        return

    sound = _sounds.get(sound_id)
    if sound is None:
        return

    cooldown = _SFX_COOLDOWN_SECONDS.get(sound_id, 0.0)
    now = time.monotonic()
    last = _last_played_at.get(sound_id)
    if last is not None and cooldown > 0.0 and (now - last) < cooldown:
        return

    try:
        channel = _pygame.mixer.find_channel(force=False)
        if channel is None:
            return
        channel.play(sound)
    except Exception as exc:
        _disable_backend(exc)
        return

    _last_played_at[sound_id] = time.monotonic()


def handle_feedback(event: FeedbackEvent) -> None:
    """Traduz um FeedbackEvent em SFX.

    Nao altera state, nao conta births, nao salva, nao carrega, nao
    gera mundo. Somente traducao semantica.
    """
    sound_id = _EVENT_TO_SOUND.get(event)
    if sound_id is None:
        return
    _play_sfx(sound_id)


def set_sfx_enabled(enabled: bool) -> None:
    """Liga/desliga SFX. Nao afeta a musica.

    Desabilitar interrompe SFX atualmente em execucao (best-effort).
    Habilitar nao emite confirmacao nem recarrega assets: proximos
    eventos voltam a tocar.
    """
    global _sfx_enabled
    enabled = bool(enabled)
    if enabled == _sfx_enabled:
        return
    _sfx_enabled = enabled
    if enabled:
        return
    # Desabilitado: silenciar canais SFX. music NAO e tocada por stop().
    if not _mixer_available() or _pygame is None:
        return
    try:
        _pygame.mixer.stop()
    except Exception:
        # Best-effort: silenciar falhou, mas _sfx_enabled ja e False.
        # Nao derruba o backend de musica nem a aplicacao.
        pass


def set_music_enabled(enabled: bool) -> None:
    """Liga/desliga musica. Nao afeta SFX.

    Music OFF pausa a musica imediatamente. Music ON apenas atualiza o
    flag: o start/resume fica a cargo de sync_music(), que combina
    esta preferencia com state.paused via chamada do loop grafico.
    """
    global _music_enabled, _music_paused
    enabled = bool(enabled)
    if enabled == _music_enabled:
        return
    _music_enabled = enabled
    if enabled:
        return
    # Desabilitado: pausar a musica (permite retomada do ponto).
    if not _mixer_available() or _pygame is None:
        return
    if not _music_available or not _music_started or _music_paused:
        return
    try:
        _pygame.mixer.music.pause()
        _music_paused = True
    except Exception as exc:
        _disable_music(exc)


def sync_music(*, running: bool) -> None:
    """Sincroniza o estado da musica com o estado da aplicacao.

    running=True  -> simulacao em execucao
    running=False -> simulacao pausada

    Trabalha por transicao. Chamadas repetidas com o mesmo valor sao
    no-op. Falha operacional da musica desabilita apenas a musica,
    sem afetar SFX.
    """
    global _pygame
    global _music_started, _music_paused

    if not _music_enabled:
        return
    if not _mixer_available() or _pygame is None:
        return
    if not _music_available:
        return

    try:
        if running:
            if not _music_started:
                _pygame.mixer.music.play(loops=-1)
                _music_started = True
                _music_paused = False
            elif _music_paused:
                _pygame.mixer.music.unpause()
                _music_paused = False
        else:
            if _music_started and not _music_paused:
                _pygame.mixer.music.pause()
                _music_paused = True
    except Exception as exc:
        _disable_music(exc)


def shutdown() -> None:
    """Encerra o backend de audio de forma best-effort.

    Idempotente e nao bloqueante. Nao espera nenhum SFX terminar.
    Nao executa fadeout temporizado. O som terminal e tocado por
    play_shutdown_sound(), chamada explicitamente pelo loop grafico
    antes deste shutdown; aqui o delay nao existe.
    """
    global _pygame, _initialized, _disabled
    global _music_available, _music_started, _music_paused
    global _music_warning_emitted
    global _music_enabled, _sfx_enabled

    pygame = _pygame
    if pygame is not None:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        try:
            pygame.mixer.stop()
        except Exception:
            pass
        try:
            pygame.mixer.quit()
        except Exception:
            pass

    _sounds.clear()
    _last_played_at.clear()

    _pygame = None
    _initialized = False
    _disabled = False

    _music_available = False
    _music_started = False
    _music_paused = False
    _music_warning_emitted = False

    # Reset da copia operacional. A preferencia persistente vive em
    # prefs.py; numa nova sessao grafica ela e reaplicada por
    # simulation.run().
    _music_enabled = (
        cfg.CONFIG_SNAPSHOT.operator.default_music_enabled
    )
    _sfx_enabled = (
        cfg.CONFIG_SNAPSHOT.operator.default_sfx_enabled
    )


def play_shutdown_sound() -> None:
    """Reproduz quit_game.wav e aguarda 1.5 s.

    Chamada somente pelo ramo Flow.EXIT, depois que prefs foram
    persistidas e o feedback sink foi limpo. Nenhum evento de
    feedback chega aqui.

    Precondicoes de saida SEM delay:
        SFX desabilitado            -> return
        backend indisponivel        -> return
        quit_game.wav nao carregado -> return
        nenhum canal disponivel     -> return
        falha ao iniciar reproducao -> return

    Contrato: o delay de 1.5 s existe somente quando o som realmente
    comecou. O usuario que desabilitou SFX (ou cujo mixer quebrou)
    nao espera por audio que nunca tocara.
    """
    global _pygame
    global _music_started, _music_paused

    if not _sfx_enabled:
        return
    if not _mixer_available() or _pygame is None:
        return
    sound = _sounds.get("quit")
    if sound is None:
        return

    # Silenciar musica antes do quit. A aplicacao ja esta no lifecycle
    # terminal; stop() (nao pause) e a escolha correta aqui.
    try:
        _pygame.mixer.music.stop()
        _music_started = False
        _music_paused = False
    except Exception:
        # Best-effort: nao abortar o quit por falha ao parar musica.
        pass

    # Silenciar SFX anteriores: birth/menu/etc. nao devem competir
    # auditivamente com quit_game.wav, e isso libera canais.
    try:
        _pygame.mixer.stop()
    except Exception:
        pass

    # Canal do quit: sem force=True.
    try:
        channel = _pygame.mixer.find_channel(force=False)
    except Exception:
        return
    if channel is None:
        return

    try:
        channel.play(sound)
    except Exception:
        return

    # Somente aqui o delay existe.
    import time as _time
    _time.sleep(_SHUTDOWN_SOUND_DELAY_SECONDS)
