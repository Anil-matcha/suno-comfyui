"""
MuAPI Suno ComfyUI Nodes
=========================
Focused nodes for Suno music & audio generation via muapi.ai.

  SunoCreateMusic        — POST /api/v1/suno-create-music
  SunoRemixMusic         — POST /api/v1/suno-remix-music
  SunoExtendMusic        — POST /api/v1/suno-extend-music
  SunoGenerateSounds     — POST /api/v1/suno-generate-sounds
  SunoGenerateLyrics     — POST /api/v1/suno-generate-lyrics
  SunoBoostMusicStyle    — POST /api/v1/suno-boost-music-style
  SunoAddVocals          — POST /api/v1/suno-add-vocals
  SunoGenerateMashup     — POST /api/v1/suno-generate-mashup
  SunoAddInstrumental    — POST /api/v1/suno-add-instrumental

Auth:     x-api-key header
Polling:  GET /api/v1/predictions/{request_id}/result
Upload:   POST /api/v1/upload_file

Suno music endpoints typically return TWO audio tracks per generation;
both URLs are exposed as audio_url_1 / audio_url_2.
"""

import os
import time

import requests

BASE_URL = "https://api.muapi.ai/api/v1"
POLL_INTERVAL = 10
MAX_WAIT = 900

AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".opus")
_NONE_CHOICE = "(none)"

SUNO_MODELS = ["V3_5", "V4", "V4_5", "V4_5PLUS", "V4_5ALL", "V5", "V5_5"]
VOCAL_GENDERS = ["", "male", "female"]
SOUND_KEYS = [
    "Any", "Cm", "C#m", "Dm", "D#m", "Em", "Fm", "F#m", "Gm", "G#m",
    "Am", "A#m", "Bm", "C", "C#", "D", "D#", "E", "F", "F#",
    "G", "G#", "A", "A#", "B",
]


def _list_input_files(extensions):
    """Return sorted list of files in ComfyUI/input/ matching the given extensions."""
    try:
        import folder_paths
        input_dir = folder_paths.get_input_directory()
        files = [
            f for f in os.listdir(input_dir)
            if os.path.isfile(os.path.join(input_dir, f))
            and f.lower().endswith(extensions)
        ]
        return [_NONE_CHOICE] + sorted(files)
    except Exception:
        return [_NONE_CHOICE]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_api_key(api_key_input):
    """Return api_key_input if set, otherwise fall back to ~/.muapi/config.json."""
    if api_key_input and api_key_input.strip():
        return api_key_input.strip()
    config_path = os.path.expanduser("~/.muapi/config.json")
    if os.path.isfile(config_path):
        try:
            import json as _json
            with open(config_path) as f:
                key = _json.load(f).get("api_key", "")
            if key:
                return key
        except Exception:
            pass
    raise RuntimeError(
        "No API key found. Either paste your key into the api_key field, "
        "or run `muapi auth configure --api-key YOUR_KEY` in a terminal."
    )


def _resolve_audio_ref(api_key, ref):
    """Resolve an audio reference to a URL.
       - empty/whitespace → None
       - starts with http(s) → returned as-is
       - existing local file or filename in ComfyUI/input/ → uploaded, URL returned
    """
    import mimetypes
    if not ref or not ref.strip():
        return None
    ref = ref.strip().strip('"').strip("'")
    if ref.lower().startswith(("http://", "https://")):
        return ref
    path = ref
    if not os.path.isfile(path):
        try:
            import folder_paths
            candidate = os.path.join(folder_paths.get_input_directory(), ref)
            if os.path.isfile(candidate):
                path = candidate
        except Exception:
            pass
    if not os.path.isfile(path):
        raise RuntimeError(
            f"[Suno] audio reference not found: {ref!r}. "
            f"Provide an http(s) URL, an absolute file path, or a filename inside ComfyUI/input/."
        )
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        mime = "audio/mpeg"
    filename = os.path.basename(path)
    print(f"[Suno] Uploading audio: {filename} ({mime})")
    with open(path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/upload_file",
            headers={"x-api-key": api_key},
            files={"file": (filename, f, mime)},
            timeout=600,
        )
    _check(resp)
    return _url(resp.json())


