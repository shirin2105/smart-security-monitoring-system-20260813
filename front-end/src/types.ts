export interface User {
  id: number;
  username: string;
  full_name: string;
  role: 'bao_ve' | 'quan_ly';
}

export interface Camera {
  id: number;
  name: string;
  location: string;
  stream_url: string;
  status: 'online' | 'warning' | 'offline';
}

export interface Incident {
  id: number;
  camera_id: number;
  camera_name?: string;
  event_type: 'xam_nhap' | 'dam_dong' | string;
  severity: 'warning' | 'critical' | string;
  description: string;
  status: 'pending' | 'acknowledged' | 'escalated';
  created_at: string;
  bbox?: [number, number, number, number]; // [x, y, w, h]
}

export interface AuditLog {
  id: number;
  user_name: string;
  action: string;
  incident_id?: number;
  timestamp: string;
}

export interface WebSocketMessage {
  type: 'NEW_ALERT' | 'ALERT_UPDATED';
  incident?: Incident;
  incident_id?: number;
  status?: 'acknowledged' | 'escalated';
  action_by?: string;
}
