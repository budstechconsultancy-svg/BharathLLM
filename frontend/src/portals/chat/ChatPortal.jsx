import React, { useState } from 'react'
import { API_URL } from '../../api/client.js'

export default function ChatPortal({ token, user }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Welcome to the Document Intelligence System. Ask me anything about your department documents.' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  
  // Advanced filters pane
  const [docType, setDocType] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  
  // Query metadata drawer
  const [activeMeta, setActiveMeta] = useState(null)

  const handleSend = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return
    
    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setActiveMeta(null)
    
    try {
      const response = await fetch(`${API_URL}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          question: input,
          doc_type: docType || null,
          date_from: dateFrom || null,
          date_to: dateTo || null
        })
      })
      
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || "Query failed.")
      }
      
      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        query_type: data.query_type,
        confidence: data.confidence,
        sql: data.sql_generated,
        sources: data.sources
      }
      
      setMessages(prev => [...prev, assistantMessage])
      setActiveMeta(assistantMessage)
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex overflow-hidden bg-white text-[#1A1A1A] font-inter">
      {/* Primary chat canvas */}
      <div className="flex-1 flex flex-col justify-between overflow-hidden">
        
        {/* Top title bar */}
        <div style={{ padding: '0 24px', height: '64px', borderBottom: '1px solid #E8E8E4', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: '#22C55E' }}></div>
            <h3 style={{ fontWeight: 600, fontSize: '14px', color: '#1A1A1A' }}>Scoped Search: {user?.department || 'System'}</h3>
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="hover:bg-[#F7F6F3]"
            style={{
              padding: '6px 12px', background: '#FFFFFF', border: '1px solid #E8E8E4', color: '#1A1A1A', borderRadius: '8px', fontSize: '12px', fontWeight: 500, transition: 'all 0.2s'
            }}
          >
            {showFilters ? "Hide Filters" : "Show Filters"}
          </button>
        </div>
        
        {/* Advanced Filters section */}
        {showFilters && (
          <div style={{ padding: '16px 24px', background: '#FAFAF8', borderBottom: '1px solid #E8E8E4', display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center' }}>
            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 600, color: '#9B9B9B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Doc Type</label>
              <select
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                style={{ padding: '6px 12px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', fontSize: '12px', color: '#1A1A1A', outline: 'none' }}
              >
                <option value="">All Document Types</option>
                <option value="GO">Government Order (G.O.)</option>
                <option value="CIRCULAR">Circular</option>
                <option value="POLICY">Policy Document</option>
                <option value="SCHEME">Scheme Guidelines</option>
                <option value="NOTIFICATION">Notification</option>
              </select>
            </div>
            
            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 600, color: '#9B9B9B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Date Range (From)</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                style={{ padding: '6px 12px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', fontSize: '12px', color: '#1A1A1A', outline: 'none' }}
              />
            </div>
            
            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 600, color: '#9B9B9B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Date Range (To)</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                style={{ padding: '6px 12px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', fontSize: '12px', color: '#1A1A1A', outline: 'none' }}
              />
            </div>
            
            <button
              onClick={() => { setDocType(''); setDateFrom(''); setDateTo(''); }}
              style={{ marginTop: '16px', fontSize: '12px', color: '#6B6B6B', cursor: 'pointer', border: 'none', background: 'none' }}
            >
              Reset Filters
            </button>
          </div>
        )}
        
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                style={{
                  maxWidth: '42rem', padding: '16px', borderRadius: '16px', fontSize: '14px', lineHeight: '1.6',
                  background: msg.role === 'user' ? '#534AB7' : '#F7F6F3',
                  color: msg.role === 'user' ? '#FFFFFF' : '#1A1A1A',
                  border: msg.role === 'user' ? 'none' : '1px solid #E8E8E4',
                  borderBottomRightRadius: msg.role === 'user' ? '4px' : '16px',
                  borderBottomLeftRadius: msg.role === 'assistant' ? '4px' : '16px'
                }}
                className="animate-fade-in shadow-sm"
              >
                <div style={{ fontWeight: 600, fontSize: '12px', color: msg.role === 'user' ? '#EEEDFE' : '#6B6B6B', marginBottom: '4px' }}>
                  {msg.role === 'user' ? 'You' : 'System Assistant'}
                </div>
                
                <div className="whitespace-pre-line">{msg.content}</div>
                
                {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                  <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #E8E8E4', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '11px', color: '#6B6B6B' }}>Citations matched: {msg.sources.length}</span>
                    <button
                      onClick={() => setActiveMeta(msg)}
                      style={{ fontSize: '12px', color: '#534AB7', fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer' }}
                    >
                      Inspect Citations & SQL →
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div style={{ background: '#F7F6F3', border: '1px solid #E8E8E4', borderRadius: '16px', borderBottomLeftRadius: '4px', padding: '16px', fontSize: '14px', color: '#6B6B6B' }} className="animate-pulse shadow-sm">
                Assistant is thinking...
              </div>
            </div>
          )}
        </div>
        
        {/* Input box */}
        <form onSubmit={handleSend} style={{ padding: '24px', borderTop: '1px solid #E8E8E4', background: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '16px' }}>
          <input
            type="text"
            required
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Ask a question about ${user?.department || 'System'} documents or databases...`}
            style={{
              flex: 1, padding: '14px 20px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '12px', color: '#1A1A1A', outline: 'none', fontSize: '14px', boxShadow: '0 1px 2px rgba(0,0,0,0.02)'
            }}
          />
          <button type="submit" style={{ padding: '14px 24px', background: '#534AB7', color: '#FFFFFF', fontWeight: 600, borderRadius: '12px', border: 'none', cursor: 'pointer', fontSize: '14px' }}>
            Search
          </button>
        </form>
      </div>
      
      {/* Right Drawer: Metadata citations inspections */}
      {activeMeta && (
        <div style={{ width: '320px', background: '#FAFAF8', borderLeft: '1px solid #E8E8E4', padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <div className="space-y-6">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #E8E8E4', paddingBottom: '12px' }}>
              <h4 style={{ fontWeight: 600, fontSize: '14px', color: '#1A1A1A' }}>Execution Inspector</h4>
              <button
                onClick={() => setActiveMeta(null)}
                style={{ fontSize: '12px', color: '#6B6B6B', cursor: 'pointer', background: 'none', border: 'none' }}
              >
                Close
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <p style={{ fontSize: '10px', fontWeight: 600, color: '#9B9B9B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Route Selected</p>
                <span style={{ padding: '4px 8px', background: '#F0FDF4', border: '1px solid #22C55E', color: '#166534', fontSize: '12px', fontWeight: 600, borderRadius: '4px' }}>
                  {activeMeta.query_type}
                </span>
              </div>
              
              <div>
                <p style={{ fontSize: '10px', fontWeight: 600, color: '#9B9B9B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Confidence Score</p>
                <p style={{ fontSize: '24px', fontWeight: 700, color: '#1A1A1A' }}>{activeMeta.confidence ? `${(activeMeta.confidence * 100).toFixed(1)}%` : "N/A"}</p>
              </div>
            </div>
            
            {activeMeta.sources && activeMeta.sources.length > 0 && (
              <div className="space-y-3">
                <p style={{ fontSize: '10px', fontWeight: 600, color: '#9B9B9B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Citations Used</p>
                <div className="space-y-2">
                  {activeMeta.sources.map((src, i) => (
                    <div key={i} style={{ padding: '12px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', fontSize: '12px' }}>
                      <p style={{ fontWeight: 600, color: '#1A1A1A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{src.filename}</p>
                      <p style={{ color: '#6B6B6B', marginTop: '4px' }}>{src.doc_type} | {src.date}</p>
                      <p style={{ color: '#1A7A52', marginTop: '4px', fontWeight: 600 }}>Match Score: {(src.relevance_score * 100).toFixed(1)}%</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {activeMeta.sql && (
              <div className="space-y-2">
                <p style={{ fontSize: '10px', fontWeight: 600, color: '#9B9B9B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Executed SQL Statement</p>
                <pre style={{ padding: '12px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', fontSize: '11px', color: '#1A1A1A', overflowX: 'auto', whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
                  {activeMeta.sql}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
