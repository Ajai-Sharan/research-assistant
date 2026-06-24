import React from 'react';

interface AgentGraphProps {
  currentStage: string;
}

interface GraphNodeConfig {
  id: string;
  label: string;
  x: number;
  y: number;
}

const NODES: GraphNodeConfig[] = [
  { id: 'planning', label: 'Planner', x: 70, y: 60 },
  { id: 'searching', label: 'Searcher', x: 200, y: 60 },
  { id: 'reading', label: 'Reader', x: 330, y: 60 },
  { id: 'synthesizing', label: 'Synthesizer', x: 460, y: 60 },
  { id: 'awaiting_review', label: 'Reviewer', x: 590, y: 60 },
  { id: 'drafting', label: 'Drafter', x: 720, y: 60 },
  { id: 'citation_check', label: 'Citation Audit', x: 850, y: 60 },
  { id: 'complete', label: 'Complete', x: 960, y: 60 },
];

const STAGE_ORDER: Record<string, number> = {
  queued: -1,
  planning: 0,
  searching: 1,
  reading: 2,
  synthesizing: 3,
  awaiting_review: 4,
  drafting: 5,
  citation_check: 6,
  complete: 7,
};

export const AgentGraph: React.FC<AgentGraphProps> = ({ currentStage }) => {
  // Safe parsing of stages in case they come slightly different
  const activeIdx = STAGE_ORDER[currentStage] !== undefined ? STAGE_ORDER[currentStage] : -1;

  return (
    <div className="svg-graph-container fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0 8px 10px 8px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
        <span>ACTIVE WORKFLOW STATE: <strong style={{ color: 'var(--accent-purple)' }}>{currentStage.toUpperCase()}</strong></span>
        <span>Agents pipeline orchestration</span>
      </div>
      
      <svg 
        viewBox="0 0 1020 120" 
        width="100%" 
        height="100%" 
        style={{ overflow: 'visible' }}
      >
        <defs>
          {/* Drop shadows for glowing elements */}
          <filter id="glow-active" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          
          <linearGradient id="line-grad-active" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--accent-indigo)" />
            <stop offset="100%" stopColor="var(--accent-purple)" />
          </linearGradient>

          <linearGradient id="line-grad-completed" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="var(--accent-green)" />
            <stop offset="100%" stopColor="var(--accent-cyan)" />
          </linearGradient>
        </defs>

        {/* Draw Pathway Connections */}
        {NODES.slice(0, -1).map((node, idx) => {
          const nextNode = NODES[idx + 1];
          const isCompleted = idx < activeIdx;
          const isActive = idx === activeIdx;

          let pathClass = 'graph-path';
          if (isCompleted) pathClass += ' graph-path-completed';
          if (isActive) pathClass += ' graph-path-active';

          const pathId = `path-${node.id}`;

          return (
            <g key={pathId}>
              {/* Connection Line */}
              <path
                id={pathId}
                d={`M ${node.x} ${node.y} L ${nextNode.x} ${nextNode.y}`}
                className={pathClass}
                stroke={isCompleted ? 'url(#line-grad-completed)' : isActive ? 'url(#line-grad-active)' : 'rgba(255,255,255,0.06)'}
              />

              {/* Animating Data Packets along Active / Completed paths */}
              {isActive && (
                <circle r="4" fill="var(--accent-cyan)">
                  <animateMotion 
                    dur="1.5s" 
                    repeatCount="indefinite" 
                    path={`M ${node.x} ${node.y} L ${nextNode.x} ${nextNode.y}`}
                  />
                </circle>
              )}
            </g>
          );
        })}

        {/* Draw Nodes */}
        {NODES.map((node, idx) => {
          const isCompleted = idx < activeIdx;
          const isActive = idx === activeIdx;
          const isPending = idx > activeIdx;

          let nodeClass = 'graph-node';
          if (isCompleted) nodeClass += ' graph-node-completed';
          if (isActive) nodeClass += ' graph-node-active';
          if (isPending) nodeClass += ' graph-node-pending';

          return (
            <g key={node.id} className={nodeClass} transform={`translate(0, 0)`}>
              {/* Outer pulsing ring for active node */}
              {isActive && (
                <circle 
                  cx={node.x} 
                  cy={node.y} 
                  r="24" 
                  className="pulse-ring" 
                />
              )}

              {/* Main Node Circle */}
              <circle
                cx={node.x}
                cy={node.y}
                r="18"
                className="graph-node-circle"
              />

              {/* Checkmark inside completed nodes */}
              {isCompleted ? (
                <path
                  d={`M ${node.x - 5} ${node.y} L ${node.x - 1} ${node.y + 4} L ${node.x + 6} ${node.y - 3}`}
                  fill="none"
                  stroke="var(--accent-green)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              ) : isActive ? (
                // Pulse dot inside active node
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="5"
                  fill="var(--accent-purple)"
                />
              ) : (
                // Simple dot inside pending nodes
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="3"
                  fill="rgba(255, 255, 255, 0.2)"
                />
              )}

              {/* Node Labels */}
              <text
                x={node.x}
                y={node.y + 36}
                className="graph-node-text"
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
