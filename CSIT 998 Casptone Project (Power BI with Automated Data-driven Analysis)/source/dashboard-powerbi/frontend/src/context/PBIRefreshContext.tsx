import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { App, Button } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { API_BASE, powerbiTriggerRefresh, powerbiRefreshStatus } from '../api/client';

type RefreshStatus = 'idle' | 'processing' | 'success' | 'failed' | 'timeout' | 'error';

interface PBIRefreshContextValue {
  status: RefreshStatus;
  todayCount: number | null;
  triggerRefresh: () => Promise<void>;
}

const PBIRefreshContext = createContext<PBIRefreshContextValue | undefined>(undefined);

export function usePBIRefresh() {
  const ctx = useContext(PBIRefreshContext);
  if (!ctx) throw new Error('usePBIRefresh must be used within PBIRefreshProvider');
  return ctx;
}

export const PBIRefreshProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { notification, message } = App.useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const [status, setStatus] = useState<RefreshStatus>('idle');
  const [todayCount, setTodayCount] = useState<number | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const finishedRef = useRef<boolean>(false);

  const closeEs = useCallback((finalStatus: RefreshStatus) => {
    // prevent duplicate terminal notifications (e.g., stream end triggers error after success)
    if (finishedRef.current) return;
    finishedRef.current = true;
    if (esRef.current) {
      try { esRef.current.close(); } catch {}
      esRef.current = null;
    }
    setStatus(finalStatus);
    if (finalStatus === 'success') {
      // If user is on dashboard page, refresh the page to show updated data without notification
      if (location.pathname === '/dashboard') {
        setTimeout(() => {
          window.location.reload();
        }, 500); // Short delay for smooth transition
      } else {
        // Show notification only if user is not on dashboard page
        notification.success({ 
          message: 'Power BI refreshed', 
          description: 'The dataset has been updated.', 
          duration: 5, 
          placement: 'topRight',
          btn: (
            <Button type="primary" onClick={() => { try { notification.destroy(); } catch {}; navigate('/dashboard'); }}>
              View Dashboard
            </Button>
          )
        });
      }
    } else if (finalStatus === 'failed') {
      notification.error({ message: 'Power BI refresh failed', description: 'Please try again later.', duration: 5, placement: 'topRight' });
    } else if (finalStatus === 'timeout') {
      notification.warning({ message: 'Power BI refresh timeout', description: 'Please check later.', duration: 5, placement: 'topRight' });
    } else if (finalStatus === 'error') {
      notification.error({ message: 'Power BI refresh error', description: 'Unable to receive refresh status.', duration: 5, placement: 'topRight' });
    }
  }, [notification, navigate, location.pathname]);

  const startEs = useCallback(() => {
    if (esRef.current) {
      try { esRef.current.close(); } catch {}
      esRef.current = null;
    }
    finishedRef.current = false;
    setStatus('processing');
    notification.open({ message: 'Power BI refresh in progress', description: 'Refreshing dataset in background...', duration: 5, placement: 'topRight' });
    const es = new EventSource(`${API_BASE}/api/powerbi/datasets/refresh/stream`);
    esRef.current = es;
    es.addEventListener('status', async (ev: MessageEvent) => {
      try {
        const payload = JSON.parse(ev.data || '{}');
        if (payload.status === 'completed') {
          // update today count after completion
          try {
            const st = await powerbiRefreshStatus();
            if (typeof (st as any)?.today_count === 'number') setTodayCount((st as any).today_count);
          } catch {}
          closeEs('success');
        } else if (payload.status === 'failed') {
          closeEs('failed');
        } else if (payload.status === 'timeout') {
          closeEs('timeout');
        } else {
          setStatus('processing');
        }
      } catch {
        // ignore parse errors
      }
    });
    es.addEventListener('error', async () => {
      if (finishedRef.current) return;
      // Fallback: query latest status once to disambiguate
      try {
        const st = await powerbiRefreshStatus();
        const latest = (st as any)?.latest;
        if (latest?.status === 'Completed') {
          try {
            if (typeof (st as any)?.today_count === 'number') setTodayCount((st as any).today_count);
          } catch {}
          closeEs('success');
          return;
        }
        if (latest?.status === 'Failed') {
          closeEs('failed');
          return;
        }
      } catch {}
      closeEs('error');
    });
  }, [API_BASE, closeEs, notification]);

  const triggerRefresh = useCallback(async () => {
    try {
      const res = await powerbiTriggerRefresh();
      if (!res.ok) {
        message.error('Failed to start Power BI refresh');
        return;
      }
      startEs();
    } catch (e) {
      message.error('Failed to start Power BI refresh');
    }
  }, [message, startEs]);

  const value = useMemo(() => ({ status, todayCount, triggerRefresh }), [status, todayCount, triggerRefresh]);
  // Initial fetch of today's count on mount
  useEffect(() => {
    (async () => {
      try {
        const st = await powerbiRefreshStatus();
        if (typeof (st as any)?.today_count === 'number') setTodayCount((st as any).today_count);
      } catch {}
    })();
  }, []);
  return <PBIRefreshContext.Provider value={value}>{children}</PBIRefreshContext.Provider>;
};


