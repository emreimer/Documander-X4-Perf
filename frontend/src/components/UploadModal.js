import React, { useState } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { toast } from 'sonner';
import { X, Upload as UploadIcon, FileText, Loader2, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Processing Overlay Component
const ProcessingOverlay = ({ fileCount }) => (
  <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[100] flex items-center justify-center">
    <div className="bg-card border-2 border-primary shadow-2xl p-8 max-w-md w-full mx-4 text-center">
      <div className="relative mb-6">
        <Loader2 className="w-16 h-16 text-primary mx-auto animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <FileText className="w-6 h-6 text-primary/50" />
        </div>
      </div>
      <h3 className="text-xl font-heading font-bold mb-2">Faturalar İşleniyor</h3>
      <p className="text-muted-foreground mb-4">
        {fileCount} dosya analiz ediliyor...
      </p>
      <div className="space-y-2">
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-primary rounded-full animate-pulse" style={{ width: '100%' }} />
        </div>
        <p className="text-xs text-muted-foreground">
          Bu işlem birkaç saniye sürebilir. Lütfen bekleyin...
        </p>
      </div>
      <div className="mt-6 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded">
        <p className="text-xs text-yellow-600 font-medium">
          ⚠️ Sayfayı kapatmayın veya yenilemeyin
        </p>
      </div>
    </div>
  </div>
);

// Result Overlay Component - Shows upload results with warnings/errors
const ResultOverlay = ({ result, onClose, onShowPlans }) => {
  const { success, errors, date_mismatches, quota_warning, isQuotaError } = result;
  
  const hasWarnings = (date_mismatches && date_mismatches.length > 0) || quota_warning;
  const hasErrors = errors && errors.length > 0;
  
  // Special case for quota exhausted
  if (isQuotaError) {
    return (
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[100] flex items-center justify-center">
        <div className="bg-card border-2 border-destructive shadow-2xl p-8 max-w-md w-full mx-4 text-center">
          {/* Icon */}
          <div className="mb-6">
            <div className="w-20 h-20 bg-destructive/10 rounded-full flex items-center justify-center mx-auto">
              <XCircle className="w-12 h-12 text-destructive" />
            </div>
          </div>
          
          {/* Title */}
          <h3 className="text-2xl font-heading font-bold text-destructive mb-2">Kota Doldu</h3>
          <p className="text-muted-foreground mb-6">
            Fatura yükleme kotanız dolmuştur. Devam etmek için yeni bir paket satın alın.
          </p>
          
          {/* Error Detail */}
          {errors && errors.length > 0 && (
            <div className="mb-6 p-3 bg-destructive/10 border border-destructive/30 rounded text-left">
              <p className="text-sm text-destructive">
                {errors[0]}
              </p>
            </div>
          )}
          
          {/* Buttons */}
          <div className="space-y-3">
            <Button
              onClick={onShowPlans}
              className="w-full rounded-none uppercase tracking-wide"
            >
              Paketleri İncele
            </Button>
            <Button
              onClick={onClose}
              variant="outline"
              className="w-full rounded-none uppercase tracking-wide"
            >
              Kapat
            </Button>
          </div>
        </div>
      </div>
    );
  }
  
  // Determine overlay type for normal results
  let title = 'İşlem Tamamlandı';
  let borderColor = 'border-green-500';
  let Icon = CheckCircle2;
  let iconColor = 'text-green-500';
  
  if (hasErrors && success === 0) {
    title = 'Yükleme Başarısız';
    borderColor = 'border-destructive';
    Icon = XCircle;
    iconColor = 'text-destructive';
  } else if (hasWarnings || hasErrors) {
    title = 'Dikkat Edilmesi Gerekenler';
    borderColor = 'border-yellow-500';
    Icon = AlertTriangle;
    iconColor = 'text-yellow-500';
  }
  
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[100] flex items-center justify-center">
      <div className={`bg-card border-2 ${borderColor} shadow-2xl p-8 max-w-lg w-full mx-4`}>
        {/* Header */}
        <div className="text-center mb-6">
          <Icon className={`w-16 h-16 ${iconColor} mx-auto mb-4`} />
          <h3 className="text-xl font-heading font-bold">{title}</h3>
        </div>
        
        {/* Success Message */}
        {success > 0 && (
          <div className="mb-4 p-3 bg-green-500/10 border border-green-500/30 rounded">
            <p className="text-sm text-green-700 font-medium flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              {success} fatura başarıyla yüklendi
            </p>
          </div>
        )}
        
        {/* Date Mismatch Warnings */}
        {date_mismatches && date_mismatches.length > 0 && (
          <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded">
            <p className="text-sm font-medium text-yellow-700 mb-2 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              Tarih Uyuşmazlığı
            </p>
            <ul className="text-xs text-yellow-600 space-y-1 ml-6">
              {date_mismatches.map((msg, idx) => (
                <li key={idx}>• {msg}</li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Quota Warning */}
        {quota_warning && (
          <div className="mb-4 p-3 bg-orange-500/10 border border-orange-500/30 rounded">
            <p className="text-sm text-orange-700 font-medium flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              {quota_warning}
            </p>
          </div>
        )}
        
        {/* Errors */}
        {errors && errors.length > 0 && (
          <div className="mb-4 p-3 bg-destructive/10 border border-destructive/30 rounded">
            <p className="text-sm font-medium text-destructive mb-2 flex items-center gap-2">
              <XCircle className="w-4 h-4" />
              Hatalar
            </p>
            <ul className="text-xs text-destructive/80 space-y-1 ml-6">
              {errors.map((err, idx) => (
                <li key={idx}>• {err}</li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Close Button */}
        <Button
          onClick={onClose}
          className="w-full rounded-none uppercase tracking-wide mt-4"
        >
          Tamam
        </Button>
      </div>
    </div>
  );
};

const UploadModal = ({ category, onClose, onSuccess }) => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploadResult, setUploadResult] = useState(null); // For result overlay

  const getAuthHeader = () => {
    // Send visitor ID and Wix Member ID for user isolation
    const visitorId = localStorage.getItem('documander_visitor_id') || 'anonymous';
    const wixMemberId = localStorage.getItem('documander_wix_member_id');
    
    const headers = { 'X-Visitor-ID': visitorId };
    if (wixMemberId) {
      headers['X-Wix-Member-ID'] = wixMemberId;
    }
    return headers;
  };

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    if (selectedFiles.length > 0) {
      setFiles(selectedFiles);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      setFiles(droppedFiles);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      toast.error('Lütfen en az bir dosya seçin');
      return;
    }

    setUploading(true);
    setUploadResult(null);
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('category', category);

    try {
      const headers = getAuthHeader();
      
      const response = await axios.post(`${API}/invoices/upload`, formData, {
        headers: {
          ...headers
        }
      });
      
      const { success, failed, errors, date_mismatches, quota_warning, remaining_quota } = response.data;
      
      // Check if there are any warnings or errors to show in overlay
      const hasIssues = (date_mismatches && date_mismatches.length > 0) || 
                        quota_warning || 
                        (errors && errors.length > 0);
      
      if (hasIssues) {
        // Show result overlay with warnings/errors
        setUploadResult({ success, errors: errors || [], date_mismatches: date_mismatches || [], quota_warning });
      } else if (success > 0) {
        // Pure success - just show toast and close
        toast.success(`${success} fatura başarıyla yüklendi!`);
        onSuccess(remaining_quota);
        onClose();
      }
      
      // Always call onSuccess to refresh the list
      if (success > 0) {
        onSuccess(remaining_quota);
      }
      
    } catch (error) {
      const errorStatus = error.response?.status;
      const message = error.response?.data?.detail || 'Fatura yüklenemedi';
      
      // Special handling for quota exceeded
      if (errorStatus === 403 && (message.includes('limit') || message.includes('kota') || message.includes('Kota'))) {
        setUploadResult({ 
          success: 0, 
          errors: [message], 
          date_mismatches: [], 
          quota_warning: null,
          isQuotaError: true 
        });
      } else {
        setUploadResult({ 
          success: 0, 
          errors: [message], 
          date_mismatches: [], 
          quota_warning: null 
        });
      }
    } finally {
      setUploading(false);
    }
  };

  // Handle showing plans modal
  const handleShowPlans = () => {
    setUploadResult(null);
    onClose();
    window.dispatchEvent(new CustomEvent('showPlansModal'));
  };

  // Handle result overlay close
  const handleResultClose = () => {
    const result = uploadResult;
    setUploadResult(null);
    
    // If there were successful uploads and no critical errors, close upload modal
    if (result?.success > 0) {
      onClose();
    }
  };

  return (
    <>
      {/* Processing Overlay - Full Screen */}
      {uploading && <ProcessingOverlay fileCount={files.length} />}
      
      {/* Result Overlay - Shows after upload completes with warnings/errors */}
      {uploadResult && (
        <ResultOverlay 
          result={uploadResult} 
          onClose={handleResultClose} 
          onShowPlans={handleShowPlans}
        />
      )}
      
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="upload-modal">
        <div className="bg-card border border-border shadow-lg max-w-lg w-full">
        {/* Header */}
        <div className="border-b border-border p-4 flex items-center justify-between bg-muted/20">
          <h3 className="text-xl font-heading font-semibold">
            {category === 'income' ? 'Gelir Faturaları Yükle' : 'Gider Faturaları Yükle'}
          </h3>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
            data-testid="close-upload-modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          <p className="text-sm text-muted-foreground mb-6">
            PDF, JPG, PNG, XML veya HTML formatında {category === 'income' ? 'gelir' : 'gider'} faturası yükleyin.
          </p>

          {/* Drag & Drop Zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`upload-zone border-2 border-dashed p-8 text-center transition-all ${
              dragOver ? 'drag-over' : 'border-border'
            }`}
            data-testid="upload-drop-zone"
          >
            {files.length > 0 ? (
              <div className="space-y-4">
                <FileText className="w-12 h-12 text-primary mx-auto" strokeWidth={1.5} />
                <div className="max-h-48 overflow-y-auto space-y-2">
                  {files.map((file, index) => (
                    <div key={index} className="text-sm">
                      <p className="font-medium">{file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {(file.size / 1024).toFixed(2)} KB
                      </p>
                    </div>
                  ))}
                </div>
                <div className="text-sm font-medium text-primary">
                  {files.length} dosya seçildi
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setFiles([])}
                  className="rounded-none"
                  data-testid="clear-file-button"
                >
                  Dosyaları Temizle
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <UploadIcon className="w-12 h-12 text-muted mx-auto" strokeWidth={1.5} />
                <div>
                  <p className="font-medium text-sm mb-2">
                    Dosyaları buraya sürükleyin
                  </p>
                  <p className="text-xs text-muted-foreground mb-4">veya</p>
                  <label htmlFor="file-input">
                    <span className="inline-block px-4 py-2 bg-secondary text-secondary-foreground text-sm uppercase tracking-wide cursor-pointer hover:bg-secondary/80 transition-colors">
                      Dosya Seç
                    </span>
                  </label>
                  <input
                    id="file-input"
                    type="file"
                    multiple
                    accept=".pdf,.jpg,.jpeg,.png,.xml,.html,.htm"
                    onChange={handleFileChange}
                    className="hidden"
                    data-testid="file-input"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Desteklenen formatlar: PDF, JPG, PNG, XML, HTML
                </p>
                <p className="text-xs text-muted-foreground font-medium">
                  Toplu yükleme desteklenir
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-border p-4 flex items-center justify-end gap-3">
          <Button
            variant="outline"
            onClick={onClose}
            disabled={uploading}
            className="rounded-none uppercase tracking-wide"
            data-testid="cancel-upload-button"
          >
            İptal
          </Button>
          <Button
            onClick={handleUpload}
            disabled={files.length === 0 || uploading}
            className="rounded-none uppercase tracking-wide"
            data-testid="submit-upload-button"
          >
            {uploading ? 'İşleniyor...' : `Yükle (${files.length})`}
          </Button>
        </div>
      </div>
    </div>
    </>
  );
};

export default UploadModal;
