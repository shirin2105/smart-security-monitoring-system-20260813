import React, { useState } from 'react';
import { Incident } from '../types';
import { Bell, CheckCircle2, ArrowUpRight, AlertTriangle, ShieldAlert, Filter, Clock } from 'lucide-react';

interface AlertSidebarProps {
  incidents: Incident[];
  onAcknowledge: (incidentId: number) => void;
  onEscalate: (incidentId: number) => void;
}

export const AlertSidebar: React.FC<AlertSidebarProps> = ({
  incidents,
  onAcknowledge,
  onEscalate
}) => {
  const [filter, setFilter] = useState<'all' | 'pending' | 'resolved'>('all');
  const [processingId, setProcessingId] = useState<number | null>(null);

  const filteredIncidents = incidents.filter(inc => {
    if (filter === 'pending') return inc.status === 'pending';
    if (filter === 'resolved') return inc.status !== 'pending';
    return true;
  });

  const pendingCount = incidents.filter(inc => inc.status === 'pending').length;

  const handleAction = async (action: 'ack' | 'esc', id: number) => {
    setProcessingId(id);
    try {
      if (action === 'ack') {
        await onAcknowledge(id);
      } else {
        await onEscalate(id);
      }
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <aside className="w-full lg:w-96 glass-panel rounded-2xl border border-gray-800 flex flex-col h-[calc(100vh-6rem)] overflow-hidden shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-gray-800 bg-gray-950/80 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Bell className="w-5 h-5 text-amber-400" />
            {pendingCount > 0 && (
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full animate-ping"></span>
            )}
          </div>
          <div>
            <h2 className="text-sm font-bold text-white tracking-wide">CẢNH BÁO THỜI GIAN THỰC</h2>
            <p className="text-[11px] text-gray-400">WebSocket Live Alerts ({incidents.length})</p>
          </div>
        </div>

        {pendingCount > 0 && (
          <span className="px-2 py-0.5 bg-red-500/20 text-red-400 border border-red-500/40 rounded-full text-xs font-mono font-bold animate-pulse">
            {pendingCount} CHỜ XỬ LÝ
          </span>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="p-2 border-b border-gray-800/80 bg-gray-900/60 flex items-center gap-1 text-xs">
        <Filter className="w-3.5 h-3.5 text-gray-500 ml-2 mr-1" />
        <button
          onClick={() => setFilter('all')}
          className={`px-2.5 py-1 rounded-md transition-colors ${
            filter === 'all' ? 'bg-blue-600/30 text-blue-300 font-semibold border border-blue-500/30' : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Tất cả ({incidents.length})
        </button>
        <button
          onClick={() => setFilter('pending')}
          className={`px-2.5 py-1 rounded-md transition-colors ${
            filter === 'pending' ? 'bg-amber-600/30 text-amber-300 font-semibold border border-amber-500/30' : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Chưa xử lý ({pendingCount})
        </button>
        <button
          onClick={() => setFilter('resolved')}
          className={`px-2.5 py-1 rounded-md transition-colors ${
            filter === 'resolved' ? 'bg-emerald-600/30 text-emerald-300 font-semibold border border-emerald-500/30' : 'text-gray-400 hover:text-gray-200'
          }`}
        >
          Đã xong ({incidents.length - pendingCount})
        </button>
      </div>

      {/* Incidents List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {filteredIncidents.length === 0 ? (
          <div className="h-48 flex flex-col items-center justify-center text-center text-gray-500 p-4">
            <CheckCircle2 className="w-10 h-10 text-emerald-500/40 mb-2" />
            <p className="text-xs">Không có cảnh báo nào trong danh mục này</p>
          </div>
        ) : (
          filteredIncidents.map((inc) => {
            const isCritical = inc.severity === 'critical';
            const isPending = inc.status === 'pending';
            const formattedTime = new Date(inc.created_at).toLocaleTimeString('vi-VN', { hour12: false });

            return (
              <div
                key={inc.id}
                className={`p-3.5 rounded-xl border transition-all ${
                  isPending
                    ? isCritical
                      ? 'bg-red-950/40 border-red-500/60 shadow-lg shadow-red-950/50'
                      : 'bg-amber-950/30 border-amber-500/50'
                    : 'bg-gray-900/60 border-gray-800 opacity-75'
                }`}
              >
                {/* Top header */}
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5">
                    {isCritical ? (
                      <ShieldAlert className="w-4 h-4 text-red-400 animate-bounce" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-400" />
                    )}
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded uppercase border ${
                      isCritical
                        ? 'bg-red-600/30 text-red-300 border-red-500/40'
                        : 'bg-amber-600/30 text-amber-300 border-amber-500/40'
                    }`}>
                      {inc.severity.toUpperCase()}
                    </span>
                    <span className="text-xs font-semibold text-gray-200">
                      {inc.camera_name || `Camera #${inc.camera_id}`}
                    </span>
                  </div>

                  <div className="flex items-center gap-1 text-[11px] font-mono text-gray-400">
                    <Clock className="w-3 h-3 text-gray-500" />
                    <span>{formattedTime}</span>
                  </div>
                </div>

                {/* Description */}
                <p className="text-xs text-gray-300 mb-3 leading-relaxed">
                  {inc.description}
                </p>

                {/* Status or Actions */}
                {isPending ? (
                  <div className="flex items-center gap-2 pt-2 border-t border-gray-800/80">
                    <button
                      onClick={() => handleAction('ack', inc.id)}
                      disabled={processingId === inc.id}
                      className="flex-1 py-1.5 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-all shadow-md shadow-emerald-600/20"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Xác Nhận (HITL)</span>
                    </button>

                    <button
                      onClick={() => handleAction('esc', inc.id)}
                      disabled={processingId === inc.id}
                      className="py-1.5 px-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs font-medium flex items-center justify-center gap-1 transition-all border border-gray-700"
                    >
                      <ArrowUpRight className="w-3.5 h-3.5 text-amber-400" />
                      <span>Chuyển Quản Lý</span>
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center justify-between text-[11px] font-mono pt-2 border-t border-gray-800/80 text-gray-400">
                    <span>Trạng thái:</span>
                    <span className={`px-2 py-0.5 rounded uppercase font-semibold ${
                      inc.status === 'acknowledged' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-indigo-500/20 text-indigo-400'
                    }`}>
                      {inc.status === 'acknowledged' ? '✓ Đã Xác Nhận' : '↑ Đã Chuyển Quản Lý'}
                    </span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
};
