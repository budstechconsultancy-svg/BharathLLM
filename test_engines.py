import os
os.environ["MOCK_AI_MODELS"] = "True"

from pipeline.query_router import QueryRouter

def main():
    router = QueryRouter()
    
    questions = [
        "What is the stamp duty in TN for a residential property?",
        "What are the drug interactions between Aspirin and Ibuprofen?",
        "How is gratuity calculated for 5 years of service under the new labour code?"
    ]
    
    print("\n--- Testing BharatLLM Vertical Routing ---")
    for q in questions:
        print(f"\nQuestion: {q}")
        res = router.route_and_query(q, "General")
        print(f"Routed to Vertical: {res.get('vertical')}")
        print(f"Answer snippet: {res.get('answer')[:100]}")

if __name__ == "__main__":
    main()