def _pick_audio(dropdown, override):
    """Prefer dropdown; fall back to URL/path override string."""
    if dropdown and dropdown != _NONE_CHOICE:
        return dropdown
    return override


def _url(data):
    u = data.get("url") or data.get("file_url") or data.get("output")
    if not u:
        raise RuntimeError(f"Upload missing URL: {data}")
    return str(u)


def _submit(api_key, endpoint, payload):
    resp = requests.post(
        f"{BASE_URL}/{endpoint}",
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    _check(resp)
    rid = resp.json().get("request_id")
    if not rid:
        raise RuntimeError(f"No request_id: {resp.json()}")
    return rid


def _poll(api_key, request_id):
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        resp = requests.get(
            f"{BASE_URL}/predictions/{request_id}/result",
            headers={"x-api-key": api_key},
            timeout=30,
        )
        _check(resp)
        data = resp.json()
        status = data.get("status")
        print(f"[Suno] {status}  {request_id}")
        if status == "completed":
            return data
        if status == "failed":
            raise RuntimeError(f"Failed: {data.get('error', 'unknown')}")
        time.sleep(POLL_INTERVAL)
    raise RuntimeError(f"Timeout: {request_id}")


def _audio_outputs(result):
    """Return the list of audio URLs from a completed Suno music result.
       Suno typically returns two tracks per generation."""
    out = result.get("outputs") or result.get("output") or []
    if isinstance(out, str):
        return [out]
    if isinstance(out, list):
        return [str(u) for u in out if u]
    for k in ("audio_url", "url"):
        if result.get(k):
            return [str(result[k])]
    return []


def _text_output(result):
    """Return text output (e.g., lyrics, boosted style) from a completed result."""
    out = result.get("outputs") or result.get("output") or ""
    if isinstance(out, list):
        return "\n\n---\n\n".join(str(x) for x in out if x)
    if isinstance(out, str):
        return out
    for k in ("text", "lyrics"):
        if result.get(k):
            return str(result[k])
    return ""


def _check(resp):
    if resp.status_code == 401:
        raise RuntimeError("Auth failed — check API key.")
    if resp.status_code == 402:
        raise RuntimeError("Insufficient credits — top up at muapi.ai")
    if resp.status_code == 429:
        raise RuntimeError("Rate limited — retry later.")
    if not resp.ok:
        print(f"[Suno] API ERROR {resp.status_code}: {resp.text[:500]}")
        try:
            err = resp.json()
            raise RuntimeError(f"API {resp.status_code}: {err}")
        except Exception:
            raise RuntimeError(f"API {resp.status_code}: {resp.text[:300]}")


def _two_tracks(urls):
    """Pad to exactly two URL slots."""
    a = urls[0] if len(urls) > 0 else ""
    b = urls[1] if len(urls) > 1 else ""
    return a, b


# ── Nodes ──────────────────────────────────────────────────────────────────────

class SunoApiKey:
    """
    Store your MuAPI API key once and wire it to any Suno node.
    Leave all node api_key fields empty — they auto-read from this node
    or from ~/.muapi/config.json (set via `muapi auth configure`).
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "api_key": ("STRING", {"multiline": False, "default": "",
                "tooltip": "Your muapi.ai API key. Get one at muapi.ai → Dashboard → API Keys"}),
        }}
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("api_key",)
    FUNCTION = "run"
    CATEGORY = "🎵 Suno"

    def run(self, api_key):
        return (_load_api_key(api_key),)


class SunoCreateMusic:
    """
    Suno Create Music
    ------------------
    Generate original music tracks from a text style description, optionally
    with custom lyrics in `prompt`. Returns two audio variants per generation.

    Models: V3_5 | V4 | V4_5 | V4_5PLUS | V4_5ALL | V5 | V5_5
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "style": ("STRING", {"multiline": True,
                "default": "lofi hip hop, mellow piano, soft drums, late-night study vibe"}),
            "model": (SUNO_MODELS, {"default": "V5"}),
            "instrumental": ("BOOLEAN", {"default": True,
                "tooltip": "If False, you must supply lyrics in `prompt`."}),
            "custom_mode": ("BOOLEAN", {"default": True}),
        }, "optional": {
            "api_key":   ("STRING", {"multiline": False, "default": ""}),
            "prompt":    ("STRING", {"multiline": True, "default": "",
                "tooltip": "Required when instrumental is False — these become the lyrics."}),
            "title":     ("STRING", {"multiline": False, "default": ""}),
            "persona_id": ("STRING", {"multiline": False, "default": ""}),
            "negative_tags": ("STRING", {"multiline": False, "default": ""}),
            "vocal_gender":  (VOCAL_GENDERS, {"default": ""}),
            "style_weight":         ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0, "step": 0.05,
                "tooltip": "0–1 to set; -1 to leave unset."}),
            "weirdness_constraint": ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0, "step": 0.05,
                "tooltip": "0–1 to set; -1 to leave unset."}),
            "audio_weight":         ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0, "step": 0.05,
                "tooltip": "0–1 to set; -1 to leave unset."}),
        }}
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio_url_1", "audio_url_2", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎵 Suno"

    def run(self, style, model, instrumental, custom_mode, api_key="",
            prompt="", title="", persona_id="", negative_tags="", vocal_gender="",
            style_weight=-1.0, weirdness_constraint=-1.0, audio_weight=-1.0):
        api_key = _load_api_key(api_key)
        if not instrumental and not prompt.strip():
            raise ValueError("Prompt (lyrics) is required when instrumental is False.")
        payload = {
            "style": style,
            "model": model,
            "instrumental": instrumental,
            "custom_mode": custom_mode,
        }
        if prompt.strip():       payload["prompt"] = prompt
        if title.strip():        payload["title"] = title.strip()
        if persona_id.strip():   payload["persona_id"] = persona_id.strip()
        if negative_tags.strip():payload["negative_tags"] = negative_tags.strip()
        if vocal_gender:         payload["vocal_gender"] = vocal_gender
        if style_weight >= 0:        payload["style_weight"] = style_weight
        if weirdness_constraint >= 0:payload["weirdness_constraint"] = weirdness_constraint
        if audio_weight >= 0:        payload["audio_weight"] = audio_weight

        print(f"[Suno Create] Submitting ({model}, instrumental={instrumental})...")
        rid = _submit(api_key, "suno-create-music", payload)
        result = _poll(api_key, rid)
        urls = _audio_outputs(result)
        a, b = _two_tracks(urls)
        print(f"[Suno Create] Done → {a}  |  {b}")
        return (a, b, rid)


