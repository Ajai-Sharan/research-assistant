import { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { InputScreen } from './components/InputScreen';
import { RunningScreen } from './components/RunningScreen';
import { ReviewScreen } from './components/ReviewScreen';
import { DoneScreen } from './components/DoneScreen';
import { ErrorScreen } from './components/ErrorScreen';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || (window.location.port === '5173' ? 'http://localhost:8000' : window.location.origin);
const POLL_INTERVAL = 2000; // 2 seconds

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

function App() {
  const [jobId, setJobId] = useState<string | null>(() => localStorage.getItem('research_job_id'));
  const [view, setView] = useState<string>(() => localStorage.getItem('research_view') || 'input');
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'checking'>('checking');

  const pollingRef = useRef<any>(null);

  // Sync state to localStorage to prevent losing state on refresh
  useEffect(() => {
    if (jobId) {
      localStorage.setItem('research_job_id', jobId);
    } else {
      localStorage.removeItem('research_job_id');
    }
  }, [jobId]);

  useEffect(() => {
    localStorage.setItem('research_view', view);
  }, [view]);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);



  // Poll status helper
  const fetchStatus = async (id: string) => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/status/${id}`);
      if (!res.ok) {
        if (res.status === 404) {
          // Unknown job, reset
          handleReset();
          return;
        }
        throw new Error(`Error fetching status: ${res.statusText}`);
      }
      const data: StatusResponse = await res.json();
      setStatus(data);

      if (data.error) {
        setView('error');
        setErrorMsg(data.error);
        stopPolling();
      } else if (data.awaiting_review) {
        setView('review');
        stopPolling();
      } else if (data.stage === 'complete') {
        setView('done');
        stopPolling();
      } else {
        setView('running');
      }
    } catch (err: any) {
      console.error(err);
      // Don't crash polling on transient network errors, just log it
    }
  };

  const startPolling = (id: string) => {
    stopPolling();
    // Fetch immediately first
    fetchStatus(id);
    pollingRef.current = setInterval(() => {
      fetchStatus(id);
    }, POLL_INTERVAL);
  };

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  // Start polling if we reload and have an active running job
  useEffect(() => {
    if (jobId && view === 'running') {
      startPolling(jobId);
    } else if (jobId && (view === 'review' || view === 'done' || view === 'error')) {
      // Fetch once to load data
      fetchStatus(jobId);
    } else if (!jobId && view !== 'input') {
      // Safeguard: if no jobId is found but we are in a state that requires it, reset
      handleReset();
    }
  }, [jobId, view]);

  const handleStartResearch = async (topic: string) => {
    setIsLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch(`${BACKEND_URL}/api/start-research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}: ${res.statusText}`);
      const data = await res.json();
      
      setJobId(data.job_id);
      setView('running');
      startPolling(data.job_id);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to start research session.');
      setView('error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitFeedback = async (
    decision: 'approve' | 'revise',
    feedbackText: string | null,
    _editedOutline: string | null
  ) => {
    if (!jobId) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/submit-feedback/${jobId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          feedback: feedbackText,
        }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}: ${res.statusText}`);
      
      // Update view back to running and resume polling
      setView('running');
      startPolling(jobId);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit feedback.');
      setView('error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    stopPolling();
    setJobId(null);
    setView('input');
    setStatus(null);
    setErrorMsg('');
    localStorage.removeItem('research_job_id');
    localStorage.removeItem('research_view');
  };

  return (
    <div className="app-container">
      <Header backendUrl={BACKEND_URL} />
      
      <main className="main-content">
        {view === 'input' && (
          <InputScreen onSubmit={handleStartResearch} isLoading={isLoading} />
        )}
        
        {view === 'running' && status && (
          <RunningScreen status={status} onAbandon={handleReset} />
        )}
        
        {view === 'review' && status && (
          <ReviewScreen 
            status={status} 
            onSubmitFeedback={handleSubmitFeedback} 
            isLoading={isLoading} 
          />
        )}
        
        {view === 'done' && status && (
          <DoneScreen status={status} onReset={handleReset} />
        )}
        
        {view === 'error' && (
          <ErrorScreen error={errorMsg} onReset={handleReset} />
        )}

        {/* Loading / Reconnecting State Safeguard */}
        {(view === 'running' || view === 'review' || view === 'done') && !status && (
          <div className="glass-panel text-center fade-in" style={{ maxWidth: '600px', margin: '80px auto', padding: '40px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
            <div className="animate-pulse-radar" style={{ width: '48px', height: '48px', borderRadius: '50%', background: 'var(--accent-purple)' }} />
            <h3 style={{ fontSize: '1.4rem', fontWeight: 700, margin: 0 }}>Reconnecting to Research Pipeline...</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', margin: 0, lineHeight: '1.5' }}>
              Attempting to retrieve status for job ID: <code style={{ color: 'var(--accent-purple)' }}>{jobId || 'unknown'}</code>. 
              The backend may be processing or restarting.
            </p>
            <button className="btn btn-secondary" onClick={handleReset} style={{ marginTop: '10px' }}>
              Reset & Start New Research
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
