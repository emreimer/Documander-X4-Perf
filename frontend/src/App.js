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
    
    // TEMPORARILY DISABLED: Domain check for preview testing
    // To re-enable production domain restriction, uncomment the block below
    // and remove the setIsAllowed(true) line
    setIsAllowed(true);
    return;
    
    /* PRODUCTION DOMAIN CHECK - DISABLED FOR PREVIEW
    // Admin page has its own key-based auth, allow access
    if (isAdmin) {
      setIsAllowed(true);
      return;
    }
    
    // Check if running inside iframe from allowed domain
    const checkAccess = () => {
      // Development mode bypass - check for localhost
      const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      if (isLocalhost) {
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
