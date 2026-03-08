"""
SPARK SIGINT — NLP Threat Sentiment Analysis
=============================================
Cross-references a given security topic or CVE across multiple intelligence
sources, then passes the aggregated text to the local SPARK LLM (Ollama) for
sentiment scoring and threat-level synthesis.

Returns a structured sentiment report with:
  - Threat level: CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL
  - Exploitation likelihood score (0-100)
  - Analyst summary (LLM-generated prose)
  - Source citations
"""
import logging
from typing import Optional

log = logging.getLogger(__name__)

try:
    import httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False

_OLLAMA_URL = "http://localhost:11434"
_TIMEOUT    = 60


_SENTIMENT_PROMPT = """You are a cybersecurity threat intelligence analyst.

Analyse the following security intelligence data and return a structured assessment.

Topic: {topic}

Raw intelligence:
{intel}

Respond ONLY with valid JSON in this exact format:
{{
  "threat_level": "<CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL>",
  "exploitation_likelihood": <0-100>,
  "active_exploitation": <true|false>,
  "analyst_summary": "<2-3 sentence synthesis>",
  "key_indicators": ["<indicator1>", "<indicator2>"],
  "recommended_actions": ["<action1>", "<action2>"]
}}"""


async def _call_ollama(prompt: str, model: str = "llama3") -> Optional[str]:
    if not _HTTPX:
        return None
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(
                f"{_OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                return r.json().get("response", "")
        except Exception as e:
            log.warning("Ollama call failed: %s", e)
    return None


async def _gather_intel_text(topic: str) -> str:
    """Build a raw intelligence string by polling CISA + NVD for the topic."""
    intel_parts = []

    if _HTTPX:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # NVD keyword search
            try:
                r = await client.get(
                    "https://services.nvd.nist.gov/rest/json/cves/2.0",
                    params={"keywordSearch": topic, "resultsPerPage": 10},
                    headers={"Accept": "application/json"},
                    timeout=20,
                )
                if r.status_code == 200:
                    data = r.json()
                    for v in data.get("vulnerabilities", [])[:5]:
                        cve = v.get("cve", {})
                        descs = cve.get("descriptions", [])
                        desc = next((d["value"] for d in descs if d.get("lang") == "en"), "")
                        intel_parts.append(f"[NVD {cve.get('id')}] {desc[:300]}")
            except Exception:
                pass

    if not intel_parts:
        intel_parts.append(f"No recent NVD records found for: {topic}")

    return "\n".join(intel_parts)


async def analyze_sentiment(topic: str) -> dict:
    intel_text = await _gather_intel_text(topic)
    prompt     = _SENTIMENT_PROMPT.format(topic=topic, intel=intel_text[:3000])
    raw_llm    = await _call_ollama(prompt)

    result: dict = {
        "topic":       topic,
        "intel_used":  intel_text[:1000],
        "llm_response": raw_llm,
        "parsed":      None,
    }

    if raw_llm:
        import json, re
        # Extract JSON block from LLM response
        json_match = re.search(r"\{.*\}", raw_llm, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                result["parsed"] = parsed
            except json.JSONDecodeError:
                pass

    if not result["parsed"]:
        result["parsed"] = {
            "threat_level":            "UNKNOWN",
            "exploitation_likelihood":  0,
            "active_exploitation":      False,
            "analyst_summary":          "LLM analysis unavailable. Ensure Ollama is running with a suitable model.",
            "key_indicators":           [],
            "recommended_actions":      ["Start Ollama: ollama serve", "Pull model: ollama pull llama3"],
        }

    return result
