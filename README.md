# Suno ComfyUI Nodes

> **ComfyUI custom nodes for Suno** — generate, remix, extend, and shape AI music directly inside ComfyUI using the [muapi.ai](https://muapi.ai) API.
> If you wish to check the API documentation, see [suno-api](https://github.com/Anil-matcha/suno-api).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom%20Node-blue)](https://github.com/comfyanonymous/ComfyUI)
[![Suno](https://img.shields.io/badge/Model-Suno-purple)](https://muapi.ai)

---

## Related Projects

- [Suno on MuAPI](https://muapi.ai/suno) — Model landing page for music creation, remix, and extension.
- [Music and speech docs](https://muapi.ai/docs/music-and-speech) — API workflows for Suno and audio generation.
- [suno-api](https://github.com/Anil-matcha/suno-api) — Python SDK for Suno music, audio, and voice workflows.
- [minimax-music-3-comfyui](https://github.com/Anil-matcha/minimax-music-3-comfyui) — ComfyUI custom nodes for MiniMax Music 3.0 text-to-music generation.
- [awesome-minimax-music-3-prompts](https://github.com/Anil-matcha/awesome-minimax-music-3-prompts) — Curated song prompts and lyrics-formatting guide for MiniMax Music 3.0.

## What is Suno?

Suno is a state-of-the-art generative music model that produces full-length songs, instrumentals, and sound effects from text prompts. This node pack wraps the muapi.ai Suno endpoints so you can compose, remix, and edit music inside ComfyUI workflows.

- **Create Music** — generate two original tracks from a style prompt (with optional lyrics)
- **Remix / Extend** — transform or continue an existing audio track
- **Add Vocals / Add Instrumental** — layer vocals onto an instrumental, or build an instrumental for a topline
- **Generate Sounds / Lyrics / Boost Style** — sound effects, full lyrics, and rich style descriptors
- **Mashup** — blend up to 4 tracks into a single composition

---

## Nodes

| Node | Description |
|------|-------------|
| 🔑 Suno API Key | Set your key once — wire to all nodes |
| 🎵 Suno Create Music | Generate two original tracks from a style + optional lyrics |
| 🎵 Suno Remix Music | Re-imagine an existing track in a new style |
| 🎵 Suno Extend Music | Continue an existing track from a chosen second mark |
| 🎵 Suno Generate Sounds | One-shot SFX or short musical loops |
| 🎵 Suno Generate Lyrics | Generate lyrics from a topic/style prompt |
| 🎵 Suno Boost Music Style | Expand a short style tag into a richer style prompt |
| 🎵 Suno Add Vocals | Layer AI vocals onto an instrumental |
| 🎵 Suno Generate Mashup | Blend up to 4 tracks |
| 🎵 Suno Add Instrumental | Generate an instrumental backing track |
| 🎵 Suno Save Audio | Download URL → disk + ComfyUI AUDIO tensor |

---

## Installation

### Via ComfyUI Manager (recommended)
1. Open **ComfyUI Manager** → **Install via Git URL**
2. Paste: `https://github.com/Anil-matcha/suno-comfyui`
3. Restart ComfyUI

### Manual
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Anil-matcha/suno-comfyui
pip install -r suno-comfyui/requirements.txt
```

---

## Quick Start

1. Sign up at [muapi.ai](https://muapi.ai) and go to **Dashboard → API Keys → Create Key**
2. Right-click the ComfyUI canvas → **Add Node** → **🎵 Suno**
3. Add a **🔑 Suno API Key** node, paste your key, and wire its output to any generation node
4. Write a prompt and hit **Queue Prompt**

> **Tip:** If you use the [MuAPI CLI](https://github.com/SamurAIGPT/muapi-cli), run `muapi auth configure --api-key YOUR_KEY` once and all nodes will pick it up automatically — no need to paste the key anywhere.

---

## Node Reference

### 🔑 Suno API Key

Set your muapi.ai API key once and wire the output to all generation nodes. Alternatively, leave every `api_key` field blank — nodes automatically read from `~/.muapi/config.json` if you've authenticated via the CLI.

---

### 🎵 Suno Create Music

Generate two original music variants from a style description. Provide custom lyrics in `prompt` (required when `instrumental` is False).

| Field | Values | Default |
|-------|--------|---------|
| `style` | Free-text style description (genre, mood, tempo, instruments) | — |
| `model` | V3_5 / V4 / V4_5 / V4_5PLUS / V4_5ALL / V5 / V5_5 | V5 |
| `instrumental` | True for instrumental only, False for sung lyrics | True |
| `custom_mode` | Use the full custom prompt schema | True |
| `prompt` | Optional lyrics (required when `instrumental=False`) | — |
| `title`, `persona_id`, `negative_tags`, `vocal_gender` | Optional fine controls | — |
| `style_weight`, `weirdness_constraint`, `audio_weight` | 0–1 to set, -1 to leave unset | -1 |

**Outputs:** `audio_url_1` · `audio_url_2` · `request_id`

---

### 🎵 Suno Remix Music

Transform an existing track in a new style. Pass either a hosted URL via `audio_url` or pick a file from `ComfyUI/input/` via `audio_file`. Returns two remix variants.

```
[Audio file or URL] → [🎵 Remix Music] → audio_url_1 / audio_url_2 → [🎵 Save Audio]
```

---

### 🎵 Suno Extend Music

Continue an existing track from a chosen second mark.

| Field | Description |
|-------|-------------|
| `audio_file` / `audio_url` | Source track (file in input/ or URL) |
| `continue_at` | Seconds into the source to continue from |
| `style` | Style of the continuation |

**Outputs:** `audio_url_1` · `audio_url_2` · `request_id`

---

### 🎵 Suno Generate Sounds

Generate a short sound effect or musical loop.

| Field | Description |
|-------|-------------|
| `prompt` | Description of the sound |
| `model` | `chirp-crow` |
| `sound_loop` | Make the result loopable |
| `sound_tempo` | BPM (-1 to leave unset) |
| `sound_key` | Musical key (or `Any`) |

---

### 🎵 Suno Generate Lyrics

Generate full lyrics from a topic / style prompt.

**Outputs:** `lyrics` (STRING — wire into Create Music or Add Vocals) · `request_id`

---

### 🎵 Suno Boost Music Style

Expand a short style tag (e.g., `lofi hip hop`) into a richer style prompt for downstream music nodes.

**Outputs:** `boosted_style` (STRING) · `request_id`

---

### 🎵 Suno Add Vocals

Layer AI vocals onto an instrumental track.

| Field | Description |
|-------|-------------|
| `prompt` | Lyrics |
| `title` | Song title |
| `style` | Style description |
| `vocal_gender` | male / female |
| `audio_file` / `audio_url` | Optional instrumental track |

---

### 🎵 Suno Generate Mashup

Blend up to 4 audio tracks into a single mashup. Each slot accepts a file from `ComfyUI/input/` or an override URL.

---

### 🎵 Suno Add Instrumental

Generate an instrumental backing track for a given title and tag set.

---

### 🎵 Suno Save Audio

Download a generated track to ComfyUI's output folder and expose it as a ComfyUI **AUDIO** tensor (waveform + sample_rate) for downstream audio nodes.

---

## Example Workflows

Load any `.json` file from this repo via **File → Load** in ComfyUI.

| File | Description |
|------|-------------|
| `Suno_CreateMusic_Example.json` | Style → Suno Create Music → Save Audio |
| `Suno_LyricsToSong_Example.json` | Generate Lyrics → Create Music with vocals → Save Audio |

**Create Music:**
```
[🔑 API Key] ──────────────────────────────────────┐
                                                    ↓
[🎵 Create Music] → audio_url_1 → [🎵 Save Audio] → audio → [Preview Audio]
```

**Lyrics → Song:**
```
[🔑 API Key] ─────────────────────────────────────────────────────────────┐
                                                                           ↓
[🎵 Generate Lyrics] → lyrics ──→ [🎵 Create Music (instrumental=False)] → [🎵 Save Audio]
```

---

## API

This node pack uses the **muapi.ai** API under the hood:
- **Create Music:**     `POST https://api.muapi.ai/api/v1/suno-create-music`
- **Remix:**            `POST https://api.muapi.ai/api/v1/suno-remix-music`
- **Extend:**           `POST https://api.muapi.ai/api/v1/suno-extend-music`
- **Sounds:**           `POST https://api.muapi.ai/api/v1/suno-generate-sounds`
- **Lyrics:**           `POST https://api.muapi.ai/api/v1/suno-generate-lyrics`
- **Boost Style:**      `POST https://api.muapi.ai/api/v1/suno-boost-music-style`
- **Add Vocals:**       `POST https://api.muapi.ai/api/v1/suno-add-vocals`
- **Mashup:**           `POST https://api.muapi.ai/api/v1/suno-generate-mashup`
- **Add Instrumental:** `POST https://api.muapi.ai/api/v1/suno-add-instrumental`
- **Poll:**             `GET  https://api.muapi.ai/api/v1/predictions/{id}/result`
- **Upload:**           `POST https://api.muapi.ai/api/v1/upload_file`

Authentication is a single `x-api-key` header — no session tokens required.

Suno music endpoints typically return **two** audio tracks per generation; both URLs are exposed as `audio_url_1` and `audio_url_2`.

---

## Requirements

- Python ≥ 3.8
- `requests` ≥ 2.28 · `numpy` ≥ 1.23 · `torch` ≥ 2.0 · `torchaudio` ≥ 2.0

---

## Want More Models?

This repo is focused on Suno only. If you need access to **100+ models** — Kling, Veo3, Flux, HiDream, GPT-image-1.5, Imagen4, Wan, Seedance, lipsync, image enhancement and more — check out the full MuAPI ComfyUI node pack:

**[SamurAIGPT/muapi-comfyui](https://github.com/SamurAIGPT/muapi-comfyui)** — ComfyUI nodes for every muapi.ai model in one place.

---

## License

MIT © 2026