class SunoRemixMusic:
    """
    Suno Remix Music
    -----------------
    Re-imagine an existing track in a new style. Provide either a hosted URL
    or a local audio file (will be auto-uploaded). Returns two remix variants.
    """
    @classmethod
    def INPUT_TYPES(cls):
        audio_files = _list_input_files(AUDIO_EXTS)
        return {"required": {
            "style": ("STRING", {"multiline": True,
                "default": "high-energy synthwave, driving 808s, neon-bright leads"}),
            "model": (SUNO_MODELS, {"default": "V5"}),
            "instrumental": ("BOOLEAN", {"default": True}),
            "custom_mode":  ("BOOLEAN", {"default": True}),
        }, "optional": {
            "api_key":   ("STRING", {"multiline": False, "default": ""}),
            "audio_file": (audio_files, {"default": _NONE_CHOICE,
                "tooltip": "Pick a file from ComfyUI/input/. (none) means use audio_url instead."}),
            "audio_url":  ("STRING", {"multiline": False, "default": "",
                "tooltip": "http(s) URL or absolute path. Used if audio_file is (none)."}),
            "prompt":    ("STRING", {"multiline": True, "default": ""}),
            "title":     ("STRING", {"multiline": False, "default": ""}),
            "persona_id":("STRING", {"multiline": False, "default": ""}),
            "negative_tags":("STRING", {"multiline": False, "default": ""}),
            "vocal_gender":(VOCAL_GENDERS, {"default": ""}),
            "style_weight":         ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0, "step": 0.05}),
            "weirdness_constraint": ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0, "step": 0.05}),
            "audio_weight":         ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0, "step": 0.05}),
        }}
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio_url_1", "audio_url_2", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎵 Suno"

    def run(self, style, model, instrumental, custom_mode, api_key="",
            audio_file=_NONE_CHOICE, audio_url="",
            prompt="", title="", persona_id="", negative_tags="", vocal_gender="",
            style_weight=-1.0, weirdness_constraint=-1.0, audio_weight=-1.0):
        api_key = _load_api_key(api_key)
        ref = _pick_audio(audio_file, audio_url)
        resolved = _resolve_audio_ref(api_key, ref)
        if not resolved:
            raise ValueError("Provide an audio file (dropdown) or audio_url to remix.")
        if not instrumental and not prompt.strip():
            raise ValueError("Prompt (lyrics) is required when instrumental is False.")
        payload = {
            "audio_url": resolved,
            "style": style,
            "model": model,
            "instrumental": instrumental,
            "custom_mode": custom_mode,
        }
        if prompt.strip():       payload["prompt"] = prompt
        if title.strip():        payload["title"] = title.strip()
        if persona_id.strip():   payload["persona_id"] = persona_id.strip()
        if negative_tags.strip():payload["negative_tags"] = negative_tags.strip()
        if vocal_gender:         payload["vocal_gender"] = vocal_gender
        if style_weight >= 0:        payload["style_weight"] = style_weight
        if weirdness_constraint >= 0:payload["weirdness_constraint"] = weirdness_constraint
        if audio_weight >= 0:        payload["audio_weight"] = audio_weight

        print(f"[Suno Remix] Submitting...")
        rid = _submit(api_key, "suno-remix-music", payload)
        result = _poll(api_key, rid)
        urls = _audio_outputs(result)
        a, b = _two_tracks(urls)
        print(f"[Suno Remix] Done → {a}  |  {b}")
        return (a, b, rid)


