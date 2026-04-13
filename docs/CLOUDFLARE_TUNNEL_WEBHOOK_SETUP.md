# Cloudflare Tunnel + Webhook Setup (S.P.A.R.K.)

This guide exposes your local FastAPI server over HTTPS without opening router ports.

## 1) Prerequisites

- `cloudflared` installed (Windows): https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
- A Cloudflare-managed domain
- Running backend on `http://127.0.0.1:8000`

## 2) Create and route the tunnel

```powershell
cloudflared tunnel login
cloudflared tunnel create spark-core
cloudflared tunnel route dns spark-core spark-api.yourdomain.com
```

This prints a tunnel UUID and creates credentials under your Cloudflare profile directory.

## 3) Create local tunnel config

Create `%USERPROFILE%\.cloudflared\config.yml`:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: C:\Users\<YOUR_USER>\.cloudflared\<TUNNEL_UUID>.json

ingress:
  - hostname: spark-api.yourdomain.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

## 4) Start the tunnel

```powershell
cloudflared tunnel run spark-core
```

Your backend is now reachable at:

- `https://spark-api.yourdomain.com/webhooks/telegram`
- `https://spark-api.yourdomain.com/webhooks/whatsapp`
- `https://spark-api.yourdomain.com/webhooks/social/generic`

## 5) Secure webhook verification (required)

Set these in `.env`:

```env
SPARK_WEBHOOK_SECRET=<long-random-secret>
SPARK_ALLOW_UNSIGNED_WEBHOOKS=false
SPARK_TELEGRAM_SECRET_TOKEN=<telegram-secret-header-token>
SPARK_WHATSAPP_VERIFY_TOKEN=<meta-verify-token>
TELEGRAM_BOT_TOKEN=<telegram-bot-token>
WHATSAPP_ACCESS_TOKEN=<meta-whatsapp-access-token>
WHATSAPP_PHONE_NUMBER_ID=<meta-phone-number-id>
```

HMAC signatures are validated against `SPARK_WEBHOOK_SECRET`.

## 6) Provider configuration

### Telegram

- Webhook URL: `https://spark-api.yourdomain.com/webhooks/telegram`
- Set Telegram secret token to match `SPARK_TELEGRAM_SECRET_TOKEN`

### WhatsApp Cloud API

- Verify URL: `https://spark-api.yourdomain.com/webhooks/whatsapp`
- Verify token: `SPARK_WHATSAPP_VERIFY_TOKEN`
- Event callback URL: `https://spark-api.yourdomain.com/webhooks/whatsapp`

## 7) Health checks

- Runtime webhook status: `GET /webhooks/health`
- Core health: `GET /api/health`
- Runtime diagnostics: `GET /api/health/runtime`

## 8) Security notes

- Do not expose `:8000` directly to the internet.
- Keep `SPARK_ALLOW_UNSIGNED_WEBHOOKS=false` in production.
- Rotate webhook secrets periodically.
- Use separate tunnel hostnames for staging and production.
