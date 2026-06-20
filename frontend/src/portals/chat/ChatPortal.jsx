import React, { useState, useEffect, useRef } from 'react'
import { API_URL } from '../../api/client.js'

export default function ChatPortal({ token, user }) {
  const getWelcomeMessage = () => {
    if (user?.vertical === 'legal') return "⚖ BharatLLM Legal provides AI-assisted research only. Always verify with current law and consult a qualified advocate.\n\nWelcome to BharatLLM Legal. Ask me about Indian Acts, case laws, and legal drafting.";
    if (user?.vertical === 'finance') return "₹ BharatLLM Finance provides AI-assisted research only. Always verify with latest notifications and consult your CA.\n\nWelcome to BharatLLM Finance. Ask me about GST, tax rates, circulars, and compliance.";
    return "Welcome to the Document Intelligence System. Ask me anything about your department documents.";
  }

  // Q&A States
  const [messages, setMessages] = useState([
    { role: 'assistant', content: getWelcomeMessage() }
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
  
  // Agent Mode States
  const [isAgentMode, setIsAgentMode] = useState(false)
  const [agentTaskStatus, setAgentTaskStatus] = useState(null)
  const [agentTaskData, setAgentTaskData] = useState(null)
  
  // Multimodal States (Voice & Image)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingDuration, setRecordingDuration] = useState(0)
  const [selectedImage, setSelectedImage] = useState(null)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const recordingTimerRef = useRef(null)
  
  const handleImageSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedImage(e.target.files[0])
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      audioChunksRef.current = []
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }
      
      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        stream.getTracks().forEach(track => track.stop())
        if (checkGuestLimit()) {
          await processMultimodalInput(audioBlob, null)
        }
      }
      
      mediaRecorderRef.current.start()
      setIsRecording(true)
      setRecordingDuration(0)
      
      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration(prev => {
          if (prev >= 119) {
            stopRecording()
            return 120
          }
          return prev + 1
        })
      }, 1000)
    } catch (err) {
      alert("Please allow microphone access to use voice input.")
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      clearInterval(recordingTimerRef.current)
    }
  }
  
  const playAudioReply = (base64Audio) => {
    try {
      const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`)
      audio.play()
    } catch (e) {
      console.error("Audio playback failed", e)
    }
  }

  const checkGuestLimit = () => {
    if (user?.isGuest) {
      let tokens = parseInt(localStorage.getItem('guestTokens') || '0');
      if (tokens >= 3) {
        alert('Playground token limit reached! Please log out and register with your NIC ID to continue using BharatLLM.');
        return false;
      }
      localStorage.setItem('guestTokens', (tokens + 1).toString());
    }
    return true;
  }

  const processMultimodalInput = async (audioBlob, imageFile) => {
    const formData = new FormData()
    if (audioBlob) formData.append('audio', audioBlob, 'voice.webm')
    if (imageFile) formData.append('image', imageFile)
    if (input.trim()) formData.append('text', input.trim())
    
    // Optimistic UI update
    let userMessageContent = input
    if (audioBlob) userMessageContent = "🎤 [Voice message]"
    if (imageFile) userMessageContent = `🖼 [Image: ${imageFile.name}]\n` + input
    
    setMessages(prev => [...prev, { role: 'user', content: userMessageContent }])
    setInput('')
    setSelectedImage(null)
    setLoading(true)
    
    try {
      const response = await fetch(`${API_URL}/multimodal/query`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData
      })
      
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Query failed.")
      
      const assistantMessage = {
        role: 'assistant',
        content: data.answer,
        query_type: data.query_type || "MULTIMODAL",
        audio_answer_base64: data.audio_answer_base64
      }
      
      setMessages(prev => [...prev, assistantMessage])
      if (data.audio_answer_base64) {
        playAudioReply(data.audio_answer_base64)
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  const handleSend = async (e) => {
    if (e) e.preventDefault()
    
    if (!input.trim() && !selectedImage) return
    if (!checkGuestLimit()) return
    
    // Use Multimodal route if image is attached
    if (selectedImage) {
      await processMultimodalInput(null, selectedImage)
      return
    }
    
    if (!input.trim() || loading) return
    
    if (isAgentMode) {
      await handleAgentSend()
      return
    }
    
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
        sources: data.sources,
        web_source_type: data.web_source_type,
        cited_cases: data.cited_cases,
        circulars_cited: data.circulars_cited,
        document_drafted: data.document_drafted
      }
      
      setMessages(prev => [...prev, assistantMessage])
      setActiveMeta(assistantMessage)
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  const handleAgentSend = async () => {
    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    const currentTask = input
    setInput('')
    setAgentTaskStatus('planning')
    setAgentTaskData(null)
    
    try {
      const response = await fetch(`${API_URL}/agent/task`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          task: currentTask,
          priority: "normal"
        })
      })
      
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Agent task failed.")
      
      setAgentTaskData(data)
      if (data.status === "awaiting_approval") {
        setAgentTaskStatus('awaiting_approval')
      } else {
        setAgentTaskStatus('complete')
        const assistantMessage = {
          role: 'assistant',
          content: data.answer || "Task completed successfully.",
          artifacts: data.artifacts,
          agents_used: data.agents_used,
          steps_taken: data.steps_taken
        }
        setMessages(prev => [...prev, assistantMessage])
      }
    } catch (err) {
      setAgentTaskStatus(null)
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    }
  }

  const handleApprove = async (approved) => {
    setAgentTaskStatus('running')
    try {
      const response = await fetch(`${API_URL}/agent/task/${agentTaskData.task_id}/approve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ approved })
      })
      
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || "Agent approval failed.")
      
      setAgentTaskData(data)
      setAgentTaskStatus('complete')
      const assistantMessage = {
        role: 'assistant',
        content: data.answer || (approved ? "Task completed successfully." : "Action cancelled by user."),
        artifacts: data.artifacts,
        agents_used: data.agents_used,
        steps_taken: data.steps_taken
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      setAgentTaskStatus(null)
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    }
  }

  return (
    <div className="flex-1 flex overflow-hidden bg-white text-[#1A1A1A] font-inter">
      {/* Primary chat canvas */}
      <div className="flex-1 flex flex-col justify-between overflow-hidden">
        
        {/* Top title bar */}
        <div style={{ padding: '0 24px', height: '64px', borderBottom: '1px solid #E8E8E4', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: user?.vertical === 'legal' ? '#3B82F6' : user?.vertical === 'finance' ? '#22C55E' : '#F97316' }}></div>
            <div>
              <h3 style={{ fontWeight: 600, fontSize: '14px', color: '#1A1A1A' }}>
                {user?.vertical === 'legal' ? '⚖ Legal mode' : user?.vertical === 'finance' ? '₹ Finance mode' : `Scoped Search: ${user?.department || 'System'}`}
              </h3>
              <p style={{ fontSize: '11px', color: '#1D4ED8', marginTop: '2px' }}>↗ Multimodal Voice & Image Enabled</p>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ display: 'flex', background: '#F7F6F3', borderRadius: '8px', padding: '4px', border: '1px solid #E8E8E4' }}>
              <button 
                onClick={() => setIsAgentMode(false)}
                style={{ padding: '6px 12px', borderRadius: '4px', fontSize: '12px', fontWeight: 600, background: !isAgentMode ? '#FFFFFF' : 'transparent', boxShadow: !isAgentMode ? '0 1px 2px rgba(0,0,0,0.05)' : 'none', color: !isAgentMode ? '#1A1A1A' : '#6B6B6B', border: 'none', cursor: 'pointer' }}>
                Q&A Mode
              </button>
              <button 
                onClick={() => setIsAgentMode(true)}
                style={{ padding: '6px 12px', borderRadius: '4px', fontSize: '12px', fontWeight: 600, background: isAgentMode ? '#534AB7' : 'transparent', color: isAgentMode ? '#FFFFFF' : '#6B6B6B', boxShadow: isAgentMode ? '0 1px 2px rgba(0,0,0,0.1)' : 'none', border: 'none', cursor: 'pointer' }}>
                Agent Mode
              </button>
            </div>
            
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="hover:bg-[#F7F6F3]"
              style={{ padding: '6px 12px', background: '#FFFFFF', border: '1px solid #E8E8E4', color: '#1A1A1A', borderRadius: '8px', fontSize: '12px', fontWeight: 500, transition: 'all 0.2s' }}
            >
              {showFilters ? "Hide Filters" : "Show Filters"}
            </button>
          </div>
        </div>
        
        {/* Advanced Filters section */}
        {showFilters && !isAgentMode && (
          <div style={{ padding: '16px 24px', background: '#FAFAF8', borderBottom: '1px solid #E8E8E4', display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center' }}>
            {/* Same filters as before */}
            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 600, color: '#9B9B9B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>Doc Type</label>
              <select value={docType} onChange={(e) => setDocType(e.target.value)} style={{ padding: '6px 12px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', fontSize: '12px', color: '#1A1A1A', outline: 'none' }}>
                <option value="">All Document Types</option>
                <option value="GO">Government Order (G.O.)</option>
                <option value="CIRCULAR">Circular</option>
                <option value="POLICY">Policy Document</option>
              </select>
            </div>
          </div>
        )}
        
        {/* Quick Questions (Vertical Specific) */}
        {!isAgentMode && messages.length === 1 && (
          <div style={{ padding: '24px 24px 0', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {user?.vertical === 'legal' && [
              "Find IPC 302 BNS equivalent", "Draft legal notice", "Limitation period for cheque bounce", "Latest SC on NI Act"
            ].map((q, i) => (
              <button key={i} onClick={() => setInput(q)} style={{ padding: '8px 16px', background: '#F0F9FF', color: '#0369A1', border: '1px solid #BAE6FD', borderRadius: '20px', fontSize: '13px', cursor: 'pointer' }}>{q}</button>
            ))}
            {user?.vertical === 'finance' && [
              "GST rate for software services", "CBDT circular today", "Upcoming compliance deadlines", "Draft notice reply"
            ].map((q, i) => (
              <button key={i} onClick={() => setInput(q)} style={{ padding: '8px 16px', background: '#F0FDF4', color: '#15803D', border: '1px solid #BBF7D0', borderRadius: '20px', fontSize: '13px', cursor: 'pointer' }}>{q}</button>
            ))}
          </div>
        )}
        
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg, index) => (
            <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
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
                <div style={{ fontWeight: 600, fontSize: '12px', color: msg.role === 'user' ? '#EEEDFE' : '#6B6B6B', marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
                  <span>{msg.role === 'user' ? 'You' : 'System Assistant'}</span>
                  {msg.audio_answer_base64 && (
                    <button 
                      onClick={() => playAudioReply(msg.audio_answer_base64)}
                      style={{ background: 'none', border: 'none', color: '#534AB7', cursor: 'pointer', fontSize: '16px' }}>
                      🔊 Play
                    </button>
                  )}
                </div>
                
                <div className="whitespace-pre-line">{msg.content}</div>
                
                {msg.document_drafted && (
                  <div style={{ marginTop: '16px', padding: '16px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', fontFamily: 'monospace', fontSize: '12px', whiteSpace: 'pre-wrap' }}>
                    {msg.document_drafted}
                  </div>
                )}
                
                {msg.cited_cases && msg.cited_cases.length > 0 && (
                  <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {msg.cited_cases.map((c, i) => (
                      <a key={i} href="https://indiankanoon.org" target="_blank" rel="noreferrer" style={{ padding: '6px 10px', background: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '16px', fontSize: '11px', color: '#1D4ED8', textDecoration: 'none' }}>
                        ⚖ {c.name} ({c.year}) {c.citation} ↗
                      </a>
                    ))}
                  </div>
                )}
                
                {msg.circulars_cited && msg.circulars_cited.length > 0 && (
                  <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {msg.circulars_cited.map((c, i) => (
                      <a key={i} href={c.url || "https://incometaxindia.gov.in"} target="_blank" rel="noreferrer" style={{ padding: '6px 10px', background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '16px', fontSize: '11px', color: '#15803D', textDecoration: 'none' }}>
                        📄 {c.number} ↗
                      </a>
                    ))}
                  </div>
                )}
                
                {msg.role === 'assistant' && msg.artifacts && msg.artifacts.length > 0 && (
                  <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid #E8E8E4' }}>
                    <p style={{ fontSize: '12px', fontWeight: 600, marginBottom: '8px' }}>Artifacts Generated:</p>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {msg.artifacts.map((art, i) => (
                        <div key={i} style={{ padding: '8px 12px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          📄 <span>{art.path.split('/').pop()}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {loading && !isAgentMode && (
            <div className="flex justify-start">
              <div style={{ background: '#F7F6F3', border: '1px solid #E8E8E4', borderRadius: '16px', borderBottomLeftRadius: '4px', padding: '16px', fontSize: '14px', color: '#6B6B6B' }} className="animate-pulse shadow-sm">
                Assistant is thinking...
              </div>
            </div>
          )}
          
          {agentTaskStatus && agentTaskStatus !== 'complete' && (
            <div className="flex justify-start w-full">
              <div style={{ width: '100%', maxWidth: '42rem', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '12px', padding: '20px' }}>
                <h4 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '16px' }}>
                  {agentTaskStatus === 'planning' && "BharatLLM is planning your task..."}
                  {agentTaskStatus === 'running' && "Agents are executing your task..."}
                  {agentTaskStatus === 'awaiting_approval' && "Action requires your approval"}
                </h4>
                
                {agentTaskData?.plan && (
                  <div style={{ marginBottom: '16px' }}>
                    {agentTaskData.plan.map((step, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', marginBottom: '8px' }}>
                        <span style={{ color: agentTaskStatus === 'awaiting_approval' ? '#22C55E' : '#534AB7' }}>✓</span>
                        <span style={{ padding: '2px 6px', background: '#F7F6F3', borderRadius: '4px', fontWeight: 600 }}>{step.agent}</span>
                        <span>{step.sub_task}</span>
                      </div>
                    ))}
                  </div>
                )}
                
                {agentTaskStatus === 'awaiting_approval' && agentTaskData?.pending_action && (
                  <div style={{ background: '#FEF3C7', padding: '16px', borderRadius: '8px', border: '1px solid #FDE68A' }}>
                    <p style={{ fontWeight: 600, color: '#92400E', fontSize: '13px', marginBottom: '8px' }}>
                      Tool: {agentTaskData.pending_action.name}
                    </p>
                    <p style={{ fontSize: '12px', color: '#92400E', marginBottom: '12px' }}>
                      {agentTaskData.pending_action.description}
                    </p>
                    <div style={{ display: 'flex', gap: '12px' }}>
                      <button 
                        onClick={() => handleApprove(true)}
                        style={{ padding: '8px 16px', background: '#D97706', color: '#FFFFFF', border: 'none', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}>
                        Approve
                      </button>
                      <button 
                        onClick={() => handleApprove(false)}
                        style={{ padding: '8px 16px', background: '#FFFFFF', color: '#92400E', border: '1px solid #FCD34D', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}>
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        
        {/* Input box */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid #E8E8E4', background: '#FFFFFF' }}>
          
          {selectedImage && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', background: '#F7F6F3', borderRadius: '8px', marginBottom: '12px', width: 'max-content' }}>
              <span style={{ fontSize: '20px' }}>🖼</span>
              <span style={{ fontSize: '12px', fontWeight: 500 }}>{selectedImage.name}</span>
              <button onClick={() => setSelectedImage(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', marginLeft: '8px', color: '#991B1B' }}>✕</button>
            </div>
          )}
          
          {isRecording ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 20px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#DC2626' }} className="animate-pulse"></div>
                <span style={{ fontSize: '14px', fontWeight: 600, color: '#DC2626' }}>Recording... 0:{recordingDuration.toString().padStart(2, '0')}</span>
              </div>
              <button onClick={stopRecording} style={{ padding: '8px 16px', background: '#DC2626', color: '#FFFFFF', fontWeight: 600, borderRadius: '8px', border: 'none', cursor: 'pointer' }}>
                Stop & Send
              </button>
            </div>
          ) : (
            <form onSubmit={handleSend} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <label style={{ cursor: 'pointer', padding: '12px', background: '#F7F6F3', borderRadius: '50%', color: '#6B6B6B' }}>
                📷
                <input type="file" accept="image/*" style={{ display: 'none' }} onChange={handleImageSelect} />
              </label>
              
              <button type="button" onClick={startRecording} style={{ cursor: 'pointer', padding: '12px', background: '#F7F6F3', borderRadius: '50%', color: '#6B6B6B', border: 'none' }}>
                🎤
              </button>
              
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type a message, or use voice/image..."
                style={{
                  flex: 1, padding: '14px 20px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '12px', color: '#1A1A1A', outline: 'none', fontSize: '14px'
                }}
              />
              <button type="submit" disabled={(!input.trim() && !selectedImage) || loading} style={{ padding: '14px 24px', background: '#534AB7', color: '#FFFFFF', fontWeight: 600, borderRadius: '12px', border: 'none', cursor: 'pointer', fontSize: '14px', opacity: (!input.trim() && !selectedImage) || loading ? 0.6 : 1 }}>
                Send
              </button>
            </form>
          )}
        </div>
      </div>
      
    </div>
  )
}
