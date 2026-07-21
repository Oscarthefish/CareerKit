import json
import re
import httpx
from typing import Optional
from .base import AIProvider


class OllamaProvider(AIProvider):

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = 300.0

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_ctx": 8192,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    async def generate_json(self, prompt: str, system: Optional[str] = None) -> dict:
        json_system = (system or "") + "\n\nYou must respond with valid JSON only. No explanation, no markdown fences, just the raw JSON object."
        messages = [
            {"role": "system", "content": json_system.strip()},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.3,
                "num_ctx": 8192,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["message"]["content"]

        # Strip markdown fences if model ignored the format instruction
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content.strip())

        return json.loads(content)

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    model_available = any(
                        m == self.model or m.startswith(self.model + ":") for m in models
                    )
                    return {
                        "status": "ok",
                        "url": self.base_url,
                        "model": self.model,
                        "model_available": model_available,
                        "available_models": models,
                    }
        except httpx.ConnectError:
            return {
                "status": "error",
                "message": f"Cannot connect to Ollama at {self.base_url}. Run: ollama serve",
                "url": self.base_url,
                "model": self.model,
                "model_available": False,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "url": self.base_url,
                "model": self.model,
                "model_available": False,
            }
