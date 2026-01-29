/**
 * Power BI Dashboard Embed Component
 * 
 * Embeds Power BI dashboard in iframe with automatic refresh capability.
 * 
 * @component
 */

import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';

export default function PowerBIEmbed() {
  const [embedUrl, setEmbedUrl] = useState<string>(() => {
    try { return localStorage.getItem('pbi-embed-url') || ''; } catch { return ''; }
  });
  const [loading, setLoading] = useState<boolean>(() => !Boolean((() => { try { return localStorage.getItem('pbi-embed-url'); } catch { return ''; } })()));
  const [error, setError] = useState<string | null>(null);
  const [iframeKey, setIframeKey] = useState<number>(0);

  useEffect(() => {
    function onPbiRefresh(evt: any) {
      const status = evt?.detail?.status as 'processing' | 'success' | 'failed' | undefined;
      if (status === 'success') {
        // Delay reload to ensure Power BI service has propagated changes
        setTimeout(() => {
          setIframeKey(prev => prev + 1);
        }, 2000);
      }
    }
    window.addEventListener('pbi-refresh-state', onPbiRefresh as any);
    return () => {
      window.removeEventListener('pbi-refresh-state', onPbiRefresh as any);
    };
  }, []);

  // Fetch embed URL from backend at runtime; fallback to env; cache to localStorage to avoid flash
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setError(null);
      setLoading(true);
      try {
        const res = await apiGet<{ ok: boolean; url: string }>('/api/powerbi/embed-url');
        if (!cancelled) {
          const url = (res && res.url) || '';
          setEmbedUrl(url);
          try { localStorage.setItem('pbi-embed-url', url); } catch {}
        }
      } catch (e: any) {
        const envUrl = (import.meta as any).env?.VITE_PBI_EMBED_URL as string | undefined;
        if (envUrl) {
          if (!cancelled) {
            setEmbedUrl(envUrl);
            try { localStorage.setItem('pbi-embed-url', envUrl); } catch {}
          }
        } else {
          if (!cancelled) setError(e?.message || 'Power BI embed URL is not configured');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (!embedUrl) {
    if (loading) {
      return (
        <div style={{ padding: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Loading Power BI…</div>
          <div style={{ color: '#8c8c8c' }}>Please wait while we fetch the embed URL.</div>
        </div>
      );
    }
    return (
      <div style={{ padding: 16 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Failed to load Power BI</div>
        <div style={{ color: '#8c8c8c' }}>{error || 'Server has not configured PBI_EMBED_URL, or a network error occurred.'}</div>
      </div>
    );
  }

  const isHttpsPage = typeof window !== 'undefined' && window.location.protocol === 'https:';
  if (isHttpsPage && embedUrl.startsWith('http://')) {
    return (
      <div style={{ padding: 16 }}>
        <div style={{ fontWeight: 600, marginBottom: 8 }}>Mixed content blocked</div>
        <div style={{ color: '#8c8c8c' }}>This site uses HTTPS but the Power BI URL is HTTP. Please set PBI_EMBED_URL to an https link on the server.</div>
        <div style={{ marginTop: 12 }}>
          <a href={embedUrl} target="_blank" rel="noreferrer">Open in a new window</a>
        </div>
      </div>
    );
  }

  return (
    <div style={{ height: 'calc(100vh - 56px)', width: '100%' }}>
      <iframe
        key={iframeKey}
        title="Power BI Dashboard"
        src={embedUrl}
        style={{ border: 'none', width: '100%', height: '100%', display: 'block' }}
        allowFullScreen
      />
    </div>
  );
}


