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
  Eye,
  Mail,
  User,
  Calendar,
  CreditCard,
  ChevronDown,
  ChevronUp,
  Search,
  Trash2
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
  const [expandedUsers, setExpandedUsers] = useState({});
  const [searchTerm, setSearchTerm] = useState('');
  const [stats, setStats] = useState({ total: 0, active: 0, expired: 0, exhausted: 0 });
  const [deleteConfirm, setDeleteConfirm] = useState(null); // 'all' or wix_member_id

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

  const toggleUserExpand = (userId) => {
    setExpandedUsers(prev => ({
      ...prev,
      [userId]: !prev[userId]
    }));
  };

  const filteredUsers = users.filter(user => {
    if (!searchTerm) return true;
    const search = searchTerm.toLowerCase();
    return (
      (user.full_name && user.full_name.toLowerCase().includes(search)) ||
      (user.email && user.email.toLowerCase().includes(search)) ||
      (user.wix_member_id && user.wix_member_id.toLowerCase().includes(search))
    );
  });

  const exportToExcel = () => {
    // CSV export with user info
    const headers = ['Ad Soyad', 'Email', 'Wix Member ID', 'Paketler', 'Toplam Kalan', 'Durum', 'Kayıt Tarihi'];
    const rows = filteredUsers.map(user => [
      user.full_name || '-',
      user.email || '-',
      user.wix_member_id,
      user.packages.map(p => `${p.plan_name} (${p.remaining_quota}/${p.total_quota})`).join('; '),
      user.total_remaining === -1 ? 'Sınırsız' : user.total_remaining,
      user.is_active ? 'Aktif' : (user.is_quota_exhausted ? 'Kota Doldu' : 'Süresi Doldu'),
      formatDate(user.created_at)
    ]);
    
    const csv = [headers, ...rows].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `documander_users_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const deleteUser = async (wixMemberId) => {
    try {
      await axios.delete(`${API}/admin/user/${wixMemberId}?key=${adminKey}`);
      setDeleteConfirm(null);
      fetchUsers(filter);
    } catch (err) {
      setError(err.response?.data?.detail || 'Kullanıcı silinemedi');
    }
  };

  const deleteAllUsers = async () => {
    try {
      await axios.delete(`${API}/admin/users/all?key=${adminKey}`);
      setDeleteConfirm(null);
      fetchUsers(filter);
    } catch (err) {
      setError(err.response?.data?.detail || 'Kullanıcılar silinemedi');
    }
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
          {/* Search */}
          <div className="flex items-center gap-2 flex-1 min-w-[200px]">
            <Search className="w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Ad, email veya ID ara..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="p-2 border border-border bg-background text-foreground flex-1"
            />
          </div>
          
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

        {/* Users List - Card Style */}
        <div className="space-y-4">
          {filteredUsers.length === 0 && !loading && (
            <div className="bg-card border border-border p-8 text-center text-muted-foreground">
              Kullanıcı bulunamadı
            </div>
          )}
          
          {filteredUsers.map((user, idx) => (
            <div key={idx} className="bg-card border border-border">
              {/* User Header - Always Visible */}
              <div 
                className="p-4 flex items-center justify-between cursor-pointer hover:bg-muted/10"
                onClick={() => toggleUserExpand(user.wix_member_id)}
              >
                <div className="flex items-center gap-4 flex-1">
                  {/* User Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <User className="w-4 h-4 text-muted-foreground" />
                      <span className="font-semibold truncate">
                        {user.full_name || 'İsimsiz Kullanıcı'}
                      </span>
                      {user.is_active ? (
                        <span className="inline-flex items-center gap-1 text-xs bg-green-500/10 text-green-700 px-2 py-0.5">
                          <CheckCircle2 className="w-3 h-3" /> Aktif
                        </span>
                      ) : user.is_quota_exhausted ? (
                        <span className="inline-flex items-center gap-1 text-xs bg-yellow-500/10 text-yellow-700 px-2 py-0.5">
                          <AlertTriangle className="w-3 h-3" /> Kota Doldu
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs bg-destructive/10 text-destructive px-2 py-0.5">
                          <XCircle className="w-3 h-3" /> Süresi Doldu
                        </span>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      {user.email && (
                        <span className="flex items-center gap-1">
                          <Mail className="w-3 h-3" />
                          {user.email}
                        </span>
                      )}
                      <span className="text-xs font-mono bg-muted px-1">
                        {user.wix_member_id?.substring(0, 12)}...
                      </span>
                    </div>
                  </div>
                  
                  {/* Quick Stats */}
                  <div className="flex items-center gap-6 text-sm">
                    <div className="text-center">
                      <p className="text-muted-foreground text-xs">Paket Sayısı</p>
                      <p className="font-bold">{user.packages.length}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-muted-foreground text-xs">Toplam Kota</p>
                      <p className={`font-bold ${
                        user.total_remaining === -1 ? 'text-primary' :
                        user.total_remaining === 0 ? 'text-destructive' :
                        user.total_remaining < 50 ? 'text-yellow-600' : ''
                      }`}>
                        {user.total_remaining === -1 ? '∞' : user.total_remaining}
                      </p>
                    </div>
                  </div>
                </div>
                
                {/* Expand Icon */}
                <div className="ml-4">
                  {expandedUsers[user.wix_member_id] ? (
                    <ChevronUp className="w-5 h-5 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-muted-foreground" />
                  )}
                </div>
              </div>
              
              {/* Expanded Content - Packages */}
              {expandedUsers[user.wix_member_id] && (
                <div className="border-t border-border p-4 bg-muted/5">
                  <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                    <Package className="w-4 h-4" />
                    Paketler ({user.packages.length})
                  </h4>
                  
                  <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                    {user.packages.map((pkg, pidx) => (
                      <div 
                        key={pidx} 
                        className={`p-3 border ${
                          pkg.is_active 
                            ? 'bg-green-500/5 border-green-500/30' 
                            : pkg.is_exhausted 
                              ? 'bg-yellow-500/5 border-yellow-500/30'
                              : 'bg-destructive/5 border-destructive/30'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-semibold">{pkg.plan_name}</span>
                          {pkg.is_active ? (
                            <span className="text-[10px] bg-green-500/20 text-green-700 px-1.5 py-0.5">AKTİF</span>
                          ) : pkg.is_exhausted ? (
                            <span className="text-[10px] bg-yellow-500/20 text-yellow-700 px-1.5 py-0.5">KOTA DOLDU</span>
                          ) : (
                            <span className="text-[10px] bg-destructive/20 text-destructive px-1.5 py-0.5">SÜRESİ DOLDU</span>
                          )}
                        </div>
                        
                        <div className="space-y-1 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="text-muted-foreground">Kullanım:</span>
                            <span>{pkg.used_quota} / {pkg.total_quota === -1 ? '∞' : pkg.total_quota}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-muted-foreground">Kalan:</span>
                            <span className={`font-semibold ${
                              pkg.remaining_quota === 0 ? 'text-destructive' : 
                              pkg.remaining_quota < 50 ? 'text-yellow-600' : 'text-green-600'
                            }`}>
                              {pkg.remaining_quota === -1 ? '∞' : pkg.remaining_quota}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="text-muted-foreground">Bitiş:</span>
                            <span>{formatDate(pkg.end_date)}</span>
                          </div>
                        </div>
                        
                        {/* Progress bar */}
                        {pkg.total_quota !== -1 && (
                          <div className="mt-2 h-1.5 bg-muted rounded-full overflow-hidden">
                            <div 
                              className={`h-full ${
                                pkg.is_exhausted ? 'bg-destructive' : 
                                (pkg.used_quota / pkg.total_quota) > 0.8 ? 'bg-yellow-500' : 'bg-primary'
                              }`}
                              style={{ width: `${Math.min(100, (pkg.used_quota / pkg.total_quota) * 100)}%` }}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  
                  {/* User Meta */}
                  <div className="mt-4 pt-3 border-t border-border flex items-center gap-6 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      Kayıt: {formatDate(user.created_at)}
                    </span>
                    <span>
                      Son Güncelleme: {formatDate(user.updated_at)}
                    </span>
                    <span className="font-mono">
                      ID: {user.wix_member_id}
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
