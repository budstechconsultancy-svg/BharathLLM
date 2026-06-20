import React, { useState } from 'react'
import { API_URL } from '../../api/client.js'

export default function DeveloperPortal({ token, user }) {
  const [keyName, setKeyName] = useState('')
  const [rateLimit, setRateLimit] = useState(100)
  
  const [apiKeyDetails, setApiKeyDetails] = useState(null)
  const [error, setError] = useState('')
  
  const [activeSnippetTab, setActiveSnippetTab] = useState('python')

  const handleGenerateKey = async (e) => {
    e.preventDefault()
    setError('')
    setApiKeyDetails(null)
    
    try {
      const response = await fetch(`${API_URL}/auth/api-keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          name: keyName,
          rate_limit_per_min: rateLimit
        })
      })
      
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || "Failed to generate API Key.")
      }
      
      setApiKeyDetails(data)
      setKeyName('')
    } catch (err) {
      setError(err.message)
    }
  }

  const pythonSnippet = `import requests

url = "${API_URL}/query"
headers = {
    "X-API-Key": "${apiKeyDetails ? apiKeyDetails.api_key : "YOUR_API_KEY_HERE"}",
    "Content-Type": "application/json"
}
payload = {
    "question": "What does G.O. 142 say about hospital norms?",
    "top_k": 5
}

response = requests.post(url, json=payload, headers=headers)
data = response.json()
print("Answer:", data["answer"])"`

  const jsSnippet = `const url = "${API_URL}/query";
const headers = {
    "X-API-Key": "${apiKeyDetails ? apiKeyDetails.api_key : "YOUR_API_KEY_HERE"}",
    "Content-Type": "application/json"
};
const payload = {
    "question": "What is the total CMHIS beneficiary enrollment count in 2024?",
    "top_k": 5
};

fetch(url, {
    method: "POST",
    headers: headers,
    body: JSON.stringify(payload)
})
.then(res => res.json())
.then(data => console.log("Answer:", data.answer))
.catch(err => console.error("Error:", err));`

  return (
    <div className="flex-1 overflow-y-auto p-8 lg:p-12 bg-white text-[#1A1A1A] font-inter animate-fade-in">
      <div className="max-w-5xl mx-auto space-y-8">
        <div style={{ borderBottom: '1px solid #E8E8E4', paddingBottom: '16px' }}>
          <h2 style={{ fontSize: '24px', fontWeight: 600, color: '#1A1A1A' }}>Developer Portal</h2>
          <p style={{ marginTop: '4px', fontSize: '13px', color: '#6B6B6B' }}>Generate programmatic X-API-Key credentials to query the BharatLLM Document Intelligence System from custom backend applications.</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          
          {/* Generation form container */}
          <div className="space-y-6">
            <h4 style={{ fontSize: '10px', fontWeight: 600, color: '#9B9B9B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Generate API Key</h4>
            
            <form onSubmit={handleGenerateKey} style={{ background: '#FFFFFF', padding: '24px', borderRadius: '10px', border: '1px solid #E8E8E4' }} className="space-y-4 shadow-sm">
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#6B6B6B', marginBottom: '4px' }}>Key Name</label>
                <input
                  type="text"
                  required
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  placeholder="e.g. Health Ingestion Service"
                  style={{ width: '100%', padding: '10px 14px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', fontSize: '13px', color: '#1A1A1A', outline: 'none' }}
                />
              </div>
              
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#6B6B6B', marginBottom: '4px' }}>Rate Limit (per min)</label>
                <input
                  type="number"
                  min="1"
                  max="1000"
                  value={rateLimit}
                  onChange={(e) => setRateLimit(parseInt(e.target.value))}
                  style={{ width: '100%', padding: '10px 14px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', fontSize: '13px', color: '#1A1A1A', outline: 'none' }}
                />
              </div>
              
              <button type="submit" style={{ width: '100%', padding: '12px', background: '#534AB7', color: '#FFFFFF', fontWeight: 600, borderRadius: '8px', fontSize: '13px', border: 'none', cursor: 'pointer', marginTop: '16px' }}>
                Create Credentials
              </button>
            </form>
            
            {error && (
              <div style={{ padding: '12px', background: '#FEF2F2', border: '1px solid #EF4444', color: '#991B1B', borderRadius: '8px', fontSize: '12px' }}>
                {error}
              </div>
            )}
            
            {/* Show API Key Container securely */}
            {apiKeyDetails && (
              <div style={{ padding: '20px', background: '#F0FDF4', border: '1px solid #22C55E', borderRadius: '10px' }} className="space-y-3">
                <span style={{ fontSize: '10px', fontWeight: 600, color: '#166534', textTransform: 'uppercase', letterSpacing: '0.05em', background: '#DCFCE7', padding: '4px 8px', borderRadius: '4px' }}>
                  Active Scoped API Key Created
                </span>
                <div style={{ marginTop: '12px' }}>
                  <p style={{ fontSize: '12px', color: '#1A7A52', marginBottom: '8px', fontWeight: 500 }}>Copy and save this key. It will not be shown again:</p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input
                      type="text"
                      readOnly
                      value={apiKeyDetails.api_key}
                      style={{ flex: 1, padding: '10px', background: '#FFFFFF', border: '1px solid #22C55E', borderRadius: '8px', fontSize: '12px', color: '#1A1A1A', fontFamily: 'monospace', outline: 'none' }}
                    />
                    <button
                      onClick={() => navigator.clipboard.writeText(apiKeyDetails.api_key)}
                      style={{ padding: '10px 16px', background: '#FFFFFF', border: '1px solid #E8E8E4', color: '#1A1A1A', fontWeight: 600, borderRadius: '8px', fontSize: '12px', cursor: 'pointer' }}
                    >
                      Copy
                    </button>
                  </div>
                </div>
                <p style={{ fontSize: '11px', color: '#1A7A52', lineHeight: '1.5', marginTop: '12px' }}>
                  Sponsoring Scope : {apiKeyDetails.department} Department<br />
                  Rate Throttles   : {apiKeyDetails.rate_limit_per_min} req/min
                </p>
              </div>
            )}
          </div>
          
          {/* Integration SDK Codes snippets */}
          <div className="space-y-4">
            <h4 style={{ fontSize: '10px', fontWeight: 600, color: '#9B9B9B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>SDK Integrations</h4>
            
            <div style={{ background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '10px', overflow: 'hidden', display: 'flex', flexDirection: 'column', height: '384px' }} className="shadow-sm">
              {/* Tab Selector */}
              <div style={{ display: 'flex', borderBottom: '1px solid #E8E8E4', background: '#F8F7F4' }}>
                <button
                  onClick={() => setActiveSnippetTab('python')}
                  style={{
                    flex: 1, padding: '12px', fontSize: '12px', fontWeight: 600, transition: 'all 0.2s', cursor: 'pointer',
                    background: activeSnippetTab === 'python' ? '#FFFFFF' : 'transparent',
                    color: activeSnippetTab === 'python' ? '#534AB7' : '#6B6B6B',
                    border: 'none', borderBottom: activeSnippetTab === 'python' ? '2px solid #534AB7' : '2px solid transparent'
                  }}
                >
                  Python Requests
                </button>
                <button
                  onClick={() => setActiveSnippetTab('javascript')}
                  style={{
                    flex: 1, padding: '12px', fontSize: '12px', fontWeight: 600, transition: 'all 0.2s', cursor: 'pointer',
                    background: activeSnippetTab === 'javascript' ? '#FFFFFF' : 'transparent',
                    color: activeSnippetTab === 'javascript' ? '#534AB7' : '#6B6B6B',
                    border: 'none', borderBottom: activeSnippetTab === 'javascript' ? '2px solid #534AB7' : '2px solid transparent'
                  }}
                >
                  JavaScript Fetch
                </button>
              </div>
              
              {/* Code Snippets view */}
              <div style={{ flex: 1, padding: '16px', background: '#FAFAF8', overflow: 'auto' }}>
                <pre style={{ fontSize: '11px', fontFamily: 'monospace', color: '#1A1A1A', whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>
                  {activeSnippetTab === 'python' ? pythonSnippet : jsSnippet}
                </pre>
              </div>
            </div>
          </div>
          
        </div>
      </div>
    </div>
  )
}
