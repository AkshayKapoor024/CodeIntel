import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Code2, LayoutDashboard, MessageSquare, LogOut, FolderGit2, User } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import AnalysisPage from './pages/AnalysisPage';
import ChatPage from './pages/ChatPage';
import './index.css';

function AppInner() {
  const { user, loading, logout } = useAuth();
  const [view, setView] = useState('dashboard'); // 'dashboard' | 'analysis' | 'chat'
  const [selectedRepo, setSelectedRepo] = useState(null);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--bg-primary)' }}>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
          style={{ width: 40, height: 40, border: '3px solid var(--border)', borderTop: '3px solid var(--accent)', borderRadius: '50%' }}
        />
      </div>
    );
  }

  if (!user) return <AuthPage />;

  const handleSelectRepo = (repo) => {
    setSelectedRepo(repo);
    setView('analysis');
  };

  const handleOpenChat = () => setView('chat');
  const handleBackToAnalysis = () => setView('analysis');

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} />, action: () => { setView('dashboard'); setSelectedRepo(null); } },
    ...(selectedRepo ? [
      { id: 'analysis', label: selectedRepo.id.split('_').slice(1).join('_') || selectedRepo.id, icon: <FolderGit2 size={18} />, action: () => setView('analysis') },
      { id: 'chat', label: 'AI Chat', icon: <MessageSquare size={18} />, action: () => setView('chat') },
    ] : []),
  ];

  return (
    <div className="app-container">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="logo-icon">
            <Code2 size={18} color="white" />
          </div>
          <span className="logo-text">CodeIntel</span>
        </div>

        <div className="sidebar-content">
          <div>
            <div className="section-title">Navigation</div>
            <ul className="nav-list">
              {navItems.map(item => (
                <li key={item.id}>
                  <button
                    className={`nav-item ${view === item.id ? 'active' : ''}`}
                    onClick={item.action}
                  >
                    {item.icon}
                    <span style={{ fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.label}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {selectedRepo && (
            <div style={{ padding: '12px', background: 'rgba(139,92,246,0.08)', borderRadius: 10, border: '1px solid rgba(139,92,246,0.15)' }}>
              <div className="section-title" style={{ marginBottom: 8 }}>Active Repository</div>
              <div style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--accent-light)', wordBreak: 'break-all' }}>
                {selectedRepo.github_url}
              </div>
              <div style={{ marginTop: 6 }}>
                <span className={`status-badge status-${selectedRepo.status}`} style={{ fontSize: '0.7rem' }}>
                  {selectedRepo.status}
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">
              <User size={16} color="white" />
            </div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ fontWeight: 600, fontSize: '0.875rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.name}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.email}
              </div>
            </div>
          </div>
          <button className="btn btn-secondary" onClick={logout} style={{ width: '100%', gap: 8 }}>
            <LogOut size={15} /> Sign Out
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        <AnimatePresence mode="wait">
          {view === 'dashboard' && (
            <motion.div key="dashboard" style={{ height: '100%' }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <DashboardPage onSelectRepo={handleSelectRepo} />
            </motion.div>
          )}
          {view === 'analysis' && selectedRepo && (
            <motion.div key="analysis" style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <AnalysisPage repo={selectedRepo} onOpenChat={handleOpenChat} />
            </motion.div>
          )}
          {view === 'chat' && selectedRepo && (
            <motion.div key="chat" style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <ChatPage repo={selectedRepo} onBack={handleBackToAnalysis} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  );
}
