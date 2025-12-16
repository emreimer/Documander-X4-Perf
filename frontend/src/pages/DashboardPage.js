import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Upload, LogOut, Download, Pencil, Trash2, FileText } from 'lucide-react';
import UploadModal from '../components/UploadModal';
import EditModal from '../components/EditModal';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DashboardPage = ({ setIsAuthenticated }) => {
  const [incomeInvoices, setIncomeInvoices] = useState([]);
  const [expenseInvoices, setExpenseInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadCategory, setUploadCategory] = useState('income');
  const [editingInvoice, setEditingInvoice] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    }
    fetchInvoices();
  }, []);

  const getAuthHeader = () => {
    const token = localStorage.getItem('token');
    return { Authorization: `Bearer ${token}` };
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

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    toast.success('Çıkış başarılı');
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

  const handleExport = async () => {
    try {
      const response = await axios.get(`${API}/invoices/export/excel`, {
        headers: getAuthHeader(),
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'faturalar.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Excel dosyası indirildi');
    } catch (error) {
      toast.error('Excel dışa aktarma başarısız');
    }
  };

  return (
    <div className="min-h-screen" data-testid="dashboard-page">
      {/* Header */}
      <header className="border-b border-border bg-card shadow-sm">
        <div className="px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="w-7 h-7 text-primary" strokeWidth={1.5} />
            <div>
              <h1 className="text-2xl font-heading font-bold tracking-tight">
                Fatura Yönetim
              </h1>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">
                {user?.full_name}
              </p>
            </div>
          </div>
          <Button
            onClick={handleLogout}
            variant="outline"
            className="rounded-none gap-2"
            data-testid="logout-button"
          >
            <LogOut className="w-4 h-4" />
            Çıkış
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-8 py-8">
        {/* Action Bar */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-3xl font-heading font-semibold tracking-tight mb-1">
              Faturalar
            </h2>
            <p className="text-sm text-muted-foreground">
              Toplam {invoices.length} fatura
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              onClick={handleExport}
              disabled={invoices.length === 0}
              variant="outline"
              className="rounded-none gap-2 uppercase tracking-wide"
              data-testid="export-excel-button"
            >
              <Download className="w-4 h-4" />
              Excel İndir
            </Button>
            <Button
              onClick={() => setShowUploadModal(true)}
              className="rounded-none gap-2 uppercase tracking-wide"
              data-testid="upload-invoice-button"
            >
              <Upload className="w-4 h-4" />
              Fatura Yükle
            </Button>
          </div>
        </div>

        {/* Invoices Table */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-lg font-mono text-muted-foreground">Yükleniyor...</div>
          </div>
        ) : invoices.length === 0 ? (
          <div className="bg-card border border-border p-12 text-center">
            <FileText className="w-16 h-16 text-muted mx-auto mb-4" strokeWidth={1} />
            <h3 className="text-xl font-heading font-semibold mb-2">Henüz fatura yok</h3>
            <p className="text-muted-foreground mb-6">Başlamak için ilk faturanızı yükleyin</p>
            <Button
              onClick={() => setShowUploadModal(true)}
              className="rounded-none gap-2 uppercase tracking-wide"
              data-testid="upload-first-invoice-button"
            >
              <Upload className="w-4 h-4" />
              Fatura Yükle
            </Button>
          </div>
        ) : (
          <div className="bg-card border border-border shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full" data-testid="invoices-table">
                <thead className="bg-muted/20 border-b border-border">
                  <tr>
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      Fatura No
                    </th>
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      Tarih
                    </th>
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      Düzenleyen
                    </th>
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      D. VKN
                    </th>
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      D. V.Dairesi
                    </th>
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      Müşteri
                    </th>
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      M. VKN
                    </th>
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      M. V.Dairesi
                    </th>
                    <th className="px-2 py-3 text-left text-xs uppercase tracking-wider text-muted-foreground font-medium">
                      İçerik
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
                      <td className="px-2 py-3 text-xs">{invoice.issuer_name}</td>
                      <td className="px-2 py-3 font-mono text-xs">{invoice.issuer_tax_id}</td>
                      <td className="px-2 py-3 text-xs">{invoice.issuer_tax_office}</td>
                      <td className="px-2 py-3 text-xs">{invoice.customer_name}</td>
                      <td className="px-2 py-3 font-mono text-xs">{invoice.customer_tax_id}</td>
                      <td className="px-2 py-3 text-xs">{invoice.customer_tax_office}</td>
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
              </table>
            </div>
          </div>
        )}
      </main>

      {/* Modals */}
      {showUploadModal && (
        <UploadModal
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
