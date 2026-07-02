import React, { useState } from 'react';
import { 
  Upload, Cpu, Users, MessageSquare, AlertTriangle, 
  CheckCircle2, ShieldAlert, Loader2, FileText, RefreshCw, Star, HeartHandshake 
} from 'lucide-react';

function OpsDashboard({ industry, sessionId, agentReport, isSwarmRunning, onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('idle'); // 'idle' | 'uploading' | 'success' | 'error'
  const [uploadMessage, setUploadMessage] = useState('');
  const [dragActive, setDragActive] = useState(false);

  // Parse findings if available
  const findings = agentReport?.findings || {};
  const status = agentReport?.status || 'idle';
  const metrics = findings.metrics || {};
  const flags = findings.flags || [];

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.csv') || droppedFile.name.endsWith('.CSV')) {
        handleFileSelect(droppedFile);
      } else {
        setUploadStatus('error');
        setUploadMessage('Only CSV file formats are supported.');
      }
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleFileSelect = (selectedFile) => {
    setFile(selectedFile);
    setUploadStatus('idle');
    setUploadMessage(`Selected: ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB)`);
  };

  const uploadFile = async () => {
    if (!file) return;

    setUploadStatus('uploading');
    setUploadMessage('Uploading and validating operations reviews CSV schema...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    formData.append('industry', industry);

    try {
      const response = await fetch('/api/ingest/logs', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed');
      }

      setUploadStatus('success');
      setUploadMessage(`Successfully validated! Ingested ${data.record_count} customer and employee reviews.`);
      if (onUploadSuccess) {
        onUploadSuccess(file.name);
      }
    } catch (error) {
      console.error('Log upload error:', error);
      setUploadStatus('error');
      setUploadMessage(error.message || 'File schema validation failed.');
    }
  };

  // Helper: Get Index Color
  const getIndexColor = (val) => {
    if (val >= 0.75) return 'var(--accent-success)';
    if (val >= 0.50) return 'var(--accent-warning)';
    return 'var(--accent-danger)';
  };

  return (
    <div className="ops-dashboard-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* 1. Header Area */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(6, 182, 212, 0.1)', border: '1px solid rgba(6, 182, 212, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Users size={18} color="var(--accent-secondary)" />
          </div>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Operations Diligence Panel</h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Audit Focus: <strong style={{ color: 'var(--accent-secondary)' }}>Customer & Organizational Sentiment</strong></p>
          </div>
        </div>

        {status === 'success' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '4px 10px', borderRadius: '20px', background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', color: 'var(--accent-success)' }}>
            <CheckCircle2 size={12} />
            <span>Audit Completed</span>
          </div>
        )}
      </div>

      {/* 2. Ingestion Section (Only when not succeeded yet) */}
      {status !== 'success' && (
        <div className="glass" style={{ padding: '20px', border: '1px dashed var(--border-color)' }}>
          <h4 style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileText size={16} color="var(--accent-primary)" />
            Customer & Employee Reviews Data Room
          </h4>
          
          <div 
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            style={{
              border: dragActive ? '2px dashed var(--accent-primary)' : '2px dashed var(--border-color)',
              borderRadius: '8px',
              padding: '24px 20px',
              textAlign: 'center',
              backgroundColor: dragActive ? 'rgba(99, 102, 241, 0.05)' : 'rgba(15, 23, 42, 0.3)',
              cursor: 'pointer',
              position: 'relative',
              transition: 'all 0.2s ease',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            <input 
              type="file" 
              accept=".csv" 
              onChange={handleChange}
              disabled={isSwarmRunning || uploadStatus === 'uploading'}
              style={{
                position: 'absolute',
                width: '100%',
                height: '100%',
                top: 0,
                left: 0,
                opacity: 0,
                cursor: 'pointer'
              }}
            />
            
            <Upload size={28} color="var(--text-muted)" />
            <p style={{ fontSize: '0.85rem', fontWeight: 600 }}>Drag & Drop Customer/Employee Reviews CSV</p>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Required columns: ReviewText, Rating, Category</p>
          </div>

          {uploadMessage && (
            <div style={{ 
              marginTop: '12px', 
              padding: '10px 12px', 
              borderRadius: '6px', 
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              backgroundColor: 'rgba(0,0,0,0.1)',
              borderLeft: `3px solid ${
                uploadStatus === 'success' ? 'var(--accent-success)' :
                uploadStatus === 'error' ? 'var(--accent-danger)' :
                'var(--accent-primary)'
              }`
            }}>
              {uploadStatus === 'success' && <CheckCircle2 size={14} color="var(--accent-success)" style={{ flexShrink: 0, marginTop: '2px' }} />}
              {uploadStatus === 'error' && <AlertTriangle size={14} color="var(--accent-danger)" style={{ flexShrink: 0, marginTop: '2px' }} />}
              {uploadStatus === 'uploading' && <Loader2 size={14} className="spin" color="var(--accent-primary)" style={{ flexShrink: 0, marginTop: '2px' }} />}
              <span style={{ color: 'var(--text-secondary)', wordBreak: 'break-all' }}>{uploadMessage}</span>
            </div>
          )}

          {file && uploadStatus !== 'success' && (
            <button 
              onClick={uploadFile}
              disabled={uploadStatus === 'uploading' || isSwarmRunning}
              className="btn-primary"
              style={{ width: '100%', justifyContent: 'center', marginTop: '12px', padding: '10px' }}
            >
              {uploadStatus === 'uploading' ? 'Ingesting Reviews...' : 'Ingest Reviews File'}
            </button>
          )}
        </div>
      )}

      {/* 3. Results dashboard: Render when status is success */}
      {status === 'success' && (
        <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
            
            {/* Customer Support Index (CSI) Card */}
            <div className="glass" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '150px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>CUSTOMER SUPPORT INDEX (CSI)</span>
                <HeartHandshake size={16} color="var(--accent-secondary)" />
              </div>
              <div>
                <div style={{ fontSize: '2.25rem', fontWeight: 700, color: getIndexColor(metrics.csi) }}>
                  {metrics.csi !== undefined ? `${roundValue(metrics.csi * 100, 1)}%` : '0%'}
                </div>
                <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', marginTop: '8px', overflow: 'hidden' }}>
                  <div style={{ 
                    width: `${(metrics.csi || 0) * 100}%`, 
                    height: '100%', 
                    background: getIndexColor(metrics.csi),
                    borderRadius: '3px'
                  }} />
                </div>
              </div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>CSI target threshold: &gt; 50%</span>
            </div>

            {/* Employee Sentiment Index (ESI) Card */}
            <div className="glass" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '150px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>EMPLOYEE SENTIMENT (ESI)</span>
                <Star size={16} color="var(--accent-primary)" />
              </div>
              <div>
                <div style={{ fontSize: '2.25rem', fontWeight: 700, color: getIndexColor(metrics.esi) }}>
                  {metrics.esi !== undefined ? `${roundValue(metrics.esi * 100, 1)}%` : '0%'}
                </div>
                <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', marginTop: '8px', overflow: 'hidden' }}>
                  <div style={{ 
                    width: `${(metrics.esi || 0) * 100}%`, 
                    height: '100%', 
                    background: getIndexColor(metrics.esi),
                    borderRadius: '3px'
                  }} />
                </div>
              </div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>ESI target threshold: &gt; 50%</span>
            </div>

            {/* Operational Risks Summary */}
            <div className="glass" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px', justifyContent: 'center' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>DISPUTES & TURNOVER CHECKS</span>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Fulfillment Delays Flagged:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: metrics.delivery_issues > 0 ? 'var(--accent-warning)' : 'var(--accent-success)' }}>
                  {metrics.delivery_issues || 0}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Turnover Risks Flagged:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: metrics.turnover_issues > 0 ? 'var(--accent-warning)' : 'var(--accent-success)' }}>
                  {metrics.turnover_issues || 0}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Total Reviews Analyzed:</span>
                <strong style={{ fontFamily: 'var(--font-mono)' }}>{metrics.total_reviews || 0}</strong>
              </div>
            </div>

          </div>

          {/* 4. Flags Breakdown */}
          {flags.length > 0 && (
            <div className="glass" style={{ padding: '16px', borderLeft: '3px solid var(--accent-danger)', backgroundColor: 'rgba(239, 68, 68, 0.03)' }}>
              <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-danger)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <ShieldAlert size={14} /> Operational Risk Alerts Flagged:
              </h4>
              <ul style={{ paddingLeft: '16px', fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {flags.map((flag, idx) => (
                  <li key={idx}>
                    <strong>{flag.metric || 'Alert'}:</strong> {flag.description} <span style={{ color: 'var(--accent-danger)', fontSize: '0.7rem', fontWeight: 600, border: '1px solid var(--accent-danger)', borderRadius: '3px', padding: '1px 4px', marginLeft: '6px' }}>{flag.severity}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

        </div>
      )}

      {/* 4. Swarm Running State */}
      {status === 'running' && (
        <div className="glass" style={{ padding: '30px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <RefreshCw size={24} className="spin" color="var(--accent-secondary)" style={{ animationDuration: '1.5s' }} />
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Swarm is actively auditing customer and employee sentiment...</p>
        </div>
      )}

      {/* 5. Awaiting Swarm (Idle state, no success or running) */}
      {status === 'idle' && file && (
        <div style={{ padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.04)', background: 'rgba(255,255,255,0.01)', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem', fontStyle: 'italic' }}>
          Awaiting Swarm Dispatch to analyze review metrics.
        </div>
      )}

    </div>
  );
}

// Inline value rounding helper
function roundValue(value, decimals) {
  if (typeof value !== 'number') return value;
  return Number(Math.round(value + 'e' + decimals) + 'e-' + decimals);
}

export default OpsDashboard;
