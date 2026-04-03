"""
SPARK Combat Mode — Central FastAPI Router
==========================================
All routes under /api/combat/* are gated by require_combat_mode dependency.
The /auth/* routes are un-gated (they ARE the authentication mechanism).
"""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .mode_gate import (
    require_combat_mode,
    passphrase_is_set,
    set_passphrase,
    verify_passphrase,
    reset_passphrase,
    issue_token,
    revoke_all,
)

router = APIRouter(prefix="/api/combat", tags=["combat"])


# ─────────────────────────────────────────────────────────────────────────────
#  AUTHENTICATION  (no combat-token required — these ARE the gate)
# ─────────────────────────────────────────────────────────────────────────────

class ActivateRequest(BaseModel):
    passphrase: str = Field(..., min_length=8)

class SetPassphraseRequest(BaseModel):
    passphrase: str = Field(..., min_length=8)


@router.get("/auth/status")
async def auth_status():
    """Check whether a combat passphrase has ever been set."""
    return {
        "passphrase_configured": passphrase_is_set(),
        "mode": "COMBAT",
    }


@router.post("/auth/setup")
async def setup_passphrase(req: SetPassphraseRequest):
    """First-run endpoint: set the combat passphrase."""
    if passphrase_is_set():
        raise HTTPException(400, "Passphrase already set. Use /auth/activate to authenticate.")
    set_passphrase(req.passphrase)
    return {"status": "PASSPHRASE_SET"}


@router.post("/auth/activate")
async def activate_combat(req: ActivateRequest):
    """Validate passphrase and issue a combat session token."""
    if not passphrase_is_set():
        raise HTTPException(400, "Passphrase not configured. Call /auth/setup first.")
    if not verify_passphrase(req.passphrase):
        raise HTTPException(403, "Invalid passphrase.")
    token = issue_token()
    return {"status": "COMBAT_MODE_ACTIVE", "token": token}


@router.post("/auth/deactivate")
async def deactivate_combat(_token: str = Depends(require_combat_mode)):
    """Revoke all active combat sessions."""
    revoke_all()
    return {"status": "COMBAT_MODE_DEACTIVATED"}


@router.post("/auth/reset")
async def reset_combat_passphrase():
    """Delete stored passphrase hash so a new one can be set via /auth/setup.
    Called when user clicks 'Forgot passphrase?' in the UI.
    Protected only by SPARK's existing network access controls."""
    reset_passphrase()
    return {"status": "PASSPHRASE_RESET", "message": "Call /auth/setup to configure a new passphrase."}


# ─────────────────────────────────────────────────────────────────────────────
#  OPSEC
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/opsec/check")
async def opsec_check(_token: str = Depends(require_combat_mode)):
    from .opsec.vpn_check import run_vpn_check
    result = await run_vpn_check()
    return result


@router.get("/opsec/scope")
async def get_scope(_token: str = Depends(require_combat_mode)):
    from .opsec.scope_enforcer import scope_enforcer
    return {"targets": scope_enforcer.get_targets()}


@router.post("/opsec/scope/add")
async def add_scope_target(body: dict, _token: str = Depends(require_combat_mode)):
    from .opsec.scope_enforcer import scope_enforcer
    target = body.get("target", "").strip()
    if not target:
        raise HTTPException(400, "target is required.")
    scope_enforcer.add_target(target)
    return {"status": "ADDED", "target": target, "targets": scope_enforcer.get_targets()}


@router.delete("/opsec/scope/{target}")
async def remove_scope_target(target: str, _token: str = Depends(require_combat_mode)):
    from .opsec.scope_enforcer import scope_enforcer
    scope_enforcer.remove_target(target)
    return {"status": "REMOVED", "target": target}


# ─────────────────────────────────────────────────────────────────────────────
#  VAULT
# ─────────────────────────────────────────────────────────────────────────────

class VaultSetRequest(BaseModel):
    key: str
    value: str
    passphrase: str

