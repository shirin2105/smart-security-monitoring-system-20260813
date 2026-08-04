import React, { useState, useEffect } from 'react';
import { Shield, Clock, Wifi, AlertTriangle, History, LogOut, User as UserIcon } from 'lucide-react';
import { User } from '../types';

interface NavbarProps {
  user: User | null;
  wsConnected: boolean;
  onOpenAuditLog: () => void;
  onTriggerSimulation: () => void;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  wsConnected,
  onOpenAuditLog,
  onTriggerSimulation,
  onLogout
}) => {
  const [time, setTime] = useState<string>('');

  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString('vi-VN', { hour12: false }) + ' - ' + now.toLocaleDateString('vi-VN'));
    };
    updateClock();
    const interval = setInterval(updateClock, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="glass-panel border-b border-gray-800 px-6 py-3.5 sticky top-0 z-40 flex flex-wrap items-center justify-between gap-4">
      {/* Left logo & title */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-blue-600/20 border border-blue-500/40 rounded-lg text-blue-400 shadow-lg shadow-blue-500/10">
          <Shield className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <h1 className="font-bold tracking-wider text-white text-lg flex items-center gap-2">
            AI MONITORING COMMAND CENTER
            <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded border border-blue-500/30 font-mono">
              MVP v1.0
            </span>
          </h1>
          <p className="text-xs text-gray-400 flex items-center gap-2">
            <span>Trung tâm trực ban Bảo vệ Tòa nhà</span>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>6/6 Cam Active</span>
          </p>
        </div>
      </div>

      {/* Middle Status & Clock */}
      <div className="hidden md:flex items-center gap-6">
        <div className="flex items-center gap-2 text-gray-300 font-mono text-sm bg-gray-900/60 px-3.5 py-1.5 rounded-md border border-gray-800">
          <Clock className="w-4 h-4 text-blue-400" />
          <span>{time}</span>
        </div>

        <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border ${
          wsConnected
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
            : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
        }`}>
          <Wifi className={`w-3.5 h-3.5 ${wsConnected ? 'text-emerald-400' : 'text-amber-400 animate-ping'}`} />
          <span className="font-semibold">{wsConnected ? 'WEBSOCKET REALTIME: RUNNING' : 'WEBSOCKET: RECONNECTING...'}</span>
        </div>
      </div>

      {/* Right Controls & User Info */}
      <div className="flex items-center gap-3">
        <button
          onClick={onTriggerSimulation}
          className="flex items-center gap-1.5 text-xs bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/40 px-3 py-1.5 rounded-md transition-all active:scale-95 font-medium"
          title="Kích hoạt sự cố giả lập thử nghiệm WebSocket & Alert"
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>Giả Lập Cảnh Báo</span>
        </button>

        <button
          onClick={onOpenAuditLog}
          className="flex items-center gap-1.5 text-xs bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 px-3 py-1.5 rounded-md transition-all active:scale-95 font-medium"
        >
          <History className="w-3.5 h-3.5 text-blue-400" />
          <span>Nhật Ký HITL</span>
        </button>

        {user && (
          <div className="flex items-center gap-2 pl-3 border-l border-gray-800">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-blue-600/30 border border-blue-500/50 flex items-center justify-center text-blue-300">
                <UserIcon className="w-4 h-4" />
              </div>
              <div className="text-left hidden lg:block">
                <div className="text-xs font-semibold text-white">{user.full_name}</div>
                <div className="text-[10px] text-gray-400 uppercase font-mono">
                  {user.role === 'bao_ve' ? 'Bảo Vệ Trực Cam' : 'Quản Lý An Ninh'}
                </div>
              </div>
            </div>

            <button
              onClick={onLogout}
              className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-colors"
              title="Đăng xuất"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
