# Nexus Server Operations

Use this guide on the Ubuntu server at `~/Nexus`.

## One-command setup or update

Run this on `y-core` to pull the latest code, install/build the voice console, auto-start `nexus_server.py` and the voice console, and configure persistent HTTPS through Tailscale:

```bash
cd ~/Nexus && git pull origin main && bash ./scripts/install-voice-console-service.sh && sudo tailscale serve --bg http://127.0.0.1:3001 && tailscale serve status
```

If Tailscale is not installed yet, run this once first:

```bash
curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up
```

Then run the one-command setup above again.

After it completes, open the HTTPS hostname printed by `tailscale serve status` on the tablet.

## Pull and apply updates

```bash
cd ~/Nexus
git pull origin main
source ./scripts/set-nexus-environment.sh
systemctl --user daemon-reload
systemctl --user restart nexus-voice-console.service
```

`git pull` updates files only. The restart makes the voice console use the new code and `nexus.config.json` values.

## Check the voice console

```bash
systemctl --user status nexus-voice-console.service
```

It should say:

```text
Active: active (running)
```

View live logs:

```bash
journalctl --user -u nexus-voice-console.service -f
```

Stop viewing logs with `Ctrl+C`.

## Install or repair the service

Run this after a fresh setup or if the service is missing:

```bash
cd ~/Nexus
bash ./scripts/install-voice-console-service.sh
```

The installer builds the voice console, installs both user services, enables automatic startup after reboot, and enables automatic restart after a crash.

## Enable HTTPS permanently

Install and connect Tailscale once:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Configure Tailscale Serve once with the voice console as its local target:

```bash
sudo tailscale serve --bg http://127.0.0.1:3001
tailscale serve status
```

Open the HTTPS hostname shown by `tailscale serve status` on the tablet. The `--bg` configuration is saved by Tailscale and automatically resumes after the server or Tailscale daemon restarts. You do not need to regenerate certificates after a reboot.

The tablet and Ubuntu server must both be connected to the same Tailscale network. The tablet should use the HTTPS hostname, not the server IP with port `3001`.

## After a server reboot

Check the voice console and HTTPS mapping:

```bash
systemctl --user status nexus-voice-console.service --no-pager
tailscale serve status
```

Expected results:

```text
Active: active (running)
https://<server-name>.<tailnet-name>.ts.net
```

The `systemctl --user` service is enabled for automatic startup by the installer. `tailscale serve --bg` is persistent independently of the Nexus repository.

## Check both services

```bash
systemctl --user status nexus.service --no-pager
systemctl --user status nexus-voice-console.service --no-pager
```

Both should show `Active: active (running)`.

## Start the Nexus runtime manually

The voice console needs the Nexus runtime running on port `8765`:

```bash
cd ~/Nexus
source ./scripts/set-nexus-environment.sh
python3 nexus_server.py
```

The installer normally manages this as `nexus.service`; use the manual command only for troubleshooting.

## Change the server host or ports

Edit only:

```text
~/Nexus/nexus.config.json
```

The main setting is:

```json
"host": "100.118.250.51"
```

After changing it:

```bash
cd ~/Nexus
source ./scripts/set-nexus-environment.sh
systemctl --user restart nexus-voice-console.service
```

Restart any manually running Nexus runtime and dashboard processes too, because they read configuration only at startup.

## Private environment values

`.env` is not stored in Git. It contains provider settings and API keys.

After copying `.env` to the server, load it with:

```bash
cd ~/Nexus
source ./scripts/set-nexus-environment.sh
```

Never commit `.env` or paste API keys into `nexus.config.json`.

## If a pull is blocked

Back up the host config first:

```bash
cd ~/Nexus
cp nexus.config.json ~/nexus.config.json.backup
git status --short
git pull origin main
```

If Git reports local changes to `nexus.config.json`:

```bash
cp nexus.config.json ~/nexus.config.json.server
git restore nexus.config.json
git pull origin main
cp ~/nexus.config.json.server nexus.config.json
```

For tracked Python cache conflicts:

```bash
cd ~/Nexus
rm -rf plugins/memory/__pycache__
git pull origin main
```

## Voice console address

The auto-start service listens on port `3001`:

```text
http://100.118.250.51:3001
```

Remote tablet microphone access uses the voice console's direct HTTPS endpoint at `https://<server-host>:3001`. Tailscale Serve remains optional; if enabled, it can still proxy to the HTTPS service with `https+insecure://127.0.0.1:3001`.

The voice console service itself now starts HTTPS using `~/Nexus/nexus-cert.pem` and `~/Nexus/nexus-key.pem`. Copy those two private files to the server before running the installer; they are ignored by Git.

## Run the Python runtime with HTTPS directly

If the certificate and key are stored in `~/Nexus`, start the Python runtime with:

```bash
cd ~/Nexus
source ./scripts/set-nexus-environment.sh
python3 nexus_server.py --https-cert ./nexus-cert.pem --https-key ./nexus-key.pem
```

This serves the runtime on `https://<host>:8765` and the realtime gateway on `wss://<host>:8766/device`. The certificate must include the hostname or IP used by clients. The normal auto-start service remains HTTP unless its service command is changed to include these same flags.