class VaultGetRequest(BaseModel):
    key: str
    passphrase: str


@router.post("/vault/set")
async def vault_set(req: VaultSetRequest, _token: str = Depends(require_combat_mode)):
    from .opsec.vault import combat_vault
    combat_vault.set_secret(req.key, req.value, req.passphrase)
    return {"status": "STORED", "key": req.key}


@router.post("/vault/get")
async def vault_get(req: VaultGetRequest, _token: str = Depends(require_combat_mode)):
    from .opsec.vault import combat_vault
    value = combat_vault.get_secret(req.key, req.passphrase)
    if value is None:
        raise HTTPException(404, f"Key '{req.key}' not found in vault.")
    return {"key": req.key, "value": value}


@router.post("/vault/list")
async def vault_list(body: dict, _token: str = Depends(require_combat_mode)):
    from .opsec.vault import combat_vault
    passphrase = body.get("passphrase", "")
    keys = combat_vault.list_keys(passphrase)
    return {"keys": keys}


# ─────────────────────────────────────────────────────────────────────────────
#  IDENTITY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/identity/username/{username}")
async def hunt_username(
    username: str,
    background_tasks: BackgroundTasks,
    _token: str = Depends(require_combat_mode),
):
    """Stream username hunt results via WebSocket; HTTP returns job_id."""
    from .identity.sherlock_wrapper import start_username_hunt
    job_id = await start_username_hunt(username)
    return {"status": "STARTED", "job_id": job_id, "username": username}


@router.get("/identity/email/{email}")
async def hunt_email(email: str, _token: str = Depends(require_combat_mode)):
    from .identity.email_intel import run_email_intel
    result = await run_email_intel(email)
    return result


@router.get("/identity/holehe/{email}")
async def holehe_check(email: str, _token: str = Depends(require_combat_mode)):
    from .identity.holehe_wrapper import run_holehe
    result = await run_holehe(email)
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  RECON
# ─────────────────────────────────────────────────────────────────────────────

class PassiveReconRequest(BaseModel):
    target: str
    modules: list[str] = ["shodan", "harvester", "subfinder"]

class ActiveReconRequest(BaseModel):
    target: str
    scan_type: str = "basic"     # basic | full | stealth | vuln


@router.post("/recon/passive")
async def passive_recon(req: PassiveReconRequest, _token: str = Depends(require_combat_mode)):
    from .recon.passive import run_passive_recon
    from .opsec.scope_enforcer import scope_enforcer, OutOfScopeError
    try:
        scope_enforcer.assert_in_scope(req.target)
    except OutOfScopeError as e:
        raise HTTPException(403, str(e))
    result = await run_passive_recon(req.target, req.modules)
    return result


@router.post("/recon/active")
async def active_recon(req: ActiveReconRequest, _token: str = Depends(require_combat_mode)):
    from .recon.active import run_active_recon
    from .opsec.scope_enforcer import scope_enforcer, OutOfScopeError
    try:
        scope_enforcer.assert_in_scope(req.target)
    except OutOfScopeError as e:
        raise HTTPException(403, str(e))
    result = await run_active_recon(req.target, req.scan_type)
    return result


@router.get("/recon/engagements")
async def list_engagements(_token: str = Depends(require_combat_mode)):
    from .recon.engagement import list_engagements as _list
    return {"engagements": _list()}


@router.post("/recon/engagements")
async def create_engagement(body: dict, _token: str = Depends(require_combat_mode)):
    from .recon.engagement import EngagementManager
    mgr = EngagementManager(
        target=body.get("target", "unknown"),
        description=body.get("description", ""),
    )
    await mgr.begin()
    return {"engagement_id": mgr.engagement_id, "target": mgr.target}


# ─────────────────────────────────────────────────────────────────────────────
#  SIGINT
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/sigint/feeds")
async def get_sigint_feeds(_token: str = Depends(require_combat_mode)):
    from .sigint.feed_aggregator import aggregate_feeds
    result = await aggregate_feeds()
    return result


