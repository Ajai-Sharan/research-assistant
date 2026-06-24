import React, { useState } from 'react';
import { Check, Edit3, Send, Link as LinkIcon, BookOpen, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { AgentGraph } from './AgentGraph';

interface PaperSummary {
  paper_id: string;
  title: string;
  url: string;
  core_claims: string[];
  methodology: string;
  limitations: string[];
  relevance: string;
}

interface StatusResponse {
  job_id: string;
  stage: string;
  awaiting_review: boolean;
  error: string | null;
  sub_queries: string[];
  downloaded_papers: any[];
  paper_summaries: PaperSummary[];
  draft_outline: string | null;
  final_draft: string | null;
}

interface ReviewScreenProps {
  status: StatusResponse;
  onSubmitFeedback: (decision: 'approve' | 'revise', feedback: string | null, editedOutline: string | null) => void;
  isLoading: boolean;
}

export const ReviewScreen: React.FC<ReviewScreenProps> = ({ status, onSubmitFeedback, isLoading }) => {
  const [editedOutline, setEditedOutline] = useState<string>(status.draft_outline || '');
  const [feedback, setFeedback] = useState<string>('');
  const [feedbackError, setFeedbackError] = useState<string>('');
  const [expandedPapers, setExpandedPapers] = useState<Record<string, boolean>>({});

  const togglePaper = (id: string) => {
    setExpandedPapers(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const handleApprove = () => {
    // If the user modified the outline, we'll send it back.
    // The Streamlit app does:
    // if edited.strip() and edited.strip() != outline_default.strip():
    //    api_feedback(job_id, decision="approve", feedback=None) // note: it uses the local edits
    // Wait, the API feedback endpoint takes FeedbackRequest which has decision: "approve" | "revise", and feedback.
    // Let's pass the edited outline or feedback correctly.
    // In FastAPI backend:
    // decision: Literal["approve", "revise"]
    // feedback: str | None = None
    // If decision == "approve", we simply resume the graph.
    // Note that we don't have a direct "update state outline" endpoint, but we can call feedback with approve.
    // Wait, let's call onSubmitFeedback('approve', null, editedOutline);
    onSubmitFeedback('approve', null, editedOutline);
  };

  const handleRevise = () => {
    if (!feedback.trim()) {
      setFeedbackError('Feedback is required to request a revision.');
      return;
    }
    setFeedbackError('');
    onSubmitFeedback('revise', feedback.trim(), editedOutline);
  };

  return (
    <div className="fade-in" style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '32px',
      margin: '40px auto',
      width: '100%',
      maxWidth: '1300px'
    }}>
      {/* Visual Agent Graph showing pipeline paused at Human Review */}
      <AgentGraph currentStage="awaiting_review" />

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.2fr 1fr',
        gap: '32px',
        width: '100%',
        alignItems: 'start'
      }}>
      {/* Left Column: Paper Summaries & References */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="glass-panel" style={{ padding: '32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <BookOpen size={22} style={{ color: 'var(--accent-cyan)' }} />
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
              References & Paper Summaries
            </h3>
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: '1.5' }}>
            These papers were retrieved from ArXiv and synthesized by the agents. Review their findings to help assess the outline.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxHeight: '700px', overflowY: 'auto', paddingRight: '8px' }}>
            {status.paper_summaries && status.paper_summaries.length > 0 ? (
              status.paper_summaries.map((s, idx) => {
                const id = s.paper_id || `paper-${idx}`;
                const isExpanded = !!expandedPapers[id];
                return (
                  <div key={id} className="glass-panel" style={{
                    background: isExpanded ? 'rgba(255, 255, 255, 0.01)' : 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '12px',
                    transition: 'all var(--transition-fast)'
                  }}>
                    {/* Header bar click to toggle */}
                    <div 
                      onClick={() => togglePaper(id)}
                      style={{
                        padding: '16px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        cursor: 'pointer',
                        gap: '12px'
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, margin: '0 0 6px 0', color: 'var(--text-primary)', lineHeight: '1.4' }}>
                          [P{idx + 1}] {s.title || '(untitled)'}
                        </h4>
                        {s.url && (
                          <a href={s.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} style={{
                            color: 'var(--text-link)',
                            fontSize: '0.8rem',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            textDecoration: 'none'
                          }}>
                            <span>View original paper</span>
                            <LinkIcon size={12} />
                          </a>
                        )}
                      </div>
                      <div style={{ color: 'var(--text-muted)', paddingTop: '2px' }}>
                        {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                      </div>
                    </div>

                    {isExpanded && (
                      <div style={{
                        padding: '0 16px 16px 16px',
                        borderTop: '1px solid var(--border-color)',
                        fontSize: '0.88rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '12px',
                        background: 'rgba(0, 0, 0, 0.05)'
                      }}>
                        {s.relevance && (
                          <div style={{ marginTop: '12px' }}>
                            <p style={{ fontWeight: 600, color: 'var(--accent-cyan)', fontSize: '0.8rem', textTransform: 'uppercase', marginBottom: '4px' }}>Relevance to Outline</p>
                            <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>"{s.relevance}"</p>
                          </div>
                        )}

                        {s.core_claims && s.core_claims.length > 0 && (
                          <div>
                            <p style={{ fontWeight: 600, color: 'var(--accent-purple)', fontSize: '0.8rem', textTransform: 'uppercase', marginBottom: '4px' }}>Core Claims & Key Insights</p>
                            <ul style={{ paddingLeft: '16px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              {s.core_claims.map((claim, cIdx) => <li key={cIdx}>{claim}</li>)}
                            </ul>
                          </div>
                        )}

                        {s.methodology && (
                          <div>
                            <p style={{ fontWeight: 600, color: 'var(--accent-indigo)', fontSize: '0.8rem', textTransform: 'uppercase', marginBottom: '4px' }}>Methodology</p>
                            <p style={{ color: 'var(--text-secondary)' }}>{s.methodology}</p>
                          </div>
                        )}

                        {s.limitations && s.limitations.length > 0 && (
                          <div>
                            <p style={{ fontWeight: 600, color: 'var(--accent-red)', fontSize: '0.8rem', textTransform: 'uppercase', marginBottom: '4px' }}>Limitations & Gaps</p>
                            <ul style={{ paddingLeft: '16px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              {s.limitations.map((limit, lIdx) => <li key={lIdx}>{limit}</li>)}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', textAlign: 'center', padding: '24px 0' }}>
                No paper summaries available.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right Column: Outline Editor & Action Panel */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div className="glass-panel" style={{ padding: '32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <Edit3 size={22} style={{ color: 'var(--accent-purple)' }} />
            <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
              Review & Refine Outline
            </h3>
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: '1.5' }}>
            Modify the outline draft directly below, or send feedback to re-run the planner and synthesizer.
          </p>

          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label className="label">Generated Literature Outline (Markdown)</label>
            <textarea
              className="textarea-custom"
              style={{
                fontFamily: 'var(--mono-font)',
                fontSize: '0.9rem',
                minHeight: '350px'
              }}
              value={editedOutline}
              onChange={(e) => setEditedOutline(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '24px' }}>
            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label className="label">Revision Feedback (Optional)</label>
              <textarea
                className="textarea-custom"
                placeholder="e.g. 'Add a section comparing closed- vs open-source RAG architectures, and detail embedding model selections.'"
                rows={3}
                value={feedback}
                onChange={(e) => {
                  setFeedback(e.target.value);
                  if (e.target.value.trim()) setFeedbackError('');
                }}
                disabled={isLoading}
              />
              {feedbackError && (
                <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertCircle size={14} />
                  <span>{feedbackError}</span>
                </p>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <button
                onClick={handleRevise}
                disabled={isLoading}
                className="btn btn-secondary"
                style={{ justifySelf: 'stretch' }}
              >
                <Send size={16} />
                <span>Request Revision</span>
              </button>

              <button
                onClick={handleApprove}
                disabled={isLoading}
                className="btn btn-primary"
                style={{ justifySelf: 'stretch' }}
              >
                <Check size={16} />
                <span>Approve & Draft</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  );
};
