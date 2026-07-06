import React, { useState } from 'react';
import { Upload, FileText, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react';
import { apiFetch } from '../services/api';

function DocumentUploader({ 
  sessionId, 
  onUploadSuccess, 
  uploadType = 'financial',
  accept = '.csv',
  label = 'Drag & Drop CSV Financials',
  subLabel = 'or click to browse local files',
  endpoint = '/api/ingest/financial',
  showSessionId = true
}) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // 'idle' | 'uploading' | 'success' | 'error'
  const [message, setMessage] = useState('');
  const [dragActive, setDragActive] = useState(false);

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
      const hasAllowedExtension = accept.split(',').some(ext => droppedFile.name.toLowerCase().endsWith(ext.trim().toLowerCase()));
      if (hasAllowedExtension) {
        handleFileSelect(droppedFile);
      } else {
        setStatus('error');
        setMessage(`Only ${accept} file formats are supported.`);
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
    setStatus('idle');
    setMessage(`Selected: ${selectedFile.name} (${(selectedFile.size / 1024).toFixed(1)} KB)`);
  };

  const uploadFile = async () => {
    if (!file) return;

    setStatus('uploading');
    setMessage(uploadType === 'legal' ? 'Uploading and indexing legal agreement...' : 'Uploading and performing structural checks...');

    const formData = new FormData();
    formData.append('file', file);
    if (showSessionId) {
      formData.append('session_id', sessionId);
    }

    try {
      const response = await apiFetch(endpoint, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed');
      }

      setStatus('success');
      if (uploadType === 'legal') {
        setMessage(`Successfully ingested and indexed: ${file.name}`);
      } else {
        setMessage(`Successfully validated! Loaded ${data.record_count} financial periods.`);
      }
      if (onUploadSuccess) {
        onUploadSuccess(file.name);
      }
    } catch (error) {
      console.error('Upload error:', error);
      setStatus('error');
      setMessage(error.message || 'File validation failed.');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div 
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        style={{
          border: dragActive ? '2px dashed var(--accent-primary)' : '2px dashed var(--border-color)',
          borderRadius: '8px',
          padding: '20px',
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
          id={`file-upload-${uploadType}`} 
          accept={accept} 
          onChange={handleChange}
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
        
        {file ? (
          <FileText size={32} color="var(--accent-primary)" />
        ) : (
          <Upload size={32} color="var(--text-muted)" />
        )}
        
        <p style={{ fontSize: '0.85rem', fontWeight: 600 }}>
          {file ? 'File Selected' : label}
        </p>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {file ? 'Click upload button below to ingest' : subLabel}
        </p>
      </div>

      {message && (
        <div 
          className="glass animate-fade-in" 
          style={{ 
            padding: '12px', 
            borderRadius: '6px', 
            fontSize: '0.8rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '8px',
            borderLeft: `3px solid ${
              status === 'success' ? 'var(--accent-success)' :
              status === 'error' ? 'var(--accent-danger)' :
              status === 'uploading' ? 'var(--accent-primary)' :
              'var(--border-color)'
            }`
          }}
        >
          {status === 'success' && <CheckCircle2 size={16} color="var(--accent-success)" style={{ marginTop: '2px', flexShrink: 0 }} />}
          {status === 'error' && <AlertTriangle size={16} color="var(--accent-danger)" style={{ marginTop: '2px', flexShrink: 0 }} />}
          {status === 'uploading' && <Loader2 size={16} className="spin" color="var(--accent-primary)" style={{ marginTop: '2px', flexShrink: 0 }} />}
          <div style={{ wordBreak: 'break-word', color: 'var(--text-secondary)' }}>{message}</div>
        </div>
      )}

      {file && status !== 'success' && (
        <button 
          onClick={uploadFile}
          disabled={status === 'uploading'}
          className="btn-primary"
          style={{ 
            width: '100%', 
            justifyContent: 'center', 
            padding: '10px',
            background: 'linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%)'
          }}
        >
          {status === 'uploading' ? (
            <>
              <Loader2 size={14} className="spin" /> Uploading...
            </>
          ) : (
            'Validate & Ingest File'
          )}
        </button>
      )}
    </div>
  );
}

export default DocumentUploader;
