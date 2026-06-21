import httpx
import asyncio

async def test_whatsapp():
    url = "http://localhost:8000/api/whatsapp"
    
    print("--- 1. Testing Registration ---")
    data_reg = {
        "From": "whatsapp:+919876543210",
        "Body": "Register Finance 12345",
        "MessageType": "text",
        "NumMedia": "0"
    }
    
    async with httpx.AsyncClient() as client:
        r = await client.post(url, data=data_reg)
        print(r.text)
        
    print("\n--- 2. Testing Finance Query ---")
    data_query = {
        "From": "whatsapp:+919876543210",
        "Body": "What is the GST on software services?",
        "MessageType": "text",
        "NumMedia": "0"
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.post(url, data=data_query)
        print(r.text)

if __name__ == "__main__":
    asyncio.run(test_whatsapp())
