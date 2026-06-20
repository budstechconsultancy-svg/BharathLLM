import os
import json
import asyncio
import hashlib
import datetime
import logging
import httpx
import trafilatura
from dataclasses import dataclass
from typing import Optional, List, Tuple

# In a real setup, you would use your actual Redis configuration.
# For simplicity and given the prompt, we use a basic mock or the actual redis_client if configured in the app.
try:
    import redis
    redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
except Exception:
    redis_client = None

# Assuming normalise_numerals exists in language_registry
try:
    from pipeline.language_registry import normalise_numerals
except ImportError:
    def normalise_numerals(text): return text

log = logging.getLogger("WebSearchEngine")

WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED", "true").lower() == "true"
WEB_SEARCH_PROVIDER = os.getenv("WEB_SEARCH_PROVIDER", "tavily").lower()
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
WEB_SEARCH_TIMEOUT_SEC = int(os.getenv("WEB_SEARCH_TIMEOUT_SEC", "8"))
WEB_SEARCH_DAILY_LIMIT = int(os.getenv("WEB_SEARCH_DAILY_LIMIT", "500"))

# Load domains JSON
try:
    with open(os.path.join(os.path.dirname(__file__), "assets", "india_govt_domains.json"), "r") as f:
        DOMAINS_DATA = json.load(f)
        PRIORITY_DOMAINS = set(DOMAINS_DATA.get("priority_domains", []))
        BLOCKED_DOMAINS = set(DOMAINS_DATA.get("blocked_domains", []))
        TRUSTED_NEWS = set(DOMAINS_DATA.get("trusted_news", []))
except Exception as e:
    log.warning(f"Could not load domain registry: {e}")
    PRIORITY_DOMAINS = set()
    BLOCKED_DOMAINS = set()
    TRUSTED_NEWS = set()

CACHE_TTL_SECONDS = {
    "GOV": 3600,
    "WEB": 1800,
    "NEWS": 900
}

@dataclass
class WebResult:
    url: str
    title: str
    snippet: str
    full_text: str
    domain: str
    source_type: str
    fetch_success: bool
    word_count: int

def cache_key(question: str, org_unit: str) -> str:
    key_str = f"websearch:{org_unit}:{question.lower().strip()}"
    return hashlib.md5(key_str.encode()).hexdigest()

def check_daily_limit() -> bool:
    if not redis_client:
        return True
    try:
        today = datetime.date.today().isoformat()
        key = f"web_search_count:{today}"
        count = int(redis_client.get(key) or 0)
        
        limits = {"brave": 2000, "tavily": 1000, "serpapi": 100}
        limit = limits.get(WEB_SEARCH_PROVIDER, WEB_SEARCH_DAILY_LIMIT)
        
        if count >= limit:
            log.warning(f"Daily web search limit reached: {count}/{limit}")
            return False
        redis_client.incr(key)
        redis_client.expire(key, 86400)
        return True
    except Exception:
        return True

class BraveSearchProvider:
    def search(self, query: str, max_results: int, site_filter: str = None) -> List[dict]:
        if not BRAVE_SEARCH_API_KEY:
            return []
            
        endpoint = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": BRAVE_SEARCH_API_KEY
        }
        
        search_query = f"site:{site_filter} {query}" if site_filter else query
        params = {
            "q": search_query,
            "count": max_results,
            "search_lang": "en",
            "country": "IN",
            "freshness": "pm"
        }
        
        try:
            with httpx.Client() as client:
                res = client.get(endpoint, headers=headers, params=params, timeout=5.0)
                res.raise_for_status()
                data = res.json()
                results = []
                for item in data.get("web", {}).get("results", []):
                    results.append({
                        "url": item.get("url"),
                        "title": item.get("title"),
                        "snippet": item.get("description", ""),
                        "content": None,
                        "raw_content": None
                    })
                return results
        except Exception as e:
            log.error(f"Brave Search failed: {e}")
            return []

class TavilySearchProvider:
    def search(self, query: str, max_results: int) -> List[dict]:
        if not TAVILY_API_KEY:
            return []
            
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=TAVILY_API_KEY)
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_domains=[],
                include_raw_content=True,
                include_answer=False
            )
            
            results = []
            for item in response.get("results", []):
                results.append({
                    "url": item.get("url"),
                    "title": item.get("title"),
                    "snippet": item.get("content", "")[:200],
                    "content": item.get("content", ""),
                    "raw_content": item.get("raw_content", "")
                })
            return results
        except Exception as e:
            log.error(f"Tavily Search failed: {e}")
            return []

