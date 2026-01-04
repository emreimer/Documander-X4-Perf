import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { 
  Users, 
  Package, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle,
  RefreshCw,
  Download,
  Filter,
  Eye
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminPage = () => {
  const [adminKey, setAdminKey] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');
  const [selectedUser, setSelectedUser] = useState(null);
  const [stats, setStats] = useState({ total: 0, active: 0, expired: 0, exhausted: 0 });

  const fetchUsers = async (filterType = 'all') => {
    setLoading(true);
    setError('');
    try {
      const filterParam = filterType !== 'all' ? `&filter=${filterType}` : '';
      const response = await axios.get(`${API}/admin/users?key=${adminKey}${filterParam}`);
      setUsers(response.data.users);
      
      // Calculate stats from all users
      if (filterType === 'all') {
        const allUsers = response.data.users;
        setStats({
          total: allUsers.length,
          active: allUsers.filter(u => u.is_active).length,
          expired: allUsers.filter(u => !u.is_active).length,
          exhausted: allUsers.filter(u => u.is_quota_exhausted).length
        });
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Veriler alınamadı');
      if (err.response?.status === 403) {
        setIsAuthenticated(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!adminKey.trim()) return;
    
    setLoading(true);
    try {
      await axios.get(`${API}/admin/users?key=${adminKey}`);
      setIsAuthenticated(true);
      fetchUsers();
    } catch (err) {
      setError('Geçersiz admin anahtarı');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('tr-TR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  const exportToExcel = () => {
    // Simple CSV export
    const headers = ['Wix Member ID', 'Paketler', 'Toplam Kalan', 'Durum', 'Kayıt Tarihi'];
    const rows = users.map(user => [
      user.wix_member_id,
      user.packages.map(p => `${p.plan_name} (${p.remaining_quota}/${p.total_quota})`).join('; '),
      user.total_remaining === -1 ? 'Sınırsız' : user.total_remaining,
      user.is_active ? 'Aktif' : (user.is_quota_exhausted ? 'Kota Doldu' : 'Süresi Doldu'),
      formatDate(user.created_at)
    ]);
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `documander_users_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  // Login Screen
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="bg-card border border-border p-8 max-w-md w-full">
          <h1 className="text-2xl font-heading font-bold mb-6 text-center">
            Documander Admin
          </h1>
          
          <form onSubmit={handleLogin}>
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Admin Anahtarı</label>
              <input
                type="password"
                value={adminKey}
                onChange={(e) => setAdminKey(e.target.value)}
                className="w-full p-3 border border-border bg-background text-foreground"
                placeholder="Gizli anahtarınızı girin"
              />
            </div>
            
            {error && (
              <div className="mb-4 p-3 bg-destructive/10 border border-destructive/30 text-destructive text-sm">
                {error}
              </div>
            )}
            
            <Button 
              type="submit" 
              className="w-full rounded-none"
              disabled={loading}
            >
              {loading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
            </Button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-border p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-heading font-bold">Documander Admin Panel</h1>
          <Button 
            variant="outline" 
            className="rounded-none"
            onClick={() => setIsAuthenticated(false)}
          >
            Çıkış
          </Button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-card border border-border p-4">
            <div className="flex items-center gap-3">
              <Users className="w-8 h-8 text-primary" />
              <div>
                <p className="text-2xl font-bold">{stats.total}</p>
                <p className="text-sm text-muted-foreground">Toplam Kullanıcı</p>
              </div>
            </div>
          </div>
          
          <div className="bg-card border border-border p-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-8 h-8 text-green-500" />
              <div>
                <p className="text-2xl font-bold">{stats.active}</p>
                <p className="text-sm text-muted-foreground">Aktif</p>
              </div>
            </div>
          </div>
          
          <div className="bg-card border border-border p-4">
            <div className="flex items-center gap-3">
              <XCircle className="w-8 h-8 text-destructive" />
              <div>
                <p className="text-2xl font-bold">{stats.expired}</p>
                <p className="text-sm text-muted-foreground">Süresi Dolmuş</p>
              </div>
            </div>
          </div>
          
          <div className="bg-card border border-border p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-8 h-8 text-yellow-500" />
              <div>
                <p className="text-2xl font-bold">{stats.exhausted}</p>
                <p className="text-sm text-muted-foreground">Kotası Dolmuş</p>
              </div>
            </div>
          </div>
        </div>

        {/* Actions Bar */}
        <div className="bg-card border border-border p-4 mb-6 flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4" />
            <select 
              value={filter}
              onChange={(e) => { setFilter(e.target.value); fetchUsers(e.target.value); }}
              className="p-2 border border-border bg-background text-foreground"
            >
              <option value="all">Tümü</option>
              <option value="active">Aktif</option>
              <option value="expired">Süresi Dolmuş</option>
              <option value="quota_exhausted">Kotası Dolmuş</option>
            </select>
          </div>
          
          <Button 
            variant="outline" 
            className="rounded-none"
            onClick={() => fetchUsers(filter)}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Yenile
          </Button>
          
          <Button 
            variant="outline" 
            className="rounded-none"
            onClick={exportToExcel}
          >
            <Download className="w-4 h-4 mr-2" />
            Excel İndir
          </Button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-destructive/10 border border-destructive/30 text-destructive">
            {error}
          </div>
        )}

        {/* Users Table */}
        <div className="bg-card border border-border overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/30 border-b border-border">
              <tr>
                <th className="text-left p-4 font-medium">Wix Member ID</th>
                <th className="text-left p-4 font-medium">Paketler</th>
                <th className="text-left p-4 font-medium">Kalan Kota</th>
                <th className="text-left p-4 font-medium">Durum</th>
                <th className="text-left p-4 font-medium">Kayıt</th>
                <th className="text-left p-4 font-medium">İşlem</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 && !loading && (
                <tr>
                  <td colSpan="6" className="p-8 text-center text-muted-foreground">
                    Kullanıcı bulunamadı
                  </td>
                </tr>
              )}
              
              {users.map((user, idx) => (
                <tr key={idx} className="border-b border-border hover:bg-muted/10">
                  <td className="p-4">
                    <code className="text-xs bg-muted px-2 py-1">
                      {user.wix_member_id || user.user_id}
                    </code>
                  </td>
                  <td className="p-4">
                    <div className="space-y-1">
                      {user.packages.map((pkg, pidx) => (
                        <div key={pidx} className={`text-xs p-2 border ${
                          pkg.is_active 
                            ? 'bg-green-500/10 border-green-500/30' 
                            : pkg.is_exhausted 
                              ? 'bg-yellow-500/10 border-yellow-500/30'
                              : 'bg-destructive/10 border-destructive/30'
                        }`}>
                          <div className="font-medium">{pkg.plan_name}</div>
                          <div className="text-muted-foreground">
                            {pkg.total_quota === -1 
                              ? 'Sınırsız' 
                              : `${pkg.used_quota}/${pkg.total_quota} kullanıldı`}
                          </div>
                          <div className="text-muted-foreground">
                            Bitiş: {formatDate(pkg.end_date)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </td>
                  <td className="p-4">
                    <span className={`font-bold ${
                      user.total_remaining === -1 
                        ? 'text-primary' 
                        : user.total_remaining === 0 
                          ? 'text-destructive' 
                          : user.total_remaining < 50 
                            ? 'text-yellow-600' 
                            : ''
                    }`}>
                      {user.total_remaining === -1 ? 'Sınırsız' : user.total_remaining}
                    </span>
                  </td>
                  <td className="p-4">
                    {user.is_active ? (
                      <span className="inline-flex items-center gap-1 text-xs bg-green-500/10 text-green-700 px-2 py-1">
                        <CheckCircle2 className="w-3 h-3" /> Aktif
                      </span>
                    ) : user.is_quota_exhausted ? (
                      <span className="inline-flex items-center gap-1 text-xs bg-yellow-500/10 text-yellow-700 px-2 py-1">
                        <AlertTriangle className="w-3 h-3" /> Kota Doldu
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs bg-destructive/10 text-destructive px-2 py-1">
                        <XCircle className="w-3 h-3" /> Süresi Doldu
                      </span>
                    )}
                  </td>
                  <td className="p-4 text-sm text-muted-foreground">
                    {formatDate(user.created_at)}
                  </td>
                  <td className="p-4">
                    <Button 
                      variant="ghost" 
                      size="sm"
                      className="rounded-none"
                      onClick={() => setSelectedUser(user)}
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* User Detail Modal */}
        {selectedUser && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-card border border-border max-w-2xl w-full max-h-[80vh] overflow-y-auto">
              <div className="p-4 border-b border-border flex items-center justify-between">
                <h3 className="font-heading font-bold">Kullanıcı Detayı</h3>
                <button onClick={() => setSelectedUser(null)} className="text-muted-foreground hover:text-foreground">
                  ✕
                </button>
              </div>
              <div className="p-4 space-y-4">
                <div>
                  <label className="text-sm text-muted-foreground">Wix Member ID</label>
                  <p className="font-mono">{selectedUser.wix_member_id || selectedUser.user_id}</p>
                </div>
                
                <div>
                  <label className="text-sm text-muted-foreground">Toplam Kalan Kota</label>
                  <p className="text-2xl font-bold">
                    {selectedUser.total_remaining === -1 ? 'Sınırsız' : selectedUser.total_remaining}
                  </p>
                </div>
                
                <div>
                  <label className="text-sm text-muted-foreground">Paketler</label>
                  <div className="space-y-2 mt-2">
                    {selectedUser.packages.map((pkg, idx) => (
                      <div key={idx} className={`p-3 border ${
                        pkg.is_active 
                          ? 'border-green-500/30 bg-green-500/5' 
                          : 'border-border'
                      }`}>
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium">{pkg.plan_name}</p>
                            <p className="text-sm text-muted-foreground">
                              Kullanım: {pkg.used_quota} / {pkg.total_quota === -1 ? '∞' : pkg.total_quota}
                            </p>
                          </div>
                          <div className="text-right text-sm">
                            <p>Bitiş: {formatDate(pkg.end_date)}</p>
                            <p className={pkg.is_active ? 'text-green-600' : 'text-destructive'}>
                              {pkg.is_active ? 'Aktif' : pkg.is_exhausted ? 'Kota Doldu' : 'Süresi Doldu'}
                            </p>
                          </div>
                        </div>
                        {/* Progress bar */}
                        {pkg.total_quota !== -1 && (
                          <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
                            <div 
                              className={`h-full ${pkg.is_exhausted ? 'bg-destructive' : 'bg-primary'}`}
                              style={{ width: `${Math.min(100, (pkg.used_quota / pkg.total_quota) * 100)}%` }}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <label className="text-muted-foreground">Kayıt Tarihi</label>
                    <p>{formatDate(selectedUser.created_at)}</p>
                  </div>
                  <div>
                    <label className="text-muted-foreground">Son Güncelleme</label>
                    <p>{formatDate(selectedUser.updated_at)}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPage;
