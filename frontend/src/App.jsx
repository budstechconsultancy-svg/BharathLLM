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
      <div style={{ minHeight: '100vh', background: '#F7F6F3', fontFamily: "system-ui, -apple-system, sans-serif" }} className="w-full flex items-center justify-center px-4 py-12">
        <div style={{ background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '10px', padding: '32px' }} className="max-w-md w-full shadow-sm animate-fade-in">
          <div className="text-center mb-8">
            <h2 style={{ fontSize: '24px', fontWeight: 600, color: '#1A1A1A' }}>{DEPLOYMENT_LABEL}</h2>
            <p style={{ fontSize: '13px', color: '#6B6B6B', marginTop: '4px' }}>Document Intelligence Portal Gateway</p>
          </div>
          
          {error && (
            <div style={{ padding: '12px', background: '#FEF2F2', border: '1px solid #EF4444', color: '#991B1B', borderRadius: '8px', fontSize: '13px', marginBottom: '16px' }}>
              {error}
            </div>
          )}
          
          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#6B6B6B', marginBottom: '4px' }}>Employee ID or Email</label>
              <input
                type="text"
                required
                value={employeeId}
                onChange={(e) => setEmployeeId(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', color: '#1A1A1A', fontSize: '14px' }}
                placeholder="e.g. ADM001"
              />
            </div>
            
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 500, color: '#6B6B6B', marginBottom: '4px' }}>Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ width: '100%', padding: '10px 14px', background: '#FFFFFF', border: '1px solid #E8E8E4', borderRadius: '8px', color: '#1A1A1A', fontSize: '14px' }}
                placeholder="••••••••"
              />
            </div>
            
            <button type="submit" style={{ width: '100%', padding: '12px', background: '#534AB7', color: '#FFFFFF', fontWeight: 500, borderRadius: '8px', fontSize: '14px', border: 'none', cursor: 'pointer' }}>
              Log In
            </button>
          </form>
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
          <div style={{ fontSize: "12px", fontWeight: 500, color: "#534AB7" }}>{user?.role === "super_admin" ? "Super Admin" : "User"}</div>
        </div>

        <div style={{ overflowY: "auto", flex: 1 }}>
          <span style={{ display: "block", fontSize: "10px", fontWeight: 600, color: "#9B9B9B", textTransform: "uppercase", letterSpacing: "0.1em", padding: "16px 12px 4px" }}>PORTALS</span>
          <NavItem id="chat" icon={MessageSquare} label="Chat Search" />
          
          {(user?.role === "dept_admin" || user?.role === "super_admin") && (
             <NavItem id="admin" icon={ShieldAlert} label="Admin Upload" />
          )}
          
          <NavItem id="apidev" icon={Code} label="API Developers" />
        </div>

        <div style={{ marginTop: "auto", padding: "16px", borderTop: "1px solid #E8E8E4", margin: "0 -16px" }}>
          <div style={{ fontSize: "11px", color: "#6B6B6B", marginBottom: "8px" }}>
            {user?.name || "User"} • {user?.department || "System"}
          </div>
          <button 
            onClick={() => setShowPasswordModal(true)}
            className="hover:text-[#1A1A1A]" 
            style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#6B6B6B", background: "none", border: "none", padding: 0, cursor: "pointer", marginBottom: "12px" }}
          >
            <Settings size={13} /> Change Password
          </button>
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
