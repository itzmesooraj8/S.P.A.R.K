"""SPARK Tor Gateway — curated onion registry and site verification."""
from .onion_registry import get_all_sites, get_site
from .site_verifier import verify_site

__all__ = ["get_all_sites", "get_site", "verify_site"]
