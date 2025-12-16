import React, { useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AuthPage = ({ setIsAuthenticated }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: ''
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const payload = isLogin
        ? { email: formData.email, password: formData.password }
        : formData;

      const response = await axios.post(`${API}${endpoint}`, payload);
      
      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      
      toast.success(isLogin ? 'Giriş başarılı!' : 'Kayıt başarılı!');
      setIsAuthenticated(true);
    } catch (error) {
      const message = error.response?.data?.detail || 'Bir hata oluştu';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left Side - Form */}
      <div className="flex items-center justify-center p-8 lg:p-12">
        <div className="w-full max-w-md">
          <div className="mb-8">
            <img src="/logo.png" alt="Documander" className="h-12 mb-4" />
            <p className="text-sm text-muted-foreground tracking-wide uppercase">
              Muhasebe için profesyonel çözüm
            </p>
          </div>

          <div className="mb-6">
            <h2 className="text-2xl font-heading font-semibold mb-2">
              {isLogin ? 'Giriş Yap' : 'Kayıt Ol'}
            </h2>
            <p className="text-sm text-muted-foreground">
              {isLogin
                ? 'Hesabınıza giriş yapın'
                : 'Yeni hesap oluşturun'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6" data-testid="auth-form">
            {!isLogin && (
              <div className="space-y-2">
                <Label htmlFor="full_name" className="uppercase text-xs tracking-wider">
                  Ad Soyad
                </Label>
                <Input
                  id="full_name"
                  name="full_name"
                  type="text"
                  value={formData.full_name}
                  onChange={handleChange}
                  required={!isLogin}
                  className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0"
                  data-testid="full-name-input"
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="uppercase text-xs tracking-wider">
                E-posta
              </Label>
              <Input
                id="email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                required
                className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0"
                data-testid="email-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="uppercase text-xs tracking-wider">
                Şifre
              </Label>
              <Input
                id="password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
                required
                className="rounded-none border-0 border-b-2 px-0 focus-visible:ring-0"
                data-testid="password-input"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full rounded-none uppercase tracking-wide font-medium"
              data-testid="auth-submit-button"
            >
              {loading ? 'İşlem yapılıyor...' : isLogin ? 'Giriş Yap' : 'Kayıt Ol'}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <button
              type="button"
              onClick={() => setIsLogin(!isLogin)}
              className="text-sm text-muted-foreground hover:text-primary"
              data-testid="toggle-auth-mode"
            >
              {isLogin
                ? 'Hesabınız yok mu? Kayıt olun'
                : 'Zaten hesabınız var mı? Giriş yapın'}
            </button>
          </div>
        </div>
      </div>

      {/* Right Side - Image */}
      <div
        className="hidden lg:block bg-cover bg-center relative"
        style={{
          backgroundImage: "url('https://images.pexels.com/photos/8534174/pexels-photo-8534174.jpeg')",
        }}
      >
        <div className="absolute inset-0 bg-primary/20"></div>
        <div className="absolute bottom-12 left-12 right-12 text-white">
          <p className="text-xl font-heading italic leading-relaxed">
            "Hassasiyet, güvenin temelidir."
          </p>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;