class SunoExtendMusic:
    """
    Suno Extend Music
    ------------------
    Continue an existing track from a chosen second mark (continue_at).
    Returns two extended variants.
    """
    @classmethod
    def INPUT_TYPES(cls):
        audio_files = _list_input_files(AUDIO_EXTS)
        return {"required": {
            "style": ("STRING", {"multiline": True,
                "default": "epic orchestral build, swelling strings, percussive crescendo"}),
            "model": (SUNO_MODELS, {"default": "V5"}),
            "continue_at": ("INT", {"default": 30, "min": 1, "max": 600,
                "tooltip": "Seconds into the source track to continue from."}),
            "instrumental": ("BOOLEAN", {"default": True}),
            "custom_mode":  ("BOOLEAN", {"default": True}),
        }, "optional": {
            "api_key":   ("STRING", {"multiline": False, "default": ""}),
            "audio_file": (audio_files, {"default": _NONE_CHOICE}),
            "audio_url":  ("STRING", {"multiline": False, "default": ""}),
            "prompt":    ("STRING", {"multiline": True, "default": ""}),
            "title":     ("STRING", {"multiline": False, "default": ""}),
            "persona_id":("STRING", {"multiline": False, "default": ""}),
            "negative_tags":("STRING", {"multiline": False, "default": ""}),
            "vocal_gender":(VOCAL_GENDERS, {"default": ""}),
            "style_weight":         ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0, "step": 0.05}),
            "weirdness_constraint": ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0, "step": 0.05}),
            "audio_weight":         ("FLOAT", {"default": -1.0, "min": -1.0, "max": 1.0, "step": 0.05}),
        }}
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio_url_1", "audio_url_2", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎵 Suno"

    def run(self, style, model, continue_at, instrumental, custom_mode, api_key="",
            audio_file=_NONE_CHOICE, audio_url="",
            prompt="", title="", persona_id="", negative_tags="", vocal_gender="",
            style_weight=-1.0, weirdness_constraint=-1.0, audio_weight=-1.0):
        api_key = _load_api_key(api_key)
        ref = _pick_audio(audio_file, audio_url)
        resolved = _resolve_audio_ref(api_key, ref)
        if not resolved:
            raise ValueError("Provide an audio file (dropdown) or audio_url to extend.")
        if not instrumental and not prompt.strip():
            raise ValueError("Prompt (lyrics) is required when instrumental is False.")
        payload = {
            "audio_url": resolved,
            "style": style,
            "model": model,
            "continue_at": continue_at,
            "instrumental": instrumental,
            "custom_mode": custom_mode,
        }
        if prompt.strip():       payload["prompt"] = prompt
        if title.strip():        payload["title"] = title.strip()
        if persona_id.strip():   payload["persona_id"] = persona_id.strip()
        if negative_tags.strip():payload["negative_tags"] = negative_tags.strip()
        if vocal_gender:         payload["vocal_gender"] = vocal_gender
        if style_weight >= 0:        payload["style_weight"] = style_weight
        if weirdness_constraint >= 0:payload["weirdness_constraint"] = weirdness_constraint
        if audio_weight >= 0:        payload["audio_weight"] = audio_weight

        print(f"[Suno Extend] Submitting (continue_at={continue_at}s)...")
        rid = _submit(api_key, "suno-extend-music", payload)
        result = _poll(api_key, rid)
        urls = _audio_outputs(result)
        a, b = _two_tracks(urls)
        print(f"[Suno Extend] Done → {a}  |  {b}")
        return (a, b, rid)


