import { useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import { powerbiRefreshStatus } from '../api/client';
import { usePBIRefresh } from '../context/PBIRefreshContext';
import { Table, Radio, Typography, Space, Progress, Card, Row, Col, message, Button } from 'antd';

dayjs.extend(utc);
dayjs.extend(timezone);

export default function PowerBIDebug() {
  const [historyRows, setHistoryRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<'pro' | 'ppu' | 'premium'>(() => {
    try {
      const saved = localStorage.getItem('pbi-plan') as any;
      return saved === 'ppu' || saved === 'premium' ? saved : 'pro';
    } catch {
      return 'pro';
    }
  });

  const dailyQuota = useMemo(() => (plan === 'pro' ? 8 : 48), [plan]);
  const [todayCount, setTodayCount] = useState<number | null>(null);

  const formatToAustralianTime = (timeString: string | null | undefined) => {
    if (!timeString) return '-';
    try {
      const time = dayjs(timeString).tz('Australia/Sydney');
      return time.format('YYYY-MM-DD HH:mm:ss');
    } catch (error) {
      console.error('Error formatting time:', error);
      return timeString;
    }
  };

  const rowsSorted = useMemo(() => {
    return [...historyRows].sort((a, b) => dayjs(b.startTime).valueOf() - dayjs(a.startTime).valueOf());
  }, [historyRows]);

  async function loadStatus() {
    setLoading(true);
    setError(null);
    try {
      console.log('Calling powerbiRefreshStatus API...');
      const res = await powerbiRefreshStatus();
      console.log('API response received:', res);
      if (typeof (res as any)?.today_count === 'number') setTodayCount((res as any).today_count);
      const rows = (res.history || []).map((it: any, idx: number) => ({
        key: idx + 1,
        id: it.id,
        requestId: it.requestId,
        refreshType: it.refreshType,
        startTime: it.startTime,
        endTime: it.endTime,
        status: it.status,
        durationSec: it.startTime && it.endTime ? Math.max(0, (dayjs(it.endTime).valueOf() - dayjs(it.startTime).valueOf())/1000) : undefined,
      }));
      setHistoryRows(rows);
      console.log('Successfully loaded refresh history with', rows.length, 'records');
    } catch (error: any) {
      console.error('Failed to load Power BI refresh history:', error);
      console.error('Error details:', {
        message: error.message,
        status: error.status,
        body: error.body,
        stack: error.stack
      });
      const errorMessage = `Failed to load refresh history: ${error.message || 'Unknown error'}. Please check your connection and try again.`;
      setError(errorMessage);
      message.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    console.log('PowerBIDebug component mounted, loading status...');
    loadStatus();
  }, []);

  const { status: pbiStatus } = usePBIRefresh();
  useEffect(() => {
    if (pbiStatus === 'success' || pbiStatus === 'failed') {
      loadStatus();
    }
  }, [pbiStatus]);

  useEffect(() => {
    try { localStorage.setItem('pbi-plan', plan); } catch (error) {
      console.error('Failed to save plan to localStorage:', error);
    }
    try { window.dispatchEvent(new CustomEvent('pbi-plan-changed', { detail: { plan, quota: dailyQuota } })); } catch (error) {
      console.error('Failed to dispatch plan change event:', error);
    }
  }, [plan, dailyQuota]);

  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
      <h3 style={{ margin: 0 }}>Refresh History</h3>

      {loading && (
        <Card bodyStyle={{ padding: 16 }} style={{ borderRadius: 12 }}>
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div>Loading refresh history...</div>
          </div>
        </Card>
      )}

      {error && (
        <Card bodyStyle={{ padding: 16 }} style={{ borderRadius: 12 }}>
          <div style={{ color: '#ff4d4f', textAlign: 'center', padding: '20px 0' }}>
            <div style={{ marginBottom: 16 }}>{error}</div>
            <Button type="primary" onClick={() => loadStatus()}>
              Retry
            </Button>
          </div>
        </Card>
      )}

      {!loading && !error && (
        <>
          <Card bodyStyle={{ padding: 16 }} style={{ borderRadius: 12 }}>
            <Row gutter={[16, 16]} align="middle">
              <Col xs={24} md={16}>
                <Space direction="vertical" size={10} style={{ width: '100%' }}>
                  <Typography.Text strong>Daily refresh limit</Typography.Text>
                  <Radio.Group
                    value={plan}
                    onChange={(e) => setPlan(e.target.value)}
                    optionType="button"
                    buttonStyle="solid"
                  >
                    <Radio.Button value="pro">Power BI Pro (8/day)</Radio.Button>
                    <Radio.Button value="ppu">Premium Per User (48/day)</Radio.Button>
                    <Radio.Button value="premium">Premium Capacity (48/day)</Radio.Button>
                  </Radio.Group>
                  <Typography.Text type="secondary">Current limit: {dailyQuota} per dataset per day</Typography.Text>
                  <div style={{ color: '#64748b' }}>
                    <div>- Power BI Pro: up to 8 refreshes per dataset per day.</div>
                    <div>- Premium Per User (PPU): up to 48 refreshes per dataset per day.</div>
                    <div>- Premium Capacity: up to 48 refreshes per dataset per day.</div>
                  </div>
                </Space>
              </Col>
              <Col xs={24} md={8}>
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  <Typography.Text strong>Today's refreshes</Typography.Text>
                  <Typography.Title level={4} style={{ margin: 0 }}>{todayCount !== null ? todayCount : '-'} / {dailyQuota}</Typography.Title>
                  <Progress
                    percent={(() => {
                      const tc = todayCount ?? 0;
                      const dq = dailyQuota || 1;
                      return Math.min(100, Math.round((tc / dq) * 100));
                    })()}
                    size="small"
                  />
                </Space>
              </Col>
            </Row>
          </Card>
          <Table
            size="small"
            dataSource={rowsSorted}
            pagination={{ pageSize: 10 }}
            columns={[
              { title: '#', dataIndex: 'key', width: 60 },
              { title: 'Status', dataIndex: 'status' },
              { title: 'Type', dataIndex: 'refreshType' },
              { 
                title: 'Start', 
                dataIndex: 'startTime',
                render: (time: string) => formatToAustralianTime(time)
              },
              { 
                title: 'End', 
                dataIndex: 'endTime',
                render: (time: string) => formatToAustralianTime(time)
              },
              { title: 'Duration(s)', dataIndex: 'durationSec', render: (v: any) => (v !== undefined ? Number(v).toFixed(1) : '-') },
              { title: 'RequestId', dataIndex: 'requestId' },
            ]}
            rowKey="key"
          />
        </>
      )}
    </div>
  );
}


