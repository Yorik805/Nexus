# Nexus Voice Console

This is a separate Next.js client for the existing Nexus runtime. It does not duplicate Nexus plugins or runtime logic.

## Configure

Copy `.env.example` to `.env.local` and set the server-side dashboard backend URL:

```env
NEXUS_URL=http://127.0.0.1:8765
NEXUS_DASHBOARD_BACKEND_URL=http://127.0.0.1:11882
```

The dashboard backend must be configured with `NEXUS_RUNTIME_URL`, normally:

```env
NEXUS_RUNTIME_URL=http://127.0.0.1:8765
```

The browser talks only to this app's same-origin `/api/state` and `/api/events` routes. `/api/events` forwards correctly shaped messages directly to Nexus, while `/api/state` reads the original dashboard event feed. This avoids browser CORS and keeps server addresses out of client JavaScript.

## Run the voice console

From any PowerShell terminal, use this complete command:

```powershell
Set-Location "E:\Nexus\assets\web_client\nexus-voice-console"; if (!(Test-Path "node_modules")) { npm install }; npm run dev -- -p 3001
```

Then open http://localhost:3001.

The client expects the Nexus dashboard backend to already be running on port `11882`, with that backend forwarding to Nexus on port `8765`.

For a normal local setup, start the backend first in another terminal:

```powershell
Set-Location "E:\Nexus"; $env:NEXUS_DASHBOARD_PORT = "11882"; $env:NEXUS_RUNTIME_URL = "http://127.0.0.1:8765"; python .\nexus_dashboard_server.py
```

Start Nexus itself in another terminal if it is not already running:

```powershell
Set-Location "E:\Nexus"; .\scripts\Set-NexusEnvironment.ps1; python .\nexus_server.py
```

The client runs on port `3001` so it does not replace or conflict with the original dashboard on port `3000`. For a LAN/Tailscale browser connection, use the network URL printed by Next.js.

### Auto-start on the Linux server

From `~/Nexus`, run once:

```bash
bash ./scripts/install-voice-console-service.sh
```

The service builds the client, starts it on port `3001`, starts automatically after reboot, and restarts after a crash. View logs with:

```bash
journalctl --user -u nexus-voice-console.service -f
```

## HTTPS for microphone access

Microphone access is allowed over plain HTTP on `localhost`, but a network address such as `100.118.250.51` must use HTTPS. The browser must also trust the certificate.

### Quick local HTTPS

For testing on the same computer, Next.js can generate a self-signed certificate:

```powershell
Set-Location "E:\Nexus\assets\web_client\nexus-voice-console"; npm run dev -- -p 3001 --experimental-https
```

Open `https://localhost:3001` and continue past the browser certificate warning.

### Trusted HTTPS for the network IP

Install `mkcert` once, then create a certificate containing both network addresses:

```powershell
winget install FiloSottile.mkcert
Set-Location "E:\Nexus\assets\web_client\nexus-voice-console"; mkcert -install; mkcert -key-file nexus-key.pem -cert-file nexus-cert.pem localhost 127.0.0.1 100.102.195.9 100.118.250.51 100.104.252.100
```

If the current PowerShell says `mkcert is not recognized` immediately after installation, use the installed binary directly:

```powershell
$mkcert = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\FiloSottile.mkcert_Microsoft.Winget.Source_8wekyb3d8bbwe\mkcert.exe"; Set-Location "E:\Nexus\assets\web_client\nexus-voice-console"; & $mkcert -install; & $mkcert -key-file nexus-key.pem -cert-file nexus-cert.pem localhost 127.0.0.1 100.102.195.9 100.118.250.51 100.104.252.100
```

Start Next.js with that certificate:

```powershell
Set-Location "E:\Nexus\assets\web_client\nexus-voice-console"; npm run dev -- -H 0.0.0.0 -p 3001 --experimental-https --experimental-https-key nexus-key.pem --experimental-https-cert nexus-cert.pem
```

Then open:

```text
https://100.102.195.9:3001
```

`100.102.195.9` is the Nexus computer's Tailscale address. Do not use the tablet's own IP address in the URL. If the tablet cannot connect, confirm that Tailscale is connected on both devices and that Windows Firewall allows inbound TCP port `3001`.

