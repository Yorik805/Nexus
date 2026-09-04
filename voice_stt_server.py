#!/usr/bin/env python3
"""Low-resource server-side voice capture and Whisper wake-word service."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import ssl
import time
from collections import deque
from pathlib import Path
from typing import Any

import websockets
import numpy as np
from faster_whisper import WhisperModel

LOGGER = logging.getLogger("nexus.voice_stt")
SAMPLE_RATE = 16_000
BYTES_PER_SAMPLE = 2
FRAME_BYTES = SAMPLE_RATE // 10 * BYTES_PER_SAMPLE
WAKE_WORDS = ("hey nexus", "hay nexus", "hey nex us", "hey nxs", "hey ncx", "hey nxc", "hey")


def normalize(text: str) -> str:
    return " ".join("".join(char.lower() if char.isalnum() or char == " " else " " for char in text).split())


def wake_command(text: str) -> tuple[bool, str]:
    normalized = normalize(text)
    for wake in WAKE_WORDS:
        if normalized == wake:
            return True, ""
        prefix = f"{wake} "
        if normalized.startswith(prefix):
            return True, normalized[len(prefix):].strip()
    return False, ""


class VoiceSession:
    def __init__(self, websocket: Any, model: WhisperModel, silence_seconds: float) -> None:
        self.websocket = websocket
        self.model = model
        self.silence_seconds = silence_seconds
        self.audio = bytearray()
        self.pre_roll: deque[bytes] = deque(maxlen=5)
        self.speech_started = False
        self.last_voice = 0.0
        self.armed_until = 0.0
        self.nexus_speaking = False

    async def send(self, payload: dict[str, Any]) -> None:
        await self.websocket.send(json.dumps(payload))

    async def transcribe(self) -> None:
        if not self.audio:
            return
        audio = np.frombuffer(bytes(self.audio), dtype=np.int16).astype(np.float32) / 32768.0
        self.audio.clear()
        self.speech_started = False
        try:
            segments, _ = await asyncio.to_thread(
                self.model.transcribe,
                audio,
                language="en",
                beam_size=1,
                best_of=1,
                temperature=0.0,
                vad_filter=False,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
        except Exception as exc:
            LOGGER.exception("Whisper transcription failed: %s", exc)
            await self.send({"type": "error", "message": "Whisper transcription failed."})
            return
        if not text:
            await self.send({"type": "state", "state": "listening"})
            return
        detected, command = wake_command(text)
        now = time.monotonic()
        if detected:
            self.armed_until = now + 90.0
            await self.send({"type": "wake", "text": text, "command": command, "interrupt": self.nexus_speaking})
        elif now <= self.armed_until:
            command = text
        else:
            command = ""
        await self.send({"type": "transcript", "text": text, "command": command, "final": True, "state": "user_speaking" if command else "listening"})

    @staticmethod
    def is_voice(frame: bytes) -> bool:
        if not frame:
            return False
        samples = memoryview(frame).cast("h")
        energy = sum(abs(sample) for sample in samples) / max(1, len(samples))
        return energy >= 420.0

    async def receive(self) -> None:
        await self.send({"type": "ready", "sample_rate": SAMPLE_RATE, "model": "faster-whisper/tiny-int8", "wake": "Hey Nexus"})
        async for message in self.websocket:
            if isinstance(message, str):
                try:
                    control = json.loads(message)
                except json.JSONDecodeError:
                    continue
                if control.get("type") == "control":
                    self.nexus_speaking = bool(control.get("speaking", False))
                    if control.get("speaking") is False:
                        await self.send({"type": "state", "state": "listening"})
                continue
            if not isinstance(message, bytes):
                continue
            for offset in range(0, len(message), FRAME_BYTES):
                frame = message[offset:offset + FRAME_BYTES]
                now = time.monotonic()
                voice = self.is_voice(frame)
                self.pre_roll.append(frame)
                if voice:
                    if not self.speech_started:
                        self.audio.extend(b"".join(self.pre_roll))
                        self.speech_started = True
                        await self.send({"type": "state", "state": "user_speaking"})
                    else:
                        self.audio.extend(frame)
                    self.last_voice = now
                elif self.speech_started:
                    self.audio.extend(frame)
                    if now - self.last_voice >= self.silence_seconds:
                        await self.transcribe()
                        self.pre_roll.clear()


async def serve(host: str, port: int, model_name: str, compute_type: str, silence_seconds: float, cert: str | None, key: str | None) -> None:
    LOGGER.info("Loading Whisper model %s (%s)", model_name, compute_type)
    model = WhisperModel(model_name, device="cpu", compute_type=compute_type, cpu_threads=2, num_workers=1)
    ssl_context = None
    if cert and key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=cert, keyfile=key)
    async def handler(websocket: Any) -> None:
        session = VoiceSession(websocket, model, silence_seconds)
        try:
            await session.receive()
        except websockets.exceptions.ConnectionClosed:
            pass
    async with websockets.serve(handler, host, port, ssl=ssl_context, max_size=2**20, ping_interval=20, ping_timeout=20):
        LOGGER.info("Nexus server-side voice STT listening on %s://%s:%s", "wss" if ssl_context else "ws", host, port)
        await asyncio.Future()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--silence-seconds", type=float, default=1.0)
    parser.add_argument("--https-cert")
    parser.add_argument("--https-key")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
    asyncio.run(serve(args.host, args.port, args.model, args.compute_type, args.silence_seconds, args.https_cert, args.https_key))


if __name__ == "__main__":
    main()
