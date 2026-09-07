import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Plus, FolderGit2, GitBranch, RefreshCw, Trash2, Play, Loader2,
  ChevronRight, Clock, CheckCircle2, XCircle, Activity, GitFork, Layers
} from 'lucide-react';
import { repoApi } from '../api';

export default function DashboardPage({ onSelectRepo }) {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newUrl, setNewUrl] = useState('');
  const [newBranch, setNewBranch] = useState('main');
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);

  const fetchRepos = useCallback(async () => {
    try {
      const data = await repoApi.list();
      setRepos(data.repositories || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRepos();
  }, [fetchRepos]);

  // Poll status for repos that are in-progress
  useEffect(() => {
    const inProgress = repos.filter(r =>
      !['completed', 'failed', 'cloned_registered'].includes(r.status)
    );
    if (inProgress.length === 0) return;

    const interval = setInterval(async () => {
      const updates = await Promise.all(
        inProgress.map(r => repoApi.status(r.id).catch(() => null))
      );
      setRepos(prev => prev.map(r => {
        const match = inProgress.find(ir => ir.id === r.id);
        const idx = match ? inProgress.indexOf(match) : -1;
        if (idx >= 0 && updates[idx]) {
          return { ...r, status: updates[idx].status };
        }
        return r;
      }));
    }, 3000);

    return () => clearInterval(interval);
  }, [repos]);

  const handleAdd = async (e) => {
    e.preventDefault();
    setError('');
    setAdding(true);
    try {
      await repoApi.create({ github_url: newUrl, branch: newBranch });
      setNewUrl('');
      setNewBranch('main');
      setShowForm(false);
      await fetchRepos();
    } catch (err) {
      setError(err.message);
    } finally {
      setAdding(false);
    }
  };

  const handleAnalyze = async (repoId, e) => {
    e.stopPropagation();
    try {
      await repoApi.analyze(repoId);
      setRepos(prev => prev.map(r => r.id === repoId ? { ...r, status: 'cloning' } : r));
    } catch (err) {
      alert('Failed to start analysis: ' + err.message);
    }
  };

  const handleDelete = async (repoId, e) => {
    e.stopPropagation();
    if (!confirm('Delete this repository?')) return;
    try {
      await repoApi.delete(repoId);
      setRepos(prev => prev.filter(r => r.id !== repoId));
    } catch (err) {
      alert('Failed to delete: ' + err.message);
    }
  };

  return (
    <div className="content-pane">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 30 }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 4 }}>Repository Dashboard</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            Submit a GitHub repository to start multi-agent codebase analysis & exploration
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-secondary" onClick={fetchRepos}>
            <RefreshCw size={16} /> Refresh
          </button>
          <button className="btn" onClick={() => setShowForm(f => !f)}>
            <Plus size={16} /> Add Repository
          </button>
        </div>
      </div>

      {/* Add Repo Form */}
      {showForm && (
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          className="card"
          style={{ marginBottom: 28 }}
        >
          <h3 style={{ marginBottom: 16, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
            <GitFork size={18} style={{ color: 'var(--accent)' }} />
            Add GitHub Repository
          </h3>
          <form onSubmit={handleAdd}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, marginBottom: 12 }}>
              <input
                className="form-input"
                placeholder="https://github.com/owner/repository"
                value={newUrl}
                onChange={e => setNewUrl(e.target.value)}
                required
              />
              <input
                className="form-input"
                placeholder="Branch (e.g. main)"
                value={newBranch}
                onChange={e => setNewBranch(e.target.value)}
                style={{ width: 160 }}
              />
            </div>
            {error && (
              <p style={{ color: 'var(--danger)', fontSize: '0.875rem', marginBottom: 12 }}>{error}</p>
            )}
            <div style={{ display: 'flex', gap: 10 }}>
              <button type="submit" className="btn" disabled={adding}>
                {adding ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : <Plus size={16} />}
                Register Repository
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>
          </form>
        </motion.div>
      )}

      {/* Stats row */}
      {repos.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 28 }}>
          {[
            { label: 'Total Tracked', value: repos.length, icon: <Layers size={20} />, color: 'var(--accent)' },
            { label: 'Completed', value: repos.filter(r => r.status === 'completed').length, icon: <CheckCircle2 size={20} />, color: 'var(--success)' },
            { label: 'In Progress', value: repos.filter(r => !['completed','failed','cloned_registered'].includes(r.status)).length, icon: <Activity size={20} />, color: 'var(--info)' },
            { label: 'Failed', value: repos.filter(r => r.status === 'failed').length, icon: <XCircle size={20} />, color: 'var(--danger)' },
          ].map(stat => (
            <div key={stat.label} className="card" style={{ margin: 0, textAlign: 'center' }}>
              <div style={{ color: stat.color, marginBottom: 8, display: 'flex', justifyContent: 'center' }}>{stat.icon}</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{stat.value}</div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{stat.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Repo Grid */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', color: 'var(--accent)' }} />
          <p style={{ marginTop: 12, color: 'var(--text-secondary)' }}>Loading repositories...</p>
        </div>
      ) : repos.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card"
          style={{ textAlign: 'center', padding: 60 }}
        >
          <FolderGit2 size={48} style={{ color: 'var(--text-muted)', marginBottom: 16, margin: '0 auto 16px' }} />
          <h3 style={{ marginBottom: 8 }}>No repositories yet</h3>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 20 }}>
            Add a GitHub repository to start multi-agent analysis and interactive chat
          </p>
          <button className="btn" onClick={() => setShowForm(true)}>
            <Plus size={16} /> Add Your First Repository
          </button>
        </motion.div>
      ) : (
        <div className="repo-grid">
          {repos.map((repo, i) => (
            <RepoCard
              key={repo.id}
              repo={repo}
              index={i}
              onSelect={() => onSelectRepo(repo)}
              onAnalyze={e => handleAnalyze(repo.id, e)}
              onDelete={e => handleDelete(repo.id, e)}
            />
          ))}
        </div>
      )}

      <style>{`@keyframes spin { from{transform:rotate(0deg)}to{transform:rotate(360deg)} }`}</style>
    </div>
  );
}

