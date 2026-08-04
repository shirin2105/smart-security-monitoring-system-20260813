import React, { useState } from 'react';
import { ShieldCheck, Lock, User as UserIcon, AlertCircle, KeyRound } from 'lucide-react';
import { User } from '../types';

interface LoginModalProps {
  onLoginSuccess: (user: User, token: string) => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('guard');
  const [password, setPassword] = useState('guard123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Đăng nhập thất bại');
      }

      const data = await response.json();
      onLoginSuccess(data.user, data.access_token);
    } catch (err: any) {
      setError(err.message || 'Lỗi kết nối đến Backend Server');
    } finally {
      setLoading(false);
    }
  };

  const fillCredentials = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
      <div className="w-full max-w-md bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl overflow-hidden glass-panel">
        {/* Header banner */}
        <div className="p-6 bg-gradient-to-r from-blue-900/40 via-gray-900 to-indigo-900/40 border-b border-gray-800 text-center">
          <div className="mx-auto w-14 h-14 bg-blue-600/20 border border-blue-500/50 rounded-2xl flex items-center justify-center text-blue-400 mb-3 shadow-lg shadow-blue-500/20">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-wide">ĐĂNG NHẬP HỆ THỐNG AN NINH</h2>
          <p className="text-xs text-gray-400 mt-1">Hệ Thống Giám Sát Realtime & Xử Lý Sự Cố (HITL)</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5 uppercase font-mono">
              Tên tài khoản
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
                <UserIcon className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full pl-9 pr-4 py-2.5 bg-gray-950 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="guard / manager"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5 uppercase font-mono">
              Mật khẩu
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full pl-9 pr-4 py-2.5 bg-gray-950 border border-gray-800 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-medium rounded-lg text-sm transition-all shadow-lg shadow-blue-600/30 flex items-center justify-center gap-2"
          >
            {loading ? (
              <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            ) : (
              <>
                <KeyRound className="w-4 h-4" />
                <span>Truy Cập Command Center</span>
              </>
            )}
          </button>
        </form>

        {/* Demo preset credentials helper */}
        <div className="px-6 py-4 bg-gray-950/60 border-t border-gray-800/80 text-xs text-gray-400">
          <p className="font-semibold text-gray-300 mb-2 flex items-center gap-1">
            <span>Tài khoản mẫu từ PostgreSQL DB:</span>
          </p>
          <div className="grid grid-cols-2 gap-2 font-mono">
            <button
              type="button"
              onClick={() => fillCredentials('guard', 'guard123')}
              className="p-2 bg-gray-900 border border-gray-800 rounded text-left hover:border-blue-500/50 hover:bg-gray-800/60 transition-all text-[11px]"
            >
              <div className="font-bold text-blue-400">Bảo Vệ:</div>
              <div className="text-gray-300">guard / guard123</div>
            </button>

            <button
              type="button"
              onClick={() => fillCredentials('manager', 'manager123')}
              className="p-2 bg-gray-900 border border-gray-800 rounded text-left hover:border-indigo-500/50 hover:bg-gray-800/60 transition-all text-[11px]"
            >
              <div className="font-bold text-indigo-400">Quản Lý:</div>
              <div className="text-gray-300">manager / manager123</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
