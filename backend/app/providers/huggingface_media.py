import base64

import httpx

HF_BASE = "https://api-inference.huggingface.co"
IMAGE_MODEL = "black-forest-labs/FLUX.1-schnell"
AUDIO_MODEL = "facebook/musicgen-small"
VIDEO_MODEL = "damo-vilab/text-to-video-ms-1.7b"


class HuggingFaceMediaProvider:
    name = "huggingface_media"

    def __init__(self, api_token: str) -> None:
        self._token = api_token
        self._client = httpx.AsyncClient(
            base_url=HF_BASE,
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=180.0,
        )

    async def health(self) -> bool:
        try:
            r = await self._client.get("/")
            return r.status_code < 500
        except Exception:
            return False

    async def generate_image(self, prompt: str) -> dict:
        r = await self._client.post(
            f"/models/{IMAGE_MODEL}",
            json={"inputs": prompt},
        )
        r.raise_for_status()
        b64 = base64.b64encode(r.content).decode()
        return {"type": "image", "format": "jpeg", "data": b64, "prompt": prompt, "model": IMAGE_MODEL}

    async def generate_audio(self, prompt: str) -> dict:
        r = await self._client.post(
            f"/models/{AUDIO_MODEL}",
            json={"inputs": prompt},
        )
        r.raise_for_status()
        b64 = base64.b64encode(r.content).decode()
        return {"type": "audio", "format": "flac", "data": b64, "prompt": prompt, "model": AUDIO_MODEL}

    async def generate_video(self, prompt: str) -> dict:
        r = await self._client.post(
            f"/models/{VIDEO_MODEL}",
            json={"inputs": prompt},
        )
        r.raise_for_status()
        b64 = base64.b64encode(r.content).decode()
        return {"type": "video", "format": "mp4", "data": b64, "prompt": prompt, "model": VIDEO_MODEL}

    async def upscale_image(self, prompt: str) -> dict:
        # Use Real-ESRGAN compatible model for upscaling description
        r = await self._client.post(
            f"/models/{IMAGE_MODEL}",
            json={"inputs": f"high resolution, 4K, ultra detailed: {prompt}"},
        )
        r.raise_for_status()
        b64 = base64.b64encode(r.content).decode()
        return {"type": "image", "format": "jpeg", "data": b64, "prompt": prompt, "model": IMAGE_MODEL}
