# Nexus Server Operations

Use this guide on the Ubuntu server at `~/Nexus`.

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

The installer builds the voice console, installs the user service, enables automatic startup after reboot, and enables automatic restart after a crash.

## Start the Nexus runtime

The voice console needs the Nexus runtime running on port `8765`:

```bash
cd ~/Nexus
source ./scripts/set-nexus-environment.sh
python3 nexus_server.py
```

Keep that terminal or a separate runtime service running.

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

Remote tablet microphone access requires HTTPS. The service itself currently serves HTTP; place it behind a trusted HTTPS reverse proxy for production microphone use.
