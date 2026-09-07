import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Code2, Mail, Lock, User, UserCircle,ArrowRight, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function AuthPage() {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [form, setForm] = useState({ name: '', username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'login') {
        await login({ email: form.email, password: form.password });
      } else {
        await register(form);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="auth-card card"
      >
        {/* Brand */}
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>
            <div style={{
              width: 56, height: 56, borderRadius: 14,
              background: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 24px rgba(139,92,246,0.45)'
            }}>
              <Code2 size={28} color="white" />
            </div>
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 6 }}>
            Codebase Intelligence
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
            {mode === 'login' ? 'Sign in to your workspace' : 'Create your workspace'}
          </p>
        </div>

        {/* Toggle */}
        <div style={{ display: 'flex', background: 'var(--bg-tertiary)', borderRadius: 10, padding: 4, marginBottom: 24 }}>
          {['login', 'register'].map(m => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(''); }}
              style={{
                flex: 1, padding: '10px', border: 'none', borderRadius: 8, cursor: 'pointer',
                background: mode === m ? 'var(--accent)' : 'transparent',
                color: mode === m ? 'white' : 'var(--text-secondary)',
                fontWeight: 600, fontSize: '0.9rem',
                transition: 'all 0.2s ease'
              }}
            >
              {m === 'login' ? 'Sign In' : 'Register'}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.form
            key={mode}
            initial={{ opacity: 0, x: mode === 'login' ? -20 : 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            onSubmit={handleSubmit}
          >
            {mode === 'register' && (
              <>
                <InputField icon={<UserCircle size={16} />} placeholder="Full Name" value={form.name}
                  onChange={v => setForm(f => ({ ...f, name: v }))} />
                <InputField icon={<User size={16} />} placeholder="Username" value={form.username}
                  onChange={v => setForm(f => ({ ...f, username: v }))} />
              </>
            )}
            <InputField icon={<Mail size={16} />} placeholder="Email Address" type="email"
              value={form.email} onChange={v => setForm(f => ({ ...f, email: v }))} />
            <InputField icon={<Lock size={16} />} placeholder="Password" type="password"
              value={form.password} onChange={v => setForm(f => ({ ...f, password: v }))} />

            {error && (
              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                style={{ color: 'var(--danger)', fontSize: '0.875rem', marginBottom: 16,
                  background: 'rgba(239,68,68,0.1)', padding: '10px 14px', borderRadius: 8,
                  border: '1px solid rgba(239,68,68,0.2)' }}
              >
                {error}
              </motion.div>
            )}

            <button type="submit" className="btn" style={{ width: '100%', marginTop: 8 }} disabled={loading}>
              {loading ? <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} /> : (
                <>{mode === 'login' ? 'Sign In' : 'Create Account'} <ArrowRight size={16} /></>
              )}
            </button>
          </motion.form>
        </AnimatePresence>
      </motion.div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function InputField({ icon, placeholder, type = 'text', value, onChange }) {
  return (
    <div style={{ position: 'relative', marginBottom: 14 }}>
      <div style={{
        position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
        color: 'var(--text-muted)', pointerEvents: 'none'
      }}>
        {icon}
      </div>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        required
        onChange={e => onChange(e.target.value)}
        className="form-input"
        style={{ paddingLeft: 40, width: '100%' }}
      />
    </div>
  );
}