@router.get("/sigint/cve")
async def search_cves(q: str = "", limit: int = 50, _token: str = Depends(require_combat_mode)):
    from .sigint.cve_indexer import search_cves as _search
    result = await _search(q, limit)
    return result


@router.post("/sigint/cve/sync")
async def sync_cves(_token: str = Depends(require_combat_mode)):
    from .sigint.cve_indexer import sync_nvd_feed
    asyncio.create_task(sync_nvd_feed())
    return {"status": "SYNC_STARTED"}


@router.get("/sigint/sentiment")
async def sigint_sentiment(topic: str, _token: str = Depends(require_combat_mode)):
    from .sigint.nlp_sentiment import analyze_sentiment
    result = await analyze_sentiment(topic)
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  TOR GATEWAY
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/tor/registry")
async def get_onion_registry(_token: str = Depends(require_combat_mode)):
    from .tor.onion_registry import get_all_sites
    return {"sites": get_all_sites()}


@router.post("/tor/verify")
async def verify_onion(body: dict, _token: str = Depends(require_combat_mode)):
    from .tor.site_verifier import verify_site
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(400, "url is required.")
    result = await verify_site(url)
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  SELF-BUILD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/self-build/capabilities")
async def get_capabilities(_token: str = Depends(require_combat_mode)):
    from .self_build.capability_manager import get_capability_status
    return get_capability_status()


@router.post("/self-build/install/{capability}")
async def install_capability(capability: str, _token: str = Depends(require_combat_mode)):
    from .self_build.capability_manager import request_install
    result = await request_install(capability)
    return result


@router.get("/self-build/techniques")
async def get_techniques(_token: str = Depends(require_combat_mode)):
    from .self_build.technique_scorer import get_all_techniques
    return {"techniques": get_all_techniques()}


@router.post("/self-build/debrief/{engagement_id}")
async def create_debrief(engagement_id: str, _token: str = Depends(require_combat_mode)):
    from .self_build.debrief_synthesizer import synthesize_debrief
    result = await synthesize_debrief(engagement_id)
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  WIFI AUDIT  (Commit 3)
# ─────────────────────────────────────────────────────────────────────────────

class WifiCaptureRequest(BaseModel):
    bssid:     str
    channel:   int
    interface: str = "wlan0mon"
    duration:  int = 60


@router.get("/wifi/scan")
async def wifi_scan(interface: str = "wlan0", _token: str = Depends(require_combat_mode)):
    """Enumerate nearby WiFi networks."""
    from .wifi.scanner import scan_wifi
    networks = await scan_wifi(interface)
    return {"networks": networks}


@router.post("/wifi/capture")
async def wifi_capture(req: WifiCaptureRequest, _token: str = Depends(require_combat_mode)):
    """Capture a WPA handshake for offline auditing."""
    from .wifi.handshake import capture_handshake
    cap_file = await capture_handshake(
        bssid=req.bssid, channel=req.channel,
        interface=req.interface, duration_secs=req.duration,
    )
    return {"cap_file": cap_file, "captured": cap_file is not None}


@router.get("/wifi/benchmark")
async def wifi_benchmark(_token: str = Depends(require_combat_mode)):
    """GPU hashcat benchmark for WPA2 crack-time estimation."""
    from .wifi.audit import benchmark_hashcat
    return await benchmark_hashcat()


# ─────────────────────────────────────────────────────────────────────────────
#  SECURITY STACK  (Commit 4)
# ─────────────────────────────────────────────────────────────────────────────

class CaptureRequest(BaseModel):
    interface: str = "eth0"
    bpf_filter: str = ""
    max_packets: int = 500

class ZapScanRequest(BaseModel):
    target_url: str
    zap_url:    str = "http://localhost:8080"
    api_key:    str = ""
    scan_type:  str = "spider"

class MispEventRequest(BaseModel):
    title:       str
    description: str
    tlp:         str = "amber"

class MispSearchRequest(BaseModel):
    value: str
    limit: int = 20


