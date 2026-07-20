# `from __future__ import annotations` makes type hints lazy strings, so we can
# annotate with `Style` without importing supertonic at module load time.
from __future__ import annotations

import json
import os
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

# supertonic is heavy and only needed when TTS actually runs. It is imported
# lazily inside VoiceSynthesizer so this module (and the whole app) loads even
# before supertonic is installed in the image. Install it via requirements + a
# docker rebuild before TTS will produce audio.

#Load the model ONCE (module level), not per request. It's heavy, otherwise.
_synth = None
def get_synth():
    global _synth
    if _synth is None:
        _synth = VoiceSynthesizer()
    return _synth


# Whisper (speech-to-text) is also loaded ONCE. faster-whisper is a heavy import,
# so it stays lazy inside get_whisper() — the app loads fine before it's installed.
_whisper = None
def get_whisper():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel  # lazy: heavy import
        # Model size is env-configurable. Default "small" is SERVER-SAFE (fits the
        # live container). "medium" is more accurate (far fewer Finnish/Estonian
        # misreads) but needs ~11GB, so it only runs where RAM allows. Set
        # WHISPER_MODEL=medium on a dev machine with enough RAM (WSL raised to
        # 11GB). Never set "medium" on the live server (OOM = exit 247).
        model_size = os.environ.get("WHISPER_MODEL", "small")
        _whisper = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _whisper

@login_required
@require_POST
def tts(request):
    data = json.loads(request.body)
    text = (data.get("text") or "").strip()
    if not text:
        return JsonResponse({"error": "no text"}, status=400)
    lang = data.get("lang") or "en"
    if lang not in ("en", "fi", "et"):          # Supertonic codes we support
        lang = "en"
    wav_bytes = get_synth().synthesize(text, lang)
    return HttpResponse(wav_bytes, content_type="audio/wav")


@login_required
@require_POST
def stt(request):
    """Transcribe the mic audio into text. The browser sends a webm blob plus a
    language hint; we return {text, lang}. The front-end drops the text into the
    input box — it is NEVER auto-sent, so injection detection, crisis logging, and
    encryption still run in StreamView when the person hits send.
    """
    import os
    import tempfile

    audio = request.FILES.get("audio")
    if not audio:
        return JsonResponse({"error": "no audio"}, status=400)

    # We deliberately do NOT force the language from the chat context. The person
    # may speak a different language than the chat is in (e.g. Finnish speech in an
    # Estonian chat). Whisper detects the language from the audio itself, which is
    # the real source of truth. Forcing the wrong language mangles the transcript.

    # SAFETY: never store the audio at rest. Write it to a temp file just long
    # enough to decode, then delete it in the finally block, always.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            for chunk in audio.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        segments, info = get_whisper().transcribe(tmp_path)
        text = "".join(segment.text for segment in segments).strip()
        return JsonResponse({"text": text, "lang": info.language})
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


class VoiceSynthesizer():
    def __init__(self):
        from supertonic import TTS  # lazy: heavy import, only when TTS is first used
        # No device= argument: Supertonic's TTS does not accept one, and adding it
        # crashes synthesis. This plain call is the version verified working. It runs
        # on CPU via onnxruntime, which is what we want.
        self.tts = TTS(auto_download=True)
        self.style = self._set_style()

    def __validate_style(self, style_code: str) -> bool:
        if style_code in ["M1", "M2", "M3", "M4", "F1", "F2", "F3", "F4"]:
            return True
        return False

    def _set_style(self) -> Style:
        return self.tts.get_voice_style("M1")
    
    def change_style(self, style_code: str) -> None:
        if self.__validate_style(self, style_code):
            self.style = self.tts.get_voice_style(style_code)

    def synthesize(self, agent_response: str, lang: str = "en") -> bytes:
        """Synthesize speech and return WAV bytes ready to stream to the browser.

        Supertonic's synthesize() returns (wav, durations) as numpy arrays with no
        sample rate, so we read the rate off the engine and encode to WAV with
        soundfile (a supertonic dependency). We do NOT import supertonic.server —
        that needs the 'serve' extra (fastapi), which is not installed.
        """
        import io
        import numpy as np
        import soundfile as sf

        wav, _durations = self.tts.synthesize(
            text=agent_response,
            voice_style=self.style,
            lang=lang,
            speed=1.0,
        )
        wav = np.asarray(wav).squeeze()                        # (1, frames) -> (frames,), mono
        sample_rate = getattr(self.tts, "sample_rate", 44100)  # Supertonic outputs 44.1kHz
        buffer = io.BytesIO()
        sf.write(buffer, wav, sample_rate, format="WAV")
        return buffer.getvalue()
    


