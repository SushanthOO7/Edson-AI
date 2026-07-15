from typing import Any

import httpx

from app.core.config import Settings


class CreateAIProviderError(RuntimeError):
    pass


class CreateAIProvider:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def is_mock(self) -> bool:
        return self.settings.createai_mock or not self.settings.createai_query_url

    async def query(
        self,
        *,
        system_prompt: str,
        query: str,
        session_id: str | None = None,
        response_schema: dict[str, Any] | None = None,
        response_schema_name: str = "servicenow_response",
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if self.is_mock:
            raise CreateAIProviderError("CreateAI provider is in mock mode.")

        payload: dict[str, Any] = {
            "endpoint": "query",
            "action": "query",
            "model_provider": self.settings.createai_model_provider,
            "model_name": self.settings.createai_model_name,
            "query": query,
            "model_params": {
                "temperature": self.settings.createai_temperature,
                "top_p": self.settings.createai_top_p,
                "system_prompt": system_prompt,
            },
            "enable_search": False,
            "enable_history": bool(self.settings.createai_enable_history and session_id),
            "response_format": {"type": "json"},
        }
        if session_id:
            payload["session_id"] = session_id
        if history is not None:
            payload["history"] = history
        response_format = self._build_model_response_format(response_schema, response_schema_name)
        if response_format:
            payload["model_params"]["response_format"] = response_format

        headers = {"Content-Type": "application/json"}
        if self.settings.createai_api_key:
            if self.settings.createai_api_key_header.lower() == "authorization":
                headers["Authorization"] = f"Bearer {self.settings.createai_api_key}"
            else:
                headers[self.settings.createai_api_key_header] = self.settings.createai_api_key

        try:
            async with httpx.AsyncClient(timeout=self.settings.createai_timeout_seconds) as client:
                response = await client.post(
                    str(self.settings.createai_query_url),
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise CreateAIProviderError(f"CreateAI request failed: {exc}") from exc
        except ValueError as exc:
            raise CreateAIProviderError("CreateAI returned a non-JSON response.") from exc

        if not isinstance(data, dict):
            raise CreateAIProviderError("CreateAI returned an unexpected response shape.")
        return data

    @staticmethod
    def _build_model_response_format(
        response_schema: dict[str, Any] | None,
        response_schema_name: str,
    ) -> dict[str, Any] | None:
        if not response_schema:
            return None
        return {
            "type": "json_schema",
            "json_schema": {
                "name": response_schema_name,
                "schema": response_schema,
                "strict": True,
            },
        }
