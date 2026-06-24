import { useState } from 'react';
import { Play, Search, BookOpen, FileText, CheckCircle2, HelpCircle, FileCheck2, ChevronDown, ChevronUp, Link as LinkIcon, Users, CheckSquare } from 'lucide-react';
import { AgentGraph } from './AgentGraph';

interface PaperRecord {
  paper_id: string;
  title: string;
  authors: string[];
  abstract?: string;
  url: string;
  published?: string;
  source_query?: string;
}

interface StatusResponse {
  job_id: string;
  stage: string;
  awaiting_review: boolean;
  error: string | null;
  sub_queries: string[];
  downloaded_papers: PaperRecord[];
  paper_summaries: any[];
  draft_outline: string | null;
  final_draft: string | null;
}

interface RunningScreenProps {
  status: StatusResponse;
  onAbandon: () => void;
}

const STAGE_FLOW: [string, string, any][] = [
  ["planning", "Planning sub-queries", Play],
  ["searching", "Searching ArXiv & Semantic Scholar", Search],
  ["reading", "Reading & summarising papers", BookOpen],
  ["synthesizing", "Synthesising literature outline", FileText],
  ["awaiting_review", "Awaiting human review", HelpCircle],
  ["drafting", "Drafting final paper", FileCheck2],
  ["citation_check", "Citation Audit & Verification", CheckSquare],
  ["complete", "Complete", CheckCircle2],
];

const STAGE_ORDER = STAGE_FLOW.reduce((acc, [name], idx) => {
  acc[name] = idx;
  return acc;
}, {} as Record<string, number>);

