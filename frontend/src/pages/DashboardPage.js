import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Upload, Download, Pencil, Trash2, RotateCcw, Calendar, Building2, FileText } from 'lucide-react';
import UploadModal from '../components/UploadModal.js';
import EditModal from '../components/EditModal.js';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const MONTH_NAMES = {
  1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 5: 'Mayıs', 6: 'Haziran',
  7: 'Temmuz', 8: 'Ağustos', 9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
};

const DashboardPage = () => {
  const [incomeInvoices, setIncomeInvoices] = useState([]);
  const [expenseInvoices, setExpenseInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadCategory, setUploadCategory] = useState('income');
  const [editingInvoice, setEditingInvoice] = useState(null);
  const [user, setUser] = useState(null);
  
  // Session state
  const [session, setSession] = useState(null);
  const [showSessionForm, setShowSessionForm] = useState(false);
  const [taxpayerName, setTaxpayerName] = useState('');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  
  // Subscription state
  const [subscription, setSubscription] = useState(null);
  const [showPlansModal, setShowPlansModal] = useState(false);
  const [plans, setPlans] = useState([]);

  const getVisitorId = () => {
    let visitorId = localStorage.getItem('documander_visitor_id');
    if (!visitorId) {
      visitorId = 'visitor_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
      localStorage.setItem('documander_visitor_id', visitorId);
    }
    return visitorId;
  };

  const getAuthHeader = () => {
    const visitorId = getVisitorId();
    return { 'X-Visitor-ID': visitorId };
  };

  useEffect(() => {
    const visitorId = getVisitorId();
    console.log('Dashboard loaded with Visitor ID:', visitorId);
    setUser({ visitorId });
    fetchSession();
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    if (session) {
      fetchInvoices();
    }
    // eslint-disable-next-line
  }, [session]);

  const fetchSession = async () => {
    try {
      const response = await axios.get(`${API}/sessions/current`, {
        headers: getAuthHeader()
      });
      if (response.data) {
        setSession(response.data);
        setTaxpayerName(response.data.taxpayer_name);
        setSelectedYear(response.data.year);
        setSelectedMonth(response.data.month);
      } else {
        setShowSessionForm(true);
        setLoading(false);
      }
    } catch (error) {
      setShowSessionForm(true);
      setLoading(false);
    }
  };

  const createSession = async () => {
    if (!taxpayerName.trim()) {
      toast.error('Mükellef adı giriniz');
      return;
    }
    try {
      const response = await axios.post(`${API}/sessions`, {
        taxpayer_name: taxpayerName.trim(),
        year: selectedYear,
        month: selectedMonth
      }, { headers: getAuthHeader() });
      setSession(response.data);
      setShowSessionForm(false);
      toast.success('İşlem dönemi oluşturuldu');
    } catch (error) {
      toast.error('Dönem oluşturulamadı');
    }
  };

  const changeSession = () => {
    setShowSessionForm(true);
  };

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      
      // Fetch income invoices
      const incomeResponse = await axios.get(`${API}/invoices?category=income`, {
        headers: getAuthHeader()
      });
      setIncomeInvoices(incomeResponse.data);
      
      // Fetch expense invoices
      const expenseResponse = await axios.get(`${API}/invoices?category=expense`, {
        headers: getAuthHeader()
      });
      setExpenseInvoices(expenseResponse.data);
    } catch (error) {
      toast.error('Faturalar yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (invoiceId) => {
    if (!window.confirm('Bu faturayı silmek istediğinizden emin misiniz?')) {
      return;
    }

    try {
      await axios.delete(`${API}/invoices/${invoiceId}`, {
        headers: getAuthHeader()
      });
      toast.success('Fatura silindi');
      fetchInvoices();
    } catch (error) {
      toast.error('Fatura silinemedi');
    }
  };

  const handleExport = async (category = null) => {
    try {
      const url = category 
        ? `${API}/invoices/export/excel?category=${category}`
        : `${API}/invoices/export/excel`;
      
      const headers = getAuthHeader();
      console.log('Export headers:', headers);
      console.log('Export URL:', url);
      
      const response = await axios.get(url, {
        headers: headers,
        responseType: 'blob'
      });
      
      // Get filename from response headers or generate default
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'faturalar.xlsx';
      if (contentDisposition) {
        // Try RFC 5987 format first: filename*=UTF-8''encoded_name
        const rfc5987Match = contentDisposition.match(/filename\*=UTF-8''(.+)/);
        if (rfc5987Match) {
          filename = decodeURIComponent(rfc5987Match[1]);
        } else {
          // Fallback to simple format: filename=name
          const simpleMatch = contentDisposition.match(/filename=(.+)/);
          if (simpleMatch) filename = simpleMatch[1];
        }
      }
      
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Excel dosyası indirildi');
    } catch (error) {
      console.error('Excel export error:', error);
      console.error('Error response:', error.response);
      
      if (error.response?.status === 404) {
        toast.error('İndirilecek fatura bulunamadı');
      } else {
        const errorMsg = error.response?.data?.detail || error.message || 'Bilinmeyen hata';
        toast.error(`Excel dışa aktarma başarısız: ${errorMsg}`);
      }
    }
  };

  const handleResetAll = async () => {
    if (!window.confirm('Tüm faturaları silmek istediğinizden emin misiniz? Bu işlem geri alınamaz!')) {
      return;
    }

    try {
      await axios.delete(`${API}/invoices`, {
        headers: getAuthHeader()
      });
      toast.success('Tüm faturalar silindi');
      fetchInvoices();
    } catch (error) {
      toast.error('Faturalar silinemedi');
    }
  };

  const openUploadModal = (category) => {
    setUploadCategory(category);
    setShowUploadModal(true);
  };

  const InvoiceTable = ({ invoices, type }) => {
    const title = type === 'income' ? 'Gelir Faturaları' : 'Gider Faturaları';
    const emptyMessage = type === 'income' ? 'gelir faturası' : 'gider faturası';
    
    return (
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-heading font-semibold tracking-tight">{title}</h2>
          <div className="flex gap-2">
            {invoices.length > 0 && (
              <Button
                onClick={() => handleExport(type)}
                variant="outline"
                className="rounded-none gap-2 uppercase tracking-wide"
                data-testid={`export-${type}-button`}
              >
                <Download className="w-4 h-4" />
                {type === 'income' ? 'Gelir Excel' : 'Gider Excel'}
              </Button>
            )}
            <Button
              onClick={() => openUploadModal(type)}
              className="rounded-none gap-2 uppercase tracking-wide"
              data-testid={`upload-${type}-button`}
            >
              <Upload className="w-4 h-4" />
              {type === 'income' ? 'Gelir Yükle' : 'Gider Yükle'}
            </Button>
          </div>
        </div>

        {invoices.length === 0 ? (
          <div className="bg-card border border-border p-8 text-center">
            <FileText className="w-12 h-12 text-muted mx-auto mb-3" strokeWidth={1} />
            <p className="text-muted-foreground">Henüz {emptyMessage} yok</p>
          </div>
        ) : (
          <div className="bg-card border border-border shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full" data-testid={`${type}-invoices-table`}>
                <thead className="bg-muted/20 border-b border-border">
                  <tr>
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      Fatura No
                    </th>
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      Tarih
                    </th>
                    {type === 'income' ? (
                      <>
                        <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                          Müşteri
                        </th>
                        <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                          M. VKN
                        </th>
                        <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                          M. V.Dairesi
                        </th>
                      </>
                    ) : (
                      <>
                        <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                          Düzenleyen
                        </th>
                        <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                          D. VKN
                        </th>
                        <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                          D. V.Dairesi
                        </th>
                      </>
                    )}
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      Açıklama
                    </th>
                    <th className="px-2 py-3 text-right text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      Net
                    </th>
                    <th className="px-2 py-3 text-right text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      KDV
                    </th>
                    <th className="px-2 py-3 text-right text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      Toplam
                    </th>
                    <th className="px-2 py-3 text-center text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      İşlem
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {invoices.map((invoice) => (
                    <tr
                      key={invoice.id}
                      className="hover:bg-muted/30 transition-colors"
                      data-testid={`invoice-row-${invoice.id}`}
                    >
                      <td className="px-2 py-3 font-mono text-xs">{invoice.invoice_number}</td>
                      <td className="px-2 py-3 font-mono text-xs">{invoice.date}</td>
                      {type === 'income' ? (
                        <>
                          <td className="px-2 py-3 text-xs">{invoice.customer_name}</td>
                          <td className="px-2 py-3 font-mono text-xs">{invoice.customer_tax_id}</td>
                          <td className="px-2 py-3 text-xs">{invoice.customer_tax_office}</td>
                        </>
                      ) : (
                        <>
                          <td className="px-2 py-3 text-xs">{invoice.issuer_name}</td>
                          <td className="px-2 py-3 font-mono text-xs">{invoice.issuer_tax_id}</td>
                          <td className="px-2 py-3 text-xs">{invoice.issuer_tax_office}</td>
                        </>
                      )}
                      <td className="px-2 py-3 text-xs max-w-xs truncate" title={invoice.description}>
                        {invoice.description}
                      </td>
                      <td className="px-2 py-3 font-mono text-xs text-right">
                        {invoice.amount.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺
                      </td>
                      <td className="px-2 py-3 font-mono text-xs text-right">
                        {invoice.vat.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺
                      </td>
                      <td className="px-2 py-3 font-mono text-xs text-right font-semibold">
                        {invoice.total.toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺
                      </td>
                      <td className="px-2 py-3">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => setEditingInvoice(invoice)}
                            className="text-primary hover:text-primary/80 p-1"
                            data-testid={`edit-invoice-${invoice.id}`}
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(invoice.id)}
                            className="text-destructive hover:text-destructive/80 p-1"
                            data-testid={`delete-invoice-${invoice.id}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-muted/10 border-t-2 border-border">
                  <tr>
                    <td colSpan={type === 'income' ? 6 : 6} className="px-2 py-3 text-right font-semibold text-sm uppercase tracking-wider">
                      Toplam:
                    </td>
                    <td className="px-2 py-3 font-mono text-xs text-right font-bold">
                      {invoices.reduce((sum, inv) => sum + inv.amount, 0).toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺
                    </td>
                    <td className="px-2 py-3 font-mono text-xs text-right font-bold">
                      {invoices.reduce((sum, inv) => sum + inv.vat, 0).toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺
                    </td>
                    <td className="px-2 py-3 font-mono text-xs text-right font-bold">
                      {invoices.reduce((sum, inv) => sum + inv.total, 0).toLocaleString('tr-TR', { minimumFractionDigits: 2 })} ₺
                    </td>
                    <td className="px-2 py-3"></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen" data-testid="dashboard-page">
      {/* Session Form Modal */}
      {showSessionForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card border border-border p-8 max-w-md w-full mx-4 shadow-lg">
            <div className="flex items-center gap-3 mb-6">
              <Building2 className="w-6 h-6 text-primary" />
              <h2 className="text-xl font-heading font-semibold">İşlem Dönemi Seçin</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 uppercase tracking-wider">Mükellef Adı</label>
                <input
                  type="text"
                  value={taxpayerName}
                  onChange={(e) => setTaxpayerName(e.target.value)}
                  placeholder="Firma veya şahıs adı"
                  className="w-full px-4 py-3 border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                  autoFocus
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2 uppercase tracking-wider">Yıl</label>
                  <select
                    value={selectedYear}
                    onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                    className="w-full px-4 py-3 border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    {[2023, 2024, 2025, 2026].map(year => (
                      <option key={year} value={year}>{year}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2 uppercase tracking-wider">Ay</label>
                  <select
                    value={selectedMonth}
                    onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
                    className="w-full px-4 py-3 border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    {Object.entries(MONTH_NAMES).map(([num, name]) => (
                      <option key={num} value={num}>{name}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div className="flex gap-3 pt-4">
                {session && (
                  <Button
                    onClick={() => setShowSessionForm(false)}
                    variant="outline"
                    className="flex-1 rounded-none"
                  >
                    İptal
                  </Button>
                )}
                <Button
                  onClick={createSession}
                  className="flex-1 rounded-none"
                >
                  {session ? 'Yeni Dönem Başlat' : 'Başla'}
                </Button>
              </div>
              
              {session && (
                <p className="text-xs text-muted-foreground text-center">
                  Yeni dönem başlatıldığında mevcut faturalar silinecektir
                </p>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Header */}
      <header className="border-b border-border bg-card shadow-sm">
        <div className="px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img src="/logo.png" alt="Documander" className="h-10" />
            <div className="border-l border-border pl-4">
              <h1 className="text-xl font-heading font-bold tracking-tight">
                {session ? `${session.taxpayer_name}` : 'Fatura Yönetim'}
              </h1>
              <p className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                {session && (
                  <>
                    <Calendar className="w-3 h-3" />
                    {MONTH_NAMES[session.month]} {session.year}
                  </>
                )}
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <Button
              onClick={changeSession}
              variant="outline"
              className="rounded-none gap-2 uppercase tracking-wide"
              data-testid="change-session-button"
            >
              <Calendar className="w-4 h-4" />
              Dönem Değiştir
            </Button>
            <Button
              onClick={() => handleExport()}
              disabled={incomeInvoices.length === 0 && expenseInvoices.length === 0 || !session}
              variant="outline"
              className="rounded-none gap-2 uppercase tracking-wide"
              data-testid="export-excel-button"
            >
              <Download className="w-4 h-4" />
              Tümünü Excel İndir
            </Button>
            <Button
              onClick={handleResetAll}
              disabled={incomeInvoices.length === 0 && expenseInvoices.length === 0}
              variant="outline"
              className="rounded-none gap-2 uppercase tracking-wide text-destructive border-destructive hover:bg-destructive hover:text-white"
              data-testid="reset-all-button"
            >
              <RotateCcw className="w-4 h-4" />
              Tabloları Sıfırla
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-8 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-lg font-mono text-muted-foreground">Yükleniyor...</div>
          </div>
        ) : (
          <>
            <InvoiceTable invoices={incomeInvoices} type="income" />
            <InvoiceTable invoices={expenseInvoices} type="expense" />
          </>
        )}
      </main>

      {/* Modals */}
      {showUploadModal && (
        <UploadModal
          category={uploadCategory}
          onClose={() => setShowUploadModal(false)}
          onSuccess={fetchInvoices}
        />
      )}

      {editingInvoice && (
        <EditModal
          invoice={editingInvoice}
          onClose={() => setEditingInvoice(null)}
          onSuccess={fetchInvoices}
        />
      )}
    </div>
  );
};

export default DashboardPage;