@router.post("/security/capture/start")
async def start_packet_capture(req: CaptureRequest, _token: str = Depends(require_combat_mode)):
    """Start a live Wireshark/pyshark capture job."""
    from .security.wireshark_capture import start_capture
    job_id = await start_capture(req.interface, req.bpf_filter, req.max_packets)
    return {"job_id": job_id, "status": "RUNNING"}


@router.delete("/security/capture/{job_id}")
async def stop_packet_capture(job_id: str, _token: str = Depends(require_combat_mode)):
    from .security.wireshark_capture import stop_capture
    stopped = stop_capture(job_id)
    return {"job_id": job_id, "stopped": stopped}


@router.get("/security/capture")
async def list_packet_captures(_token: str = Depends(require_combat_mode)):
    from .security.wireshark_capture import list_captures
    return {"captures": list_captures()}


@router.post("/security/zap/scan")
async def zap_scan(req: ZapScanRequest, _token: str = Depends(require_combat_mode)):
    """Run an OWASP ZAP web application scan."""
    from .security.zap_scanner import run_zap_scan
    return await run_zap_scan(req.target_url, req.zap_url, req.api_key, req.scan_type)


@router.post("/security/misp/incident")
async def misp_create_incident(req: MispEventRequest, _token: str = Depends(require_combat_mode)):
    """Create a MISP threat intelligence incident event."""
    import os
    from .security.misp_client import MispClient
    misp_url = os.getenv("MISP_URL", "")
    misp_key = os.getenv("MISP_API_KEY", "")
    if not misp_url or not misp_key:
        raise HTTPException(503, "Set MISP_URL and MISP_API_KEY environment variables.")
    client = MispClient(misp_url, misp_key)
    return await client.create_incident_event(req.title, req.description, req.tlp)


@router.post("/security/misp/search")
async def misp_search(req: MispSearchRequest, _token: str = Depends(require_combat_mode)):
    """Search MISP for IOCs matching a value."""
    import os
    from .security.misp_client import MispClient
    misp_url = os.getenv("MISP_URL", "")
    misp_key = os.getenv("MISP_API_KEY", "")
    if not misp_url or not misp_key:
        raise HTTPException(503, "Set MISP_URL and MISP_API_KEY environment variables.")
    client = MispClient(misp_url, misp_key)
    return await client.search_iocs(req.value, req.limit)


# ─────────────────────────────────────────────────────────────────────────────
#  PASSWORD AUDIT LAB  (Commit 5)
# ─────────────────────────────────────────────────────────────────────────────

class HashcatRequest(BaseModel):
    hash_file: str
    wordlist:  str
    hash_type: str = "ntlm"
    rules:     str = ""

class CuppRequest(BaseModel):
    first_name: str = ""
    last_name:  str = ""
    nickname:   str = ""
    birthdate:  str = ""
    partner:    str = ""
    pet_name:   str = ""
    company:    str = ""
    keywords:   list = []

class StrengthRequest(BaseModel):
    file_path: str


@router.post("/auth/hashcat")
async def run_hashcat_job(req: HashcatRequest, _token: str = Depends(require_combat_mode)):
    """Run a hashcat password recovery job (streams progress via WS)."""
    from .auth.hashcat_wrapper import run_hashcat
    return await run_hashcat(req.hash_file, req.wordlist, req.hash_type, req.rules or None)


@router.post("/auth/cupp")
async def run_cupp(req: CuppRequest, _token: str = Depends(require_combat_mode)):
    """Generate a targeted wordlist using CUPP."""
    from .auth.cupp_wrapper import generate_wordlist, ProfileData
    profile = ProfileData(
        first_name=req.first_name, last_name=req.last_name, nickname=req.nickname,
        birthdate=req.birthdate, partner=req.partner, pet_name=req.pet_name,
        company=req.company, keywords=req.keywords,
    )
    return await generate_wordlist(profile)