export const RunningScreen: React.FC<RunningScreenProps> = ({ status, onAbandon }) => {
  const [subQueriesOpen, setSubQueriesOpen] = useState(true);
  const [papersOpen, setPapersOpen] = useState(true);

  const currentStage = status.stage || 'queued';
  const currentIdx = STAGE_ORDER[currentStage] ?? -1;

  // Let's compute progress percentage
  const totalStages = STAGE_FLOW.length;
  const pct = currentIdx === -1 ? 0 : Math.round((currentIdx / (totalStages - 1)) * 100);

  return (
    <div className="fade-in" style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '32px',
      margin: '40px auto',
      width: '100%',
      maxWidth: '1200px'
    }}>
      {/* Dynamic Agent Graph Visualization */}
      <AgentGraph currentStage={currentStage} />

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1.5fr',
        gap: '32px',
        width: '100%',
        alignItems: 'start'
      }}>
      {/* Left Column: Progress Stepper */}
      <div className="glass-panel" style={{ padding: '32px', position: 'sticky', top: '24px' }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Pipeline Progress</span>
          <span style={{ fontSize: '0.85rem', color: 'var(--accent-purple)', fontWeight: 600 }}>{pct}%</span>
        </h3>

        {/* Progress Bar Header */}
        <div style={{
          width: '100%',
          height: '6px',
          background: 'rgba(255, 255, 255, 0.05)',
          borderRadius: '999px',
          overflow: 'hidden',
          marginBottom: '32px'
        }}>
          <div style={{
            width: `${pct}%`,
            height: '100%',
            background: 'linear-gradient(90deg, var(--accent-indigo) 0%, var(--accent-purple) 100%)',
            borderRadius: '999px',
            transition: 'width var(--transition-slow)'
          }} />
        </div>

        {/* Vertical Stepper */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', position: 'relative' }}>
          {/* Timeline connecting line */}
          <div style={{
            position: 'absolute',
            left: '19px',
            top: '16px',
            bottom: '16px',
            width: '2px',
            background: 'rgba(255, 255, 255, 0.05)',
            zIndex: 0
          }} />

          {STAGE_FLOW.map(([name, label, Icon], idx) => {
            const isCompleted = idx < currentIdx;
            const isActive = idx === currentIdx;

            return (
              <div key={name} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                zIndex: 1
              }}>
                {/* Step Marker */}
                <div 
                  className={isActive ? "animate-pulse-radar" : ""}
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: isCompleted 
                      ? 'rgba(16, 185, 129, 0.1)' 
                      : isActive 
                      ? 'rgba(168, 85, 247, 0.15)' 
                      : 'rgba(255, 255, 255, 0.02)',
                    border: `2px solid ${
                      isCompleted 
                        ? 'var(--accent-green)' 
                        : isActive 
                        ? 'var(--accent-purple)' 
                        : 'rgba(255, 255, 255, 0.08)'
                    }`,
                    color: isCompleted 
                      ? 'var(--accent-green)' 
                      : isActive 
                      ? 'var(--accent-purple)' 
                      : 'var(--text-muted)',
                    transition: 'all var(--transition-normal)',
                    boxShadow: isActive ? '0 0 15px rgba(168, 85, 247, 0.2)' : 'none'
                  }}
                >
                  <Icon size={18} />
                </div>

                {/* Step Details */}
                <div style={{ flex: 1 }}>
                  <p style={{
                    fontSize: '0.95rem',
                    fontWeight: isActive || isCompleted ? 600 : 400,
                    color: isActive 
                      ? 'var(--text-primary)' 
                      : isCompleted 
                      ? 'var(--text-secondary)' 
                      : 'var(--text-muted)',
                    transition: 'color var(--transition-normal)'
                  }}>
                    {label}
                  </p>
                  {isActive && (
                    <span style={{
                      fontSize: '0.75rem',
                      color: 'var(--accent-cyan)',
                      fontWeight: 600,
                      display: 'inline-block',
                      marginTop: '2px'
                    }} className="animate-pulse-glow">
                      Agent active...
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Abandon Button */}
        <button
          onClick={onAbandon}
          className="btn btn-danger"
          style={{ width: '100%', marginTop: '36px' }}
        >
          Abandon Research Session
        </button>
      </div>

      {/* Right Column: Dynamic Feed logs (Sub-queries & Fetched papers) */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Sub-Queries */}
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <button 
            onClick={() => setSubQueriesOpen(!subQueriesOpen)}
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '24px',
              background: 'transparent',
              border: 'none',
              color: 'inherit',
              cursor: 'pointer',
              outline: 'none'
            }}
          >
            <h4 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="gradient-text">Planned Sub-queries</span>
              <span className="badge badge-info" style={{ textTransform: 'none' }}>
                {status.sub_queries ? status.sub_queries.length : 0}
              </span>
            </h4>
            {subQueriesOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </button>
          
          {subQueriesOpen && (
            <div style={{
              padding: '0 24px 24px 24px',
              borderTop: '1px solid var(--border-color)',
              background: 'rgba(0, 0, 0, 0.05)'
            }}>
              {status.sub_queries && status.sub_queries.length > 0 ? (
                <ul style={{ listStyleType: 'none', display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
                  {status.sub_queries.map((q, idx) => (
                    <li key={idx} style={{
                      padding: '12px 16px',
                      background: 'var(--bg-input)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      fontSize: '0.9rem',
                      lineHeight: '1.5',
                      color: 'var(--text-secondary)',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '12px'
                    }}>
                      <span style={{
                        background: 'rgba(99, 102, 241, 0.1)',
                        color: 'var(--accent-indigo)',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        width: '20px',
                        height: '20px',
                        borderRadius: '4px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        marginTop: '1px'
                      }}>{idx + 1}</span>
                      <span>{q}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  Waiting for planner node to generate sub-queries...
                </div>
              )}
            </div>
          )}
        </div>

        {/* Fetched Papers */}
        <div className="glass-panel" style={{ overflow: 'hidden' }}>
          <button 
            onClick={() => setPapersOpen(!papersOpen)}
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '24px',
              background: 'transparent',
              border: 'none',
              color: 'inherit',
              cursor: 'pointer',
              outline: 'none'
            }}
          >
            <h4 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="gradient-text">ArXiv Papers Fetched</span>
              <span className="badge badge-purple" style={{ textTransform: 'none' }}>
                {status.downloaded_papers ? status.downloaded_papers.length : 0}
              </span>
            </h4>
            {papersOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </button>

          {papersOpen && (
            <div style={{
              padding: '0 24px 24px 24px',
              borderTop: '1px solid var(--border-color)',
              background: 'rgba(0, 0, 0, 0.05)'
            }}>
              {status.downloaded_papers && status.downloaded_papers.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: '16px' }}>
                  {status.downloaded_papers.map((p, idx) => (
                    <div key={p.paper_id || idx} className="glass-panel" style={{
                      padding: '16px',
                      background: 'var(--bg-input)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '10px'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', marginBottom: '8px' }}>
                        <h5 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)', lineHeight: '1.4' }}>
                          {p.title || '(untitled)'}
                        </h5>
                        <a href={p.url} target="_blank" rel="noopener noreferrer" style={{
                          color: 'var(--text-link)',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          flexShrink: 0,
                          textDecoration: 'none'
                        }}>
                          <span>ArXiv</span>
                          <LinkIcon size={12} />
                        </a>
                      </div>
                      
                      {p.authors && p.authors.length > 0 && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                          <Users size={12} style={{ flexShrink: 0 }} />
                          <span style={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }} title={p.authors.join(', ')}>
                            {p.authors.join(', ')}
                          </span>
                        </div>
                      )}

                      {p.published && (
                        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          Published: <span style={{ color: 'var(--text-secondary)' }}>{p.published.substring(0, 10)}</span>
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                  Waiting for search node to fetch papers...
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  </div>
  );
};