For the microphone to work without a certificate warning, install/trust the mkcert root CA on the tablet too. Run `mkcert -CAROOT` on the Nexus computer, copy `rootCA.pem` from that folder to the tablet, and install it as a trusted certificate according to the tablet's OS/browser instructions. The certificate itself is already valid for `100.102.195.9`.

Run `mkcert -install` on each device that will open the client, or the browser will not trust the certificate. Keep `nexus-key.pem` private and do not commit either generated PEM file.

### Manual commands

```powershell
npm install
npm run dev -- -p 3001
```

Open http://localhost:3001.

## Live behavior

- Runtime events are read from the same `/api/state` data as the original Nexus dashboard.
- Debug mode displays the dashboard event records using `TIME`, `TYPE`, `SOURCE`, and `PAYLOAD`.
- Voice requests are sent as `USER_MESSAGE` events with source `web-client`.
- The browser uses `getUserMedia` for permission-controlled microphone access. The stream stays active while the mic is enabled, but ordinary speech is ignored until the wake phrase `Hey Nexus` is detected.
- Speech recognition uses the browser's `SpeechRecognition` or `webkitSpeechRecognition` implementation.
- Nexus responses are spoken through `speechSynthesis` when available.
- If `FISH_AUDIO_API_KEY` and `FISH_AUDIO_VOICE_ID` are configured, responses use the server-side Fish Audio API first; otherwise the browser TTS fallback is used.
- Speech detected while Nexus is speaking only interrupts after the wake phrase is detected, preventing most Nexus echo from becoming a user request.
- After `Hey Nexus`, command listening stays active for 90 seconds. Any recognized speech during that window resets the timer. When Nexus finishes speaking, the 90-second command window starts again; after silence it returns to standby while passive wake-word monitoring remains available.
- While the command window is active, interim recognition text is shown immediately and the voice panel switches to `USER SPEAKING`; a blank or unusable final result returns to `LISTENING` without stopping the recognizer.
- If a wake-word interruption contains no meaningful command, playback resumes after a short grace period from the nearest browser speech boundary. Exact word-perfect resumption depends on browser TTS boundary support.
- Browser speech recognition and text-to-speech support vary by browser. Continuous recognition can stop and restart automatically, and exact speech resumption is not attempted after interruption.
- When the browser ends a recognition session, the client automatically retries with increasing delays and keeps the microphone stream enabled. If the browser speech service remains unavailable after several retries, toggle the mic once to re-authorize it.
- If the UI reports `Speech recognition error: network`, Nexus is still connected; the browser's speech-recognition service is unavailable. The VS Code/Electron integrated browser can expose this limitation, so use the current Chrome or Edge browser at `http://localhost:3001` for wake-word recognition.
- The wake phrase is intentionally still active during Nexus TTS: only `Hey Nexus` is allowed to interrupt playback. A short post-TTS guard discards buffered playback recognition so the spoken response cannot become a user command.
- Wake detection accepts `hey` by itself plus close browser recognition variants such as `hay nexus`, `he nexus`, `hey nekus`, `hey nex us`, `hey nxs`, `hey ncx`, and `hey nxc`; matching is bounded by a small edit-distance check so unrelated speech is still ignored.
- Android may still play a system sound when its browser speech service starts or ends. A web page cannot mute that OS-level sound; do not retry-start recognition rapidly, and use the native Android wake-word route for genuinely silent always-on operation.

## Fish Audio hardware note

This client uses the hosted Fish Audio API when configured, so local Fish inference requires **no CPU, GPU, or model download**. You only need an API key and voice/reference ID in the server environment.

Running Fish Speech locally is a different setup. The current Fish Audio S2 Pro model is a 4B-parameter model with GPU-oriented inference; the official project demonstrates performance on an NVIDIA H200 and does not specify a single minimum CPU-only configuration. CPU-only local synthesis is therefore not a practical low-latency target. For a tablet or normal server, use the hosted API. For self-hosting, plan around a CUDA-capable GPU with sufficient VRAM and follow the official installation guidance: https://speech.fish.audio/install/

## Runtime limitation

The current Nexus dashboard backend exposes recent events through polling, not SSE or a WebSocket event stream. This client polls `/api/state` every two seconds to match the original dashboard and avoid inventing a new runtime transport.
