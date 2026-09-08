import React, { useEffect, useState } from 'react';
import { Activity, CheckCircle2, AlertCircle, RefreshCw, Terminal, Layers, Code2 } from 'lucide-react';
import api from '../services/api';
import Card from '../components/common/Card';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';

export const AppInitView = () => {
  const [healthStatus, setHealthStatus] = useState({
    loading: true,
    data: null,
    error: null,
  });

  const checkBackendHealth = async () => {
    setHealthStatus({ loading: true, data: null, error: null });
    try {
      const response = await api.get('/health');
      setHealthStatus({ loading: false, data: response.data, error: null });
    } catch (err) {
      setHealthStatus({
        loading: false,
        data: null,
        error: err.message || 'Failed to connect to backend proxy',
      });
    }
  };

  useEffect(() => {
    checkBackendHealth();
  }, []);

  return (
    <div className="container" style={{ padding: 'var(--space-8) var(--space-4)' }}>
      <div style={{ maxWidth: '720px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
        
        {/* Foundation Header Card */}
        <Card style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
          <div style={{ display: 'inline-flex', padding: 'var(--space-3)', borderRadius: 'var(--radius-xl)', backgroundColor: 'var(--accent-primary-subtle)', marginBottom: 'var(--space-4)' }}>
            <Activity size={36} color="var(--accent-primary)" />
          </div>
          <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: '700', marginBottom: 'var(--space-2)' }}>
            DevTrack React Frontend Initialized
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginBottom: 'var(--space-6)' }}>
            Task 15.1 — React 19 + Vite + Vanilla CSS design tokens + API Client proxy established.
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            <Badge variant="primary">React 19 SPA</Badge>
            <Badge variant="success">Vite 6 Bundler</Badge>
            <Badge variant="primary">Design Tokens Active</Badge>
            <Badge variant="success">Proxy Configured (:3000 &rarr; :8000)</Badge>
          </div>
        </Card>

        {/* Backend Connectivity Status Card */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Terminal size={18} color="var(--accent-primary)" />
              <h2 style={{ fontSize: 'var(--text-base)', fontWeight: '600' }}>Backend API Proxy Verification</h2>
            </div>
            <Button variant="ghost" onClick={checkBackendHealth} disabled={healthStatus.loading} style={{ padding: '0.25rem 0.5rem' }}>
              <RefreshCw size={14} style={{ animation: healthStatus.loading ? 'spin 1s linear infinite' : 'none' }} />
              <span style={{ fontSize: 'var(--text-xs)' }}>Refresh</span>
            </Button>
          </div>

          <div style={{ padding: 'var(--space-4)', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-2)' }}>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Target: GET /api/v1/health</span>
              {healthStatus.loading && <Badge variant="warning">Connecting...</Badge>}
              {healthStatus.data && (
                <Badge variant="success">
                  <CheckCircle2 size={12} /> Connected
                </Badge>
              )}
              {healthStatus.error && (
                <Badge variant="error">
                  <AlertCircle size={12} /> Disconnected
                </Badge>
              )}
            </div>

            {healthStatus.data && (
              <pre style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--color-success)', margin: 0, overflowX: 'auto' }}>
                {JSON.stringify(healthStatus.data, null, 2)}
              </pre>
            )}

            {healthStatus.error && (
              <p style={{ color: 'var(--color-error)', fontSize: 'var(--text-xs)', margin: 0 }}>
                {healthStatus.error}
              </p>
            )}
          </div>
        </Card>

        {/* Foundation Modules Status Card */}
        <Card>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
            <Layers size={18} color="var(--accent-violet)" />
            <h2 style={{ fontSize: 'var(--text-base)', fontWeight: '600' }}>Frontend Architecture Modules</h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-3)' }}>
            <div style={{ padding: 'var(--space-3)', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--bg-surface-elevated)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-1)' }}>
                <Code2 size={14} color="var(--color-success)" />
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: '500' }}>API Client</span>
              </div>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', margin: 0 }}>Axios with Bearer token interceptor</p>
            </div>

            <div style={{ padding: 'var(--space-3)', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--bg-surface-elevated)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-1)' }}>
                <Code2 size={14} color="var(--color-success)" />
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: '500' }}>Auth Context</span>
              </div>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', margin: 0 }}>Global JWT state & localStorage</p>
            </div>

            <div style={{ padding: 'var(--space-3)', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--bg-surface-elevated)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-1)' }}>
                <Code2 size={14} color="var(--color-success)" />
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: '500' }}>Common UI</span>
              </div>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', margin: 0 }}>Button, Card, Badge primitives</p>
            </div>
          </div>
        </Card>

      </div>
    </div>
  );
};

export default AppInitView;
