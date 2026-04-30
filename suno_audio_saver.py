"""Suno Audio Saver — downloads an audio URL, saves to disk, returns a ComfyUI AUDIO tensor."""

import os
import requests
import torch

try:
    import folder_paths
except ImportError:
    class folder_paths:
        @staticmethod
        def get_output_directory():
            return os.path.join(os.path.expanduser("~"), "comfyui_output")


class SunoAudioSaver:
    """
    Suno Audio Saver
    -----------------
    Download a Suno audio URL to ComfyUI/output/<save_subfolder>/, then expose
    it as a ComfyUI AUDIO tensor (waveform + sample_rate) for downstream nodes
    (preview, audio splicing, video muxing, etc.).
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "audio_url": ("STRING", {"multiline": False, "default": ""}),
            "save_subfolder": ("STRING", {"default": "suno"}),
            "filename_prefix": ("STRING", {"default": "suno"}),
            "extension": (["mp3", "wav", "m4a", "ogg", "flac"], {"default": "mp3"}),
        }}
    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("audio", "filepath")
    FUNCTION = "run"
    CATEGORY = "🎵 Suno"
    OUTPUT_NODE = True

    def run(self, audio_url, save_subfolder, filename_prefix, extension):
        if not audio_url or not audio_url.strip().startswith("http"):
            return self._err("Invalid URL")

        out_dir = os.path.join(folder_paths.get_output_directory(), save_subfolder)
        os.makedirs(out_dir, exist_ok=True)
        n = 1
        fp = os.path.join(out_dir, f"{filename_prefix}_{n:05d}.{extension}")
        while os.path.exists(fp):
            n += 1
            fp = os.path.join(out_dir, f"{filename_prefix}_{n:05d}.{extension}")

        try:
            print(f"[Suno Saver] Downloading {audio_url[:80]}...")
            r = requests.get(audio_url, stream=True, timeout=300)
            r.raise_for_status()
            with open(fp, "wb") as fh:
                for chunk in r.iter_content(8192):
                    if chunk:
                        fh.write(chunk)

            audio = self._load(fp)
            fname = os.path.basename(fp)
            preview = {"filename": fname, "subfolder": save_subfolder, "type": "output"}
            print(f"[Suno Saver] Saved {fname}")
            return {"ui": {"audio": [preview]}, "result": (audio, fp)}
        except Exception as e:
            return self._err(str(e))

    def _load(self, path):
        """Load audio file as a ComfyUI AUDIO dict: {waveform: [B,C,T], sample_rate: int}."""
        try:
            import torchaudio
            waveform, sr = torchaudio.load(path)
            if waveform.dim() == 2:
                waveform = waveform.unsqueeze(0)
            return {"waveform": waveform, "sample_rate": int(sr)}
        except Exception as e:
            print(f"[Suno Saver] audio decode error: {e}; returning silent placeholder.")
            return {"waveform": torch.zeros(1, 2, 44100), "sample_rate": 44100}

    def _err(self, msg):
        print(f"[Suno Saver] ERROR: {msg}")
        silent = {"waveform": torch.zeros(1, 2, 44100), "sample_rate": 44100}
        return {"ui": {"text": [msg]}, "result": (silent, "ERROR")}


NODE_CLASS_MAPPINGS = {"SunoAudioSaver": SunoAudioSaver}
NODE_DISPLAY_NAME_MAPPINGS = {"SunoAudioSaver": "🎵 Suno Save Audio"}
