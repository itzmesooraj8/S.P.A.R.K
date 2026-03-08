"""SPARK SIGINT — threat feed aggregation, CVE indexing, NLP sentiment."""
from .feed_aggregator import aggregate_feeds
from .cve_indexer import search_cves, sync_nvd_feed
from .nlp_sentiment import analyze_sentiment

__all__ = ["aggregate_feeds", "search_cves", "sync_nvd_feed", "analyze_sentiment"]
