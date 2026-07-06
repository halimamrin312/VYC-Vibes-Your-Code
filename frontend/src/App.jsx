import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, Play, Settings, ShieldAlert, CheckCircle2, 
  AlertCircle, FileText, RefreshCw, TrendingUp, Download, Check
} from 'lucide-react';
import DocumentUploader from './components/DocumentUploader';
import OpsDashboard from './components/OpsDashboard';

function App() {
  const [sessionId, setSessionId] = useState('session-' + Math.floor(Math.random() * 9000 + 1000));
  const [targetCompany, setTargetCompany] = useState('Acme Danger Corp');
  const [industrySector, setIndustrySector] = useState('software');
  const [isRunning, setIsRunning] = useState(false);
  const [statusLogs, setStatusLogs] = useState([]);
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [agentReports, setAgentReports] = useState({});
  const [uploadedOpsLogName, setUploadedOpsLogName] = useState('');
  const [uploadedLegalFileName, setUploadedLegalFileName] = useState('');
  
  // Track agent states: 'idle', 'running', 'success', 'error'
  const [agentStatus, setAgentStatus] = useState({
    financial_auditor: 'idle',
    legal_compliance: 'idle',
    ops_evaluator: 'idle',
    brand_sentiment: 'idle'
  });

  const [hitlState, setHitlState] = useState(null);
  const [selectedHitlOption, setSelectedHitlOption] = useState('');
  const [hitlFeedback, setHitlFeedback] = useState('');
  const [finalMemo, setFinalMemo] = useState('');
  const [accumulatedFlags, setAccumulatedFlags] = useState([]);
  const [isHitlSubmitting, setIsHitlSubmitting] = useState(false);

  const logsEndRef = useRef(null);

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [statusLogs]);

  const generateSessionId = () => {
    setSessionId('session-' + Math.floor(Math.random() * 9000 + 1000));
  };

  const startAudit = async () => {
    if (!targetCompany.trim()) {
      alert("Please enter a target company name.");
      return;
    }
    
    setIsRunning(true);
    setFinalMemo('');
    setHitlState(null);
    setAccumulatedFlags([]);
    setAgentReports({});
    setUploadedOpsLogName('');
    setUploadedLegalFileName('');
    setStatusLogs([]);
    setAgentStatus({
      financial_auditor: 'idle',
      legal_compliance: 'idle',
      ops_evaluator: 'idle',
      brand_sentiment: 'idle'
    });

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          user_message: `Initiate M&A Due Diligence audit for ${targetCompany}`,
          target_company: targetCompany,
          industry_sector: industrySector
        })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Server error occurred");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.trim().startsWith("data: ")) {
            const jsonStr = line.replace("data: ", "").trim();
            if (!jsonStr) continue;
            
            try {
              const frame = JSON.parse(jsonStr);
              processStreamFrame(frame);
            } catch (e) {
              console.error("Failed to parse line:", line, e);
            }
          }
        }
      }
    } catch (error) {
      console.error("Stream failed:", error);
      setStatusLogs(prev => [...prev, `[ERROR] Connection failed: ${error.message}`]);
      setIsRunning(false);
    }
  };

  const processStreamFrame = (frame) => {
    const timestamp = new Date().toLocaleTimeString();

    if (frame.event === 'status') {
      setStatusLogs(prev => [...prev, `[${timestamp}] INFO: ${frame.message}`]);
    } 
    
    else if (frame.event === 'agent_status') {
      const { agent, status, message } = frame;
      setAgentStatus(prev => ({
        ...prev,
        [agent]: status
      }));
      setStatusLogs(prev => [...prev, `[${timestamp}] ${agent.replace('_', ' ').toUpperCase()}: ${message}`]);
    } 
    
    else if (frame.event === 'hitl_pause') {
      setHitlState(frame.payload);
      setIsRunning(false);
      setStatusLogs(prev => [...prev, `[${timestamp}] ⚠️ SWARM PAUSED: Human verification required.`]);
      // Mark current agent as running (waiting for HITL)
      // Since financial_auditor is first, let's mark it as running/warning
      setAgentStatus(prev => ({
        ...prev,
        financial_auditor: 'running'
      }));
    } 
    
    else if (frame.event === 'assistant_message') {
      setFinalMemo(frame.content);
      setStatusLogs(prev => [...prev, `[${timestamp}] SUCCESS: Memo synthesized successfully.`]);
    } 
    
    else if (frame.event === 'complete') {
      setIsRunning(false);
      // Fetch final memo details including flags
      fetchMemoDetails();
      setAgentStatus({
        financial_auditor: 'success',
        legal_compliance: 'success',
        ops_evaluator: 'success',
        brand_sentiment: 'success'
      });
    } 
    
    else if (frame.event === 'error') {
      setStatusLogs(prev => [...prev, `[${timestamp}] FATAL: ${frame.message}`]);
      setIsRunning(false);
    }
  };

  const fetchMemoDetails = async () => {
    try {
      const res = await fetch(`/api/memo/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setAccumulatedFlags(data.accumulated_red_flags || []);
        setAgentReports(data.agent_reports || {});
      }
    } catch (e) {
      console.error("Failed to fetch memo details:", e);
    }
  };

  const submitHitlResponse = async () => {
    if (!selectedHitlOption) {
      alert("Please select a strategic option to resume.");
      return;
    }

    setIsHitlSubmitting(true);
    try {
      const response = await fetch('/api/hitl/respond', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          selected_option: selectedHitlOption,
          custom_feedback: hitlFeedback
        })
      });

      if (!response.ok) {
        throw new Error("Failed to register decision");
      }

      setStatusLogs(prev => [
        ...prev, 
        `[${new Date().toLocaleTimeString()}] HITL DECISION: Selected Option ${selectedHitlOption}. Resuming swarm...`
      ]);

      // Reset HITL Modal State
      setHitlState(null);
      setSelectedHitlOption('');
      setHitlFeedback('');

      // Update status indicators to show resumed audit
      setAgentStatus(prev => ({
        ...prev,
        financial_auditor: 'success'
      }));

      // Resume execution loop by sending the user message again
      setIsRunning(true);
      
      const streamResponse = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          user_message: "Decision submitted. Resume audit.",
          target_company: targetCompany,
          industry_sector: industrySector
        })
      });

      const reader = streamResponse.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.trim().startsWith("data: ")) {
            const jsonStr = line.replace("data: ", "").trim();
            if (!jsonStr) continue;
            try {
              const frame = JSON.parse(jsonStr);
              processStreamFrame(frame);
            } catch (e) {
              console.error("Failed to parse resumed frame:", e);
            }
          }
        }
      }
    } catch (e) {
      console.error(e);
      alert("Error resuming swarm: " + e.message);
    } finally {
      setIsHitlSubmitting(false);
    }
  };

  const downloadMemo = () => {
    const element = document.createElement("a");
    const file = new Blob([finalMemo], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = `${targetCompany.replace(/\s+/g, '_')}_Investment_Memo.md`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="app-container">
      {/* Header Bar */}
      <header className="glass" style={{ margin: '20px', padding: '16px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', background: 'linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Activity size={22} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em', background: 'linear-gradient(to right, #fff, #94a3b8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              M&A Due Diligence Swarm
            </h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Lead Orchestrator Core Control Panel</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--accent-success)', display: 'inline-block' }}></span>
            <span style={{ color: 'var(--text-secondary)' }}>Gateway Connected</span>
          </div>
        </div>
      </header>

      {/* Grid Layout */}
      <div className="dashboard-grid">
        {/* Left Sidebar: Controls */}
        <aside className="glass" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
            <Settings size={18} color="var(--accent-primary)" />
            <h2 style={{ fontSize: '1rem', fontWeight: 600 }}>Audit Configuration</h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Target Company Name</label>
            <input 
              type="text" 
              value={targetCompany}
              onChange={(e) => setTargetCompany(e.target.value)}
              disabled={isRunning || hitlState}
              placeholder="e.g. Acme Corp"
            />
            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Tip: Include "danger" or "risk" to test HITL flow.</p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Industry Sector</label>
            <select
              value={industrySector}
              onChange={(e) => setIndustrySector(e.target.value)}
              disabled={isRunning || hitlState}
            >
              <option value="software">Software & Tech</option>
              <option value="manufacturing">Manufacturing</option>
              <option value="retail">Retail & Logistics</option>
              <option value="pharma">Pharmaceutical</option>
              <option value="generic">Generic/Other</option>
            </select>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Session ID</label>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input 
                type="text" 
                value={sessionId}
                onChange={(e) => setSessionId(e.target.value)}
                disabled={isRunning || hitlState}
                style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}
              />
              <button 
                onClick={generateSessionId}
                disabled={isRunning || hitlState}
                className="btn-secondary" 
                style={{ padding: '10px' }}
                title="Regenerate Session ID"
              >
                <RefreshCw size={14} />
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500, marginBottom: '4px' }}>Financial Data Room (Priority Ingestion)</label>
            <DocumentUploader 
              sessionId={sessionId} 
              onUploadSuccess={(name) => {
                setUploadedFileName(name);
                setStatusLogs(prev => [...prev, `[INFO] Ingested and verified financial document: ${name}`]);
              }} 
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500, marginBottom: '4px' }}>Operations Data Room (CSV Reviews)</label>
            <OpsDashboard 
              industry={industrySector}
              sessionId={sessionId}
              agentReport={{ status: 'idle' }}
              isSwarmRunning={isRunning}
              onUploadSuccess={(name) => {
                setUploadedOpsLogName(name);
                setStatusLogs(prev => [...prev, `[INFO] Ingested and verified operations log: ${name}`]);
              }}
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500, marginBottom: '4px' }}>Legal Agreements Data Room (PDF/DOCX)</label>
            <DocumentUploader 
              sessionId={sessionId}
              uploadType="legal"
              accept=".pdf,.docx"
              label="Drag & Drop PDF/DOCX Contracts"
              subLabel="or click to browse local files"
              endpoint="/api/ingest/legal"
              showSessionId={false}
              onUploadSuccess={(name) => {
                setUploadedLegalFileName(name);
                setStatusLogs(prev => [...prev, `[INFO] Ingested and indexed legal agreement: ${name}`]);
              }} 
            />
          </div>

          <button 
            onClick={startAudit}
            disabled={isRunning || hitlState}
            className="btn-primary" 
            style={{ width: '100%', justifyContent: 'center', marginTop: '10px' }}
          >
            {isRunning ? (
              <>
                <RefreshCw size={16} className="glow-active" style={{ animationDuration: '1s' }} /> Running Swarm...
              </>
            ) : (
              <>
                <Play size={16} fill="currentColor" /> Dispatch Swarm
              </>
            )}
          </button>
        </aside>

        {/* Right Main Area */}
        <main style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Swarm Agents Dashboard Status */}
          <section className="glass" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px', marginBottom: '20px' }}>
              <TrendingUp size={18} color="var(--accent-secondary)" />
              <h2 style={{ fontSize: '1rem', fontWeight: 600 }}>Active Agent Swarm Status</h2>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              {Object.entries(agentStatus).map(([agentKey, status], index) => {
                const name = agentKey.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
                let cardClass = "glass";
                let icon = <RefreshCw size={16} style={{ color: 'var(--text-muted)' }} />;
                let statusLabel = "Idle";
                let statusColor = 'var(--text-muted)';
                let glowClass = "";

                if (status === 'running') {
                  statusLabel = "Auditing...";
                  statusColor = 'var(--accent-warning)';
                  icon = <RefreshCw size={16} className="spin" style={{ color: 'var(--accent-warning)', animation: 'spin 1.5s linear infinite' }} />;
                  glowClass = "glow-active-cyan";
                } else if (status === 'success') {
                  statusLabel = "Completed";
                  statusColor = 'var(--accent-success)';
                  icon = <CheckCircle2 size={16} style={{ color: 'var(--accent-success)' }} />;
                } else if (status === 'error') {
                  statusLabel = "Error/Interrupted";
                  statusColor = 'var(--accent-danger)';
                  icon = <AlertCircle size={16} style={{ color: 'var(--accent-danger)' }} />;
                }

                return (
                  <div 
                    key={agentKey} 
                    className={`glass animate-fade-in-up stagger-${index + 1} ${glowClass}`} 
                    style={{ 
                      padding: '16px', 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '12px',
                      borderLeft: `3px solid ${statusColor}`,
                      transition: 'all 0.3s ease'
                    }}
                  >
                    <div>{icon}</div>
                    <div>
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 600 }}>{name}</h4>
                      <p style={{ fontSize: '0.75rem', color: statusColor, fontWeight: 500 }}>{statusLabel}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Logs Window */}
          <section className="glass" style={{ padding: '24px', flex: 1, display: 'flex', flexDirection: 'column', gap: '12px', minHeight: '240px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
              <Activity size={18} color="var(--accent-primary)" />
              <h2 style={{ fontSize: '1rem', fontWeight: 600 }}>Live Swarm Trajectory Logs</h2>
            </div>
            
            <div style={{ 
              background: 'rgba(15, 23, 42, 0.7)', 
              borderRadius: '8px', 
              padding: '16px', 
              fontFamily: 'var(--font-mono)', 
              fontSize: '0.85rem', 
              flex: 1, 
              overflowY: 'auto',
              maxHeight: '300px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px'
            }}>
              {statusLogs.length === 0 ? (
                <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '20px' }}>
                  Awaiting Swarm Dispatch...
                </div>
              ) : (
                statusLogs.map((log, index) => {
                  let color = 'var(--text-secondary)';
                  if (log.includes('[ERROR]') || log.includes('FATAL:')) color = 'var(--accent-danger)';
                  if (log.includes('SUCCESS:')) color = 'var(--accent-success)';
                  if (log.includes('⚠️ SWARM PAUSED:')) color = 'var(--accent-warning)';
                  return (
                    <div key={index} className="log-item-fade" style={{ color, wordBreak: 'break-all' }}>{log}</div>
                  );
                })
              )}
              <div ref={logsEndRef} />
            </div>
          </section>

          {/* HITL Pause Drawer */}
          {hitlState && (
            <section className="glass glow-active-amber animate-hitl-box" style={{ padding: '24px', backgroundColor: 'rgba(26, 36, 68, 0.95)', border: '1px solid var(--accent-warning)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--accent-warning)', borderBottom: '1px solid rgba(245, 158, 11, 0.2)', paddingBottom: '12px', marginBottom: '16px' }}>
                <ShieldAlert size={24} />
                <div>
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Human-in-the-Loop Strategic Checkpoint</h3>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Swarm is paused waiting for your investment direction.</p>
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '8px', fontWeight: 600 }}>Triggering Event:</h4>
                <p style={{ background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', borderLeft: '3px solid var(--accent-warning)', fontSize: '0.9rem', fontFamily: 'var(--font-mono)' }}>
                  {hitlState.question}
                </p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '16px' }}>
                <h4 style={{ fontSize: '0.9rem', color: 'var(--text-primary)', fontWeight: 600 }}>Select Strategic Directive:</h4>
                {hitlState.options.map((opt) => (
                  <label 
                    key={opt.key}
                    className="glass"
                    style={{ 
                      padding: '12px 16px', 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '12px', 
                      cursor: 'pointer',
                      border: selectedHitlOption === opt.key ? '1px solid var(--accent-primary)' : '1px solid var(--border-color)',
                      backgroundColor: selectedHitlOption === opt.key ? 'rgba(99,102,241,0.1)' : 'transparent',
                      borderRadius: '8px',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    <input 
                      type="radio" 
                      name="hitlOption" 
                      value={opt.key} 
                      checked={selectedHitlOption === opt.key}
                      onChange={(e) => setSelectedHitlOption(e.target.value)}
                      style={{ cursor: 'pointer' }}
                    />
                    <div style={{ fontSize: '0.9rem' }}>
                      <strong style={{ color: 'var(--text-primary)' }}>Option {opt.key}:</strong> {opt.text}
                    </div>
                  </label>
                ))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '20px' }}>
                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Optional strategic notes / feedback:</label>
                <textarea 
                  value={hitlFeedback}
                  onChange={(e) => setHitlFeedback(e.target.value)}
                  placeholder="e.g. Please proceed with valuation model changes."
                  rows={2}
                  style={{ width: '100%', resize: 'none' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
                <button 
                  onClick={submitHitlResponse} 
                  disabled={isHitlSubmitting}
                  className="btn-primary"
                  style={{ background: 'linear-gradient(135deg, var(--accent-warning) 0%, #d97706 100%)', boxShadow: '0 4px 14px rgba(245, 158, 11, 0.3)' }}
                >
                  {isHitlSubmitting ? <RefreshCw size={16} className="spin" /> : <Check size={16} />}
                  Resume Swarm Audit
                </button>
              </div>
            </section>
          )}

          {/* Operations Agent Dashboard */}
          {agentStatus.ops_evaluator !== 'idle' && (
            <section className="glass animate-fade-in-up" style={{ padding: '24px' }}>
              <OpsDashboard 
                industry={industrySector}
                sessionId={sessionId}
                agentReport={
                  agentStatus.ops_evaluator === 'success' 
                    ? agentReports.ops_evaluator 
                    : { status: agentStatus.ops_evaluator }
                }
                isSwarmRunning={isRunning}
              />
            </section>
          )}

          {/* Compiled Memo Viewer */}
          {finalMemo && (
            <section className="glass animate-fade-in-up" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <FileText size={18} color="var(--accent-success)" />
                  <h2 style={{ fontSize: '1rem', fontWeight: 600 }}>Synthesized Investment Memo</h2>
                </div>
                <button onClick={downloadMemo} className="btn-primary" style={{ padding: '8px 16px', fontSize: '0.85rem', background: 'linear-gradient(135deg, var(--accent-success) 0%, #059669 100%)', boxShadow: '0 4px 14px rgba(16, 185, 129, 0.3)' }}>
                  <Download size={14} /> Export Memo
                </button>
              </div>

              {/* Accumulated Red Flags / Valuation Adjustments */}
              {accumulatedFlags.length > 0 && (
                <div className="glass" style={{ padding: '16px', borderLeft: '3px solid var(--accent-danger)', backgroundColor: 'rgba(239, 68, 68, 0.05)', marginBottom: '10px' }}>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-danger)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                    <ShieldAlert size={14} /> Swarm Financial & Risk Adjustments:
                  </h4>
                  <ul style={{ paddingLeft: '16px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    {accumulatedFlags.map((flag, i) => (
                      <li key={i} style={{ marginBottom: '4px' }}>
                        <strong>{flag.action}:</strong> {flag.description} (Adjustment: -${flag.amount.toLocaleString()})
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Memo Content Render */}
              <div 
                className="markdown-body" 
                style={{ 
                  background: 'rgba(15, 23, 42, 0.4)', 
                  borderRadius: '8px', 
                  padding: '24px', 
                  maxHeight: '400px', 
                  overflowY: 'auto',
                  border: '1px solid var(--border-color)'
                }}
              >
                {finalMemo.split('\n').map((line, index) => {
                  if (line.startsWith('# ')) {
                    return <h1 key={index} style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', fontSize: '1.5rem', fontWeight: 700, margin: '20px 0 10px' }}>{line.slice(2)}</h1>;
                  }
                  if (line.startsWith('## ')) {
                    return <h2 key={index} style={{ fontSize: '1.25rem', fontWeight: 600, margin: '20px 0 10px' }}>{line.slice(3)}</h2>;
                  }
                  if (line.startsWith('### ')) {
                    return <h3 key={index} style={{ fontSize: '1.1rem', fontWeight: 600, margin: '15px 0 10px' }}>{line.slice(4)}</h3>;
                  }
                  if (line.startsWith('- ')) {
                    return <li key={index} style={{ marginLeft: '20px', color: 'var(--text-secondary)', marginBottom: '6px' }}>{line.slice(2)}</li>;
                  }
                  if (line.trim() === '') {
                    return <div key={index} style={{ height: '10px' }}></div>;
                  }
                  return <p key={index} style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '12px' }}>{line}</p>;
                })}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
