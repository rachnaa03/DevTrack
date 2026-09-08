import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import AppInitView from './pages/AppInitView';
import logo from './assets/logo.svg';
import './App.css';

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="app-shell">
          <header className="app-header">
            <div className="container app-header-content">
              <a href="/" className="app-brand">
                <img src={logo} alt="DevTrack Logo" className="app-brand-logo" />
              </a>
              <div className="app-header-status">
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                  Task 15.1 Foundation Active
                </span>
              </div>
            </div>
          </header>

          <main className="app-main">
            <Routes>
              <Route path="/" element={<AppInitView />} />
            </Routes>
          </main>

          <footer className="app-footer">
            <div className="container">
              DevTrack &copy; {new Date().getFullYear()} — Unified Developer Analytics Platform
            </div>
          </footer>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
