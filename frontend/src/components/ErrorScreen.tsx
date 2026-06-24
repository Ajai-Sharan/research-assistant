import React from 'react';
import { AlertOctagon, RefreshCw } from 'lucide-react';

interface ErrorScreenProps {
  error: string;
  onReset: () => void;
}

export const ErrorScreen: React.FC<ErrorScreenProps> = ({ error, onReset }) => {
  return (
    <div className="fade-in" style={{
      maxWidth: '600px',
      margin: '80px auto',
      width: '100%'
    }}>
      <div className="glass-panel" style={{
        padding: '40px',
        textAlign: 'center',
        border: '1px solid rgba(239, 68, 68, 0.2)',
        background: 'rgba(239, 68, 68, 0.02)'
      }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: 'rgba(239, 68, 68, 0.1)',
          border: '2px solid var(--accent-red)',
          color: 'var(--accent-red)',
          marginBottom: '20px'
        }}>
          <AlertOctagon size={28} />
        </div>

        <h3 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '12px' }}>
          Research Pipeline Failed
        </h3>
        
        <p style={{
          fontSize: '0.95rem',
          color: 'var(--text-secondary)',
          lineHeight: '1.6',
          marginBottom: '24px',
          background: 'rgba(0, 0, 0, 0.2)',
          border: '1px solid var(--border-color)',
          padding: '16px',
          borderRadius: '10px',
          textAlign: 'left',
          fontFamily: 'var(--mono-font)',
          wordBreak: 'break-word'
        }}>
          {error || 'An unexpected pipeline node error occurred.'}
        </p>

        <button onClick={onReset} className="btn btn-primary" style={{
          background: 'linear-gradient(135deg, #ef4444 0%, #f43f5e 100%)',
          boxShadow: '0 4px 15px rgba(239, 68, 68, 0.3)'
        }}>
          <RefreshCw size={16} />
          <span>Reset and Try Again</span>
        </button>
      </div>
    </div>
  );
};
