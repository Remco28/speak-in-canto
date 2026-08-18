# Deploying on the Home Server (LAN-only)

Run Canto Reader from source on a headless Ubuntu server, reachable from other
devices on the LAN. No Docker, no public exposure.

> **Security:** the app has no authentication. Bind it to the LAN only and do
> not forward port 8734 from your router.

## 1. Layout

Clone/copy the repo to `/opt/canto-reader` (owned by a dedicated `canto` user or
your login user):

```bash
sudo mkdir -p /opt/canto-reader
sudo chown "$USER":"$USER" /opt/canto-reader
git clone <your-repo-url> /opt/canto-reader
cd /opt/canto-reader
```

## 2. Python environment

```bash
cd /opt/canto-reader
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

The server does not need GUI dependencies (no pywebview); waitress suffices.

## 3. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env` and set:

```env
FLASK_ENV=production
PORT=8734
GOOGLE_APPLICATION_CREDENTIALS=/opt/canto-reader/secrets/gcp-sa.json
OPENROUTER_API_KEY=<your-key>
OPENROUTER_MODEL=openrouter/free
```

Copy your Google service-account JSON to
`/opt/canto-reader/secrets/gcp-sa.json`, or use `GCP_SERVICE_ACCOUNT_JSON`
inline instead of the file path.

## 4. Dictionary data (optional)

```bash
.venv/bin/python scripts/prepare_dictionary_data.py \
  --cedict /path/to/cc-cedict.u8 \
  --cccanto /path/to/cc-canto.u8
```

Default paths point at `data/dictionaries/…` relative to the repo — no override
needed if you use the helper script.

## 5. systemd unit

Copy the example unit and adjust `User`, `WorkingDirectory`, and
`EnvironmentFile` if your paths differ:

```bash
sudo cp deploy/canto-reader.service /etc/systemd/system/canto-reader.service
sudo systemctl daemon-reload
sudo systemctl enable --now canto-reader
```

Check status/logs:

```bash
systemctl status canto-reader
journalctl -u canto-reader -f
```

## 6. Firewall

Allow TCP 8734 on the LAN interface only (example with `ufw`):

```bash
sudo ufw allow from 192.168.0.0/16 to any port 8734 proto tcp
sudo ufw reload
```

## 7. Access

From another device on the LAN:

```
http://<server-lan-ip>:8734
```

No TLS/domain is needed for LAN use. If you later want internet access, add a
reverse proxy (e.g. Caddy) and reconsider protection, since the app has no login.

## Update

```bash
cd /opt/canto-reader
git pull
.venv/bin/pip install -r requirements.txt
sudo systemctl restart canto-reader
```
