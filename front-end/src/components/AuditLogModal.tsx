import React, { useState, useEffect } from 'react';
import { AuditLog } from '../types';
import { History, X, RefreshCw, UserCheck, Shield } from 'lucide-react';

interface AuditLogModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AuditLogModal: React.FC<AuditLogModalProps> = ({ isOpen, onClose }) => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/v1/alerts/audit-logs');
      if (response.ok) {
        const data = await response.json();
        setLogs(data);
      }
    } catch (e) {
      console.error('Failed to fetch audit logs', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
      <div className="w-full max-w-3xl bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden glass-panel flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between bg-gray-950">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600/20 text-blue-400 rounded-lg border border-blue-500/30">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">NHẬT KÝ THAO TÁC BẢO VỆ (AUDIT LOGS)</h3>
              <p className="text-xs text-gray-400">Dữ liệu ghi nhận trực tiếp từ PostgreSQL Database</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchLogs}
              disabled={loading}
              className="p-2 text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors text-xs flex items-center gap-1"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Tải lại</span>
            </button>

            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content table */}
        <div className="flex-1 overflow-y-auto p-6">
          {logs.length === 0 ? (
            <div className="py-12 text-center text-gray-500 text-xs">
              Chưa có dữ liệu nhật ký thao tác trong hệ thống.
            </div>
          ) : (
            <div className="relative border-l border-gray-800 pl-6 space-y-6">
              {logs.map((log) => {
                const formattedTime = new Date(log.timestamp).toLocaleString('vi-VN');
                return (
                  <div key={log.id} className="relative group">
                    {/* Circle dot on timeline */}
                    <div className="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full bg-blue-500 border-2 border-gray-900 group-hover:scale-125 transition-transform"></div>

                    <div className="p-4 bg-gray-950/70 border border-gray-800/80 rounded-xl space-y-1 hover:border-blue-500/40 transition-colors">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2 font-semibold text-blue-400">
                          <UserCheck className="w-3.5 h-3.5" />
                          <span>{log.user_name}</span>
                        </div>
                        <span className="font-mono text-[11px] text-gray-400">{formattedTime}</span>
                      </div>

                      <p className="text-xs text-gray-200 font-medium">
                        {log.action}
                      </p>

                      {log.incident_id && (
                        <div className="text-[11px] font-mono text-gray-400 pt-1 flex items-center gap-1">
                          <Shield className="w-3 h-3 text-amber-400" />
                          <span>Sự cố liên quan: <strong>#{log.incident_id}</strong></span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-gray-950 border-t border-gray-800 text-right">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
};
