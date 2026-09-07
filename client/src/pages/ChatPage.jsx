import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
  MessageSquare, Plus, Trash2, Send, Loader2, Bot, User, Code, X, ChevronLeft, FileCode2
} from 'lucide-react';
import { chatApi, repoApi } from '../api';

export default function ChatPage({ repo, onBack }) {
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [codePanel, setCodePanel] = useState(null); // { file, line }
  const [codeContent, setCodeContent] = useState('');
  const [codeLoading, setCodeLoading] = useState(false);
  const bottomRef = useRef(null);

  const selectConversation = useCallback(async (convId) => {
    setLoading(true);
    setActiveConvId(convId);
    try {
      const data = await chatApi.getConversation(convId);
      setMessages(data.conversation?.messages || []);
    } catch {
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadConversations = useCallback(async () => {
    try {
      const data = await chatApi.listConversations(repo.id);
      setConversations(data.conversations || []);
      if (data.conversations?.length > 0) {
        selectConversation(data.conversations[0].conversation_id);
      } else {
        setLoading(false);
      }
    } catch {
      setLoading(false);
    }
  }, [repo.id, selectConversation]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleOpenCitation = async (citation) => {
    setCodePanel(citation);
    setCodeLoading(true);
    try {
      const fileData = await repoApi.getFile(repo.id, citation.file);
      setCodeContent(fileData.content || '// Content unavailable');
    } catch {
      setCodeContent('// Failed to load source code for ' + citation.file);
    } finally {
      setCodeLoading(false);
    }
  };

  const createConversation = async () => {
    try {
      const data = await chatApi.createConversation(repo.id);
      const newConv = { conversation_id: data.conversation_id, title: data.title };
      setConversations(prev => [newConv, ...prev]);
      setActiveConvId(data.conversation_id);
      setMessages([]);
    } catch {
      alert('Failed to create conversation');
    }
  };

  const deleteConversation = async (convId, e) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;
    try {
      await chatApi.deleteConversation(convId);
      setConversations(prev => prev.filter(c => c.conversation_id !== convId));
      if (activeConvId === convId) {
        setActiveConvId(null);
        setMessages([]);
      }
    } catch {
      // ignore
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !activeConvId || sending) return;
    const userMsg = { role: 'human', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setSending(true);

    try {
      const data = await chatApi.sendMessage(activeConvId, userMsg.content);
      const assistantMsg = {
        role: 'assistant',
        content: data.answer,
        citations: data.references || []
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.message}`,
        citations: []
      }]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Conversations Sidebar */}
      <div style={{
        width: 280, borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column',
        background: 'var(--bg-secondary)', flexShrink: 0
      }}>
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border)' }}>
          <button className="btn btn-secondary" style={{ width: '100%', gap: 8 }} onClick={onBack}>
            <ChevronLeft size={16} /> Back to Analysis
          </button>
        </div>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Conversations</span>
          <button className="btn" style={{ padding: '6px 10px' }} onClick={createConversation} title="New Conversation">
            <Plus size={14} />
          </button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
          {conversations.length === 0 && (
            <div style={{ textAlign: 'center', padding: '30px 16px', color: 'var(--text-muted)' }}>
              <MessageSquare size={28} style={{ marginBottom: 10, margin: '0 auto 10px' }} />
              <p style={{ fontSize: '0.85rem' }}>No conversations yet</p>
            </div>
          )}
          {conversations.map(conv => (
            <div
              key={conv.conversation_id}
              onClick={() => selectConversation(conv.conversation_id)}
              style={{
                padding: '10px 12px', borderRadius: 8, cursor: 'pointer', marginBottom: 4,
                background: activeConvId === conv.conversation_id ? 'rgba(139,92,246,0.15)' : 'transparent',
                borderLeft: activeConvId === conv.conversation_id ? '3px solid var(--accent)' : '3px solid transparent',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                transition: 'all 0.15s'
              }}
            >
              <div style={{ flex: 1, overflow: 'hidden' }}>
                <div style={{ fontWeight: 500, fontSize: '0.875rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {conv.title}
                </div>
              </div>
              <button
                onClick={e => deleteConversation(conv.conversation_id, e)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 4, borderRadius: 4, flexShrink: 0 }}
                title="Delete"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="chat-conversation-area">
        {/* Header */}
        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12, background: 'var(--bg-secondary)' }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg, var(--accent), #5b21b6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Bot size={18} color="white" />
          </div>
          <div>
            <div style={{ fontWeight: 600 }}>Codebase Intelligence Agent</div>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Exploring: {repo.id}</div>
          </div>
        </div>

        {/* Messages */}
        <div className="chat-history-messages">
          {!activeConvId && !loading && (
            <div style={{ textAlign: 'center', margin: 'auto', color: 'var(--text-muted)' }}>
              <MessageSquare size={48} style={{ marginBottom: 16, margin: '0 auto 16px' }} />
              <h3 style={{ marginBottom: 8, color: 'var(--text-primary)' }}>Start a Conversation</h3>
              <p style={{ fontSize: '0.9rem' }}>Select a conversation or create a new one to begin exploring code</p>
              <button className="btn" style={{ marginTop: 16 }} onClick={createConversation}>
                <Plus size={16} /> New Conversation
              </button>
            </div>
          )}

          {loading && (
            <div style={{ textAlign: 'center', margin: 'auto' }}>
              <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', color: 'var(--accent)', margin: '0 auto' }} />
            </div>
          )}

          {!loading && messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className={`chat-message ${msg.role === 'human' ? 'human' : 'assistant'}`}
            >
              <div className="chat-message-avatar">
                {msg.role === 'human' ? <User size={16} /> : <Bot size={16} />}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="message-bubble">
                  {msg.role === 'assistant'
                    ? <ReactMarkdown>{msg.content}</ReactMarkdown>
                    : <p>{msg.content}</p>
                  }
                </div>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="citation-container">
                    {msg.citations.map((c, ci) => (
                      <button
                        key={ci}
                        className="citation-chip"
                        onClick={() => handleOpenCitation(c)}
                        title={`View ${c.file} at line ${c.line}`}
                      >
                        <Code size={11} />
                        {c.file}:{c.line}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          ))}

          {sending && (
            <div className="chat-message assistant">
              <div className="chat-message-avatar"><Bot size={16} /></div>
              <div className="message-bubble" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {[0, 1, 2].map(i => (
                  <motion.div
                    key={i}
                    animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1, 0.8] }}
                    transition={{ repeat: Infinity, duration: 1, delay: i * 0.2 }}
                    style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)' }}
                  />
                ))}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="chat-input-area">
          <div className="chat-form">
            <textarea
              className="chat-input"
              placeholder={activeConvId ? "Ask anything about the codebase... (Enter to send, Shift+Enter for newline)" : "Select or create a conversation first"}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!activeConvId || sending}
              rows={1}
            />
            <button
              className="btn"
              onClick={sendMessage}
              disabled={!activeConvId || !input.trim() || sending}
              style={{ padding: '0 20px', alignSelf: 'stretch' }}
            >
              {sending ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={18} />}
            </button>
          </div>
        </div>
      </div>

      {/* Code Viewer Panel */}
      <AnimatePresence>
        {codePanel && (
          <motion.div
            initial={{ x: 520, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 520, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="code-viewer-panel"
            style={{ width: 480, display: 'flex', flexDirection: 'column' }}
          >
            <div className="code-viewer-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                <FileCode2 size={16} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                <span className="code-viewer-title" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {codePanel.file}
                </span>
                {codePanel.line && (
                  <span style={{ color: 'var(--accent-light)', fontSize: '0.8rem', fontFamily: 'monospace', flexShrink: 0 }}>
                    :L{codePanel.line}
                  </span>
                )}
              </div>
              <button
                onClick={() => setCodePanel(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 4, borderRadius: 4 }}
              >
                <X size={16} />
              </button>
            </div>
            <div className="code-content-wrapper" style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
              <div style={{ marginBottom: 12 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                  📌 Referenced at line <strong style={{ color: 'var(--accent-light)' }}>{codePanel.line}</strong>
                </span>
              </div>
              {codeLoading ? (
                <div style={{ textAlign: 'center', padding: 40 }}>
                  <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', color: 'var(--accent)', margin: '0 auto' }} />
                  <p style={{ marginTop: 8, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Loading source code...</p>
                </div>
              ) : (
                <div style={{
                  background: 'var(--bg-primary)',
                  borderRadius: 8,
                  border: '1px solid var(--border)',
                  fontFamily: 'monospace',
                  fontSize: '0.8rem',
                  overflowX: 'auto'
                }}>
                  {codeContent.splitlines ? codeContent.split('\n').map((line, idx) => {
                    const lineNum = idx + 1;
                    const isTarget = lineNum === Number(codePanel.line);
                    return (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          background: isTarget ? 'rgba(139,92,246,0.25)' : 'transparent',
                          borderLeft: isTarget ? '3px solid var(--accent)' : '3px solid transparent',
                          padding: '1px 8px',
                          color: isTarget ? '#fff' : 'var(--text-secondary)'
                        }}
                      >
                        <span style={{ width: 36, color: 'var(--text-muted)', userSelect: 'none', textAlign: 'right', marginRight: 12 }}>
                          {lineNum}
                        </span>
                        <span style={{ whiteSpace: 'pre', color: isTarget ? 'var(--accent-light)' : 'inherit' }}>
                          {line}
                        </span>
                      </div>
                    );
                  }) : (
                    <pre style={{ padding: 12 }}>{codeContent}</pre>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
