import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Upload, LogOut, Download, Pencil, Trash2, FileText, RotateCcw } from 'lucide-react';
import UploadModal from '../components/UploadModal.js';
import EditModal from '../components/EditModal.js';

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
          <Button
            onClick={() => openUploadModal(type)}
            className="rounded-none gap-2 uppercase tracking-wide"
            data-testid={`upload-${type}-button`}
          >
            <Upload className="w-4 h-4" />
            {type === 'income' ? 'Gelir Faturaları Yükle' : 'Gider Faturaları Yükle'}
          </Button>
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
          <div className="flex gap-3">
            <Button
              onClick={handleExport}
              disabled={incomeInvoices.length === 0 && expenseInvoices.length === 0}
              variant="outline"
              className="rounded-none gap-2 uppercase tracking-wide"
              data-testid="export-excel-button"
            >
              <Download className="w-4 h-4" />
              Excel İndir
            </Button>
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
