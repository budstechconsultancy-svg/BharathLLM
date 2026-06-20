import React, { useState, useRef } from 'react'
import {
  LayoutDashboard, Building2, Upload, ListChecks,
  KeyRound, FileText, BarChart2, Cpu, LogOut,
  FileBarChart, Menu, Server, Database, Activity, Clock
} from 'lucide-react'

export default function AdminPortal({
  deploymentLabel = "India Govt LLM",
  portalVersion = "Admin Portal v2.0",
  adminRole = "Super Admin",
  adminName = "Administrator",
  orgUnit = "All Departments",
  token,
  user
}) {
  const [activeNav, setActiveNav] = useState("dashboard")
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // -- SEED DATA --
  const deptData = [
    { dept:"Health",           docs:"1,204", queries:"612", accuracy:"93.1%", lastUpload:"2h ago",  status:"Active",   statusType:"active"   },
    { dept:"School Education", docs:"987",   queries:"441", accuracy:"89.4%", lastUpload:"5h ago",  status:"Active",   statusType:"active"   },
    { dept:"Finance",          docs:"762",   queries:"388", accuracy:"94.7%", lastUpload:"1d ago",  status:"Active",   statusType:"active"   },
    { dept:"Revenue",          docs:"634",   queries:"201", accuracy:"88.1%", lastUpload:"3d ago",  status:"Active",   statusType:"active"   },
    { dept:"PWD",              docs:"410",   queries:"89",  accuracy:"85.2%", lastUpload:"5d ago",  status:"Low",      statusType:"low"      },
    { dept:"Agriculture",      docs:"298",   queries:"62",  accuracy:"81.4%", lastUpload:"7d ago",  status:"Low",      statusType:"low"      },
    { dept:"IT Department",    docs:"198",   queries:"44",  accuracy:"79.3%", lastUpload:"12d ago", status:"Critical", statusType:"critical" },
    { dept:"Transport",        docs:"156",   queries:"31",  accuracy:"76.8%", lastUpload:"15d ago", status:"Critical", statusType:"critical" },
  ]

  const jobsData = [
    { file:"GO_MS_142_Health.pdf",        dept:"Health",      pages:"12", chunks:"47", quality:"92", status:"Live",       statusType:"active"   },
    { file:"Circular_Finance_June.pdf",   dept:"Finance",     pages:"4",  chunks:"18", quality:"88", status:"Live",       statusType:"active"   },
    { file:"TN_Scheme_Education_2024.pdf",dept:"School Edu",  pages:"28", chunks:"—",  quality:"—",  status:"Processing", statusType:"processing"},
    { file:"PWD_Tender_Chennai.pdf",      dept:"PWD",         pages:"6",  chunks:"21", quality:"34", status:"Review",     statusType:"low"      },
    { file:"Revenue_Circular_May.pdf",    dept:"Revenue",     pages:"—",  chunks:"—",  quality:"—",  status:"Failed",     statusType:"critical" },
  ]

  const departmentsData = [
    { name: "Health & Family Welfare", admin: "Dr. J. Radhakrishnan", systems: 3, docs: "1,204", quota: 85, status: "Active", statusType: "active" },
    { name: "School Education", admin: "Thiru. K. Nanthakumar", systems: 2, docs: "987", quota: 62, status: "Active", statusType: "active" },
    { name: "Finance", admin: "Thiru. T. Udhayachandran", systems: 4, docs: "762", quota: 40, status: "Active", statusType: "active" },
    { name: "Revenue & Disaster Mgmt", admin: "Thiru. Kumar Jayant", systems: 1, docs: "634", quota: 92, status: "Active", statusType: "active" },
    { name: "Public Works Department", admin: "Thiru. Mangat Ram Sharma", systems: 1, docs: "410", quota: 15, status: "Low", statusType: "low" },
    { name: "Information Technology", admin: "Thiru. Dheeraj Kumar", systems: 5, docs: "198", quota: 98, status: "Critical", statusType: "critical" },
  ]

  const apiKeysData = [
    { keyName: "Health Portal Backend", dept: "Health", limit: "500/min", created: "2026-01-15", status: "Active" },
    { keyName: "Finance Dashboard", dept: "Finance", limit: "100/min", created: "2026-03-22", status: "Active" },
    { keyName: "Education Mobile App", dept: "School Edu", limit: "1000/min", created: "2026-05-10", status: "Active" },
    { keyName: "Legacy Transport System", dept: "Transport", limit: "50/min", created: "2025-11-05", status: "Revoked" },
  ]

  const queryLogsData = [
    { query: "What is the budget allocation for CMHIS?", dept: "Health", latency: "1.2s", docs: 4, time: "2 mins ago" },
    { query: "Guidelines for teacher transfers 2024", dept: "School Edu", latency: "0.8s", docs: 2, time: "15 mins ago" },
    { query: "Tender process for new highway project", dept: "PWD", latency: "2.1s", docs: 8, time: "1 hour ago" },
    { query: "Agricultural subsidies for delta region", dept: "Agriculture", latency: "1.5s", docs: 3, time: "3 hours ago" },
    { query: "Stamp duty changes in recent G.O.", dept: "Revenue", latency: "1.1s", docs: 5, time: "4 hours ago" },
  ]

  const benchmarksData = [
    { metric: "Average Latency", val: "1.12s", target: "< 1.5s", status: "Pass" },
    { metric: "Retrieval@5 Accuracy", val: "91.2%", target: "> 90%", status: "Pass" },
    { metric: "Token Throughput", val: "450 tk/s", target: "> 400 tk/s", status: "Pass" },
    { metric: "Context Window Utility", val: "84%", target: "> 80%", status: "Pass" },
    { metric: "Concurrent DB Connections", val: "124", target: "Scale @ 500", status: "Normal" },
  ]

  // -- UPLOAD STATE --
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const fileInputRef = useRef(null)

  const handleFileUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setProgress(10);
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      const response = await fetch("http://127.0.0.1:8000/ingest", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData
      });
      
      setProgress(50);
      
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Upload failed");
      }
      
      setProgress(100);
      setTimeout(() => {
        setUploading(false);
        setProgress(0);
        alert(`File successfully uploaded! Job ID: ${result.job_id}`);
      }, 500);
      
    } catch (err) {
      setUploading(false);
      setProgress(0);
      alert(`Error uploading document: ${err.message}`);
    }
  }

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  }

  // -- RENDER HELPERS --
  const renderStatusBadge = (status, type) => {
    let dot = "", bg = "", text = ""
    if (type === "active" || status === "Active" || status === "Pass" || status === "Normal") { dot = "#22C55E"; bg = "#F0FDF4"; text = "#166534" }
    else if (type === "low") { dot = "#F59E0B"; bg = "#FFFBEB"; text = "#92400E" }
    else if (type === "critical" || status === "Revoked") { dot = "#EF4444"; bg = "#FEF2F2"; text = "#991B1B" }
    else if (type === "processing") { dot = "#1E40AF"; bg = "#EFF6FF"; text = "#1E40AF" }

    return (
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <div style={{ width: "8px", height: "8px", borderRadius: "50%", flexShrink: 0, backgroundColor: dot }}></div>
        <div style={{ padding: "3px 10px", borderRadius: "20px", fontSize: "11px", fontWeight: 500, backgroundColor: bg, color: text, whiteSpace: "nowrap" }}>
          {status}
        </div>
      </div>
    )
  }

  const renderAccuracy = (val) => {
    if (val === "—") return <span style={{ color: "#1A1A1A" }}>{val}</span>
    const num = parseFloat(val)
    let col = "#C0392B"
    if (num >= 90) col = "#1A7A52"
    else if (num >= 80) col = "#92400E"
    return <span style={{ color: col }}>{val}</span>
  }

  const NavItem = ({ id, icon: Icon, label }) => {
    const isActive = activeNav === id
    return (
      <button
        onClick={() => { setActiveNav(id); setSidebarOpen(false) }}
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

  // -- PAGE CONTENTS --
  
  const dashboardContent = (
    <div style={{ padding: "28px 32px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px" }}>
        <h1 style={{ fontSize: "20px", fontWeight: 600, color: "#1A1A1A" }}>System overview</h1>
        <button 
          className="hover:bg-[#F7F6F3]"
          style={{
            padding: "8px 16px", border: "1px solid #E8E8E4", borderRadius: "8px", background: "#FFFFFF",
            fontSize: "13px", fontWeight: 500, color: "#1A1A1A", display: "flex", alignItems: "center", gap: "6px", cursor: "pointer"
          }}
        >
          <FileBarChart size={14} /> Generate report ↗
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "32px" }}>
        {[
          { label: "Departments active", val: "14", delta: "↑ 2 this month", dCol: "#1A7A52" },
          { label: "Documents indexed", val: "8,342", delta: "↑ 134 this week", dCol: "#1A7A52" },
          { label: "Queries today", val: "2,410", delta: "↑ 18% vs yesterday", dCol: "#1A7A52" },
          { label: "Retrieval@5 accuracy", val: "91.2%", delta: "↓ 0.8% vs last week", dCol: "#C0392B" }
        ].map((c, i) => (
          <div key={i} style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "10px", padding: "20px" }}>
            <div style={{ fontSize: "28px", fontWeight: 600, color: "#1A1A1A", lineHeight: 1 }}>{c.val}</div>
            <div style={{ fontSize: "13px", color: "#6B6B6B", marginTop: "4px" }}>{c.label}</div>
            <div style={{ fontSize: "12px", fontWeight: 500, color: c.dCol, marginTop: "8px" }}>{c.delta}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, color: "#1A1A1A" }}>Department activity</h2>
        <span style={{ fontSize: "12px", color: "#9B9B9B" }}>last 24 hours</span>
      </div>
      <div style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "10px", overflowX: "auto", marginBottom: "28px" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: "600px" }}>
          <thead style={{ background: "#FAFAF8", borderBottom: "1px solid #E8E8E4" }}>
            <tr>
              {["Department", "Docs", "Queries", "Accuracy", "Last upload", "Status"].map(th => (
                <th key={th} style={{ padding: "12px 20px", textAlign: "left", fontSize: "12px", fontWeight: 500, color: "#6B6B6B" }}>{th}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {deptData.map((r, i) => (
              <tr key={i} style={{ borderBottom: i < deptData.length - 1 ? "1px solid #F0F0EC" : "none" }} className="hover:bg-[#FAFAF8]">
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.dept}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.docs}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.queries}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{renderAccuracy(r.accuracy)}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.lastUpload}</td>
                <td style={{ padding: "14px 20px", verticalAlign: "middle" }}>{renderStatusBadge(r.status, r.statusType)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", marginTop: "28px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: 600, color: "#1A1A1A" }}>Recent ingestion jobs</h2>
        <span onClick={() => setActiveNav('ingestion_jobs')} className="hover:text-[#1A1A1A]" style={{ fontSize: "12px", color: "#9B9B9B", cursor: "pointer" }}>View all →</span>
      </div>
      <div style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "10px", overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: "600px" }}>
          <thead style={{ background: "#FAFAF8", borderBottom: "1px solid #E8E8E4" }}>
            <tr>
              {["File", "Department", "Pages", "Chunks", "Quality", "Status"].map(th => (
                <th key={th} style={{ padding: "12px 20px", textAlign: "left", fontSize: "12px", fontWeight: 500, color: "#6B6B6B" }}>{th}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {jobsData.map((r, i) => (
              <tr key={i} style={{ borderBottom: i < jobsData.length - 1 ? "1px solid #F0F0EC" : "none" }} className="hover:bg-[#FAFAF8]">
                <td style={{ padding: "14px 20px", fontSize: "12px", color: "#1A1A1A", fontFamily: "monospace", verticalAlign: "middle" }}>{r.file}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.dept}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.pages}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.chunks}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{renderAccuracy(r.quality)}</td>
                <td style={{ padding: "14px 20px", verticalAlign: "middle" }}>{renderStatusBadge(r.status, r.statusType)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const departmentsContent = (
    <div style={{ padding: "28px 32px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px" }}>
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: 600, color: "#1A1A1A" }}>Departments Overview</h1>
          <p style={{ fontSize: "13px", color: "#6B6B6B", marginTop: "4px" }}>Manage integrated government departments and API quotas.</p>
        </div>
        <button 
          className="hover:bg-[#4338CA]"
          style={{
            padding: "8px 16px", borderRadius: "8px", background: "#534AB7", border: "none",
            fontSize: "13px", fontWeight: 500, color: "#FFFFFF", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px"
          }}
        >
          <span>+ Add Department</span>
        </button>
      </div>

      <div style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "10px", overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: "800px" }}>
          <thead style={{ background: "#FAFAF8", borderBottom: "1px solid #E8E8E4" }}>
            <tr>
              {["Department Name", "Admin Contact", "Integrated Systems", "Total Documents", "Quota Used", "Status"].map(th => (
                <th key={th} style={{ padding: "12px 20px", textAlign: "left", fontSize: "12px", fontWeight: 500, color: "#6B6B6B" }}>{th}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {departmentsData.map((r, i) => (
              <tr key={i} style={{ borderBottom: i < departmentsData.length - 1 ? "1px solid #F0F0EC" : "none" }} className="hover:bg-[#FAFAF8]">
                <td style={{ padding: "14px 20px", fontSize: "13px", fontWeight: 500, color: "#1A1A1A", verticalAlign: "middle" }}>{r.name}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#6B6B6B", verticalAlign: "middle" }}>{r.admin}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.systems}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.docs}</td>
                <td style={{ padding: "14px 20px", verticalAlign: "middle", minWidth: "150px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <div style={{ flex: 1, height: "6px", background: "#F0F0EC", borderRadius: "3px", overflow: "hidden" }}>
                      <div style={{ width: `${r.quota}%`, height: "100%", background: r.quota > 90 ? "#EF4444" : r.quota > 75 ? "#F59E0B" : "#22C55E", borderRadius: "3px" }}></div>
                    </div>
                    <span style={{ fontSize: "11px", color: "#6B6B6B", minWidth: "30px" }}>{r.quota}%</span>
                  </div>
                </td>
                <td style={{ padding: "14px 20px", verticalAlign: "middle" }}>{renderStatusBadge(r.status, r.statusType)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const uploadDocsContent = (
    <div style={{ padding: "28px 32px" }}>
      <div>
        <h1 style={{ fontSize: "20px", fontWeight: 600, color: "#1A1A1A" }}>Upload Documents</h1>
        <p style={{ fontSize: "13px", color: "#6B6B6B", marginTop: "4px", marginBottom: "28px" }}>Ingest new files into the vector database securely.</p>
      </div>

      <div 
        onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        style={{ 
          border: dragActive ? "2px dashed #534AB7" : "2px dashed #E8E8E4",
          background: dragActive ? "#F0F0FE" : "#FFFFFF",
          borderRadius: "12px", padding: "64px 32px", textAlign: "center", transition: "all 0.2s"
        }}
      >
        <Upload size={32} color={dragActive ? "#534AB7" : "#9B9B9B"} style={{ margin: "0 auto 16px" }} />
        <p style={{ fontSize: "14px", fontWeight: 500, color: "#1A1A1A" }}>Drag & drop files here</p>
        <p style={{ fontSize: "12px", color: "#6B6B6B", marginTop: "4px", marginBottom: "24px" }}>Support for PDF files up to 50MB</p>
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          accept=".pdf"
          onChange={handleFileChange} 
        />
        <button onClick={() => fileInputRef.current.click()} className="hover:bg-[#F7F6F3]" style={{ padding: "10px 20px", background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "8px", fontSize: "13px", fontWeight: 500, color: "#1A1A1A", cursor: "pointer", boxShadow: "0 1px 2px rgba(0,0,0,0.05)" }}>
          Browse Files
        </button>
      </div>

      {uploading && (
        <div style={{ marginTop: "24px", background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "8px", padding: "16px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "12px", fontWeight: 500, color: "#1A1A1A" }}>Uploading document...</span>
            <span style={{ fontSize: "12px", color: "#6B6B6B" }}>{progress}%</span>
          </div>
          <div style={{ width: "100%", height: "6px", background: "#F0F0EC", borderRadius: "3px", overflow: "hidden" }}>
            <div style={{ width: `${progress}%`, height: "100%", background: "#534AB7", borderRadius: "3px", transition: "width 0.2s" }}></div>
          </div>
        </div>
      )}
    </div>
  )

  const ingestionJobsContent = (
    <div style={{ padding: "28px 32px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px" }}>
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: 600, color: "#1A1A1A" }}>Ingestion Jobs</h1>
          <p style={{ fontSize: "13px", color: "#6B6B6B", marginTop: "4px" }}>Monitor document parsing and vector embedding tasks.</p>
        </div>
        <button 
          className="hover:bg-[#F7F6F3]"
          style={{
            padding: "8px 16px", borderRadius: "8px", background: "#FFFFFF", border: "1px solid #E8E8E4",
            fontSize: "13px", fontWeight: 500, color: "#1A1A1A", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px"
          }}
        >
          <ListChecks size={14} /> Refresh Logs
        </button>
      </div>

      <div style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "10px", overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: "600px" }}>
          <thead style={{ background: "#FAFAF8", borderBottom: "1px solid #E8E8E4" }}>
            <tr>
              {["File", "Department", "Pages", "Chunks", "Quality", "Status"].map(th => (
                <th key={th} style={{ padding: "12px 20px", textAlign: "left", fontSize: "12px", fontWeight: 500, color: "#6B6B6B" }}>{th}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {jobsData.map((r, i) => (
              <tr key={i} style={{ borderBottom: i < jobsData.length - 1 ? "1px solid #F0F0EC" : "none" }} className="hover:bg-[#FAFAF8]">
                <td style={{ padding: "14px 20px", fontSize: "12px", color: "#1A1A1A", fontFamily: "monospace", verticalAlign: "middle" }}>{r.file}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.dept}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.pages}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.chunks}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{renderAccuracy(r.quality)}</td>
                <td style={{ padding: "14px 20px", verticalAlign: "middle" }}>{renderStatusBadge(r.status, r.statusType)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const apiKeysContent = (
    <div style={{ padding: "28px 32px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px" }}>
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: 600, color: "#1A1A1A" }}>API Keys</h1>
          <p style={{ fontSize: "13px", color: "#6B6B6B", marginTop: "4px" }}>Manage integration credentials across all departments.</p>
        </div>
      </div>
      <div style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "10px", overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: "600px" }}>
          <thead style={{ background: "#FAFAF8", borderBottom: "1px solid #E8E8E4" }}>
            <tr>
              {["Key Name", "Department", "Rate Limit", "Created", "Status", "Actions"].map(th => (
                <th key={th} style={{ padding: "12px 20px", textAlign: "left", fontSize: "12px", fontWeight: 500, color: "#6B6B6B" }}>{th}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {apiKeysData.map((r, i) => (
              <tr key={i} style={{ borderBottom: i < apiKeysData.length - 1 ? "1px solid #F0F0EC" : "none" }} className="hover:bg-[#FAFAF8]">
                <td style={{ padding: "14px 20px", fontSize: "13px", fontWeight: 500, color: "#1A1A1A", verticalAlign: "middle" }}>{r.keyName}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#6B6B6B", verticalAlign: "middle" }}>{r.dept}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.limit}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#6B6B6B", verticalAlign: "middle" }}>{r.created}</td>
                <td style={{ padding: "14px 20px", verticalAlign: "middle" }}>{renderStatusBadge(r.status, "active")}</td>
                <td style={{ padding: "14px 20px", verticalAlign: "middle" }}>
                  <button style={{ background: "none", border: "none", color: "#EF4444", fontSize: "12px", fontWeight: 500, cursor: "pointer" }}>Revoke</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const queryLogsContent = (
    <div style={{ padding: "28px 32px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px" }}>
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: 600, color: "#1A1A1A" }}>Query Logs</h1>
          <p style={{ fontSize: "13px", color: "#6B6B6B", marginTop: "4px" }}>Real-time stream of incoming queries and their execution latency.</p>
        </div>
      </div>
      <div style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "10px", overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: "600px" }}>
          <thead style={{ background: "#FAFAF8", borderBottom: "1px solid #E8E8E4" }}>
            <tr>
              {["Query", "Department", "Latency", "Docs Retrieved", "Time"].map(th => (
                <th key={th} style={{ padding: "12px 20px", textAlign: "left", fontSize: "12px", fontWeight: 500, color: "#6B6B6B" }}>{th}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {queryLogsData.map((r, i) => (
              <tr key={i} style={{ borderBottom: i < queryLogsData.length - 1 ? "1px solid #F0F0EC" : "none" }} className="hover:bg-[#FAFAF8]">
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle", maxWidth: "300px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>"{r.query}"</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#6B6B6B", verticalAlign: "middle" }}>{r.dept}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A7A52", fontWeight: 500, verticalAlign: "middle" }}>{r.latency}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.docs}</td>
                <td style={{ padding: "14px 20px", fontSize: "12px", color: "#9B9B9B", verticalAlign: "middle" }}>{r.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const benchmarksContent = (
    <div style={{ padding: "28px 32px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px" }}>
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: 600, color: "#1A1A1A" }}>System Benchmarks</h1>
          <p style={{ fontSize: "13px", color: "#6B6B6B", marginTop: "4px" }}>Key Performance Indicators and SLA compliance metrics.</p>
        </div>
      </div>
      <div style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "10px", overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", minWidth: "600px" }}>
          <thead style={{ background: "#FAFAF8", borderBottom: "1px solid #E8E8E4" }}>
            <tr>
              {["Metric", "Current Value", "Target (SLA)", "Status"].map(th => (
                <th key={th} style={{ padding: "12px 20px", textAlign: "left", fontSize: "12px", fontWeight: 500, color: "#6B6B6B" }}>{th}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {benchmarksData.map((r, i) => (
              <tr key={i} style={{ borderBottom: i < benchmarksData.length - 1 ? "1px solid #F0F0EC" : "none" }} className="hover:bg-[#FAFAF8]">
                <td style={{ padding: "14px 20px", fontSize: "13px", fontWeight: 500, color: "#1A1A1A", verticalAlign: "middle" }}>{r.metric}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#1A1A1A", verticalAlign: "middle" }}>{r.val}</td>
                <td style={{ padding: "14px 20px", fontSize: "13px", color: "#6B6B6B", verticalAlign: "middle" }}>{r.target}</td>
                <td style={{ padding: "14px 20px", verticalAlign: "middle" }}>{renderStatusBadge(r.status, "active")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )

  const modelStatusContent = (
    <div style={{ padding: "28px 32px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px" }}>
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: 600, color: "#1A1A1A" }}>Model Status</h1>
          <p style={{ fontSize: "13px", color: "#6B6B6B", marginTop: "4px" }}>Server health and inference engine diagnostics.</p>
        </div>
      </div>
      
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "16px", marginBottom: "24px" }}>
        <div style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "10px", padding: "20px", display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "#F0FDF4", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Server size={24} color="#166534" />
          </div>
          <div>
            <div style={{ fontSize: "12px", color: "#6B6B6B", marginBottom: "2px" }}>LLM Inference Engine</div>
            <div style={{ fontSize: "16px", fontWeight: 600, color: "#1A1A1A" }}>Llama-3-8B-Instruct</div>
            <div style={{ fontSize: "11px", color: "#1A7A52", fontWeight: 500, marginTop: "4px" }}>● Online</div>
          </div>
        </div>

        <div style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "10px", padding: "20px", display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "#EFF6FF", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Cpu size={24} color="#1E40AF" />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: "12px", color: "#6B6B6B", marginBottom: "2px" }}>GPU Memory Usage</div>
            <div style={{ fontSize: "16px", fontWeight: 600, color: "#1A1A1A" }}>14.2 GB / 24.0 GB</div>
            <div style={{ width: "100%", height: "4px", background: "#E8E8E4", borderRadius: "2px", marginTop: "8px", overflow: "hidden" }}>
               <div style={{ width: "59%", height: "100%", background: "#534AB7" }}></div>
            </div>
          </div>
        </div>

        <div style={{ background: "#FFFFFF", border: "1px solid #E8E8E4", borderRadius: "10px", padding: "20px", display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "#FEF2F2", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Database size={24} color="#991B1B" />
          </div>
          <div>
            <div style={{ fontSize: "12px", color: "#6B6B6B", marginBottom: "2px" }}>Vector Database</div>
            <div style={{ fontSize: "16px", fontWeight: 600, color: "#1A1A1A" }}>Qdrant Cluster</div>
            <div style={{ fontSize: "11px", color: "#1A7A52", fontWeight: 500, marginTop: "4px" }}>● Connected</div>
          </div>
        </div>
      </div>
    </div>
  )

  const renderContent = () => {
    switch (activeNav) {
      case "dashboard": return dashboardContent
      case "departments": return departmentsContent
      case "upload_docs": return uploadDocsContent
      case "ingestion_jobs": return ingestionJobsContent
      case "api_keys": return apiKeysContent
      case "query_logs": return queryLogsContent
      case "benchmarks": return benchmarksContent
      case "model_status": return modelStatusContent
      default: return dashboardContent
    }
  }

  return (
    <div style={{ display: "flex", height: "100vh", background: "#F7F6F3", fontFamily: "system-ui, -apple-system, sans-serif" }}>
      
      <div className="min-[900px]:hidden flex items-center justify-between bg-white border-b border-[#E8E8E4] p-4 absolute top-0 left-0 right-0 z-20">
        <div style={{ fontSize: "14px", fontWeight: 600, color: "#1A1A1A" }}>{deploymentLabel}</div>
        <button onClick={() => setSidebarOpen(!sidebarOpen)}>
          <Menu size={24} color="#1A1A1A" />
        </button>
      </div>

      {sidebarOpen && (
        <div 
          className="min-[900px]:hidden fixed inset-0 bg-black/50 z-30" 
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div 
        className={`${sidebarOpen ? "translate-x-0" : "-translate-x-full"} min-[900px]:translate-x-0 fixed min-[900px]:relative z-40 transition-transform duration-300 ease-in-out custom-scrollbar`}
        style={{
          width: "240px", height: "100vh", background: "#FFFFFF", borderRight: "1px solid #E8E8E4",
          display: "flex", flexDirection: "column", padding: "16px", paddingTop: "0"
        }}
      >
        <div style={{ padding: "20px 16px 16px", borderBottom: "1px solid #E8E8E4", margin: "0 -16px" }}>
          <div style={{ fontSize: "14px", fontWeight: 600, color: "#1A1A1A", paddingLeft: "16px" }}>{deploymentLabel}</div>
          <div style={{ fontSize: "11px", color: "#6B6B6B", paddingLeft: "16px" }}>{portalVersion}</div>
        </div>

        <div style={{ margin: "12px 16px 12px 0", padding: "6px 12px", background: "#EEEDFE", borderRadius: "20px", display: "inline-flex", alignItems: "center", gap: "6px", alignSelf: "flex-start" }}>
          <div style={{ width: "8px", height: "8px", background: "#534AB7", borderRadius: "50%" }}></div>
          <div style={{ fontSize: "12px", fontWeight: 500, color: "#534AB7" }}>{adminRole}</div>
        </div>

        <div style={{ overflowY: "auto", flex: 1 }}>
          <span style={{ display: "block", fontSize: "10px", fontWeight: 600, color: "#9B9B9B", textTransform: "uppercase", letterSpacing: "0.1em", padding: "16px 12px 4px" }}>OVERVIEW</span>
          <NavItem id="dashboard" icon={LayoutDashboard} label="Dashboard" />
          <NavItem id="departments" icon={Building2} label="Departments" />

          <span style={{ display: "block", fontSize: "10px", fontWeight: 600, color: "#9B9B9B", textTransform: "uppercase", letterSpacing: "0.1em", padding: "16px 12px 4px" }}>DOCUMENTS</span>
          <NavItem id="upload_docs" icon={Upload} label="Upload docs" />
          <NavItem id="ingestion_jobs" icon={ListChecks} label="Ingestion jobs" />

          <span style={{ display: "block", fontSize: "10px", fontWeight: 600, color: "#9B9B9B", textTransform: "uppercase", letterSpacing: "0.1em", padding: "16px 12px 4px" }}>SECURITY</span>
          <NavItem id="api_keys" icon={KeyRound} label="API keys" />
          <NavItem id="query_logs" icon={FileText} label="Query logs" />

          <span style={{ display: "block", fontSize: "10px", fontWeight: 600, color: "#9B9B9B", textTransform: "uppercase", letterSpacing: "0.1em", padding: "16px 12px 4px" }}>SYSTEM</span>
          <NavItem id="benchmarks" icon={BarChart2} label="Benchmarks" />
          <NavItem id="model_status" icon={Cpu} label="Model status" />
        </div>

        <div style={{ marginTop: "auto", padding: "16px", borderTop: "1px solid #E8E8E4", margin: "0 -16px" }}>
          <div style={{ fontSize: "11px", color: "#6B6B6B", marginBottom: "8px" }}>
            {adminName} • {orgUnit}
          </div>
          <button className="hover:text-[#1A1A1A]" style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#6B6B6B", background: "none", border: "none", padding: 0, cursor: "pointer" }}>
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </div>

      <div className="max-[900px]:pt-16" style={{ flex: 1, overflowY: "auto" }}>
        {renderContent()}
      </div>

    </div>
  )
}
