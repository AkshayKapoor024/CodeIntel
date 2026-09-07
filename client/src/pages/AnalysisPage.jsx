import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart3, FileCode2, GitBranch, Shield, Zap, BookOpen, TestTube2, FileText,
  ChevronRight, ChevronDown, AlertTriangle, Info, CheckCircle, Folder, File,
  MessageSquare, Loader2, X, Sparkles
} from 'lucide-react';
import { repoApi } from '../api';

const TABS = [
  { id: 'overview', label: 'Overview', icon: <BarChart3 size={15} /> },
  { id: 'structure', label: 'Structure', icon: <Folder size={15} /> },
  { id: 'quality', label: 'Quality Scores', icon: <Shield size={15} /> },
  { id: 'issues', label: 'Issues', icon: <AlertTriangle size={15} /> },
  { id: 'report', label: 'Full Report', icon: <FileText size={15} /> },
];

const QUALITY_DIMS = [
  { key: 'readability', label: 'Readability', icon: <BookOpen size={15} />, color: '#8b5cf6' },
  { key: 'maintainability', label: 'Maintainability', icon: <FileCode2 size={15} />, color: '#3b82f6' },
  { key: 'scalability', label: 'Scalability', icon: <Zap size={15} />, color: '#f59e0b' },
  { key: 'security', label: 'Security', icon: <Shield size={15} />, color: '#10b981' },
  { key: 'performance', label: 'Performance', icon: <BarChart3 size={15} />, color: '#06b6d4' },
  { key: 'testing', label: 'Testing', icon: <TestTube2 size={15} />, color: '#f97316' },
  { key: 'documentation', label: 'Documentation', icon: <FileText size={15} />, color: '#ec4899' },
];

