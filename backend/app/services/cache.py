from cachetools import TTLCache
from ..config import settings

# In-memory only, short lifetime. We deliberately never write full search results
# to disk (search vendors may restrict storing results).
search_cache: TTLCache = TTLCache(maxsize=512, ttl=settings.cache_ttl_seconds)
probe_reliability_cache: TTLCache = TTLCache(maxsize=64, ttl=3600)
