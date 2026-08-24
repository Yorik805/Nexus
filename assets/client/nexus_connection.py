"""HTTP boundary between a portable client and the Nexus server."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any


@dataclass
class NexusConnection:
    host: str
    port: int | None = None
    protocol: str = "http"
    timeout: float = 30.0

    def __post_init__(self) -> None:
        self.host = self.host.rstrip("/")

    @property
    def base_url(self) -> str:
        port = f":{self.port}" if self.port is not None else ""
        return f"{self.protocol}://{self.host}{port}"

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ConnectionError(f"Nexus server returned HTTP {exc.code}.") from exc
        except URLError as exc:
            raise ConnectionError(f"Could not connect to Nexus server: {exc.reason}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ConnectionError(f"Invalid response from Nexus server: {exc}") from exc
        if not isinstance(result, dict):
            raise ConnectionError("Nexus server returned a non-object response.")
        return result

    def register(self, device_id: str, device_type: str) -> dict[str, Any]:
        return self._request("POST", "/devices/register", {"device_id": device_id, "device_type": device_type})

    def send_user_message(self, device_id: str, text: str, message_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"device_id": device_id, "text": text}
        if message_id:
            payload["message_id"] = message_id
        result = self._request("POST", "/message", payload)
        response = result.get("response")
        if isinstance(response, dict):
            return response
        return result

    def receive_response(self, response: dict[str, Any]) -> str:
        nested = response.get("response")
        if isinstance(nested, dict):
            response = nested
        text = response.get("text")
        if not isinstance(text, str):
            raise ConnectionError("Nexus response did not contain response.text.")
        return text

    def disconnect(self, device_id: str) -> dict[str, Any]:
        return self._request("POST", "/devices/disconnect", {"device_id": device_id})


class MockNexusConnection:
    """Offline transport for client tests and microphone/TTS demos."""

    def __init__(self) -> None:
        self.registered: list[tuple[str, str]] = []
        self.messages: list[dict[str, str]] = []

    def register(self, device_id: str, device_type: str) -> dict[str, Any]:
        self.registered.append((device_id, device_type))
        return {"status": "SUCCESS", "device_id": device_id}

    def send_user_message(self, device_id: str, text: str, message_id: str | None = None) -> dict[str, Any]:
        message = {"device_id": device_id, "text": text, "message_id": message_id or "mock-message"}
        self.messages.append(message)
        return {"message_id": "mock-response", "text": f"Mock Nexus response to: {text}"}

    def receive_response(self, response: dict[str, Any]) -> str:
        return str(response["text"])

    def disconnect(self, device_id: str) -> dict[str, Any]:
        return {"status": "SUCCESS", "device_id": device_id}