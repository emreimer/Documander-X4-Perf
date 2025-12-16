import React, { useState } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { toast } from 'sonner';
import { X, Upload as UploadIcon, FileText } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const UploadModal = ({ category, onClose, onSuccess }) => {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const getAuthHeader = () => {
    const token = localStorage.getItem('token');
    return { Authorization: `Bearer ${token}` };
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
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('category', category);

    try {
      const response = await axios.post(`${API}/invoices/upload`, formData, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'multipart/form-data'
        }
      });
      
      const { success, failed, errors, date_mismatches } = response.data;
      
      if (success > 0) {
        toast.success(`${success} fatura başarıyla yüklendi!`);
      }
      
      // Show date mismatch warnings prominently
      if (date_mismatches && date_mismatches.length > 0) {
        date_mismatches.forEach(msg => {
          toast.warning(msg, { duration: 8000 });
        });
      }
      
      // Show other errors
      if (errors && errors.length > 0) {
        errors.forEach(err => toast.error(err));
      }
      
      onSuccess();
      if (success > 0 || (date_mismatches && date_mismatches.length === 0 && errors.length === 0)) {
        onClose();
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'Fatura yüklenemedi';
      toast.error(message);
    } finally {
      setUploading(false);
    }
  };

  return (
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
            PDF, JPG, PNG veya XML formatında {category === 'income' ? 'gelir' : 'gider'} faturası yükleyin. AI otomatik olarak fatura bilgilerini çıkaracaktır.
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
  );
};

export default UploadModal;
