import React, { useState } from 'react'
import ChatPortal from './portals/chat/ChatPortal.jsx'
import AdminPortal from './portals/admin/AdminPortal.jsx'
import DeveloperPortal from './portals/apidev/DeveloperPortal.jsx'
import { API_URL, DEPLOYMENT_LABEL } from './api/client.js'
import { LayoutDashboard, MessageSquare, Code, Settings, LogOut, ShieldAlert } from 'lucide-react'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "")
  const [user, setUser] = useState(JSON.parse(localStorage.getItem("user") || "null"))
  const [activePortal, setActivePortal] = useState("chat") // chat, admin, apidev
  
  const [employeeId, setEmployeeId] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")

  // Change Password States
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [modalError, setModalError] = useState("")

  const handleLogin = async (e) => {
    e.preventDefault()
    setError("")
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employee_id_or_email: employeeId, password })
      })
      
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || "Login failed.")
      }
      
      localStorage.setItem("token", data.access_token)
      localStorage.setItem("user", JSON.stringify(data.user))
      
      setToken(data.access_token)
      setUser(data.user)
    } catch (err) {
      setError(err.message)
    }
  }

  const handlePlaygroundLogin = async () => {
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employee_id_or_email: "user", password: "User@1234" })
      })
      
      const data = await response.json()
      if (!response.ok) throw new Error()
      
      const guestUser = { ...data.user, isGuest: true }
      localStorage.setItem("token", data.access_token)
      localStorage.setItem("user", JSON.stringify(guestUser))
      
      setToken(data.access_token)
      setUser(guestUser)
    } catch (err) {
      alert("Playground is currently unavailable. Please register.")
    }
  }

  const handleLogout = () => {
    localStorage.removeItem("token")
    localStorage.removeItem("user")
    setToken("")
    setUser(null)
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()
    setModalError("")
    if (newPassword !== confirmPassword) {
      setModalError("New passwords do not match.")
      return
    }
    if (newPassword.length < 12) {
      setModalError("New password must be at least 12 characters.")
      return
    }
    try {
      const response = await fetch(`${API_URL}/auth/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        })
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || "Failed to change password.")
      }
      alert("Password changed successfully. Please login again.")
      handleLogout()
      setShowPasswordModal(false)
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
    } catch (err) {
      setModalError(err.message)
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen w-full flex flex-col bg-[#FAFAFA] text-[#0F172A]" style={{ fontFamily: "var(--font-inter)" }}>
        
        {/* Enterprise Header */}
        <header className="w-full bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between z-20 sticky top-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#1E40AF] rounded-lg flex items-center justify-center text-white font-bold shadow-sm">B</div>
            <span className="font-bold text-xl tracking-tight" style={{ fontFamily: "var(--font-outfit)" }}>BharatLLM</span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            <a href="#" className="hover:text-[#1E40AF] transition-colors">Features</a>
            <a href="#" className="hover:text-[#1E40AF] transition-colors">Architecture</a>
            <a href="#" className="hover:text-[#1E40AF] transition-colors">Security</a>
          </nav>
          <div className="text-xs font-semibold px-3 py-1.5 bg-slate-100 text-slate-600 rounded-md border border-slate-200">
            NIC Directory Services
          </div>
        </header>

        <div className="flex-1 w-full flex flex-col lg:flex-row items-center justify-center p-6 lg:p-12 max-w-7xl mx-auto gap-16 relative z-10">
          
          {/* Left Hero Section */}
          <div className="flex-1 space-y-8 animate-fade-in">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 mb-6 rounded-full bg-[#EFF6FF] text-xs font-semibold text-[#1E40AF] border border-[#BFDBFE]">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#3B82F6] opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-[#2563EB]"></span>
                </span>
                Agentic Engine v3.1 Online
              </div>
              <h1 className="text-5xl lg:text-7xl font-bold mb-6 text-[#0F172A]" style={{ fontFamily: "var(--font-outfit)", lineHeight: "1.1" }}>
                Empowering <br />
                <span className="gradient-text-enterprise">Government Intelligence</span>
              </h1>
              <p className="text-lg text-slate-600 max-w-lg leading-relaxed">
                The unified, secure AI platform for the Government of India. Seamlessly process documents, analyze charts, and automate workflows with autonomous agents.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button onClick={() => document.getElementById('employeeId').focus()} className="enterprise-btn-primary px-6 py-3 rounded-xl font-semibold text-sm flex items-center gap-2">
                NIC Login <ShieldAlert size={16} />
              </button>
              <button className="enterprise-btn-secondary px-6 py-3 rounded-xl font-semibold text-sm flex items-center gap-2" onClick={handlePlaygroundLogin}>
                Try Playground <Code size={16} />
              </button>
            </div>

            {/* Feature Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-8 border-t border-slate-200 mt-8">
              <div className="animate-fade-in" style={{ animationDelay: '0.1s' }}>
                <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center mb-3">
                  <MessageSquare className="text-blue-700" size={18} />
                </div>
                <h3 className="text-sm font-bold text-slate-900 mb-1">Multimodal</h3>
                <p className="text-xs text-slate-500 leading-relaxed">Voice & Image inputs supported in 22 Indian languages.</p>
              </div>
              <div className="animate-fade-in" style={{ animationDelay: '0.2s' }}>
                <div className="w-10 h-10 rounded-xl bg-teal-100 flex items-center justify-center mb-3">
                  <LayoutDashboard className="text-teal-700" size={18} />
                </div>
                <h3 className="text-sm font-bold text-slate-900 mb-1">Agentic</h3>
                <p className="text-xs text-slate-500 leading-relaxed">Autonomous workflows managed by a Supervisor Agent.</p>
              </div>
              <div className="animate-fade-in" style={{ animationDelay: '0.3s' }}>
                <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center mb-3">
                  <Code className="text-indigo-700" size={18} />
                </div>
                <h3 className="text-sm font-bold text-slate-900 mb-1">Database RAG</h3>
                <p className="text-xs text-slate-500 leading-relaxed">Live querying of PostgreSQL and encrypted Vector Stores.</p>
              </div>
            </div>
          </div>

          {/* Right Login Panel */}
          <div className="w-full max-w-md animate-fade-in" style={{ animationDelay: '0.2s' }}>
            <div className="enterprise-card p-8 bg-white">
              <div className="mb-8">
                <h2 className="text-2xl font-bold text-slate-900 mb-2" style={{ fontFamily: "var(--font-outfit)" }}>Platform Login</h2>
                <p className="text-sm text-slate-500">Access your departmental workspace.</p>
              </div>
              
              {error && (
                <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-start gap-3 animate-fade-in">
                  <ShieldAlert size={18} className="shrink-0 mt-0.5 text-red-500" />
                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={handleLogin} className="space-y-5">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">Employee ID</label>
                  <input
                    type="text"
                    id="employeeId"
                    required
                    value={employeeId}
                    onChange={(e) => setEmployeeId(e.target.value)}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 text-sm focus:outline-none focus:border-[#1E40AF] focus:ring-1 focus:ring-[#1E40AF] transition-all placeholder:text-slate-400"
                    placeholder="e.g. ADM001"
                  />
                </div>
                
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase tracking-wider mb-2">Password</label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-slate-900 text-sm focus:outline-none focus:border-[#1E40AF] focus:ring-1 focus:ring-[#1E40AF] transition-all placeholder:text-slate-400"
                    placeholder="••••••••"
                  />
                </div>
                
                <div className="flex items-center justify-between pb-2">
                  <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer">
                    <input type="checkbox" className="rounded border-slate-300 text-[#1E40AF] focus:ring-[#1E40AF]" />
                    Remember me
                  </label>
                  <a href="#" className="text-xs font-semibold text-[#1E40AF] hover:underline">Forgot Password?</a>
                </div>

                <button type="submit" className="w-full py-3.5 rounded-xl enterprise-btn-primary font-semibold text-sm flex justify-center items-center gap-2 shadow-md">
                  Authenticate <ShieldAlert size={16} />
                </button>
              </form>

              <div className="mt-8 pt-6 border-t border-slate-100 text-center">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <img src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg" alt="Gov" className="h-6 opacity-60 grayscale" />
                </div>
                <p className="text-xs text-slate-400">
                  Secured by NIC ePramaan. Unauthorized access is strictly prohibited.
                </p>
              </div>
            </div>
          </div>

        </div>
      </div>
    )
  }

  if (activePortal === "admin") {
    return <AdminPortal token={token} user={user} onNavigate={setActivePortal} />
  }

  const NavItem = ({ id, icon: Icon, label }) => {
    const isActive = activePortal === id
    return (
      <button
        onClick={() => setActivePortal(id)}
        className="hover:bg-[#F7F6F3] hover:text-[#1A1A1A]"
        style={{
          width: "100%",
          display: "flex", alignItems: "center", gap: "10px",
          background: isActive ? "#F7F6F3" : "transparent",
          color: isActive ? "#1A1A1A" : "#6B6B6B",
          fontWeight: isActive ? 500 : 400,
          padding: isActive ? "8px 12px 8px 14px" : "8px 12px",
          borderRadius: isActive ? "0 6px 6px 0" : "6px",
          borderLeft: isActive ? "2.5px solid #534AB7" : "none",
          marginLeft: isActive ? "-16px" : "0",
          fontSize: "13px",
          transition: "all 0.2s"
        }}
      >
        <Icon size={15} strokeWidth={1.8} />
        {label}
      </button>
    )
  }

  return (
    <div style={{ display: "flex", height: "100vh", background: "#F7F6F3", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      {/* Global Light Sidebar */}
      <div 
        className="hidden md:flex flex-col z-40"
        style={{
          width: "240px", height: "100vh", background: "#FFFFFF", borderRight: "1px solid #E8E8E4",
          padding: "16px", paddingTop: "0"
        }}
      >
        <div style={{ padding: "20px 16px 16px", borderBottom: "1px solid #E8E8E4", margin: "0 -16px" }}>
          <div style={{ fontSize: "14px", fontWeight: 600, color: "#1A1A1A", paddingLeft: "16px" }}>{DEPLOYMENT_LABEL}</div>
          <div style={{ fontSize: "11px", color: "#6B6B6B", paddingLeft: "16px" }}>Platform Gateway</div>
        </div>

        <div style={{ margin: "12px 16px 12px 0", padding: "6px 12px", background: "#EEEDFE", borderRadius: "20px", display: "inline-flex", alignItems: "center", gap: "6px", alignSelf: "flex-start" }}>
          <div style={{ width: "8px", height: "8px", background: "#534AB7", borderRadius: "50%" }}></div>
          <div style={{ fontSize: "12px", fontWeight: 500, color: "#534AB7" }}>{user?.isGuest ? "Guest (Playground)" : (user?.role === "super_admin" ? "Super Admin" : "User")}</div>
        </div>

        <div style={{ overflowY: "auto", flex: 1 }}>
          <span style={{ display: "block", fontSize: "10px", fontWeight: 600, color: "#9B9B9B", textTransform: "uppercase", letterSpacing: "0.1em", padding: "16px 12px 4px" }}>PORTALS</span>
          <NavItem id="chat" icon={MessageSquare} label="Chat Search" />
          
          {(user?.role === "dept_admin" || user?.role === "super_admin") && !user?.isGuest && (
             <NavItem id="admin" icon={ShieldAlert} label="Admin Upload" />
          )}
          
          {!user?.isGuest && (
             <NavItem id="apidev" icon={Code} label="API Developers" />
          )}
        </div>

        <div style={{ marginTop: "auto", padding: "16px", borderTop: "1px solid #E8E8E4", margin: "0 -16px" }}>
          <div style={{ fontSize: "11px", color: "#6B6B6B", marginBottom: "8px" }}>
            {user?.name || "User"} • {user?.department || "System"}
          </div>
          {!user?.isGuest && (
            <button 
              onClick={() => setShowPasswordModal(true)}
              className="hover:text-[#1A1A1A]" 
              style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#6B6B6B", background: "none", border: "none", padding: 0, cursor: "pointer", marginBottom: "12px" }}
            >
              <Settings size={13} /> Change Password
            </button>
          )}
          <button 
            onClick={handleLogout}
            className="hover:text-[#C0392B]" 
            style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#6B6B6B", background: "none", border: "none", padding: 0, cursor: "pointer" }}
          >
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </div>
      
      {/* Content wrapper */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {activePortal === "chat" && <ChatPortal token={token} user={user} />}
        {activePortal === "admin" && <AdminPortal token={token} user={user} />}
        {activePortal === "apidev" && <DeveloperPortal token={token} user={user} />}
      </div>

      {/* Change Password Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div style={{ background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '10px', padding: '32px' }} className="max-w-md w-full shadow-lg animate-fade-in relative">
            <h3 style={{ fontSize: '20px', fontWeight: 600, color: '#1A1A1A', marginBottom: '24px' }}>Change Password</h3>
            {modalError && (
              <div style={{ padding: '12px', background: '#FEF2F2', border: '1px solid #EF4444', color: '#991B1B', borderRadius: '8px', fontSize: '13px', marginBottom: '16px' }}>
                {modalError}
              </div>
            )}
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#6B6B6B', marginBottom: '4px' }}>Current Password</label>
                <input
                  type="password"
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', color: '#1A1A1A', fontSize: '14px' }}
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#6B6B6B', marginBottom: '4px' }}>New Password</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', color: '#1A1A1A', fontSize: '14px' }}
                  placeholder="•••••••• (min 12 chars)"
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#6B6B6B', marginBottom: '4px' }}>Confirm New Password</label>
                <input
                  type="password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  style={{ width: '100%', padding: '10px 14px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', color: '#1A1A1A', fontSize: '14px' }}
                  placeholder="••••••••"
                />
              </div>
              <div className="flex space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  style={{ flex: 1, padding: '10px', background: '#F7F6F3', color: '#6B6B6B', fontWeight: 500, borderRadius: '8px', fontSize: '14px', border: '1px solid #E8E8E4', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ flex: 1, padding: '10px', background: '#534AB7', color: '#FFFFFF', fontWeight: 500, borderRadius: '8px', fontSize: '14px', border: 'none', cursor: 'pointer' }}
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