export default function AnalysisPage({ repo, onOpenChat }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [analysis, setAnalysis] = useState(null);
  const [structure, setStructure] = useState(null);
  const [issues, setIssues] = useState([]);
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState(repo.status);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileDetails, setFileDetails] = useState(null);
  const [fileLoading, setFileLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const [a, s, iss, r] = await Promise.all([
        repoApi.analysis(repo.id),
        repoApi.structure(repo.id),
        repoApi.issues(repo.id),
        repoApi.report(repo.id),
      ]);
      setAnalysis(a);
      setStructure(s.directory_tree);
      setIssues(iss.issues || []);
      setReport(r);
    } catch (e) {
      console.error(e);
    }
  }, [repo.id]);

  useEffect(() => {
    if (status === 'completed') {
      load();
    }
  }, [status, load]);

  // Poll until completed
  useEffect(() => {
    if (status === 'completed' || status === 'failed') return;
    const iv = setInterval(async () => {
      try {
        const d = await repoApi.status(repo.id);
        setStatus(d.status);
        if (d.status === 'completed' || d.status === 'failed') clearInterval(iv);
      } catch {
        clearInterval(iv);
      }
    }, 3000);
    return () => clearInterval(iv);
  }, [status, repo.id]);

  const handleSelectFile = async (filePath) => {
    setSelectedFile(filePath);
    setFileLoading(true);
    try {
      const data = await repoApi.getFile(repo.id, filePath);
      setFileDetails(data);
    } catch (err) {
      console.error(err);
      setFileDetails(null);
    } finally {
      setFileLoading(false);
    }
  };

  if (status !== 'completed') {
    return (
      <div className="content-pane" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '80%' }}>
        {status === 'failed' ? (
          <>
            <AlertTriangle size={48} style={{ color: 'var(--danger)', marginBottom: 16 }} />
            <h3>Analysis Failed</h3>
            <p style={{ color: 'var(--text-secondary)', marginTop: 8 }}>
              Something went wrong during analysis. Please try restarting analysis from the dashboard.
            </p>
          </>
        ) : (
          <>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 2, ease: 'linear' }}
            >
              <Loader2 size={48} style={{ color: 'var(--accent)' }} />
            </motion.div>
            <h3 style={{ marginTop: 20 }}>Analyzing Repository</h3>
            <p style={{ color: 'var(--text-secondary)', marginTop: 8 }}>
              Current stage: <strong style={{ color: 'var(--accent-light)' }}>{status.replace(/_/g, ' ')}</strong>
            </p>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 4 }}>
              Parsing AST structures and auditing code intelligence...
            </p>
            <div style={{ marginTop: 24, display: 'flex', gap: 20 }}>
              {['Cloning', 'Inspecting', 'Parsing', 'Analyzing', 'Synthesizing'].map((stage, i) => {
                const stages = ['cloning','inspecting','parsing','analyzing_files','synthesizing'];
                const current = stages.findIndex(s => status.includes(s));
                const done = i < current;
                const active = i === current;
                return (
                  <div key={stage} style={{ textAlign: 'center', opacity: done || active ? 1 : 0.3 }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', margin: '0 auto 6px',
                      background: done ? 'var(--success)' : active ? 'var(--accent)' : 'var(--border)' }} />
                    <div style={{ fontSize: '0.75rem', color: active ? 'var(--accent-light)' : 'var(--text-muted)' }}>
                      {stage}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    );
  }

  const quality = analysis?.quality_scores || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Top bar with chat button */}
      <div style={{ padding: '0 30px', borderBottom: '1px solid var(--border)',
        background: 'rgba(11,11,20,0.5)', backdropFilter: 'blur(12px)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 60 }}>
        <div className="tab-container" style={{ borderBottom: 'none', margin: 0 }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: '0.85rem' }}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>
        <button className="btn" onClick={onOpenChat} style={{ gap: 8 }}>
          <MessageSquare size={16} /> Ask AI about this repo
        </button>
      </div>

      <div className="content-pane" style={{ flex: 1, overflowY: 'auto' }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {activeTab === 'overview' && <OverviewTab analysis={analysis} />}
            {activeTab === 'structure' && (
              <StructureTab
                tree={structure}
                onSelectFile={handleSelectFile}
                selectedFile={selectedFile}
                fileDetails={fileDetails}
                fileLoading={fileLoading}
                onCloseDrawer={() => { setSelectedFile(null); setFileDetails(null); }}
              />
            )}
            {activeTab === 'quality' && <QualityTab quality={quality} />}
            {activeTab === 'issues' && <IssuesTab issues={issues} />}
            {activeTab === 'report' && <ReportTab report={report} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

function OverviewTab({ analysis }) {
  const r = analysis?.repository || {};
  const q = analysis?.quality_scores || {};
  const scores = Object.entries(q).filter(([k]) => k.endsWith('_score')).map(([, v]) => Number(v) || 0);
  const avg = scores.length > 0 ? (scores.reduce((a, b) => a + b, 0) / scores.length) : 0;

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20, marginBottom: 28 }}>
        {[
          { label: 'Total Files Indexed', value: analysis?.files_count || 0, icon: <FileCode2 size={22} />, color: 'var(--accent)' },
          { label: 'Overall Quality Score', value: avg > 0 ? `${avg.toFixed(1)}/10` : 'N/A', icon: <BarChart3 size={22} />, color: 'var(--success)' },
          { label: 'Default Branch', value: r.branch || 'main', icon: <GitBranch size={22} />, color: 'var(--info)' },
        ].map(item => (
          <div key={item.label} className="card" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ color: item.color }}>{item.icon}</div>
            <div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700 }}>{item.value}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{item.label}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="card">
        <h3 style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600 }}>
          <Info size={16} style={{ color: 'var(--accent)' }} /> Repository Metadata
        </h3>
        {[
          ['GitHub URL', r.github_url],
          ['Commit SHA', r.commit_hash],
          ['Architecture Style', r.architecture_analysis || 'Modular Codebase'],
          ['Created At', r.created_at],
        ].map(([k, v]) => (
          <div key={k} style={{ display: 'flex', gap: 16, padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
            <span style={{ color: 'var(--text-secondary)', minWidth: 160, fontSize: '0.875rem' }}>{k}</span>
            <span style={{ fontFamily: 'monospace', fontSize: '0.875rem', wordBreak: 'break-all' }}>{v || 'N/A'}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StructureTab({ tree, onSelectFile, selectedFile, fileDetails, fileLoading, onCloseDrawer }) {
  if (!tree) return <p style={{ color: 'var(--text-muted)' }}>No directory structure available.</p>;
  return (
    <div style={{ display: 'grid', gridTemplateColumns: selectedFile ? '1fr 1fr' : '1fr', gap: 20 }}>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Folder size={16} style={{ color: 'var(--accent)' }} />
            Directory Tree
          </h3>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Click any file to inspect AST</span>
        </div>
        <div style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
          <TreeNode node={tree} depth={0} onSelectFile={onSelectFile} selectedFile={selectedFile} />
        </div>
      </div>

      {selectedFile && (
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="card"
          style={{ height: 'fit-content', maxHeight: '80vh', overflowY: 'auto' }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <FileCode2 size={16} style={{ color: 'var(--accent)' }} />
              <span style={{ fontWeight: 600, fontSize: '0.9rem', wordBreak: 'break-all' }}>{selectedFile}</span>
            </div>
            <button onClick={onCloseDrawer} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
              <X size={16} />
            </button>
          </div>

          {fileLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', color: 'var(--accent)' }} />
              <p style={{ marginTop: 8, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Loading file AST...</p>
            </div>
          ) : fileDetails?.file_info ? (
            <div>
              {/* Summary / Purpose */}
              {fileDetails.file_info.analysis?.purpose && (
                <div style={{ background: 'rgba(139,92,246,0.08)', padding: 12, borderRadius: 8, marginBottom: 14 }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-light)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Sparkles size={12} /> PURPOSE
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>{fileDetails.file_info.analysis.purpose}</p>
                </div>
              )}

              {/* AST Classes & Functions */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 14 }}>
                <div style={{ background: 'var(--bg-tertiary)', padding: 10, borderRadius: 8 }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Classes</span>
                  <div style={{ fontWeight: 600, fontSize: '1rem', marginTop: 2 }}>
                    {fileDetails.file_info.ast_data?.classes?.length || 0}
                  </div>
                </div>
                <div style={{ background: 'var(--bg-tertiary)', padding: 10, borderRadius: 8 }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Functions / Methods</span>
                  <div style={{ fontWeight: 600, fontSize: '1rem', marginTop: 2 }}>
                    {fileDetails.file_info.ast_data?.functions?.length || 0}
                  </div>
                </div>
              </div>

              {/* Imports */}
              {fileDetails.file_info.ast_data?.imports?.length > 0 && (
                <div style={{ marginBottom: 14 }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block', marginBottom: 6 }}>Dependencies & Imports</span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {fileDetails.file_info.ast_data.imports.slice(0, 15).map((imp, i) => (
                      <span key={i} style={{ background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: 4, fontSize: '0.75rem', fontFamily: 'monospace' }}>
                        {imp}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Code Preview */}
              {fileDetails.content && (
                <div>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block', marginBottom: 6 }}>Source Code Preview</span>
                  <pre style={{ background: 'var(--bg-primary)', padding: 12, borderRadius: 8, fontSize: '0.75rem', overflowX: 'auto', maxHeight: 220, border: '1px solid var(--border)' }}>
                    <code>{fileDetails.content.slice(0, 2000)}</code>
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Static asset or config file without AST parsing data.</p>
          )}
        </motion.div>
      )}
    </div>
  );
}

function TreeNode({ node, depth, onSelectFile, selectedFile }) {
  const [open, setOpen] = useState(depth < 2);
  const isDir = node.type === 'directory';
  const isSelected = selectedFile === node.path;

  return (
    <div style={{ marginLeft: depth * 14 }}>
      <div
        onClick={() => {
          if (isDir) setOpen(o => !o);
          else if (node.path && onSelectFile) onSelectFile(node.path);
        }}
        style={{
          display: 'flex', alignItems: 'center', gap: 7, padding: '4px 6px',
          borderRadius: 6, cursor: 'pointer',
          color: isSelected ? 'var(--accent-light)' : isDir ? 'var(--accent-light)' : 'var(--text-primary)',
          background: isSelected ? 'rgba(139,92,246,0.15)' : 'transparent',
          borderLeft: isSelected ? '2px solid var(--accent)' : '2px solid transparent',
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
        onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
      >
        {isDir
          ? (open ? <ChevronDown size={13} /> : <ChevronRight size={13} />)
          : <span style={{ width: 13 }} />}
        {isDir ? <Folder size={14} style={{ flexShrink: 0 }} /> : <File size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
        <span>{node.name}</span>
        {!isDir && node.size > 0 && (
          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginLeft: 'auto' }}>
            {(node.size / 1024).toFixed(1)}KB
          </span>
        )}
      </div>
      {isDir && open && (node.children || []).map((child, i) => (
        <TreeNode key={i} node={child} depth={depth + 1} onSelectFile={onSelectFile} selectedFile={selectedFile} />
      ))}
    </div>
  );
}

function QualityTab({ quality }) {
  return (
    <div>
      <h3 style={{ marginBottom: 20, fontWeight: 600 }}>Codebase Quality Audit (7 Dimensions)</h3>
      <div className="quality-grid">
        {QUALITY_DIMS.map(dim => {
          const score = quality[`${dim.key}_score`] ?? 0;
          const comment = quality[`${dim.key}_comment`] || '';
          const pct = (score / 10) * 100;
          return (
            <motion.div
              key={dim.key}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className="quality-card"
            >
              <div className="quality-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: dim.color }}>
                  {dim.icon}
                  <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                    {dim.label}
                  </span>
                </div>
                <span className="quality-score-badge" style={{ color: dim.color }}>{Number(score).toFixed(1)}</span>
              </div>
              <div className="progress-bar-container">
                <motion.div
                  className="progress-bar-fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.8, ease: 'easeOut' }}
                  style={{ background: `linear-gradient(90deg, ${dim.color}, ${dim.color}99)` }}
                />
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', lineHeight: 1.5 }}>{comment}</p>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

function IssuesTab({ issues }) {
  const [filter, setFilter] = useState('ALL');
  const filtered = filter === 'ALL' ? issues : issues.filter(i => i.severity === filter);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 style={{ fontWeight: 600 }}>
          Audited Issues & Recommendations <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({issues.length})</span>
        </h3>
        <div style={{ display: 'flex', gap: 8 }}>
          {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`btn ${filter === f ? '' : 'btn-secondary'}`}
              style={{ padding: '6px 14px', fontSize: '0.8rem' }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      {filtered.length === 0
        ? <div className="card" style={{ textAlign: 'center', padding: 40 }}>
            <CheckCircle size={36} style={{ color: 'var(--success)', marginBottom: 12, margin: '0 auto 12px' }} />
            <p style={{ color: 'var(--text-secondary)' }}>No issues found for this filter</p>
          </div>
        : filtered.map((issue, i) => (
          <motion.div
            key={issue.id || i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            className={`issue-item severity-${issue.severity}`}
          >
            <div className="issue-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span className={`status-badge status-${issue.severity === 'HIGH' ? 'failed' : issue.severity === 'MEDIUM' ? 'registered' : 'completed'}`}>
                  {issue.severity}
                </span>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{issue.category}</span>
              </div>
              <span className="issue-file">{issue.file_path}:{issue.line}</span>
            </div>
            <p style={{ fontWeight: 600, marginBottom: 8 }}>{issue.problem}</p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: 8 }}>
              <strong>Impact:</strong> {issue.impact}
            </p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', background: 'rgba(255,255,255,0.03)',
              padding: '8px 12px', borderRadius: 6 }}>
              <strong>Fix:</strong> {issue.recommendation}
            </p>
          </motion.div>
        ))
      }
    </div>
  );
}

function ReportTab({ report }) {
  const summary = report?.summary || report?.report?.overview || 'No report generated yet.';
  return (
    <div className="card">
      <h3 style={{ marginBottom: 20, fontWeight: 600 }}>Multi-Agent Synthesis Report</h3>
      <div style={{ lineHeight: 1.8, color: 'var(--text-secondary)' }}>
        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: '0.9rem' }}>
          {summary}
        </pre>
      </div>
    </div>
  );
}
