import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Upload, Download, Pencil, Trash2, RotateCcw, Calendar, Building2, FileText, CreditCard, Zap, X, Check, Receipt, ArrowLeft } from 'lucide-react';
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
  
  // View state: 'invoices' or 'vat-report'
  const [currentView, setCurrentView] = useState('invoices');
  const [vatReport, setVatReport] = useState(null);
  const [vatReportLoading, setVatReportLoading] = useState(false);
  
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

  // Get Wix Member ID and plan info from URL
  const getWixMemberId = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const wixMemberId = urlParams.get('wixMemberId') || urlParams.get('memberId');
    
    if (wixMemberId) {
      localStorage.setItem('documander_wix_member_id', wixMemberId);
      
      // Also store plan info if present
      const plan = urlParams.get('plan');
      const expires = urlParams.get('expires');
      if (plan) localStorage.setItem('documander_wix_plan', plan);
      if (expires) localStorage.setItem('documander_wix_expires', expires);
      
      return wixMemberId;
    }
    
    const storedWixId = localStorage.getItem('documander_wix_member_id');
    if (storedWixId) {
      return storedWixId;
    }
    
    return null;
  };
  
  // Get Wix plan info from URL or storage
  const getWixPlanInfo = () => {
    const urlParams = new URLSearchParams(window.location.search);
    return {
      plan: urlParams.get('plan') || localStorage.getItem('documander_wix_plan') || null,
      expires: urlParams.get('expires') || localStorage.getItem('documander_wix_expires') || null
    };
  };

  const getVisitorId = () => {
    let visitorId = localStorage.getItem('documander_visitor_id');
    if (!visitorId) {
      visitorId = 'visitor_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
      localStorage.setItem('documander_visitor_id', visitorId);
    }
    return visitorId;
  };

  const getAuthHeader = () => {
    const wixMemberId = getWixMemberId();
    const visitorId = getVisitorId();
    const planInfo = getWixPlanInfo();
    
    const headers = { 'X-Visitor-ID': visitorId };
    
    if (wixMemberId) {
      headers['X-Wix-Member-ID'] = wixMemberId;
    }
    if (planInfo.plan) {
      headers['X-Wix-Plan'] = planInfo.plan;
    }
    if (planInfo.expires) {
      headers['X-Wix-Expires'] = planInfo.expires;
    }
    
    return headers;
  };

  useEffect(() => {
    const visitorId = getVisitorId();
    // Dashboard loaded
    setUser({ visitorId });
    fetchSession();
    fetchSubscription();
    fetchPlans();
    // eslint-disable-next-line
  }, []);
  
  const fetchSubscription = async () => {
    try {
      const response = await axios.get(`${API}/subscription/status`, {
        headers: getAuthHeader()
      });
      setSubscription(response.data);
    } catch (error) {
      // Subscription fetch error
    }
  };
  
  const fetchPlans = async () => {
    try {
      const response = await axios.get(`${API}/subscription/plans`);
      setPlans(response.data.plans);
    } catch (error) {
      // Plans fetch error
    }
  };

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

  // Listen for show plans modal event from UploadModal
  useEffect(() => {
    const handleShowPlans = () => setShowPlansModal(true);
    window.addEventListener('showPlansModal', handleShowPlans);
    return () => window.removeEventListener('showPlansModal', handleShowPlans);
  }, []);

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

  // Fetch VAT Report
  const fetchVatReport = async () => {
    setVatReportLoading(true);
    try {
      const response = await axios.get(`${API}/invoices/vat-report`, {
        headers: getAuthHeader()
      });
      setVatReport(response.data);
    } catch (error) {
      toast.error('KDV raporu yüklenemedi');
    } finally {
      setVatReportLoading(false);
    }
  };

  // Switch to VAT Report view
  const showVatReport = () => {
    setCurrentView('vat-report');
    fetchVatReport();
  };

  // Switch back to Invoices view
  const showInvoices = () => {
    setCurrentView('invoices');
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
      // Export request
      
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
      // Excel export error
      
      if (error.response?.status === 404) {
        toast.error('İndirilecek fatura bulunamadı');
      } else {
        const errorMsg = error.response?.data?.detail || error.message || 'Bilinmeyen hata';
        toast.error(`Excel dışa aktarma başarısız: ${errorMsg}`);
      }
    }
  };

  // VAT Report Excel export
  const handleVatExport = async (category = null) => {
    try {
      let url = `${API}/invoices/vat-report/excel`;
      if (category) {
        url += `?category=${category}`;
      }
      
      const headers = getAuthHeader();
      const response = await axios.get(url, {
        headers: headers,
        responseType: 'blob'
      });
      
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'kdv_raporu.xlsx';
      if (contentDisposition) {
        const rfc5987Match = contentDisposition.match(/filename\*=UTF-8''(.+)/);
        if (rfc5987Match) {
          filename = decodeURIComponent(rfc5987Match[1]);
        } else {
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
      
      toast.success('KDV Raporu Excel dosyası indirildi');
    } catch (error) {
      if (error.response?.status === 404) {
        toast.error('KDV verisi bulunamadı');
      } else {
        const errorMsg = error.response?.data?.detail || error.message || 'Bilinmeyen hata';
        toast.error(`KDV Excel dışa aktarma başarısız: ${errorMsg}`);
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

  // VAT Report View Component
  const VatReportView = () => {
    if (vatReportLoading) {
      return (
        <div className="flex items-center justify-center py-12">
          <div className="text-lg font-mono text-muted-foreground">KDV Raporu yükleniyor...</div>
        </div>
      );
    }

    if (!vatReport) {
      return (
        <div className="bg-card border border-border p-8 text-center">
          <p className="text-muted-foreground">KDV raporu yüklenemedi.</p>
        </div>
      );
    }

    const { items, summary, grand_total } = vatReport;

    // Separate items by category
    const incomeItems = items.filter(item => item.category === 'income');
    const expenseItems = items.filter(item => item.category === 'expense');

    // Calculate separate summaries for income and expense
    const calculateCategorySummary = (categoryItems) => {
      const summaryData = { 0: { base: 0, vat: 0 }, 1: { base: 0, vat: 0 }, 10: { base: 0, vat: 0 }, 20: { base: 0, vat: 0 } };
      categoryItems.forEach(item => {
        const rate = item.vat_rate;
        if (summaryData[rate] !== undefined) {
          summaryData[rate].base += item.base_amount || 0;
          summaryData[rate].vat += item.vat_amount || 0;
        }
      });
      return summaryData;
    };

    const incomeSummary = calculateCategorySummary(incomeItems);
    const expenseSummary = calculateCategorySummary(expenseItems);

    // Format currency
    const formatCurrency = (amount) => {
      return new Intl.NumberFormat('tr-TR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }).format(amount || 0);
    };

    // Income VAT Detail Table Component
    const IncomeVatTable = () => (
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-heading font-semibold tracking-tight flex items-center gap-2">
            <span className="w-3 h-3 bg-green-500 rounded-full"></span>
            KDV Detay Tablosu - Gelir
          </h2>
          {incomeItems.length > 0 && (
            <Button
              onClick={() => handleVatExport('income')}
              variant="outline"
              size="sm"
              className="rounded-none gap-2 text-xs"
              data-testid="vat-income-excel-button"
            >
              <Download className="w-3 h-3" />
              Excel İndir
            </Button>
          )}
        </div>
        
        {incomeItems.length === 0 ? (
          <div className="bg-card border border-border p-8 text-center">
            <p className="text-muted-foreground">Bu dönemde gelir KDV kaydı bulunmuyor.</p>
          </div>
        ) : (
          <div className="bg-card border border-border overflow-x-auto">
            <table className="w-full" data-testid="vat-income-table">
              <thead className="bg-green-500/10 border-b border-border">
                <tr>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">Fatura No</th>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">Tarih</th>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">Müşteri</th>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">M. VKN</th>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">M. V.Dairesi</th>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">Açıklama</th>
                  <th className="text-center p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">KDV %</th>
                  <th className="text-right p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">Matrah</th>
                  <th className="text-right p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">KDV Tutarı</th>
                </tr>
              </thead>
              <tbody>
                {incomeItems.map((item, idx) => (
                  <tr key={idx} className="border-b border-border/50 hover:bg-muted/20">
                    <td className="p-2 text-xs font-mono">{item.invoice_number}</td>
                    <td className="p-2 text-xs font-mono">{item.date}</td>
                    <td className="p-2 text-xs">{item.customer_name || '-'}</td>
                    <td className="p-2 text-xs font-mono">{item.customer_tax_id || '-'}</td>
                    <td className="p-2 text-xs">{item.customer_tax_office || '-'}</td>
                    <td className="p-2 text-xs text-muted-foreground max-w-xs truncate" title={item.description}>{item.description}</td>
                    <td className="p-2 text-center">
                      <span className="font-semibold text-primary">%{item.vat_rate}</span>
                    </td>
                    <td className="p-2 text-right font-mono text-xs">{formatCurrency(item.base_amount)} ₺</td>
                    <td className="p-2 text-right font-mono text-xs font-semibold">{formatCurrency(item.vat_amount)} ₺</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-green-500/5 border-t-2 border-green-500/30">
                <tr>
                  <td colSpan={6} className="p-2 text-right font-semibold text-sm uppercase tracking-wider">Gelir Toplamı:</td>
                  <td className="p-2"></td>
                  <td className="p-2 text-right font-mono text-xs font-bold">
                    {formatCurrency(incomeItems.reduce((sum, item) => sum + (item.base_amount || 0), 0))} ₺
                  </td>
                  <td className="p-2 text-right font-mono text-xs font-bold text-green-700">
                    {formatCurrency(incomeItems.reduce((sum, item) => sum + (item.vat_amount || 0), 0))} ₺
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>
    );

    // Expense VAT Detail Table Component
    const ExpenseVatTable = () => (
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-heading font-semibold tracking-tight flex items-center gap-2">
            <span className="w-3 h-3 bg-red-500 rounded-full"></span>
            KDV Detay Tablosu - Gider
          </h2>
          {expenseItems.length > 0 && (
            <Button
              onClick={() => handleVatExport('expense')}
              variant="outline"
              size="sm"
              className="rounded-none gap-2 text-xs"
              data-testid="vat-expense-excel-button"
            >
              <Download className="w-3 h-3" />
              Excel İndir
            </Button>
          )}
        </div>
        
        {expenseItems.length === 0 ? (
          <div className="bg-card border border-border p-8 text-center">
            <p className="text-muted-foreground">Bu dönemde gider KDV kaydı bulunmuyor.</p>
          </div>
        ) : (
          <div className="bg-card border border-border overflow-x-auto">
            <table className="w-full" data-testid="vat-expense-table">
              <thead className="bg-red-500/10 border-b border-border">
                <tr>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">Fatura No</th>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">Tarih</th>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">Düzenleyen</th>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">D. VKN</th>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">D. V.Dairesi</th>
                  <th className="text-left p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">Açıklama</th>
                  <th className="text-center p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">KDV %</th>
                  <th className="text-right p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">Matrah</th>
                  <th className="text-right p-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">KDV Tutarı</th>
                </tr>
              </thead>
              <tbody>
                {expenseItems.map((item, idx) => (
                  <tr key={idx} className="border-b border-border/50 hover:bg-muted/20">
                    <td className="p-2 text-xs font-mono">{item.invoice_number}</td>
                    <td className="p-2 text-xs font-mono">{item.date}</td>
                    <td className="p-2 text-xs">{item.issuer_name || '-'}</td>
                    <td className="p-2 text-xs font-mono">{item.issuer_tax_id || '-'}</td>
                    <td className="p-2 text-xs">{item.issuer_tax_office || '-'}</td>
                    <td className="p-2 text-xs text-muted-foreground max-w-xs truncate" title={item.description}>{item.description}</td>
                    <td className="p-2 text-center">
                      <span className="font-semibold text-primary">%{item.vat_rate}</span>
                    </td>
                    <td className="p-2 text-right font-mono text-xs">{formatCurrency(item.base_amount)} ₺</td>
                    <td className="p-2 text-right font-mono text-xs font-semibold">{formatCurrency(item.vat_amount)} ₺</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-red-500/5 border-t-2 border-red-500/30">
                <tr>
                  <td colSpan={6} className="p-2 text-right font-semibold text-sm uppercase tracking-wider">Gider Toplamı:</td>
                  <td className="p-2"></td>
                  <td className="p-2 text-right font-mono text-xs font-bold">
                    {formatCurrency(expenseItems.reduce((sum, item) => sum + (item.base_amount || 0), 0))} ₺
                  </td>
                  <td className="p-2 text-right font-mono text-xs font-bold text-red-700">
                    {formatCurrency(expenseItems.reduce((sum, item) => sum + (item.vat_amount || 0), 0))} ₺
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>
    );

    // KDV Summary Tables - 3 separate tables
    const VatSummaryTables = () => {
      const incomeTotal = { base: 0, vat: 0 };
      const expenseTotal = { base: 0, vat: 0 };
      
      [1, 10, 20].forEach(rate => {
        incomeTotal.base += incomeSummary[rate].base;
        incomeTotal.vat += incomeSummary[rate].vat;
        expenseTotal.base += expenseSummary[rate].base;
        expenseTotal.vat += expenseSummary[rate].vat;
      });

      const netVat = incomeTotal.vat - expenseTotal.vat;

      // Get period info from session
      const periodText = session ? `${MONTH_NAMES[session.month]} ${session.year}` : '';

      return (
        <div className="space-y-8">
          {/* 1. KDV Özet Raporu - Gelir */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-heading font-semibold tracking-tight flex items-center gap-2">
                <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                KDV Özet Raporu - Gelir
              </h2>
              <Button
                onClick={() => handleVatExport('summary-income')}
                variant="outline"
                size="sm"
                className="rounded-none gap-1 text-xs"
                data-testid="vat-summary-income-excel"
              >
                <Download className="w-3 h-3" />
                Excel İndir
              </Button>
            </div>
            
            <div className="bg-card border border-border overflow-x-auto">
              <table className="w-full" data-testid="vat-summary-income-table">
                <thead className="bg-green-500/10 border-b border-border">
                  <tr>
                    <th className="text-left p-3 text-xs uppercase tracking-wider text-muted-foreground font-medium">KDV Oranı</th>
                    <th className="text-right p-3 text-xs uppercase tracking-wider text-muted-foreground font-medium">Matrah</th>
                    <th className="text-right p-3 text-xs uppercase tracking-wider text-green-700 font-medium">KDV Tutarı</th>
                  </tr>
                </thead>
                <tbody>
                  {[0, 1, 10, 20].map((rate) => (
                    <tr key={rate} className="border-b border-border/50">
                      <td className="p-3">
                        <span className="text-lg font-semibold text-primary">%{rate}</span>
                      </td>
                      <td className="p-3 text-right font-mono text-sm">{formatCurrency(incomeSummary[rate].base)} ₺</td>
                      <td className="p-3 text-right font-mono text-sm font-semibold text-green-700">{formatCurrency(incomeSummary[rate].vat)} ₺</td>
                    </tr>
                  ))}
                  <tr className="bg-green-500/5 border-t-2 border-green-500/30">
                    <td className="p-3">
                      <span className="text-lg font-bold">TOPLAM</span>
                    </td>
                    <td className="p-3 text-right font-mono text-sm font-bold">{formatCurrency(incomeTotal.base)} ₺</td>
                    <td className="p-3 text-right font-mono text-lg font-bold text-green-700">{formatCurrency(incomeTotal.vat)} ₺</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* 2. KDV Özet Raporu - Gider */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-heading font-semibold tracking-tight flex items-center gap-2">
                <span className="w-3 h-3 bg-red-500 rounded-full"></span>
                KDV Özet Raporu - Gider
              </h2>
              <Button
                onClick={() => handleVatExport('summary-expense')}
                variant="outline"
                size="sm"
                className="rounded-none gap-1 text-xs"
                data-testid="vat-summary-expense-excel"
              >
                <Download className="w-3 h-3" />
                Excel İndir
              </Button>
            </div>
            
            <div className="bg-card border border-border overflow-x-auto">
              <table className="w-full" data-testid="vat-summary-expense-table">
                <thead className="bg-red-500/10 border-b border-border">
                  <tr>
                    <th className="text-left p-3 text-xs uppercase tracking-wider text-muted-foreground font-medium">KDV Oranı</th>
                    <th className="text-right p-3 text-xs uppercase tracking-wider text-muted-foreground font-medium">Matrah</th>
                    <th className="text-right p-3 text-xs uppercase tracking-wider text-red-700 font-medium">KDV Tutarı</th>
                  </tr>
                </thead>
                <tbody>
                  {[0, 1, 10, 20].map((rate) => (
                    <tr key={rate} className="border-b border-border/50">
                      <td className="p-3">
                        <span className="text-lg font-semibold text-primary">%{rate}</span>
                      </td>
                      <td className="p-3 text-right font-mono text-sm">{formatCurrency(expenseSummary[rate].base)} ₺</td>
                      <td className="p-3 text-right font-mono text-sm font-semibold text-red-700">{formatCurrency(expenseSummary[rate].vat)} ₺</td>
                    </tr>
                  ))}
                  <tr className="bg-red-500/5 border-t-2 border-red-500/30">
                    <td className="p-3">
                      <span className="text-lg font-bold">TOPLAM</span>
                    </td>
                    <td className="p-3 text-right font-mono text-sm font-bold">{formatCurrency(expenseTotal.base)} ₺</td>
                    <td className="p-3 text-right font-mono text-lg font-bold text-red-700">{formatCurrency(expenseTotal.vat)} ₺</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* 3. KDV Özet Raporu - Net (Dönem) */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-heading font-semibold tracking-tight flex items-center gap-2">
                <span className="w-3 h-3 bg-primary rounded-full"></span>
                KDV Özet Raporu - {periodText} Dönemi Net
              </h2>
              <Button
                onClick={() => handleVatExport('summary-net')}
                variant="outline"
                size="sm"
                className="rounded-none gap-1 text-xs"
                data-testid="vat-summary-net-excel"
              >
                <Download className="w-3 h-3" />
                Excel İndir
              </Button>
            </div>
            
            <div className="bg-card border border-border overflow-x-auto">
              <table className="w-full" data-testid="vat-summary-net-table">
                <thead className="bg-primary/10 border-b border-border">
                  <tr>
                    <th className="text-left p-3 text-xs uppercase tracking-wider text-muted-foreground font-medium">KDV Oranı</th>
                    <th className="text-right p-3 text-xs uppercase tracking-wider text-green-700 font-medium">Hesaplanan KDV (Gelir)</th>
                    <th className="text-right p-3 text-xs uppercase tracking-wider text-red-700 font-medium">İndirilecek KDV (Gider)</th>
                    <th className="text-right p-3 text-xs uppercase tracking-wider text-primary font-medium">Net KDV</th>
                  </tr>
                </thead>
                <tbody>
                  {[1, 10, 20].map((rate) => {
                    const rateNetVat = incomeSummary[rate].vat - expenseSummary[rate].vat;
                    return (
                      <tr key={rate} className="border-b border-border/50">
                        <td className="p-3">
                          <span className="text-lg font-semibold text-primary">%{rate}</span>
                        </td>
                        <td className="p-3 text-right font-mono text-sm text-green-700">{formatCurrency(incomeSummary[rate].vat)} ₺</td>
                        <td className="p-3 text-right font-mono text-sm text-red-700">{formatCurrency(expenseSummary[rate].vat)} ₺</td>
                        <td className={`p-3 text-right font-mono text-sm font-bold ${rateNetVat >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                          {rateNetVat >= 0 ? '' : '-'}{formatCurrency(Math.abs(rateNetVat))} ₺
                        </td>
                      </tr>
                    );
                  })}
                  <tr className="bg-primary/5 border-t-2 border-primary">
                    <td className="p-3">
                      <span className="text-lg font-bold">TOPLAM</span>
                    </td>
                    <td className="p-3 text-right font-mono text-sm font-bold text-green-700">{formatCurrency(incomeTotal.vat)} ₺</td>
                    <td className="p-3 text-right font-mono text-sm font-bold text-red-700">{formatCurrency(expenseTotal.vat)} ₺</td>
                    <td className={`p-3 text-right font-mono text-lg font-bold ${netVat >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                      {netVat >= 0 ? '' : '-'}{formatCurrency(Math.abs(netVat))} ₺
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            {/* Net KDV Summary Box */}
            <div className="mt-4 p-6 bg-card border-2 border-primary/30">
              <div className="text-center mb-4">
                <p className="text-sm text-muted-foreground uppercase tracking-wider">{periodText} Dönemi Sonucu</p>
              </div>
              <div className="flex items-center justify-center gap-6">
                <div className="text-center">
                  <p className="text-xs text-muted-foreground uppercase">Hesaplanan KDV</p>
                  <p className="text-2xl font-bold text-green-700">{formatCurrency(incomeTotal.vat)} ₺</p>
                </div>
                <span className="text-3xl text-muted-foreground font-light">−</span>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground uppercase">İndirilecek KDV</p>
                  <p className="text-2xl font-bold text-red-700">{formatCurrency(expenseTotal.vat)} ₺</p>
                </div>
                <span className="text-3xl text-muted-foreground font-light">=</span>
                <div className="text-center px-6 py-2 bg-primary/5 border border-primary/20">
                  <p className="text-xs text-muted-foreground uppercase">
                    {netVat >= 0 ? 'Ödenecek KDV' : 'Sonraki Aya Devreden KDV'}
                  </p>
                  <p className={`text-3xl font-bold ${netVat >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                    {netVat >= 0 ? '' : '-'}{formatCurrency(Math.abs(netVat))} ₺
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    };

    return (
      <div className="space-y-8">
        <IncomeVatTable />
        <ExpenseVatTable />
        <VatSummaryTables />
      </div>
    );
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

  // Format date for display
  const formatDate = (isoDate) => {
    if (!isoDate) return null;
    try {
      const date = new Date(isoDate);
      return date.toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });
    } catch {
      return null;
    }
  };

  // Quota badge component
  const QuotaBadge = () => {
    if (!subscription) return null;
    
    const { plan_name, remaining, total_limit, monthly_limit, is_unlimited, is_trial, expires_at, is_expired, is_quota_exhausted, days_remaining, has_multi_packages, packages, total_remaining } = subscription;
    
    // Use total_limit if available, fallback to monthly_limit for backward compatibility
    const limit = total_limit || monthly_limit;
    
    if (is_unlimited) {
      return (
        <div 
          className="flex items-center gap-3 px-4 py-2 bg-primary/10 border border-primary/20 cursor-pointer hover:bg-primary/15 transition-colors"
          onClick={() => setShowPlansModal(true)}
          title="Plan detayları için tıklayın"
        >
          <Zap className="w-5 h-5 text-primary" />
          <div className="flex flex-col">
            <span className="font-semibold text-sm">{plan_name} Plan</span>
            <span className="text-xs text-muted-foreground">Sınırsız fatura hakkı</span>
          </div>
        </div>
      );
    }
    
    // Multi-package display
    if (has_multi_packages && packages && packages.length > 0) {
      const activePackages = packages.filter(p => p.is_active);
      const totalRem = total_remaining || remaining;
      const isLow = totalRem <= 10 && totalRem > 0;
      
      // Format short date for packages
      const formatShortDate = (dateStr) => {
        if (!dateStr) return '';
        try {
          const date = new Date(dateStr);
          return date.toLocaleDateString('tr-TR', { day: '2-digit', month: '2-digit', year: 'numeric' });
        } catch {
          return '';
        }
      };
      
      return (
        <div 
          className={`flex items-center gap-3 px-4 py-2 border cursor-pointer transition-colors ${
            is_quota_exhausted ? 'bg-destructive/10 border-destructive/30' : 
            isLow ? 'bg-yellow-500/10 border-yellow-500/30' : 
            'bg-muted/30 border-border hover:bg-muted/50'
          }`}
          onClick={() => setShowPlansModal(true)}
          title="Paket detayları için tıklayın"
        >
          <CreditCard className={`w-5 h-5 ${is_quota_exhausted ? 'text-destructive' : isLow ? 'text-yellow-600' : 'text-primary'}`} />
          <div className="flex flex-col text-xs gap-1">
            {/* Packages with dates */}
            {activePackages.slice(0, 3).map((pkg, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className="bg-primary/10 text-primary px-1.5 py-0.5 text-[10px] font-medium">
                  {pkg.plan_name}
                </span>
                <span className="text-muted-foreground">
                  {pkg.remaining_quota} kalan
                </span>
                <span className="text-muted-foreground">•</span>
                <span className="text-muted-foreground">
                  {formatShortDate(pkg.end_date)}'e kadar
                </span>
              </div>
            ))}
            {activePackages.length > 3 && (
              <span className="text-muted-foreground text-[10px]">+{activePackages.length - 3} paket daha</span>
            )}
            
            {/* Total remaining */}
            <div className="flex items-center gap-2 mt-1 pt-1 border-t border-border/50">
              <span className="text-muted-foreground font-medium">Toplam:</span>
              <span className={`font-bold ${is_quota_exhausted ? 'text-destructive' : isLow ? 'text-yellow-600' : 'text-primary'}`}>
                {totalRem} fatura
              </span>
              {is_quota_exhausted && (
                <span className="text-[10px] bg-destructive text-destructive-foreground px-1.5 py-0.5 font-medium">KOTA DOLDU</span>
              )}
            </div>
          </div>
        </div>
      );
    }
    
    // Single package (legacy) display
    const isLow = remaining <= 5 && remaining > 0;
    const expiryWarning = days_remaining !== null && days_remaining <= 30 && !is_trial;
    const trialExpiryWarning = days_remaining !== null && days_remaining <= 3 && is_trial;
    
    // Determine badge color based on status
    const getBadgeStyle = () => {
      if (is_expired || is_quota_exhausted) return 'bg-destructive/10 border-destructive/30';
      if (expiryWarning || trialExpiryWarning || isLow) return 'bg-yellow-500/10 border-yellow-500/30';
      return 'bg-muted/30 border-border hover:bg-muted/50';
    };
    
    return (
      <div 
        className={`flex items-center gap-3 px-4 py-2 border cursor-pointer transition-colors ${getBadgeStyle()}`}
        onClick={() => setShowPlansModal(true)}
        title="Plan detayları için tıklayın"
      >
        <CreditCard className={`w-5 h-5 ${is_expired || is_quota_exhausted ? 'text-destructive' : (expiryWarning || trialExpiryWarning || isLow) ? 'text-yellow-600' : 'text-primary'}`} />
        <div className="flex flex-col text-xs">
          {/* Paket Türü */}
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Paket:</span>
            <span className="font-semibold">{plan_name}</span>
            {is_expired && (
              <span className="text-[10px] bg-destructive text-destructive-foreground px-1.5 py-0.5 font-medium">SÜRESİ DOLDU</span>
            )}
            {is_quota_exhausted && !is_expired && (
              <span className="text-[10px] bg-destructive text-destructive-foreground px-1.5 py-0.5 font-medium">KOTA DOLDU</span>
            )}
          </div>
          
          {/* Bitiş Tarihi - for both trial and annual plans */}
          {expires_at && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">{is_trial ? 'Deneme Bitiş:' : 'Plan Bitiş:'}</span>
              <span className={((expiryWarning || trialExpiryWarning) && !is_expired) ? 'text-yellow-600 font-semibold' : ''}>
                {formatDate(expires_at)}
                {days_remaining !== null && !is_expired && days_remaining <= 30 && ` (${days_remaining} gün)`}
              </span>
            </div>
          )}
          
          {/* Kalan Kota */}
          {!is_expired && !is_quota_exhausted && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Kalan Kota:</span>
              <span className={isLow ? 'text-yellow-600 font-semibold' : ''}>
                {remaining} / {limit} fatura
              </span>
            </div>
          )}
          
          {/* Quota exhausted message */}
          {is_quota_exhausted && !is_expired && (
            <div className="text-destructive text-[10px] mt-1">
              Yeni paket satın alın
            </div>
          )}
        </div>
      </div>
    );
  };

  // Plans Modal Component
  const PlansModal = () => {
    if (!showPlansModal) return null;
    
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div className="bg-card border border-border shadow-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="border-b border-border p-4 flex items-center justify-between bg-muted/20">
            <div>
              <h2 className="text-xl font-heading font-semibold">Abonelik Planları</h2>
              <p className="text-sm text-muted-foreground">İhtiyacınıza uygun planı seçin</p>
            </div>
            <button onClick={() => setShowPlansModal(false)} className="text-muted-foreground hover:text-foreground">
              <X className="w-5 h-5" />
            </button>
          </div>
          
          {/* Plans Grid */}
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {plans.filter(p => p.id !== 'trial').map((plan) => {
                const isCurrentPlan = subscription?.plan === plan.id;
                const isContact = plan.is_contact;
                
                return (
                  <div 
                    key={plan.id} 
                    className={`border p-4 flex flex-col ${
                      isCurrentPlan ? 'border-primary bg-primary/5' : 'border-border'
                    }`}
                  >
                    {isCurrentPlan && (
                      <span className="text-xs bg-primary text-primary-foreground px-2 py-0.5 w-fit mb-2">
                        MEVCUT PLAN
                      </span>
                    )}
                    <h3 className="font-heading font-semibold text-lg">{plan.name}</h3>
                    
                    {isContact ? (
                      <div className="my-3">
                        <p className="text-2xl font-bold">Özel Fiyat</p>
                        <p className="text-sm text-muted-foreground">Teklif için iletişime geçin</p>
                      </div>
                    ) : (
                      <div className="my-3">
                        <p className="text-2xl font-bold">₺{plan.price}<span className="text-sm font-normal text-muted-foreground">/12 ay</span></p>
                      </div>
                    )}
                    
                    <ul className="space-y-2 text-sm flex-grow mb-4">
                      <li className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-primary" />
                        {plan.monthly_limit === -1 ? 'Sınırsız fatura' : `12 ay için ${plan.monthly_limit.toLocaleString('tr-TR')} fatura`}
                      </li>
                      <li className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-primary" />
                        Excel dışa aktarma
                      </li>
                    </ul>
                    
                    <Button
                      className="w-full rounded-none uppercase tracking-wide"
                      variant={isCurrentPlan ? "outline" : "default"}
                      disabled={isCurrentPlan}
                      onClick={() => {
                        // Redirect to Wix pricing page
                        window.open('https://www.documander.com/pricing-plans/list', '_blank');
                      }}
                    >
                      {isCurrentPlan ? 'Mevcut Plan' : isContact ? 'İletişime Geç' : 'Satın Al'}
                    </Button>
                  </div>
                );
              })}
            </div>
            
            {/* Trial Info */}
            {subscription?.is_trial && (
              <div className="mt-6 p-4 bg-muted/50 border border-border">
                <p className="text-sm">
                  <strong>Deneme Hakkınız:</strong> {subscription.remaining} / {subscription.total_limit || subscription.monthly_limit} fatura kaldı. 
                  Deneme hakkınız bittiğinde, devam etmek için bir plan satın almanız gerekecektir.
                </p>
              </div>
            )}
            
            {/* Quota exhausted info */}
            {subscription?.is_quota_exhausted && !subscription?.is_trial && (
              <div className="mt-6 p-4 bg-destructive/10 border border-destructive/30">
                <p className="text-sm text-destructive">
                  <strong>Kotanız Doldu!</strong> Fatura yüklemeye devam etmek için yeni bir plan satın alın. 
                  Mevcut planınız ({subscription.plan_name}) için tüm kotanızı kullandınız.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen" data-testid="dashboard-page">
      {/* Plans Modal */}
      <PlansModal />
      
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
        <div className="px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Documander" className="h-8" />
            <div className="border-l border-border pl-3">
              <h1 className="text-lg font-heading font-bold tracking-tight">
                {session ? `${session.taxpayer_name}` : 'Fatura Yönetim'}
              </h1>
              <p className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                {session && (
                  <>
                    <Calendar className="w-3 h-3" />
                    {MONTH_NAMES[session.month]} {session.year}
                  </>
                )}
              </p>
            </div>
          </div>
          
          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            <QuotaBadge />
            
            <Button onClick={changeSession} variant="outline" size="sm" className="rounded-none gap-1 text-xs" data-testid="change-session-button">
              <Calendar className="w-3 h-3" />
              Dönem
            </Button>
            
            <Button
              onClick={() => handleExport()}
              disabled={incomeInvoices.length === 0 && expenseInvoices.length === 0 || !session}
              variant="outline" size="sm"
              className="rounded-none gap-1 text-xs"
              data-testid="export-excel-button"
            >
              <Download className="w-3 h-3" />
              Tümünü İndir
            </Button>
            
            <Button
              onClick={handleResetAll}
              disabled={incomeInvoices.length === 0 && expenseInvoices.length === 0}
              variant="outline" size="sm"
              className="rounded-none gap-1 text-xs text-destructive border-destructive hover:bg-destructive hover:text-white"
              data-testid="reset-all-button"
            >
              <RotateCcw className="w-3 h-3" />
              Sıfırla
            </Button>
            
            {currentView === 'invoices' ? (
              <Button onClick={showVatReport} disabled={!session} size="sm" className="rounded-none gap-1 text-xs bg-primary" data-testid="vat-report-button">
                <FileText className="w-3 h-3" />
                KDV Raporu
              </Button>
            ) : (
              <Button onClick={showInvoices} size="sm" className="rounded-none gap-1 text-xs" data-testid="invoices-button">
                <ArrowLeft className="w-3 h-3" />
                Faturalar
              </Button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-8 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-lg font-mono text-muted-foreground">Yükleniyor...</div>
          </div>
        ) : currentView === 'invoices' ? (
          <>
            <InvoiceTable invoices={incomeInvoices} type="income" />
            <InvoiceTable invoices={expenseInvoices} type="expense" />
          </>
        ) : (
          <VatReportView />
        )}
      </main>

      {/* Modals */}
      {showUploadModal && (
        <UploadModal
          category={uploadCategory}
          onClose={() => setShowUploadModal(false)}
          onSuccess={() => {
            fetchInvoices();
            fetchSubscription();
          }}
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
