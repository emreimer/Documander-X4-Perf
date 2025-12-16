import React, { useState } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { toast } from 'sonner';
import { X, Upload as UploadIcon, FileText } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const UploadModal = ({ onClose, onSuccess }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const getAuthHeader = () => {
    const token = localStorage.getItem('token');
    return { Authorization: `Bearer ${token}` };
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
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
    if (!file) {
      toast.error('Lütfen bir dosya seçin');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      await axios.post(`${API}/invoices/upload`, formData, {
        headers: {
          ...getAuthHeader(),
          'Content-Type': 'multipart/form-data'
        }
      });
      
      toast.success('Fatura başarıyla yüklendi ve işlendi!');
      onSuccess();
      onClose();
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
          <h3 className="text-xl font-heading font-semibold">Fatura Yükle</h3>
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
            PDF, JPG, PNG veya XML formatında fatura yükleyin. AI otomatik olarak fatura bilgilerini çıkaracaktır.
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
            {file ? (
              <div className="space-y-4">
                <FileText className="w-12 h-12 text-primary mx-auto" strokeWidth={1.5} />
                <div>
                  <p className="font-medium text-sm">{file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setFile(null)}
                  className="rounded-none"
                  data-testid="clear-file-button"
                >
                  Dosyayı Değiştir
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <UploadIcon className="w-12 h-12 text-muted mx-auto" strokeWidth={1.5} />
                <div>
                  <p className="font-medium text-sm mb-2">
                    Dosyayı buraya sürükleyin
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
                    accept=".pdf,.jpg,.jpeg,.png,.xml"
                    onChange={handleFileChange}
                    className="hidden"
                    data-testid="file-input"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Desteklenen formatlar: PDF, JPG, PNG, XML
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
            disabled={!file || uploading}
            className="rounded-none uppercase tracking-wide"
            data-testid="submit-upload-button"
          >
            {uploading ? 'İşleniyor...' : 'Yükle'}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default UploadModal;
