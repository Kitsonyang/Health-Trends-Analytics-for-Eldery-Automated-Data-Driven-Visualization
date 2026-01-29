/**
 * Main Application Layout with Sidebar Navigation
 * 
 * Provides core application shell with responsive sidebar navigation,
 * Power BI refresh control, and user profile management.
 * 
 * @component
 */

import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Layout, Menu, Button, Avatar, Tag, Drawer, Grid, Tooltip, App } from 'antd';
import { MenuOutlined, DashboardOutlined, UploadOutlined, AppstoreOutlined, RobotOutlined, ReloadOutlined } from '@ant-design/icons';
import { powerbiRefreshStatus, authLogout } from '../api/client';
import { usePBIRefresh } from '../context/PBIRefreshContext';

interface SidebarLayoutProps {
  children: ReactNode;
}


const menu = [
  { type: 'title', label: 'Dashboard' },
  { path: '/dashboard', label: 'Power BI Dashboard', icon: 'BI', description: 'Interactive analytics' },
  { path: '/refresh-history', label: 'Refresh History', icon: 'BI', description: 'View Power BI refresh history' },

  { type: 'spacer' },
  { type: 'title', label: 'Data Management' },
  { path: '/import', label: 'Import Data', icon: 'IM', description: 'Upload CSV files', roles: ['admin'] },
  { path: '/symptoms', label: 'Symptoms Analysis', icon: 'SY', description: 'Category insights', roles: ['admin'] },

  { type: 'spacer' },
  { type: 'title', label: 'AI & Analytics' },
  { path: '/ml', label: 'Machine Learning', icon: 'ML', description: 'Predictive models' },
];

