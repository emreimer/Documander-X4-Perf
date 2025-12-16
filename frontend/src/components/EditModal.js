import React, { useState } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { toast } from 'sonner';
import { X } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const EditModal = ({ invoice, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    invoice_number: invoice.invoice_number,
    date: invoice.date,
    issuer_name: invoice.issuer_name,
    issuer_tax_id: invoice.issuer_tax_id,
    issuer_tax_office: invoice.issuer_tax_office,
    customer_name: invoice.customer_name,
    customer_tax_id: invoice.customer_tax_id,
    customer_tax_office: invoice.customer_tax_office,
    description: invoice.description,
    amount: invoice.amount,
    vat: invoice.vat,
    total: invoice.total
  });
  const [saving, setSaving] = useState(false);

  const getAuthHeader = () => {
    const token = localStorage.getItem('token');
    return { Authorization: `Bearer ${token}` };
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    const newValue = ['amount', 'vat', 'total'].includes(name) ? parseFloat(value) || 0 : value;
    setFormData({
      ...formData,
      [name]: newValue
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      await axios.put(`${API}/invoices/${invoice.id}`, formData, {
        headers: getAuthHeader()
      });
      
      toast.success('Fatura güncellendi');
      onSuccess();
      onClose();
    } catch (error) {
      toast.error('Fatura güncellenemedi');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="edit-modal">
      <div className="bg-card border border-border shadow-lg max-w-lg w-full">
        {/* Header */}
        <div className="border-b border-border p-4 flex items-center justify-between bg-muted/20">
          <h3 className="text-xl font-heading font-semibold">Faturayı Düzenle</h3>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
            data-testid="close-edit-modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="invoice_number" className="uppercase text-xs tracking-wider">
                Fatura No
              </Label>
              <Input
                id="invoice_number"
                name="invoice_number"
                value={formData.invoice_number}
                onChange={handleChange}
                className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0"
                data-testid="edit-invoice-number"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="date" className="uppercase text-xs tracking-wider">
                Tarih
              </Label>
              <Input
                id="date"
                name="date"
                value={formData.date}
                onChange={handleChange}
                className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0"
                data-testid="edit-date"
              />
            </div>
          </div>

          <div className="border-b border-border pb-4 mb-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-3 font-medium">
              Düzenleyen Bilgileri
            </p>
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="issuer_name" className="uppercase text-xs tracking-wider">
                  Firma/Kişi Adı
                </Label>
                <Input
                  id="issuer_name"
                  name="issuer_name"
                  value={formData.issuer_name}
                  onChange={handleChange}
                  className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0"
                  data-testid="edit-issuer-name"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="issuer_tax_id" className="uppercase text-xs tracking-wider">
                    Vergi Kimlik No
                  </Label>
                  <Input
                    id="issuer_tax_id"
                    name="issuer_tax_id"
                    value={formData.issuer_tax_id}
                    onChange={handleChange}
                    className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0 font-mono"
                    data-testid="edit-issuer-tax-id"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="issuer_tax_office" className="uppercase text-xs tracking-wider">
                    Vergi Dairesi
                  </Label>
                  <Input
                    id="issuer_tax_office"
                    name="issuer_tax_office"
                    value={formData.issuer_tax_office}
                    onChange={handleChange}
                    className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0"
                    data-testid="edit-issuer-tax-office"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="border-b border-border pb-4 mb-4">
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-3 font-medium">
              Müşteri Bilgileri
            </p>
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="customer_name" className="uppercase text-xs tracking-wider">
                  Müşteri Adı
                </Label>
                <Input
                  id="customer_name"
                  name="customer_name"
                  value={formData.customer_name}
                  onChange={handleChange}
                  className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0"
                  data-testid="edit-customer-name"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="customer_tax_id" className="uppercase text-xs tracking-wider">
                    Vergi Kimlik No
                  </Label>
                  <Input
                    id="customer_tax_id"
                    name="customer_tax_id"
                    value={formData.customer_tax_id}
                    onChange={handleChange}
                    className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0 font-mono"
                    data-testid="edit-customer-tax-id"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="customer_tax_office" className="uppercase text-xs tracking-wider">
                    Vergi Dairesi
                  </Label>
                  <Input
                    id="customer_tax_office"
                    name="customer_tax_office"
                    value={formData.customer_tax_office}
                    onChange={handleChange}
                    className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0"
                    data-testid="edit-customer-tax-office"
                  />
                </div>
              </div>
            </div>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground mb-3 font-medium">
              Tutar Bilgileri
            </p>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label htmlFor="amount" className="uppercase text-xs tracking-wider">
                  Net Tutar
                </Label>
                <Input
                  id="amount"
                  name="amount"
                  type="number"
                  step="0.01"
                  value={formData.amount}
                  onChange={handleChange}
                  className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0 font-mono"
                  data-testid="edit-amount"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="vat" className="uppercase text-xs tracking-wider">
                  KDV
                </Label>
                <Input
                  id="vat"
                  name="vat"
                  type="number"
                  step="0.01"
                  value={formData.vat}
                  onChange={handleChange}
                  className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0 font-mono"
                  data-testid="edit-vat"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="total" className="uppercase text-xs tracking-wider">
                  Toplam
                </Label>
                <Input
                  id="total"
                  name="total"
                  type="number"
                  step="0.01"
                  value={formData.total}
                  onChange={handleChange}
                  className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0 font-mono"
                  data-testid="edit-total"
                />
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={saving}
              className="rounded-none uppercase tracking-wide"
              data-testid="cancel-edit-button"
            >
              İptal
            </Button>
            <Button
              type="submit"
              disabled={saving}
              className="rounded-none uppercase tracking-wide"
              data-testid="submit-edit-button"
            >
              {saving ? 'Kaydediliyor...' : 'Kaydet'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditModal;
