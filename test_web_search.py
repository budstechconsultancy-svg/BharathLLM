import os
import sys

os.environ["WEB_SEARCH_PROVIDER"] = "duckduckgo"
os.environ["WEB_SEARCH_ENABLED"] = "true"

from pipeline.web_search_engine import WebSearchEngine

def test():
    print("Testing Web Search Engine Initialization...")
    engine = WebSearchEngine()
    print(f"Provider loaded: {engine.provider.__class__.__name__}")
    
    print("\nTesting Govt Query Generation...")
    query = engine.build_govt_query("What is the latest G.O. for maternity leave?", "Health")
    print(f"Augmented query: {query}")
    assert "site:gov.in OR site:nic.in" in query, "Govt query logic failed"
    
    print("\nTesting Open Web Search (DDGS fallback)...")
    results = engine.search_open_web("CM breakfast scheme Tamil Nadu", "Education", max_results=2)
    print(f"Found {len(results)} results")
    for r in results:
        print(f"- {r.title} ({r.domain}): fetch_success={r.fetch_success}, words={r.word_count}")
        assert r.word_count > 0, "No content extracted"
    
    print("\nTesting Chunking...")
    chunks = engine.chunk_web_results(results)
    print(f"Created {len(chunks)} chunks from results.")
    
    print("\nAll Section J verification checks passed (simulated with DuckDuckGo).")

if __name__ == "__main__":
    test()
