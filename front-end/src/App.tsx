import { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { CameraGrid } from './components/CameraGrid';
import { AlertSidebar } from './components/AlertSidebar';
import { AuditLogModal } from './components/AuditLogModal';
import { LoginModal } from './components/LoginModal';
import { User, Camera, Incident, WebSocketMessage } from './types';

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);

  // Restore login from localStorage on mount
  useEffect(() => {
    const savedUser = localStorage.getItem('sec_user');
    const savedToken = localStorage.getItem('sec_token');
    if (savedUser && savedToken) {
      try {
        setUser(JSON.parse(savedUser));
        setToken(savedToken);
      } catch (e) {
        localStorage.clear();
      }
    }
  }, []);

  const handleLoginSuccess = (loggedInUser: User, accessToken: string) => {
    setUser(loggedInUser);
    setToken(accessToken);
    localStorage.setItem('sec_user', JSON.stringify(loggedInUser));
    localStorage.setItem('sec_token', accessToken);
  };

  const handleLogout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('sec_user');
    localStorage.removeItem('sec_token');
  };

  // Fetch initial data
  const fetchData = async () => {
    try {
      // Fetch cameras
      const resCam = await fetch('http://localhost:8000/api/v1/cameras');
      if (resCam.ok) {
        const camData = await resCam.json();
        setCameras(camData);
      }

      // Fetch alerts
      const resAlerts = await fetch('http://localhost:8000/api/v1/alerts');
      if (resAlerts.ok) {
        const alertData = await resAlerts.json();
        setIncidents(alertData);
      }
    } catch (e) {
      console.error('Error fetching initial cameras/alerts data', e);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // WebSocket Connection with auto-reconnect
  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWS = () => {
      socket = new WebSocket('ws://localhost:8000/ws/alerts');
      wsRef.current = socket;

      socket.onopen = () => {
        setWsConnected(true);
        console.log('WebSocket connected');
      };

      socket.onmessage = (event) => {
        try {
          const msg: WebSocketMessage = JSON.parse(event.data);
          if (msg.type === 'NEW_ALERT' && msg.incident) {
            setIncidents(prev => [msg.incident!, ...prev]);
          } else if (msg.type === 'ALERT_UPDATED' && msg.incident_id && msg.status) {
            setIncidents(prev =>
              prev.map(inc => inc.id === msg.incident_id ? { ...inc, status: msg.status! } : inc)
            );
          }
        } catch (err) {
          console.error('Failed to parse WS message', err);
        }
      };

      socket.onclose = () => {
        setWsConnected(false);
        console.log('WebSocket disconnected. Retrying in 3s...');
        reconnectTimeout = setTimeout(connectWS, 3000);
      };

      socket.onerror = (err) => {
        console.error('WebSocket error:', err);
        socket?.close();
      };
    };

    connectWS();

    return () => {
      if (socket) socket.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  // HITL Handlers
  const handleAcknowledge = async (incidentId: number) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/alerts/${incidentId}/acknowledge`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token || ''}`,
          'Content-Type': 'application/json'
        }
      });
      if (res.ok) {
        setIncidents(prev =>
          prev.map(inc => inc.id === incidentId ? { ...inc, status: 'acknowledged' } : inc)
        );
      }
    } catch (e) {
      console.error('Failed to acknowledge incident', e);
    }
  };

  const handleEscalate = async (incidentId: number) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/alerts/${incidentId}/escalate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token || ''}`,
          'Content-Type': 'application/json'
        }
      });
      if (res.ok) {
        setIncidents(prev =>
          prev.map(inc => inc.id === incidentId ? { ...inc, status: 'escalated' } : inc)
        );
      }
    } catch (e) {
      console.error('Failed to escalate incident', e);
    }
  };

  const handleTriggerSimulation = async () => {
    try {
      await fetch('http://localhost:8000/api/v1/alerts/simulate', { method: 'POST' });
    } catch (e) {
      console.error('Failed to trigger simulation', e);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-gray-100 flex flex-col font-sans">
      {!user && <LoginModal onLoginSuccess={handleLoginSuccess} />}

      <Navbar
        user={user}
        wsConnected={wsConnected}
        onOpenAuditLog={() => setIsAuditModalOpen(true)}
        onTriggerSimulation={handleTriggerSimulation}
        onLogout={handleLogout}
      />

      <main className="flex-1 p-6 flex flex-col lg:flex-row gap-6 max-w-[1920px] w-full mx-auto overflow-hidden">
        <CameraGrid cameras={cameras} incidents={incidents} />
        <AlertSidebar
          incidents={incidents}
          onAcknowledge={handleAcknowledge}
          onEscalate={handleEscalate}
        />
      </main>

      <AuditLogModal
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
      />
    </div>
  );
}

export default App;
