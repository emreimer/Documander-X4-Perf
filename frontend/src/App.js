import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import AdminPage from './pages/AdminPage';
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
  const [isAdminPage, setIsAdminPage] = useState(false);

  useEffect(() => {
    // Check if this is admin page
    const isAdmin = window.location.pathname === '/admin';
    setIsAdminPage(isAdmin);
    
    // Admin page has its own key-based auth, allow access
    if (isAdmin) {
      setIsAllowed(true);
      return;
    }
    
    // Check if running inside iframe from allowed domain
    const checkAccess = () => {
      // Development/Preview mode bypass
      const hostname = window.location.hostname;
      const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
      const isPreview = hostname.includes('preview.emergentagent.com') || hostname.includes('preview.emergent');
      
      if (isLocalhost || isPreview) {
        setIsAllowed(true);
        return;
      }
      
      // Production: Check if inside iframe from allowed domain
      const isInIframe = window.self !== window.top;
      
      if (!isInIframe) {
        // Direct access - not allowed in production
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
        const referrer = document.referrer.toLowerCase();
        const allowedDomains = ['documander.com', 'wix.com', 'wixsite.com', 'editorx.io'];
        setIsAllowed(allowedDomains.some(domain => referrer.includes(domain)));
      }
    };

    checkAccess();
  }, []);

  // Loading state
  if (isAllowed === null) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>Yükleniyor...</div>;
  }

  // Access denied (not for admin page)
  if (!isAllowed && !isAdminPage) {
    return <AccessDenied />;
  }

  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </>
  );
}

export default App;
