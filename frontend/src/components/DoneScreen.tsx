import React, { useEffect, useState } from 'react';
import { Download, Clipboard, Check, RefreshCw, FileText, ShieldAlert, Award } from 'lucide-react';
import confetti from 'canvas-confetti';
import { AgentGraph } from './AgentGraph';

interface StatusResponse {
  job_id: string;
  stage: string;
  awaiting_review: boolean;
  error: string | null;
  sub_queries: string[];
  downloaded_papers: any[];
  paper_summaries: any[];
  draft_outline: string | null;
  final_draft: string | null;
  citation_report: string | null;
}

interface DoneScreenProps {
  status: StatusResponse;
  onReset: () => void;
}

type TabType = 'draft' | 'citations' | 'outline';

export const DoneScreen: React.FC<DoneScreenProps> = ({ status, onReset }) => {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('draft');

  useEffect(() => {
    // Fire confetti on successful draft completion
    const duration = 2 * 1000;
    const end = Date.now() + duration;

    const frame = () => {
      confetti({
        particleCount: 4,
        angle: 60,
        spread: 55,
        origin: { x: 0 },
        colors: ['#6366f1', '#a855f7', '#06b6d4']
      });
      confetti({
        particleCount: 4,
        angle: 120,
        spread: 55,
        origin: { x: 1 },
        colors: ['#6366f1', '#a855f7', '#06b6d4']
      });

      if (Date.now() < end) {
        requestAnimationFrame(frame);
      }
    };
    
    frame();
  }, []);

  const handleCopy = () => {
    let contentToCopy = '';
    if (activeTab === 'draft') contentToCopy = status.final_draft || '';
    if (activeTab === 'citations') contentToCopy = status.citation_report || '';
    if (activeTab === 'outline') contentToCopy = status.draft_outline || '';

    if (contentToCopy) {
      navigator.clipboard.writeText(contentToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (!status.final_draft) return;
    const blob = new Blob([status.final_draft], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `research_draft_${status.job_id.substring(0, 6)}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="fade-in" style={{
      maxWidth: '1000px',
      margin: '40px auto',
      width: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: '24px'
    }}>
      {/* Workflow pipeline complete state */}
      <AgentGraph currentStage="complete" />

      {/* Top Banner */}
      <div className="glass-panel" style={{
        padding: '32px',
        textAlign: 'center',
        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%)',
        border: '1px solid rgba(168, 85, 247, 0.15)'
      }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: 'rgba(16, 185, 129, 0.1)',
          border: '2px solid var(--accent-green)',
          color: 'var(--accent-green)',
          marginBottom: '16px'
        }}>
          <Check size={28} />
        </div>
        <h2 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '8px' }}>
          Research Paper <span className="gradient-text">Draft Complete!</span>
        </h2>
        <p className="subtitle" style={{ fontSize: '1rem', maxWidth: '600px', margin: '0 auto' }}>
          The agents have completed research, synthesized outlines, drafted content, and verified academic citations.
        </p>

        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '16px',
          marginTop: '24px'
        }}>
          <button onClick={handleDownload} className="btn btn-primary">
            <Download size={18} />
            <span>Download Draft (MD)</span>
          </button>
          
          <button onClick={handleCopy} className="btn btn-secondary">
            {copied ? <Check size={18} style={{ color: 'var(--accent-green)' }} /> : <Clipboard size={18} />}
            <span>{copied ? 'Copied!' : 'Copy Section'}</span>
          </button>

          <button onClick={onReset} className="btn btn-secondary" style={{
            background: 'rgba(255, 255, 255, 0.02)',
            borderColor: 'var(--border-color)'
          }}>
            <RefreshCw size={16} />
            <span>New Research Session</span>
          </button>
        </div>
      </div>

      {/* Unified Tabbed Panel for Output Views */}
      <div className="glass-panel" style={{ padding: '32px' }}>
        <div className="tabs-header">
          <button 
            className={`tab-btn ${activeTab === 'draft' ? 'tab-btn-active' : ''}`}
            onClick={() => setActiveTab('draft')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={16} />
              <span>Final Manuscript</span>
            </div>
          </button>

          <button 
            className={`tab-btn ${activeTab === 'citations' ? 'tab-btn-active' : ''}`}
            onClick={() => setActiveTab('citations')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={16} />
              <span>Citation Audit Report</span>
            </div>
          </button>

          <button 
            className={`tab-btn ${activeTab === 'outline' ? 'tab-btn-active' : ''}`}
            onClick={() => setActiveTab('outline')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Award size={16} />
              <span>Approved Outline</span>
            </div>
          </button>
        </div>

        {/* Tab Body */}
        <div style={{
          minHeight: '400px',
          background: 'rgba(0, 0, 0, 0.15)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '24px',
          textAlign: 'left'
        }}>
          {activeTab === 'draft' && (
            <div style={{
              whiteSpace: 'pre-wrap',
              fontFamily: 'var(--sans-font)',
              fontSize: '1.05rem',
              lineHeight: '1.7',
              color: 'var(--text-primary)',
              overflowY: 'auto',
              maxHeight: '750px',
              paddingRight: '8px'
            }}>
              {status.final_draft || 'No manuscript generated.'}
            </div>
          )}

          {activeTab === 'citations' && (
            <div style={{
              whiteSpace: 'pre-wrap',
              fontFamily: 'var(--sans-font)',
              fontSize: '0.98rem',
              lineHeight: '1.6',
              color: 'var(--text-secondary)',
              overflowY: 'auto',
              maxHeight: '750px',
              paddingRight: '8px'
            }}>
              {status.citation_report || 'No citation verification report available.'}
            </div>
          )}

          {activeTab === 'outline' && (
            <div style={{
              whiteSpace: 'pre-wrap',
              fontFamily: 'var(--mono-font)',
              fontSize: '0.9rem',
              lineHeight: '1.6',
              color: 'var(--text-secondary)',
              overflowY: 'auto',
              maxHeight: '750px',
              paddingRight: '8px'
            }}>
              {status.draft_outline || 'No outline was used.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
