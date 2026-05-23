# SPARK Deployment Checklist

Use this checklist before exposing SPARK to the public internet.

## Required secrets
- Set `SPARK_ACCESS_TOKEN` in `.env` to a strong random value.
- Optionally set `GROQ_API_KEY` if you want cloud LLM access.
- Optionally set `CLOUDFLARED_TOKEN` if you are using Cloudflare Tunnel token mode.
- Do not keep `SPARK_ACCESS_TOKEN=change-this-token` in any public or shared environment.

## Local runtime checks
- Confirm `.venv` exists and `start_spark.ps1` launches without warnings.
- Confirm `http://localhost:8000/health` returns `{"status":"ok"}`.
- Confirm `http://localhost:8000/ping` returns `online`.
- Confirm `http://localhost:8000/chat` works with `Authorization: Bearer <SPARK_ACCESS_TOKEN>`.
- Confirm `http://localhost:8000/status` works with the same bearer token.
- Confirm the HUD loads at `http://localhost:8000/` and `/hud`.

## Public tunnel checks
- Replace the placeholder hostname in `cloudflared-config.yml` with a real domain, or use a tunnel token.
- Make sure Cloudflare DNS points the hostname at the tunnel.
- Make sure the tunnel reaches `http://localhost:8000`.
- Confirm the public URL uses HTTPS.
- Confirm protected routes reject missing or invalid tokens.
- Confirm WebSocket routes respond over the same public hostname.

## Smoke-test order
1. `/health`
2. `/ping`
3. `/status` with bearer auth
4. `/chat` with bearer auth
5. `/ws/system` over `ws://` locally or `wss://` publicly
6. `/hud` with bearer auth

## Failure rules
- Fix auth and tunnel config first if remote access fails.
- Fix runtime NameErrors first if the API does not start.
- Fix websocket reachability before treating the HUD as production-ready.
- Do not expose the tunnel if the app still prints placeholder-token warnings.

## Minimum ship criteria
- API starts cleanly.
- Auth works consistently.
- Public tunnel is reachable.
- HUD loads remotely.
- Chat and WebSocket routes respond remotely.
- No placeholder hostname remains in the tunnel config.
