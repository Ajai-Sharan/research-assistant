import React, { useState } from 'react';
import { Sparkles, ArrowRight } from 'lucide-react';

interface InputScreenProps {
  onSubmit: (topic: string) => void;
  isLoading: boolean;
}

const SAMPLE_TOPICS = [
  "Survey of retrieval-augmented generation for scientific literature review, covering architectures, evaluation benchmarks, and known failure modes.",
  "Analysis of multi-agent collaboration frameworks (e.g. LangGraph vs AutoGen) in enterprise reasoning systems, covering routing and persistence.",
  "A detailed survey of transformer model optimization techniques including quantization, pruning, and speculative decoding.",
];

export const InputScreen: React.FC<InputScreenProps> = ({ onSubmit, isLoading }) => {
  const [topic, setTopic] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (topic.trim().length < 4) {
      setError('Please enter a more substantive topic (minimum 4 characters).');
      return;
    }
    setError('');
    onSubmit(topic.trim());
  };

  return (
    <div className="fade-in" style={{
      maxWidth: '800px',
      margin: '60px auto',
      width: '100%'
    }}>
      <div className="glass-panel" style={{
        padding: '40px',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
        border: '1px solid rgba(255, 255, 255, 0.05)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '10px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(168, 85, 247, 0.08)',
            border: '1px solid rgba(168, 85, 247, 0.2)',
            padding: '6px 14px',
            borderRadius: '999px',
            fontSize: '0.85rem',
            color: 'var(--accent-purple)',
            marginBottom: '16px'
          }}>
            <Sparkles size={14} />
            <span>AI Research Assistant</span>
          </div>
          <h2 style={{ fontSize: '2.2rem', fontWeight: 800, letterSpacing: '-0.02em', marginBottom: '12px' }}>
            What are we <span className="gradient-text">researching today?</span>
          </h2>
          <p className="subtitle" style={{ maxWidth: '600px', margin: '0 auto' }}>
            Provide a research topic or assignment brief. Our autonomous multi-agent pipeline will compile ArXiv papers, synthesize summaries, and outline a custom paper.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="form-group">
          <label className="label" htmlFor="topic-input">
            Research Topic or Brief
          </label>
          <textarea
            id="topic-input"
            className="textarea-custom"
            rows={5}
            placeholder="e.g. 'Survey of retrieval-augmented generation for scientific literature review, covering architectures, evaluation benchmarks, and known failure modes.'"
            value={topic}
            onChange={(e) => {
              setTopic(e.target.value);
              if (e.target.value.trim().length >= 4) setError('');
            }}
            disabled={isLoading}
            style={{ fontSize: '1.05rem' }}
          />

          {error && (
            <p style={{ color: 'var(--accent-red)', fontSize: '0.85rem', fontWeight: 500 }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isLoading || !topic.trim()}
            style={{
              marginTop: '12px',
              padding: '16px 28px',
              fontSize: '1.05rem',
              alignSelf: 'stretch',
              justifyContent: 'center'
            }}
          >
            {isLoading ? (
              <>
                <div className="animate-pulse-radar" style={{
                  width: '18px',
                  height: '18px',
                  borderRadius: '50%',
                  background: '#fff'
                }} />
                <span>Launching Agents...</span>
              </>
            ) : (
              <>
                <span>Launch Research Pipeline</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div style={{ marginTop: '16px' }}>
          <p style={{
            fontSize: '0.85rem',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            marginBottom: '12px',
            textAlign: 'left'
          }}>
            Or select an example brief:
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {SAMPLE_TOPICS.map((t, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setTopic(t);
                  setError('');
                }}
                disabled={isLoading}
                type="button"
                className="glass-panel-interactive"
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '12px 16px',
                  textAlign: 'left',
                  color: 'var(--text-secondary)',
                  fontSize: '0.88rem',
                  lineHeight: '1.5',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)'
                }}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
