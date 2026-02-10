import asyncio
import json
import logging
import uuid
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.exceptions import (
    GenerationError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

SERVICE_NAME = "ComfyUI"

# Default txt2img workflow template for SDXL Lightning
DEFAULT_WORKFLOW = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "seed": 0,
            "steps": 6,
            "cfg": 1.8,
            "sampler_name": "euler",
            "scheduler": "sgm_uniform",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0],
        },
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "realvisxlV40_v40LightningBakedvae.safetensors",
        },
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "width": 1024,
            "height": 1024,
            "batch_size": 1,
        },
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "",
            "clip": ["4", 1],
        },
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "blurry, low quality, distorted, deformed, ugly, bad anatomy",
            "clip": ["4", 1],
        },
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2],
        },
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "storyforge",
            "images": ["8", 0],
        },
    },
}


class ComfyUIService:
    """Service for generating images via ComfyUI API."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.comfyui_host
        self.static_dir = Path(settings.static_dir) / "images"
        self.static_dir.mkdir(parents=True, exist_ok=True)
        self.poll_interval = 1.0  # seconds between status checks
        self.timeout = 120.0  # max seconds to wait for generation

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "blurry, low quality, distorted, deformed, ugly, bad anatomy",
        seed: int | None = None,
        width: int = 1024,
        height: int = 1024,
        steps: int = 6,
        cfg: float = 1.8,
        checkpoint: str | None = None,
    ) -> str:
        """Generate an image from a text prompt.

        Args:
            prompt: Positive text prompt describing the image.
            negative_prompt: What to avoid in the image.
            seed: Random seed for reproducibility. None = random.
            width: Image width in pixels.
            height: Image height in pixels.
            steps: Number of sampling steps.
            cfg: Classifier-free guidance scale.
            checkpoint: Override the default checkpoint model.

        Returns:
            Path to the saved image file (relative to static dir).

        Raises:
            ServiceUnavailableError: If ComfyUI cannot be reached.
            ServiceTimeoutError: If image generation times out.
            GenerationError: If generation fails.
        """
        workflow = json.loads(json.dumps(DEFAULT_WORKFLOW))

        # Configure the workflow
        workflow["6"]["inputs"]["text"] = prompt
        workflow["7"]["inputs"]["text"] = negative_prompt
        workflow["3"]["inputs"]["seed"] = seed if seed is not None else _random_seed()
        workflow["3"]["inputs"]["steps"] = steps
        workflow["3"]["inputs"]["cfg"] = cfg
        workflow["5"]["inputs"]["width"] = width
        workflow["5"]["inputs"]["height"] = height
        if checkpoint:
            workflow["4"]["inputs"]["ckpt_name"] = checkpoint

        # Queue the workflow
        prompt_id = await self.queue_workflow(workflow)
        logger.info("Queued workflow prompt_id=%s", prompt_id)

        # Wait for completion
        output = await self._wait_for_completion(prompt_id)

        # Download and save the image
        image_path = await self._save_output_image(prompt_id, output)
        logger.info("Image saved to %s", image_path)
        return image_path

    async def queue_workflow(self, workflow: dict) -> str:
        """Submit a workflow to the ComfyUI queue.

        Args:
            workflow: The ComfyUI API-format workflow dict.

        Returns:
            The prompt_id for tracking.

        Raises:
            ServiceUnavailableError: If ComfyUI cannot be reached.
            GenerationError: If the queue request fails.
        """
        client_id = str(uuid.uuid4())
        payload = {"prompt": workflow, "client_id": client_id}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/prompt",
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data["prompt_id"]
        except httpx.ConnectError as e:
            raise ServiceUnavailableError(SERVICE_NAME, str(e)) from e
        except httpx.TimeoutException as e:
            raise ServiceTimeoutError(SERVICE_NAME, timeout=30.0, detail=str(e)) from e
        except httpx.HTTPStatusError as e:
            raise GenerationError(SERVICE_NAME, f"queue failed (HTTP {e.response.status_code}): {e.response.text[:200]}") from e
        except Exception as e:
            raise GenerationError(SERVICE_NAME, f"queue failed: {e}") from e

    async def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """Retrieve a generated image from ComfyUI.

        Args:
            filename: The image filename.
            subfolder: Subfolder within the output directory.
            folder_type: 'output', 'input', or 'temp'.

        Returns:
            Raw image bytes.

        Raises:
            ServiceUnavailableError: If ComfyUI cannot be reached.
            GenerationError: If the image cannot be retrieved.
        """
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/view",
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.content
        except httpx.ConnectError as e:
            raise ServiceUnavailableError(SERVICE_NAME, str(e)) from e
        except httpx.TimeoutException as e:
            raise ServiceTimeoutError(SERVICE_NAME, timeout=30.0, detail=str(e)) from e
        except httpx.HTTPStatusError as e:
            raise GenerationError(SERVICE_NAME, f"image retrieval failed (HTTP {e.response.status_code})") from e
        except Exception as e:
            raise GenerationError(SERVICE_NAME, f"image retrieval failed: {e}") from e

    async def _wait_for_completion(self, prompt_id: str) -> dict:
        """Poll /history until the prompt completes or times out."""
        elapsed = 0.0
        try:
            async with httpx.AsyncClient() as client:
                while elapsed < self.timeout:
                    response = await client.get(
                        f"{self.base_url}/history/{prompt_id}",
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    data = response.json()

                    if prompt_id in data:
                        status = data[prompt_id].get("status", {})
                        if status.get("completed", False) or "outputs" in data[prompt_id]:
                            return data[prompt_id]
                        if status.get("status_str") == "error":
                            raise GenerationError(
                                SERVICE_NAME,
                                f"workflow failed: {status.get('messages', 'unknown error')}",
                            )

                    await asyncio.sleep(self.poll_interval)
                    elapsed += self.poll_interval
        except (ServiceUnavailableError, ServiceTimeoutError, GenerationError):
            raise
        except httpx.ConnectError as e:
            raise ServiceUnavailableError(SERVICE_NAME, f"lost connection while waiting: {e}") from e
        except httpx.TimeoutException as e:
            raise ServiceTimeoutError(SERVICE_NAME, timeout=self.timeout, detail=str(e)) from e
        except Exception as e:
            raise GenerationError(SERVICE_NAME, f"polling failed: {e}") from e

        raise ServiceTimeoutError(SERVICE_NAME, timeout=self.timeout, detail=f"prompt_id={prompt_id}")

    async def _save_output_image(self, prompt_id: str, output: dict) -> str:
        """Download the first output image and save to static directory.

        Returns:
            The filename of the saved image.
        """
        # Find the SaveImage node output
        outputs = output.get("outputs", {})
        for node_id, node_output in outputs.items():
            images = node_output.get("images", [])
            if images:
                image_info = images[0]
                filename = image_info["filename"]
                subfolder = image_info.get("subfolder", "")

                # Download from ComfyUI
                image_bytes = await self.get_image(filename, subfolder)

                # Save locally with a unique name
                local_filename = f"{prompt_id}_{filename}"
                local_path = self.static_dir / local_filename
                local_path.write_bytes(image_bytes)

                return local_filename

        raise GenerationError(SERVICE_NAME, f"no output images for prompt_id={prompt_id}")

    async def check_health(self) -> bool:
        """Check if ComfyUI is reachable.

        Returns:
            True if ComfyUI responds, False otherwise.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/system_stats", timeout=5.0)
                return resp.status_code == 200
        except Exception:
            return False


def _random_seed() -> int:
    """Generate a random seed for image generation."""
    import random
    return random.randint(0, 2**32 - 1)
