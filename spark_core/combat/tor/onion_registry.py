"""
SPARK Tor Gateway — Vetted Onion Site Registry
===============================================
A curated database of known, vetted .onion addresses.
All entries have been manually reviewed and categorised.

This is a READ-ONLY knowledge base — it does not make outbound connections.
Use site_verifier.py to check reachability and calculate trust scores.

Categories:
  OSINT         — OSINT tools and resources
  NEWS          — Journalism and press freedom
  SECURITY      — Security research and CVE disclosure
  GOVERNMENT    — Official government / law-enforcement mirrors
  PRIVACY       — Privacy-focused services
"""
from typing import Optional

# ── Vetted registry ────────────────────────────────────────────────────────────
# Each entry: {"name", "url", "category", "description", "clearweb_mirror", "trust_score"}
# trust_score: 0-100 (100 = highest confidence in legitimacy)

ONION_REGISTRY: list[dict] = [
    {
        "name":           "DuckDuckGo",
        "url":            "https://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion",
        "category":       "SEARCH",
        "description":    "DuckDuckGo privacy-focused search engine official onion.",
        "clearweb_mirror": "https://duckduckgo.com",
        "trust_score":    99,
    },
    {
        "name":           "New York Times",
        "url":            "https://www.nytimesn7cgmftshazwhfgzm37qxb44r64ytbb2dj3x62d2lljsciiyd.onion",
        "category":       "NEWS",
        "description":    "NYT official SecureDrop / onion presence.",
        "clearweb_mirror": "https://www.nytimes.com",
        "trust_score":    97,
    },
    {
        "name":           "BBC News",
        "url":            "https://www.bbcnewsd73hkzno2ini43t4gblxvycyac5aw4gnv7t2rccijh7745uqd.onion",
        "category":       "NEWS",
        "description":    "BBC News accessible in censored regions.",
        "clearweb_mirror": "https://www.bbc.com",
        "trust_score":    96,
    },
    {
        "name":           "The Tor Project",
        "url":            "http://2gzyxa5ihm7nsggfxnu52rck2vv4rvmdlkiu3zzui5du4xyclen53wid.onion",
        "category":       "PRIVACY",
        "description":    "Tor Project official website — download Tor Browser.",
        "clearweb_mirror": "https://www.torproject.org",
        "trust_score":    100,
    },
    {
        "name":           "ProPublica",
        "url":            "https://p53lf57qovyuvwsc6xnrppyply3vtqm7l6pcobkmyqusioppgpclqqid.onion",
        "category":       "NEWS",
        "description":    "ProPublica — investigative journalism.",
        "clearweb_mirror": "https://www.propublica.org",
        "trust_score":    95,
    },
    {
        "name":           "CIA SecureDrop",
        "url":            "http://ciadotgov4sjwlzihbbgxnqg3xiyrg7so2r2o3lt5wz5ypk4sxyjstad.onion",
        "category":       "GOVERNMENT",
        "description":    "CIA official onion for tip submissions.",
        "clearweb_mirror": "https://www.cia.gov",
        "trust_score":    93,
    },
    {
        "name":           "Facebook",
        "url":            "https://www.facebookwkhpilnemxj7asber7cybul7av3wkpa3crmh6qkef3ata.onion",
        "category":       "SOCIAL",
        "description":    "Facebook official onion — access from censored regions.",
        "clearweb_mirror": "https://www.facebook.com",
        "trust_score":    90,
    },
    {
        "name":           "Ahmia Search",
        "url":            "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion",
        "category":       "SEARCH",
        "description":    "Ahmia — indexes non-illegal onion sites.",
        "clearweb_mirror": "https://ahmia.fi",
        "trust_score":    85,
    },
    {
        "name":           "SecureDrop",
        "url":            "http://sdolvtfhatvsysc6l34d65ymdwxcujausv7k5jk4cy5ttzhjoi6fzvyd.onion",
        "category":       "OSINT",
        "description":    "SecureDrop whistleblower platform directory.",
        "clearweb_mirror": "https://securedrop.org",
        "trust_score":    98,
    },
    {
        "name":           "Imprints (Keybase Tor)",
        "url":            "http://keybase5wmilwokqirssclfnsqrjdsi7jdir5wy7y7iu3tanwmtp6oid.onion",
        "category":       "PRIVACY",
        "description":    "Keybase — encrypted identity and file sharing.",
        "clearweb_mirror": "https://keybase.io",
        "trust_score":    88,
    },
]


def get_all_sites() -> list[dict]:
    """Return all registered onion sites."""
    return ONION_REGISTRY


def get_site(name: str) -> Optional[dict]:
    """Find a site by name (case-insensitive)."""
    name_lower = name.lower()
    return next(
        (s for s in ONION_REGISTRY if s["name"].lower() == name_lower),
        None,
    )


def get_by_category(category: str) -> list[dict]:
    """Return all sites in a given category."""
    return [s for s in ONION_REGISTRY if s["category"].upper() == category.upper()]
