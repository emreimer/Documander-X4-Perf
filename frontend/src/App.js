import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import { Toaster } from './components/ui/sonner';
import './App.css';

// Access denied component
const AccessDenied = () => (
  <div style={{
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    fontFamily: 'system-ui, sans-serif',
    backgroundColor: '#f8f9fa',
    color: '#333'
  }}>
    <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>Erişim Engellendi</h1>
    <p style={{ color: '#666' }}>Bu uygulama sadece documander.com üzerinden erişilebilir.</p>
  </div>
);

function App() {
  const [isAllowed, setIsAllowed] = useState(null);

  useEffect(() => {
    // TEMPORARILY DISABLED - Allow all access for testing
    // TODO: Re-enable before production
    setIsAllowed(true);
    return;

    /* ORIGINAL CODE - UNCOMMENT FOR PRODUCTION
    // Check if running inside iframe from allowed domain
    const checkAccess = () => {
      // Allow localhost for development
      if (window.location.hostname === 'localhost') {
        setIsAllowed(true);
        return;
      }

      // Check if inside iframe
      const isInIframe = window.self !== window.top;
      
      if (!isInIframe) {
        // Direct access - not allowed
        setIsAllowed(false);
        return;
      }

      // Inside iframe - check referrer
      try {
        const referrer = document.referrer.toLowerCase();
        const allowedDomains = [
          'documander.com',
          'wix.com',
          'wixsite.com',
          'editorx.io'
        ];
        const isAllowedDomain = allowedDomains.some(domain => referrer.includes(domain));
        setIsAllowed(isAllowedDomain);
      } catch (e) {
        // Cross-origin iframe - check if referrer contains allowed domain
        const referrer = document.referrer.toLowerCase();
        const allowedDomains = ['documander.com', 'wix.com', 'wixsite.com', 'editorx.io'];
        setIsAllowed(allowedDomains.some(domain => referrer.includes(domain)));
      }
    };

    checkAccess();
    */
  }, []);

  // Loading state
  if (isAllowed === null) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>Yükleniyor...</div>;
  }

  // Access denied
  if (!isAllowed) {
    return <AccessDenied />;
  }

  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </>
  );
}

export default App;