export default function SidebarLayout({ children }: SidebarLayoutProps) {
  const { username, role, logout } = useAuth();
  const location = useLocation();
  // navigate no longer required; navigation handled in global provider
  const { notification } = App.useApp();

  // Filter menu items based on user role for RBAC
  const filteredMenu = useMemo(
    () => menu.filter((item) => (item as any).type || !role || !('roles' in item) || (item as any).roles.includes(role)),
    [role]
  );

  // Dashboard page uses full-bleed layout (no padding) for iframe
  const isFullBleed = location.pathname === '/dashboard';

  // Persistent sidebar collapse state across sessions
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem('sidebar-collapsed');
      return saved === '1';
    } catch (error) {
      console.error('Failed to read sidebar collapse state from localStorage:', error);
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem('sidebar-collapsed', isCollapsed ? '1' : '0');
    } catch (error) {
      console.error('Failed to save sidebar collapse state to localStorage:', error);
    }
  }, [isCollapsed]);

  // Power BI refresh state from global context
  const { status: pbiStatus, triggerRefresh } = usePBIRefresh();
  const refreshLoading = pbiStatus === 'processing';
  const refreshSuccess = pbiStatus === 'success';
  
  const DEFAULT_DAILY_QUOTA = Number(((import.meta as any).env?.VITE_PBI_DAILY_QUOTA ?? 8));
  const STATUS_CACHE_KEY = 'pbi-status-cache-v1';
  const STATUS_CACHE_TTL_MS = 30_000; // 30s to avoid duplicate requests making it "appear to be refreshing"
  
  const [dailyQuota, setDailyQuota] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('pbi-plan');
      if (saved === 'ppu' || saved === 'premium') return 48;
      if (saved === 'pro') return 8;
    } catch (error) {
      console.error('Failed to read Power BI plan from localStorage:', error);
    }
    return DEFAULT_DAILY_QUOTA;
  });
  
  const [todayCount, setTodayCount] = useState<number | null>(null);

  const sidebarWidth = isCollapsed ? 72 : 280;
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const [mobileOpen, setMobileOpen] = useState(false);

  async function handleRefresh() { await triggerRefresh(); }
  
  // Sync todayCount from global context: Provider updates todayCount after refresh completes
  useEffect(() => {
    (async () => {
      try {
        let cached: any = null; try { cached = JSON.parse(localStorage.getItem(STATUS_CACHE_KEY) || 'null'); } catch {}
        const now = Date.now();
        if (cached && typeof cached.today_count === 'number' && typeof cached.ts === 'number' && (now - cached.ts) < STATUS_CACHE_TTL_MS) {
          setTodayCount(cached.today_count);
          return;
        }
        const status = await powerbiRefreshStatus();
        const tc = typeof (status as any)?.today_count === 'number' ? (status as any).today_count : null;
        if (tc !== null) {
          setTodayCount(tc);
          try { localStorage.setItem(STATUS_CACHE_KEY, JSON.stringify({ today_count: tc, ts: now })); } catch {}
        }
      } catch {}
    })();
  }, [pbiStatus]);

  // Listen for plan changes from Refresh History page
  useEffect(() => {
    function onPlan(evt: any) {
      const quota = Number(evt?.detail?.quota);
      const plan = evt?.detail?.plan;
      if (!Number.isNaN(quota) && quota > 0) {
        setDailyQuota(quota);
      } else if (plan === 'pro') {
        setDailyQuota(8);
      } else if (plan === 'ppu' || plan === 'premium') {
        setDailyQuota(48);
      }
    }
    window.addEventListener('pbi-plan-changed', onPlan as any);
    return () => window.removeEventListener('pbi-plan-changed', onPlan as any);
  }, []);

  

  function iconFor(code?: string) {
    switch (code) {
      case 'BI': return <DashboardOutlined />;
      case 'IM': return <UploadOutlined />;
      case 'SY': return <AppstoreOutlined />;
      case 'ML': return <RobotOutlined />;
      default: return undefined;
    }
  }

  const baseText = refreshLoading ? 'Refreshing...' : (refreshSuccess ? 'Refreshed' : 'Refresh');
  const quotaText = dailyQuota > 0 ? ` ${todayCount !== null ? `(${todayCount}/${dailyQuota})` : `(/${dailyQuota})`}` : '';
  const refreshBtnText = `${baseText}${quotaText}`;
  const refreshTooltip = refreshLoading ? 'Power BI data is refreshing' : (refreshSuccess ? 'Last refresh succeeded' : 'Refresh Power BI data');

  const menuItems = useMemo(() => {
    const items: any[] = [];
    let currentGroup: any = null;
    for (const it of filteredMenu as any[]) {
      if (it.type === 'title') {
        // push previous group only if it has children
        if (currentGroup && currentGroup.children && currentGroup.children.length > 0) {
          items.push(currentGroup);
        }
        currentGroup = { type: 'group', label: it.label, children: [] as any[] };
      } else if (it.type === 'spacer') {
        // ignore spacer
      } else {
        const tooltipText = `${it.description || ''}${it.roles ? (it.description ? ' · ' : '') + 'Admin only' : ''}` || undefined;
        const labelInner = (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span>{it.label}</span>
            {it.roles ? <Tag color="orange" style={{ marginLeft: 0 }}>Admin</Tag> : null}
          </span>
        );
        const labelNode = (
          <Tooltip title={tooltipText}>
            <Link to={it.path}>{labelInner}</Link>
          </Tooltip>
        );
        const child = {
          key: it.path,
          icon: iconFor(it.icon),
          label: labelNode,
        };
        if (currentGroup) currentGroup.children.push(child); else items.push(child);
      }
    }
    // push the last group only if it has children
    if (currentGroup && currentGroup.children && currentGroup.children.length > 0) {
      items.push(currentGroup);
    }
    return items;
  }, [filteredMenu]);

  return (
    <Layout style={{ minHeight: '100vh', background: 'var(--color-bg)' }}>
      <Layout.Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 64, background: 'var(--color-surface)', borderBottom: '1px solid var(--color-border)', paddingInline: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {isMobile && (
            <Button type="text" icon={<MenuOutlined />} onClick={() => setMobileOpen(true)} />
          )}
          <img src="/logo.jpg" alt="Nursing Home Logo" style={{ width: 36, height: 36, borderRadius: 8 }} />
          <div style={{ fontWeight: 700, fontSize: 18 }}>Nursing Home</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Tooltip title={refreshTooltip}>
            <Button 
              type="text" 
              icon={<ReloadOutlined />} 
              onClick={handleRefresh}
              loading={refreshLoading}
              style={{ color: refreshSuccess ? '#52c41a' : undefined, display: 'inline-flex', alignItems: 'center', gap: 6 }}
            >
              {refreshBtnText}
            </Button>
          </Tooltip>
          <Avatar style={{ background: 'var(--color-primary)' }}>{(username || 'U').slice(0,1).toUpperCase()}</Avatar>
          <span>{username}</span>
          <Tag color="blue">{role}</Tag>
          <Button type="primary" onClick={async () => {
            try {
              await authLogout();
              notification.success({
                message: 'Logout Successful',
                description: 'You have been safely logged out',
                duration: 2,
              });
            } catch (error) {
              console.error('Logout API failed:', error);
            } finally {
              logout();
            }
          }}>Logout</Button>
        </div>
      </Layout.Header>
      {/* Removed banner; using notifications instead */}
      <Layout>
        <Layout.Sider 
          collapsible 
          collapsed={isCollapsed} 
          onCollapse={setIsCollapsed} 
          width={sidebarWidth} 
          theme="light" 
          style={{ borderRight: '1px solid var(--color-border)', display: isMobile ? 'none' : 'block' }}
          breakpoint="lg"
        >
          <Menu mode="inline" selectedKeys={[location.pathname]} style={{ height: '100%', borderRight: 0 }} items={menuItems as any} />
        </Layout.Sider>
        <Layout.Content style={{ padding: isFullBleed ? 0 : 16, height: 'calc(100vh - 64px)', overflow: isFullBleed ? 'hidden' : 'auto' }}>
          <div key={location.pathname} style={{ animation: 'crossFade .3s cubic-bezier(.22,.61,.36,1) both' }}>
            {children}
          </div>
        </Layout.Content>
      </Layout>
      <Drawer 
        placement="left" 
        width={260} 
        open={mobileOpen} 
        onClose={() => setMobileOpen(false)} 
        bodyStyle={{ padding: 0 }}
      >
        <Menu mode="inline" selectedKeys={[location.pathname]} items={menuItems as any} onClick={() => setMobileOpen(false)} />
      </Drawer>
    </Layout>
  );
}