class SunoGenerateSounds:
    """
    Suno Generate Sound Effects
    ----------------------------
    Generate a one-shot sound effect or musical loop from a text prompt.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "prompt": ("STRING", {"multiline": True,
                "default": "deep cinematic riser into a glass-shatter impact, 2 seconds"}),
            "model": (["chirp-crow"], {"default": "chirp-crow"}),
            "sound_loop": ("BOOLEAN", {"default": False}),
        }, "optional": {
            "api_key":    ("STRING", {"multiline": False, "default": ""}),
            "sound_tempo":("INT",    {"default": -1, "min": -1, "max": 300,
                "tooltip": "BPM (-1 to leave unset)."}),
            "sound_key":  (SOUND_KEYS, {"default": "Any"}),
            "grab_lyrics":("BOOLEAN", {"default": False}),
        }}
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio_url_1", "audio_url_2", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎵 Suno"

    def run(self, prompt, model, sound_loop, api_key="",
            sound_tempo=-1, sound_key="Any", grab_lyrics=False):
        api_key = _load_api_key(api_key)
        payload = {
            "prompt": prompt,
            "model": model,
            "sound_loop": sound_loop,
            "sound_key": sound_key,
            "grab_lyrics": grab_lyrics,
        }
        if sound_tempo >= 0:
            payload["sound_tempo"] = sound_tempo

        print(f"[Suno Sounds] Submitting...")
        rid = _submit(api_key, "suno-generate-sounds", payload)
        result = _poll(api_key, rid)
        urls = _audio_outputs(result)
        a, b = _two_tracks(urls)
        print(f"[Suno Sounds] Done → {a}  |  {b}")
        return (a, b, rid)


class SunoGenerateLyrics:
    """
    Suno Generate Lyrics
    ---------------------
    Generate song lyrics from a topic / style prompt. Returns the lyrics
    as a STRING you can wire into SunoCreateMusic / SunoAddVocals.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "prompt": ("STRING", {"multiline": True,
                "default": "an upbeat indie-pop song about late-night drives and city lights"}),
        }, "optional": {
            "api_key": ("STRING", {"multiline": False, "default": ""}),
        }}
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("lyrics", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎵 Suno"

    def run(self, prompt, api_key=""):
        api_key = _load_api_key(api_key)
        payload = {"prompt": prompt}
        print(f"[Suno Lyrics] Submitting...")
        rid = _submit(api_key, "suno-generate-lyrics", payload)
        result = _poll(api_key, rid)
        lyrics = _text_output(result)
        print(f"[Suno Lyrics] Done ({len(lyrics)} chars).")
        return (lyrics, rid)


class SunoBoostMusicStyle:
    """
    Suno Boost Music Style
    -----------------------
    Expand a short style description into a richer, more detailed style prompt
    you can feed into SunoCreateMusic / SunoRemixMusic / SunoExtendMusic.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "content": ("STRING", {"multiline": True,
                "default": "lofi hip hop"}),
        }, "optional": {
            "api_key": ("STRING", {"multiline": False, "default": ""}),
        }}
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("boosted_style", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎵 Suno"

    def run(self, content, api_key=""):
        api_key = _load_api_key(api_key)
        payload = {"content": content}
        print(f"[Suno Boost] Submitting...")
        rid = _submit(api_key, "suno-boost-music-style", payload)
        result = _poll(api_key, rid)
        boosted = _text_output(result)
        print(f"[Suno Boost] Done ({len(boosted)} chars).")
        return (boosted, rid)


class SunoAddVocals:
    """
    Suno Add Vocals
    ----------------
    Add AI vocals to an instrumental track. Provide lyrics in `prompt`,
    a title, a style description, and optionally an instrumental track URL.
    """
    @classmethod
    def INPUT_TYPES(cls):
        audio_files = _list_input_files(AUDIO_EXTS)
        return {"required": {
            "prompt": ("STRING", {"multiline": True,
                "default": "Verse 1:\nDrifting through the city lights..."}),
            "title": ("STRING", {"multiline": False, "default": "City Lights"}),
            "style": ("STRING", {"multiline": True, "default": "indie pop, dreamy, mid-tempo"}),
            "model": (["V4", "V4_5", "V4_5PLUS", "V5"], {"default": "V5"}),
            "vocal_gender": (["male", "female"], {"default": "male"}),
        }, "optional": {
            "api_key":    ("STRING", {"multiline": False, "default": ""}),
            "audio_file": (audio_files, {"default": _NONE_CHOICE,
                "tooltip": "Optional instrumental track to add vocals over."}),
            "audio_url":  ("STRING", {"multiline": False, "default": ""}),
            "negative_tags":("STRING", {"multiline": False, "default": ""}),
            "style_weight":         ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05}),
            "weirdness_constraint": ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05}),
            "audio_weight":         ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05}),
        }}
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio_url_1", "audio_url_2", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎵 Suno"

    def run(self, prompt, title, style, model, vocal_gender, api_key="",
            audio_file=_NONE_CHOICE, audio_url="",
            negative_tags="", style_weight=0.65, weirdness_constraint=0.65, audio_weight=0.65):
        api_key = _load_api_key(api_key)
        payload = {
            "prompt": prompt,
            "title": title,
            "style": style,
            "model": model,
            "vocal_gender": vocal_gender,
            "style_weight": style_weight,
            "weirdness_constraint": weirdness_constraint,
            "audio_weight": audio_weight,
        }
        ref = _pick_audio(audio_file, audio_url)
        resolved = _resolve_audio_ref(api_key, ref)
        if resolved:
            payload["audio_url"] = resolved
        if negative_tags.strip():
            payload["negative_tags"] = negative_tags.strip()

        print(f"[Suno AddVocals] Submitting ({vocal_gender})...")
        rid = _submit(api_key, "suno-add-vocals", payload)
        result = _poll(api_key, rid)
        urls = _audio_outputs(result)
        a, b = _two_tracks(urls)
        print(f"[Suno AddVocals] Done → {a}  |  {b}")
        return (a, b, rid)


class SunoGenerateMashup:
    """
    Suno Generate Mashup
    ---------------------
    Blend up to 4 audio tracks into a single mashup. Pass each track via
    audio_url_N or audio_file_N. Returns two mashup variants.
    """
    @classmethod
    def INPUT_TYPES(cls):
        audio_files = _list_input_files(AUDIO_EXTS)
        slot_tip = ("Pick a file from ComfyUI/input/, or use the override URL/path field. "
                    "At least 2 tracks are recommended.")
        return {"required": {
            "model": (["V4", "V4_5", "V4_5PLUS", "V4_5ALL", "V5"], {"default": "V5"}),
            "instrumental": ("BOOLEAN", {"default": True}),
        }, "optional": {
            "api_key":   ("STRING", {"multiline": False, "default": ""}),
            "audio_file_1": (audio_files, {"default": _NONE_CHOICE, "tooltip": slot_tip}),
            "audio_url_1":  ("STRING", {"multiline": False, "default": ""}),
            "audio_file_2": (audio_files, {"default": _NONE_CHOICE, "tooltip": slot_tip}),
            "audio_url_2":  ("STRING", {"multiline": False, "default": ""}),
            "audio_file_3": (audio_files, {"default": _NONE_CHOICE, "tooltip": slot_tip}),
            "audio_url_3":  ("STRING", {"multiline": False, "default": ""}),
            "audio_file_4": (audio_files, {"default": _NONE_CHOICE, "tooltip": slot_tip}),
            "audio_url_4":  ("STRING", {"multiline": False, "default": ""}),
            "prompt": ("STRING", {"multiline": True, "default": ""}),
            "style":  ("STRING", {"multiline": False, "default": ""}),
            "title":  ("STRING", {"multiline": False, "default": ""}),
            "vocal_gender": (["male", "female"], {"default": "male"}),
            "style_weight":         ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05}),
            "weirdness_constraint": ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05}),
            "audio_weight":         ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05}),
        }}
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio_url_1", "audio_url_2", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎵 Suno"

    def run(self, model, instrumental, api_key="",
            audio_file_1=_NONE_CHOICE, audio_url_1="",
            audio_file_2=_NONE_CHOICE, audio_url_2="",
            audio_file_3=_NONE_CHOICE, audio_url_3="",
            audio_file_4=_NONE_CHOICE, audio_url_4="",
            prompt="", style="", title="", vocal_gender="male",
            style_weight=0.65, weirdness_constraint=0.65, audio_weight=0.65):
        api_key = _load_api_key(api_key)
        slots = [
            _pick_audio(audio_file_1, audio_url_1),
            _pick_audio(audio_file_2, audio_url_2),
            _pick_audio(audio_file_3, audio_url_3),
            _pick_audio(audio_file_4, audio_url_4),
        ]
        audios_list = []
        for ref in slots:
            resolved = _resolve_audio_ref(api_key, ref)
            if resolved:
                audios_list.append(resolved)
        if not audios_list:
            raise ValueError("Mashup requires at least one input track.")

        payload = {
            "audios_list": audios_list,
            "model": model,
            "instrumental": instrumental,
            "vocal_gender": vocal_gender,
            "style_weight": style_weight,
            "weirdness_constraint": weirdness_constraint,
            "audio_weight": audio_weight,
        }
        if prompt.strip(): payload["prompt"] = prompt
        if style.strip():  payload["style"] = style
        if title.strip():  payload["title"] = title

        print(f"[Suno Mashup] Submitting ({len(audios_list)} track(s))...")
        rid = _submit(api_key, "suno-generate-mashup", payload)
        result = _poll(api_key, rid)
        urls = _audio_outputs(result)
        a, b = _two_tracks(urls)
        print(f"[Suno Mashup] Done → {a}  |  {b}")
        return (a, b, rid)


class SunoAddInstrumental:
    """
    Suno Add Instrumental
    ----------------------
    Generate an instrumental backing track for a given title and tag set,
    optionally seeded with an existing audio reference.
    """
    @classmethod
    def INPUT_TYPES(cls):
        audio_files = _list_input_files(AUDIO_EXTS)
        return {"required": {
            "title": ("STRING", {"multiline": False, "default": "Sunset Drive"}),
            "tags":  ("STRING", {"multiline": True,
                "default": "synthwave, retro, mid-tempo, warm analog"}),
            "model": (["V4", "V4_5", "V4_5PLUS", "V5"], {"default": "V5"}),
            "vocal_gender": (["male", "female"], {"default": "male"}),
        }, "optional": {
            "api_key":    ("STRING", {"multiline": False, "default": ""}),
            "audio_file": (audio_files, {"default": _NONE_CHOICE}),
            "audio_url":  ("STRING", {"multiline": False, "default": ""}),
            "negative_tags":("STRING", {"multiline": False, "default": ""}),
            "style_weight":         ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05}),
            "weirdness_constraint": ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05}),
            "audio_weight":         ("FLOAT", {"default": 0.65, "min": 0.0, "max": 1.0, "step": 0.05}),
        }}
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("audio_url_1", "audio_url_2", "request_id")
    FUNCTION = "run"
    CATEGORY = "🎵 Suno"

    def run(self, title, tags, model, vocal_gender, api_key="",
            audio_file=_NONE_CHOICE, audio_url="",
            negative_tags="", style_weight=0.65, weirdness_constraint=0.65, audio_weight=0.65):
        api_key = _load_api_key(api_key)
        payload = {
            "title": title,
            "tags": tags,
            "model": model,
            "vocal_gender": vocal_gender,
            "style_weight": style_weight,
            "weirdness_constraint": weirdness_constraint,
            "audio_weight": audio_weight,
        }
        ref = _pick_audio(audio_file, audio_url)
        resolved = _resolve_audio_ref(api_key, ref)
        if resolved:
            payload["audio_url"] = resolved
        if negative_tags.strip():
            payload["negative_tags"] = negative_tags.strip()

        print(f"[Suno Instrumental] Submitting...")
        rid = _submit(api_key, "suno-add-instrumental", payload)
        result = _poll(api_key, rid)
        urls = _audio_outputs(result)
        a, b = _two_tracks(urls)
        print(f"[Suno Instrumental] Done → {a}  |  {b}")
        return (a, b, rid)


NODE_CLASS_MAPPINGS = {
    "SunoApiKey":            SunoApiKey,
    "SunoCreateMusic":       SunoCreateMusic,
    "SunoRemixMusic":        SunoRemixMusic,
    "SunoExtendMusic":       SunoExtendMusic,
    "SunoGenerateSounds":    SunoGenerateSounds,
    "SunoGenerateLyrics":    SunoGenerateLyrics,
    "SunoBoostMusicStyle":   SunoBoostMusicStyle,
    "SunoAddVocals":         SunoAddVocals,
    "SunoGenerateMashup":    SunoGenerateMashup,
    "SunoAddInstrumental":   SunoAddInstrumental,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SunoApiKey":            "🔑 Suno API Key",
    "SunoCreateMusic":       "🎵 Suno Create Music",
    "SunoRemixMusic":        "🎵 Suno Remix Music",
    "SunoExtendMusic":       "🎵 Suno Extend Music",
    "SunoGenerateSounds":    "🎵 Suno Generate Sounds",
    "SunoGenerateLyrics":    "🎵 Suno Generate Lyrics",
    "SunoBoostMusicStyle":   "🎵 Suno Boost Music Style",
    "SunoAddVocals":         "🎵 Suno Add Vocals",
    "SunoGenerateMashup":    "🎵 Suno Generate Mashup",
    "SunoAddInstrumental":   "🎵 Suno Add Instrumental",
}