class SerpAPIProvider:
    def search(self, query: str, max_results: int) -> List[dict]:
        if not SERPAPI_KEY:
            return []
            
        try:
            import requests
            endpoint = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": SERPAPI_KEY,
                "engine": "google",
                "gl": "in",
                "hl": "en",
                "num": max_results
            }
            res = requests.get(endpoint, params=params, timeout=5.0)
            res.raise_for_status()
            data = res.json()
            
            results = []
            for item in data.get("organic_results", []):
                results.append({
                    "url": item.get("link"),
                    "title": item.get("title"),
                    "snippet": item.get("snippet", ""),
                    "content": None,
                    "raw_content": None
                })
            return results
        except Exception as e:
            log.error(f"SerpAPI Search failed: {e}")
            return []

class DDGSProvider:
    def search(self, query: str, max_results: int) -> List[dict]:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region='in-en', max_results=max_results))
                formatted = []
                for item in results:
                    formatted.append({
                        "url": item.get("href"),
                        "title": item.get("title"),
                        "snippet": item.get("body", ""),
                        "content": None,
                        "raw_content": None
                    })
                return formatted
        except Exception as e:
            log.error(f"DDGS Search failed: {e}")
            return []

class WebSearchEngine:
    def __init__(self):
        if WEB_SEARCH_PROVIDER == "brave":
            self.provider = BraveSearchProvider()
        elif WEB_SEARCH_PROVIDER == "serpapi":
            self.provider = SerpAPIProvider()
        elif WEB_SEARCH_PROVIDER == "tavily" and TAVILY_API_KEY:
            self.provider = TavilySearchProvider()
        else:
            # Fallback to DDGS if no keys or provider specifically set to duckduckgo
            self.provider = DDGSProvider()
            
        self.async_client = httpx.AsyncClient(timeout=WEB_SEARCH_TIMEOUT_SEC, follow_redirects=True)

    def classify_domain(self, url: str) -> str:
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
                
            if domain in BLOCKED_DOMAINS:
                return "BLOCKED"
                
            if domain.endswith(".gov.in") or domain.endswith(".nic.in") or domain in PRIORITY_DOMAINS:
                return "GOV"
                
            if domain in TRUSTED_NEWS:
                return "NEWS"
                
            return "WEB"
        except Exception:
            return "WEB"

    def build_govt_query(self, question: str, department: str) -> str:
        base = normalise_numerals(question)
        q_lower = base.lower()
        
        context_terms = []
        if any(term in q_lower for term in ["g.o.", "circular", "notification"]):
            context_terms.append("site:gov.in OR site:nic.in filetype:pdf")
            
        if any(term in q_lower for term in ["scheme", "beneficiary", "yojana"]):
            context_terms.append(f"India government scheme {department}")
            
        if not any(str(year) in q_lower for year in range(2000, 2030)):
            context_terms.append(str(datetime.datetime.now().year))
            
        augmented = base + " " + " ".join(context_terms)
        return augmented.strip()

    async def fetch_and_extract(self, url: str) -> Tuple[str, bool]:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; BharatLLM-Bot/1.0; +https://bharatllm.in/bot)",
            "Accept": "text/html,application/xhtml+xml,application/pdf",
            "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8,ta;q=0.7"
        }
        
        try:
            response = await self.async_client.get(url, headers=headers, timeout=6.0)
            response.raise_for_status()
            
            content_type = response.headers.get("Content-Type", "").lower()
            if "pdf" in content_type:
                # PDF extraction logic (simplified placeholder for trafilatura/pdf integration)
                return ("PDF extraction not fully supported without headless browser/mupdf integration.", False)
                
            extracted = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_recall=True,
                include_formatting=False
            )
            
            if extracted:
                words = extracted.split()
                if len(words) > 3000:
                    extracted = " ".join(words[:3000])
                return (extracted, True)
            else:
                import re
                text = re.sub(r'<[^>]+>', ' ', response.text[:3000])
                return (text, False)
                
        except Exception as e:
            log.warning(f"Fetch failed for {url}: {e}")
            return ("", False)

    def search_govt_web(self, question: str, department: str, max_results: int = 5) -> List[WebResult]:
        govt_query = self.build_govt_query(question, department)
        raw_results = self.provider.search(govt_query, max_results)
        
        results_with_type = []
        for r in raw_results:
            domain_type = self.classify_domain(r["url"])
            if domain_type == "BLOCKED":
                continue
            results_with_type.append((r, domain_type))
            
        priority = {"GOV": 0, "NEWS": 1, "WEB": 2}
        results_with_type.sort(key=lambda x: priority.get(x[1], 3))
        
        return self._process_results(results_with_type[:3])

    def search_open_web(self, question: str, dept: str, max_results: int = 5) -> List[WebResult]:
        query = question + " India" if "india" not in question.lower() else question
        raw_results = self.provider.search(query, max_results)
        
        results_with_type = []
        for r in raw_results:
            domain_type = self.classify_domain(r["url"])
            if domain_type == "BLOCKED":
                continue
            results_with_type.append((r, domain_type))
            
        return self._process_results(results_with_type[:3])
        
    def _process_results(self, results_with_type) -> List[WebResult]:
        loop = asyncio.get_event_loop()
        
        async def fetch_all(results):
            tasks = []
            for r, dtype in results:
                # If Tavily provided raw content, skip fetch
                if r.get("raw_content") or r.get("content"):
                    tasks.append(asyncio.sleep(0, result=(r.get("raw_content") or r.get("content"), True)))
                else:
                    tasks.append(self.fetch_and_extract(r["url"]))
            return await asyncio.gather(*tasks, return_exceptions=True)
            
        fetch_responses = loop.run_until_complete(fetch_all(results_with_type))
        
        final_results = []
        for i, (r, dtype) in enumerate(results_with_type):
            from urllib.parse import urlparse
            domain = urlparse(r["url"]).netloc.lower()
            
            fetch_data = fetch_responses[i]
            if isinstance(fetch_data, Exception):
                text, success = "", False
            else:
                text, success = fetch_data
                
            full_text = text if text else r["snippet"]
            
            final_results.append(WebResult(
                url=r["url"],
                title=r["title"],
                snippet=r["snippet"],
                full_text=full_text,
                domain=domain,
                source_type=dtype,
                fetch_success=success,
                word_count=len(full_text.split())
            ))
            
        return final_results

    def chunk_web_results(self, results: List[WebResult]) -> List[dict]:
        chunks = []
        for res in results:
            words = res.full_text.split()
            chunk_size = 300
            for i in range(0, len(words), chunk_size):
                chunk_text = " ".join(words[i:i+chunk_size])
                chunks.append({
                    "chunk_id": "web_" + hashlib.md5((res.url + str(i)).encode()).hexdigest()[:8],
                    "source_type": res.source_type,
                    "text": chunk_text,
                    "url": res.url,
                    "title": res.title,
                    "domain": res.domain,
                    "chunk_index": i // chunk_size,
                    "total_chunks": (len(words) // chunk_size) + 1,
                    "word_count": len(chunk_text.split())
                })
        return chunks

    def query(self, question: str, department: str, confidence_from_rag: float = 0.0) -> dict:
        if not WEB_SEARCH_ENABLED:
            return {"results": [], "source_type": "DISABLED", "chunks": []}
            
        if not check_daily_limit():
            return {"results": [], "source_type": "DISABLED", "chunks": []}
            
        if confidence_from_rag >= 0.70:
            return {"results": [], "source_type": "NOT_NEEDED", "chunks": []}
            
        key = cache_key(question, department)
        if redis_client:
            cached = redis_client.get(f"ws:{key}")
            if cached:
                return json.loads(cached)
                
        # Tier 2 - Govt search
        govt_results = self.search_govt_web(question, department)
        gov_chunks = self.chunk_web_results(govt_results)
        
        if gov_chunks and any(r.source_type == "GOV" for r in govt_results):
            result = {
                "results": [r.__dict__ for r in govt_results],
                "source_type": "GOV",
                "chunks": gov_chunks,
                "query_used": self.build_govt_query(question, department)
            }
            if redis_client:
                redis_client.setex(f"ws:{key}", CACHE_TTL_SECONDS.get("GOV", 3600), json.dumps(result))
            return result
            
        # Tier 3 - Open Web Fallback
        open_results = self.search_open_web(question, department)
        web_chunks = self.chunk_web_results(open_results)
        
        if web_chunks:
            result = {
                "results": [r.__dict__ for r in open_results],
                "source_type": "WEB",
                "chunks": web_chunks,
                "query_used": question
            }
            if redis_client:
                redis_client.setex(f"ws:{key}", CACHE_TTL_SECONDS.get("WEB", 1800), json.dumps(result))
            return result
            
        # Tier 4 - Total fallback
        return {"results": [], "source_type": "NOT_FOUND", "chunks": []}
