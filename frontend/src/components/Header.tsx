import React from 'react';
import { Cpu } from 'lucide-react';

interface HeaderProps {
  backendUrl: string;
}

export const Header: React.FC<HeaderProps> = ({ backendUrl }) => {
  return (
    <header className="fade-in" style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '20px 24px',
      background: 'rgba(17, 19, 28, 0.4)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border-color)',
      borderRadius: '16px',
      marginTop: '20px'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          background: 'linear-gradient(135deg, var(--accent-indigo) 0%, var(--accent-purple) 100%)',
          padding: '8px',
          borderRadius: '10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 15px rgba(99, 102, 241, 0.3)'
        }}>
          <Cpu size={24} color="#fff" />
        </div>
        <div>
          <h1 style={{
            fontSize: '1.25rem',
            fontWeight: 700,
            letterSpacing: '-0.02em',
            margin: 0,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            AI <span className="gradient-text">Research Paper Assistant</span>
          </h1>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>
            Multi-agent research workflow powered by FastAPI & LangGraph
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid var(--border-color)',
          padding: '6px 12px',
          borderRadius: '8px',
          fontSize: '0.8rem'
        }}>
          <span style={{ color: 'var(--text-muted)' }}>API:</span>
          <code style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{backendUrl}</code>
        </div>
      </div>
    </header>
  );
};