function StatusBadge({ status }) {
  const STATUS_MAP = {
    completed: { label: 'Completed', cls: 'status-completed', icon: <CheckCircle2 size={11} /> },
    failed: { label: 'Failed', cls: 'status-failed', icon: <XCircle size={11} /> },
    cloned_registered: { label: 'Registered', cls: 'status-registered', icon: <Clock size={11} /> },
  };
  const s = STATUS_MAP[status] || { label: status, cls: 'status-cloning', icon: <Activity size={11} /> };
  return (
    <span className={`status-badge ${s.cls}`} style={{ gap: 5, display: 'inline-flex', alignItems: 'center' }}>
      {s.icon} {s.label}
    </span>
  );
}

function RepoCard({ repo, index, onSelect, onAnalyze, onDelete }) {
  const inProgress = !['completed', 'failed', 'cloned_registered'].includes(repo.status);
  const nameParts = repo.id.split('_');

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="card repo-card"
      onClick={onSelect}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: 'linear-gradient(135deg, rgba(139,92,246,0.3), rgba(59,130,246,0.3))',
            border: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            <FolderGit2 size={18} style={{ color: 'var(--accent-light)' }} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{nameParts.slice(1).join('_') || repo.id}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: 4 }}>
              <GitBranch size={11} /> {repo.branch || 'main'} • {nameParts[0]}
            </div>
          </div>
        </div>
        <StatusBadge status={repo.status} />
      </div>

      <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginBottom: 16, fontFamily: 'monospace',
        background: 'var(--bg-tertiary)', padding: '6px 10px', borderRadius: 6, overflow: 'hidden',
        textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {repo.github_url}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 8 }}>
          {(repo.status === 'cloned_registered' || repo.status === 'failed') && (
            <button className="btn" style={{ padding: '8px 14px', fontSize: '0.8rem' }} onClick={onAnalyze}>
              <Play size={13} /> Analyze
            </button>
          )}
          {inProgress && (
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--info)', fontSize: '0.8rem' }}>
              <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
              {repo.status.replace(/_/g, ' ')}...
            </span>
          )}
          {repo.status === 'completed' && (
            <button className="btn" style={{ padding: '8px 14px', fontSize: '0.8rem' }} onClick={onSelect}>
              View Report <ChevronRight size={13} />
            </button>
          )}
        </div>
        <button className="btn btn-danger" style={{ padding: '8px', fontSize: '0.8rem' }} onClick={onDelete}>
          <Trash2 size={14} />
        </button>
      </div>
    </motion.div>
  );
}