@router.post("/auth/strength")
async def analyze_strength(req: StrengthRequest, _token: str = Depends(require_combat_mode)):
    """Analyse a hash dump file for policy violations (no plaintexts returned)."""
    from .auth.strength_report import analyze_hash_file
    return analyze_hash_file(req.file_path)


# ─────────────────────────────────────────────────────────────────────────────
#  AI PENTEST ASSISTANTS  (Commit 6)
# ─────────────────────────────────────────────────────────────────────────────

class PentestNextStepRequest(BaseModel):
    target:          str
    scope:           list = []
    findings:        list = []
    phase:           str  = "RECON"
    notes:           str  = ""
    open_ports:      list = []
    services:        list = []
    vulnerabilities: list = []
    model:           str  = "llama3"

class GyoithonRequest(BaseModel):
    target_url: str


@router.post("/ai/next-step")
async def pentest_next_step(req: PentestNextStepRequest, _token: str = Depends(require_combat_mode)):
    """Get AI-driven next penetration testing step (Ollama-backed)."""
    from .ai_assist.pentestgpt import get_next_step, PentestContext
    ctx = PentestContext(
        target=req.target, scope=req.scope, findings=req.findings,
        phase=req.phase, notes=req.notes, open_ports=req.open_ports,
        services=req.services, vulnerabilities=req.vulnerabilities,
    )
    return await get_next_step(ctx, model=req.model)


@router.post("/ai/gyoithon")
async def gyoithon_scan(req: GyoithonRequest, _token: str = Depends(require_combat_mode)):
    """Run Gyoithon AI-driven web technology fingerprinting."""
    from .ai_assist.gyoithon_runner import run_gyoithon
    return await run_gyoithon(req.target_url)


# ─────────────────────────────────────────────────────────────────────────────
#  SENSOR — WiFi-DensePose  (Commit 7)
# ─────────────────────────────────────────────────────────────────────────────

class SensorConnectRequest(BaseModel):
    host: str = "localhost"
    port: int = 8765


@router.post("/sensor/connect")
async def sensor_connect(req: SensorConnectRequest, _token: str = Depends(require_combat_mode)):
    """Connect to a local WiFi-DensePose inference server."""
    from .sensor.densepose_client import connect_densepose
    client = await connect_densepose(req.host, req.port)
    return {"status": "CONNECTED", "url": client.url}


@router.post("/sensor/disconnect")
async def sensor_disconnect(_token: str = Depends(require_combat_mode)):
    """Disconnect from the DensePose inference server."""
    from .sensor.densepose_client import get_densepose_client
    client = get_densepose_client()
    if client:
        await client.stop()
        return {"status": "DISCONNECTED"}
    return {"status": "NOT_CONNECTED"}


# ─────────────────────────────────────────────────────────────────────────────
#  SPARK BRIEFING  (Commit 8)
# ─────────────────────────────────────────────────────────────────────────────

class BriefingRequest(BaseModel):
    mode:     str  = "PASSIVE"
    context:  dict = {}
    speak:    bool = True
    model:    str  = "llama3"

class ScheduleBriefingRequest(BaseModel):
    hour:   int  = 7
    minute: int  = 0
    mode:   str  = "PASSIVE"


@router.post("/spark/briefing")
async def get_briefing(req: BriefingRequest, _token: str = Depends(require_combat_mode)):
    """Generate a SPARK situational briefing (text + optional TTS audio)."""
    from .spark.briefing import generate_briefing
    return await generate_briefing(mode=req.mode, context=req.context, speak=req.speak, model=req.model)


@router.post("/spark/schedule")
async def schedule_daily_briefing(req: ScheduleBriefingRequest, _token: str = Depends(require_combat_mode)):
    """Schedule a daily SPARK briefing at a given local time."""
    from .spark.briefing import schedule_briefing
    job_id = await schedule_briefing(hour=req.hour, minute=req.minute, mode=req.mode)
    return {"job_id": job_id, "scheduled_at": f"{req.hour:02d}:{req.minute:02d}"}
