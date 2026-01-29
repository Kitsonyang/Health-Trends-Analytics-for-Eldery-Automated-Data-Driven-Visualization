/**
 * Symptom Category Management Page Component
 * 
 * CRUD interface for managing symptom-to-category mappings with auto-discovery
 * of missing symptoms from patient data.
 * 
 * @component
 */

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost, apiPut } from '../api/client';
import { Layout, Menu, Badge, Space, Input, Table, Select, Button, Modal, Pagination, Spin, Empty, Alert, Tooltip, Popconfirm, message, Switch, Card } from 'antd';

interface Category {
  id: number;
  category: string;
}

interface ExistingItem { symptom: string; category_id: number | null; category?: string }

export default function SymptomsVsCategories() {
  const [activeTab, setActiveTab] = useState<'missing' | 'existing'>('missing');
  const [initialLoading, setInitialLoading] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const [categories, setCategories] = useState<Category[]>([]);
  const [categoryCounts, setCategoryCounts] = useState<Record<number, number>>({});
  const [symptomTotalCount, setSymptomTotalCount] = useState(0);
  const [catLoading, setCatLoading] = useState(false);
  const [catError, setCatError] = useState<string | null>(null);
  const [categorySearch, setCategorySearch] = useState('');
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [editCategoryId, setEditCategoryId] = useState<number | null>(null);
  const [editCategoryName, setEditCategoryName] = useState('');
  const [catSavingId, setCatSavingId] = useState<number | null>(null);

  const [result, setResult] = useState<{ inserted: number; missing_items: string[] } | null>(null);
  const [missingTypes, setMissingTypes] = useState<Record<string, 'new' | 'existing_null'>>({});
  const [selections, setSelections] = useState<Record<string, number | ''>>({});
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [insertLoading, setInsertLoading] = useState(false);

  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [refreshIntervalSec, setRefreshIntervalSec] = useState<number>(30);
  const [countdownSec, setCountdownSec] = useState<number>(30);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date | null>(null);

  const [existingItems, setExistingItems] = useState<ExistingItem[]>([]);
  const [existingSearch, setExistingSearch] = useState('');
  const [existingCategoryFilter, setExistingCategoryFilter] = useState<number | ''>('');
  const [existingPage, setExistingPage] = useState(1);
  const [existingPageSize, setExistingPageSize] = useState(25);
  const [existingSelections, setExistingSelections] = useState<Record<string, number | null>>({});
  const [existingSavingSymptom, setExistingSavingSymptom] = useState<string | null>(null);
  const [editModal, setEditModal] = useState<{ open: boolean; oldSymptom: string; name: string; categoryId: number | '' } | null>(null);

  const missingItems = useMemo(() => result?.missing_items ?? [], [result]);
  const filteredCategories = useMemo(() => {
    const q = categorySearch.trim().toLowerCase();
    if (!q) return categories;
    return categories.filter((c) => c.category.toLowerCase().includes(q));
  }, [categories, categorySearch]);

  async function fetchCategories() {
    setCatLoading(true);
    setCatError(null);
    setGlobalError(null);
    try {
      const data = await apiGet<any>('/api/categories');
      if (!data.ok) throw new Error(data?.error || 'Failed to load categories');
      setCategories(data.items || []);
    } catch (e: any) {
      const errorMessage = e.message || 'Failed to load categories';
      setCatError(errorMessage);
      setGlobalError(errorMessage);
      message.error(errorMessage);
    } finally {
      setCatLoading(false);
    }
  }

  async function fetchCategoryCounts() {
    try {
      const data = await apiGet<any>('/api/symptoms');
      if (!data.ok) return;
      const items = (data.items || []) as Array<{ category_id: number | null }>
      setSymptomTotalCount(items.length || 0);
      const counts: Record<number, number> = {};
      for (const it of items) {
        if (typeof it.category_id === 'number') counts[it.category_id] = (counts[it.category_id] || 0) + 1;
      }
      setCategoryCounts(counts);
    } catch (error: any) {
      console.error('Failed to fetch category counts:', error);
      const errorMessage = 'Failed to load category statistics. Please refresh the page.';
      setGlobalError(errorMessage);
      message.error(errorMessage);
    }
  }

  async function fetchExisting(categoryIdOverride?: number | '') {
    const params = new URLSearchParams();
    params.set('search', existingSearch.trim());
    const effCategory = categoryIdOverride !== undefined ? categoryIdOverride : existingCategoryFilter;
    if (effCategory !== '') params.set('category_id', String(effCategory));
    const data = await apiGet<any>(`/api/symptoms?${params.toString()}`);
    if (!data.ok) { message.error(data?.error || 'Failed to load symptoms'); return; }
    const items = (data.items || []) as ExistingItem[];
    setExistingItems(items);
    const sel: Record<string, number | null> = {};
    for (const it of items) sel[it.symptom] = it.category_id ?? null;
    setExistingSelections(sel);
      setExistingPage(1);
  }

  async function handleScan() {
    setResult(null);
    try {
      const data = await apiPost<any>(`/api/process_risk_factors?dry_run=true&risk_col=${encodeURIComponent('M-Risk Factors')}`);
      if (!data.ok) throw new Error(data?.error || 'Request failed');
      const unassignedResp = await apiGet<any>(`/api/symptoms?unassigned=true`);
      if (!unassignedResp.ok) throw new Error(unassignedResp?.error || 'Failed to load unassigned symptoms');

      // Clean and trim inputs
      const unassignedList: string[] = (unassignedResp.items || [])
        .map((it: any) => (typeof it?.symptom === 'string' ? it.symptom.trim() : ''))
        .filter((s: string) => !!s);
      const missingNew: string[] = (data.missing_items ?? [])
        .map((s: any) => (typeof s === 'string' ? s.trim() : ''))
        .filter((s: string) => !!s);

      // Deduplicate by normalized key, prefer DB (unassigned) display string
      const mergedMap = new Map<string, string>();
      for (const s of unassignedList) {
        const k = s.toLowerCase();
        if (!mergedMap.has(k)) mergedMap.set(k, s);
      }
      for (const s of missingNew) {
        const k = s.toLowerCase();
        if (!mergedMap.has(k)) mergedMap.set(k, s);
      }
      const mergedList = Array.from(mergedMap.values());

      // Build types with precedence: existing_null overrides new
      const unassignedNorms = new Set(unassignedList.map((s) => s.toLowerCase()));
      const missingNorms = new Set(missingNew.map((s) => s.toLowerCase()));
      const typeMap: Record<string, 'new' | 'existing_null'> = {};
      for (const s of mergedList) {
        const k = s.toLowerCase();
        typeMap[s] = unassignedNorms.has(k) ? 'existing_null' : (missingNorms.has(k) ? 'new' : 'new');
      }
      setMissingTypes(typeMap);

      setResult({ inserted: data.inserted ?? 0, missing_items: mergedList });
      const initSel: Record<string, number | ''> = {};
      for (const s of mergedList) initSel[s] = '';
      setSelections(initSel);
      setPage(1);
    } catch (e: any) {
      message.error(e.message || 'Request failed');
    }
  }

  // Silent background scan for missing list with change detection
  async function silentScan() {
    if (refreshing) return;
    try {
      setRefreshing(true);
      const data = await apiPost<any>(`/api/process_risk_factors?dry_run=true&risk_col=${encodeURIComponent('M-Risk Factors')}`);
      if (!data.ok) throw new Error(data?.error || 'Request failed');
      const unassignedResp = await apiGet<any>(`/api/symptoms?unassigned=true`);
      if (!unassignedResp.ok) throw new Error(unassignedResp?.error || 'Failed to load unassigned symptoms');

      const unassignedList: string[] = (unassignedResp.items || [])
        .map((it: any) => (typeof it?.symptom === 'string' ? it.symptom.trim() : ''))
        .filter((s: string) => !!s);
      const missingNew: string[] = (data.missing_items ?? [])
        .map((s: any) => (typeof s === 'string' ? s.trim() : ''))
        .filter((s: string) => !!s);

      const mergedMap = new Map<string, string>();
      for (const s of unassignedList) { const k = s.toLowerCase(); if (!mergedMap.has(k)) mergedMap.set(k, s); }
      for (const s of missingNew) { const k = s.toLowerCase(); if (!mergedMap.has(k)) mergedMap.set(k, s); }
      const mergedList = Array.from(mergedMap.values());

      // Compare normalized sets
      const currentList = (result?.missing_items ?? []).map((s) => s.trim()).filter(Boolean);
      const curSet = new Set(currentList.map((s) => s.toLowerCase()));
      const newSet = new Set(mergedList.map((s) => s.toLowerCase()));
      let changed = false;
      if (curSet.size !== newSet.size) changed = true; else {
        for (const n of newSet) { if (!curSet.has(n)) { changed = true; break; } }
      }

      if (changed) {
        const unassignedNorms = new Set(unassignedList.map((s) => s.toLowerCase()));
        const missingNorms = new Set(missingNew.map((s) => s.toLowerCase()));
        const typeMap: Record<string, 'new' | 'existing_null'> = {};
        for (const s of mergedList) {
          const k = s.toLowerCase();
          typeMap[s] = unassignedNorms.has(k) ? 'existing_null' : (missingNorms.has(k) ? 'new' : 'new');
        }
        setMissingTypes(typeMap);
        setResult({ inserted: data.inserted ?? 0, missing_items: mergedList });
        setSelections((prev) => {
          const next: Record<string, number | ''> = {};
          for (const s of mergedList) next[s] = prev[s] ?? '';
          return next;
        });
        setPage(1);
      }
      setLastRefreshedAt(new Date());
    } catch (e: any) {
      // Silent failure to not interrupt user
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => { fetchCategories(); }, []);
  useEffect(() => { if (categories.length > 0) fetchCategoryCounts(); }, [categories]);
  useEffect(() => {
    if (activeTab === 'existing') fetchExisting();
  }, [activeTab]);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try { setInitialLoading(true); await handleScan(); } finally { if (!cancelled) setInitialLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  // auto countdown for missing tab
  useEffect(() => {
    if (activeTab !== 'missing' || !autoRefresh) return;
    setCountdownSec(refreshIntervalSec);
    const tick = setInterval(() => {
      setCountdownSec((prev) => {
        if (prev <= 1) {
          // trigger refresh
          silentScan();
          return refreshIntervalSec;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(tick);
  }, [activeTab, autoRefresh, refreshIntervalSec]);
  useEffect(() => {
    if (selectedCategoryId !== null) {
      setExistingCategoryFilter(selectedCategoryId);
      setExistingPage(1);
      setActiveTab('existing');
      fetchExisting(selectedCategoryId);
    }
  }, [selectedCategoryId]);

  function startEditCategory(c: Category) { setEditCategoryId(c.id); setEditCategoryName(c.category); }
  function cancelEditCategory() { setEditCategoryId(null); setEditCategoryName(''); }
  async function saveCategoryName(catId: number) {
    const name = editCategoryName.trim();
    if (!name) { message.error('Category name is required'); return; }
    try {
      setCatSavingId(catId);
      // Use apiPut for category update (REST standard)
      const response = await apiPut<{ ok: boolean; error?: string }>(`/api/categories/${catId}`, { category: name });
      if (!response.ok) throw new Error(response?.error || `Update failed`);
      setCategories((prev) => prev.map((c) => c.id === catId ? { ...c, category: name } : c));
      message.success('Category updated');
      cancelEditCategory();
    } catch (e: any) { message.error(e.message || 'Update failed'); } finally { setCatSavingId(null); }
  }

  function setSelection(symptom: string, categoryId: number | '') { setSelections((prev) => ({ ...prev, [symptom]: categoryId })); }

  const filteredMissing = useMemo(() => {
    const q = search.trim().toLowerCase();
    let list = missingItems;
    if (q) list = list.filter((s) => s.toLowerCase().includes(q));
    return list;
  }, [missingItems, search]);

  const totalPages = Math.max(1, Math.ceil(filteredMissing.length / pageSize));
  useEffect(() => { if (page > totalPages) setPage(totalPages); }, [totalPages, page]);
  const pageStart = (page - 1) * pageSize;
  const pageItems = filteredMissing.slice(pageStart, pageStart + pageSize);

  async function handleSaveSingle(symptom: string) {
    const cid = selections[symptom];
    if (cid === '' || typeof cid !== 'number') { message.error('Please select a category for this symptom'); return; }
    const t = missingTypes[symptom];
    try {
      setInsertLoading(true);
      if (t === 'existing_null') {
        const upd = await apiPost<any>('/api/symptoms/update_many', { items: [{ symptom, category_id: cid }] });
        if (!upd.ok) throw new Error(upd?.error || 'Update failed');
      } else {
        const ins = await apiPost<any>('/api/symptoms/insert_many', { items: [{ symptom, category_id: cid }] });
        if (!ins.ok) throw new Error(ins?.error || 'Insert failed');
      }
      setResult((prev) => prev ? { ...prev, missing_items: prev.missing_items.filter((s) => s !== symptom) } : prev);
      setSelections((prev) => { const next = { ...prev } as Record<string, number | ''>; delete next[symptom]; return next; });
      setMissingTypes((prev) => { const next = { ...prev } as Record<string, 'new' | 'existing_null'>; delete next[symptom]; return next; });
      message.success('Saved');
    } catch (e: any) { message.error(e.message || 'Save failed'); } finally { setInsertLoading(false); }
  }

  function openEdit(symptom: string, categoryId: number | null) { setEditModal({ open: true, oldSymptom: symptom, name: symptom, categoryId: categoryId ?? '' }); }
  function closeEdit() { setEditModal(null); }
  async function saveEdit() {
    if (!editModal) return;
    const name = (editModal.name || '').trim();
    if (!name) { message.error('Symptom name is required'); return; }
    try {
      if (name !== editModal.oldSymptom) {
        const data = await apiPost<any>('/api/symptoms/rename', { old_symptom: editModal.oldSymptom, new_symptom: name });
        if (!data.ok) throw new Error(data?.error || 'Rename failed');
      }
      const cid = editModal.categoryId === '' ? null : Number(editModal.categoryId);
      const upd = await apiPost<any>('/api/symptoms/update_many', { items: [{ symptom: name, category_id: cid }] });
      if (!upd.ok) throw new Error(upd?.error || 'Update category failed');
      message.success('Saved');
      closeEdit();
      await fetchExisting();
      await handleScan();
    } catch (e: any) { message.error(e.message || 'Save failed'); }
  }

  const missingColumns = useMemo(() => [
    { title: 'Symptom', dataIndex: 'symptom', key: 'symptom', ellipsis: { showTitle: false }, render: (text: string) => (<Tooltip title={text}><span>{text}</span></Tooltip>) },
    { title: 'Category', key: 'category', render: (_: any, record: any) => (
                  <Select 
        value={selections[record.symptom] === '' ? '' : selections[record.symptom]}
        onChange={(v) => setSelection(record.symptom, v === undefined ? '' as any : (v === '' ? '' as any : Number(v)))}
                        style={{ width: '100%' }}
                        placeholder="Select category..."
        options={[{ value: '', label: (<span style={{ color: '#ff4d4f' }}>Unassigned</span>) }, ...categories.map((c) => ({ value: c.id, label: c.category }))]}
                        allowClear
                      />
    ) },
    { title: 'Actions', key: 'actions', width: 160, render: (_: any, record: any) => (
      selections[record.symptom] === '' ? (
        <span style={{ color: '#9ca3af', fontStyle: 'italic' }}>Please select category</span>
      ) : (
        <Button type="primary" onClick={() => handleSaveSingle(record.symptom)} loading={insertLoading}>Save</Button>
      )
    ) }
  ], [categories, selections, insertLoading]);

  const existingColumns = useMemo(() => [
    { title: 'Symptom', dataIndex: 'symptom', key: 'symptom', ellipsis: { showTitle: false }, render: (text: string) => (<Tooltip title={text}><span>{text}</span></Tooltip>) },
    { title: 'Category', key: 'category', render: (_: any, it: ExistingItem) => (
                <Select 
        value={existingSelections[it.symptom] === null ? '' : (existingSelections[it.symptom] ?? '')}
                        onChange={async (v) => {
          const newVal = (v === undefined || v === '') ? null : Number(v);
                          const prevVal = existingSelections[it.symptom] ?? null;
                          setExistingSelections((prev) => ({ ...prev, [it.symptom]: newVal }));
                          setExistingSavingSymptom(it.symptom);
                          try {
                            const upd = await apiPost<any>('/api/symptoms/update_many', { items: [{ symptom: it.symptom, category_id: newVal }] });
                            if (!upd.ok) throw new Error(upd?.error || 'Update failed');
                            message.success('Updated');
                            fetchCategoryCounts();
                          } catch (err: any) {
                            setExistingSelections((prev) => ({ ...prev, [it.symptom]: prevVal }));
                            message.error(err?.message || 'Update failed');
                          } finally {
                            setExistingSavingSymptom(null);
                          }
                        }}
                        disabled={existingSavingSymptom === it.symptom}
                        style={{ width: '100%' }}
                        placeholder="Unassigned"
        options={[{ value: '', label: (<span style={{ color: '#ff4d4f' }}>Unassigned</span>) }, ...categories.map((c) => ({ value: c.id, label: c.category }))]}
                        allowClear
                      />
    ) },
    { title: 'Actions', key: 'actions', width: 200, render: (_: any, it: ExistingItem) => (
      <Space>
        <Button type="primary" onClick={() => openEdit(it.symptom, existingSelections[it.symptom] ?? null)}>Edit</Button>
        <Popconfirm 
          title={`Delete "${(it.symptom || '').trim()}"?`} 
          description="This action cannot be undone." 
          okText="Delete" 
          okButtonProps={{ danger: true }} 
          zIndex={2000}
          onConfirm={async () => {
            const target = (it.symptom || '').trim();
            try {
              const resp = await apiPost<any>('/api/symptoms/delete', { symptom: target });
              if (!resp?.ok) throw new Error(resp?.error || 'Delete failed');
              if (!resp?.deleted || resp.deleted <= 0) {
                throw new Error('No record deleted. It may not exist.');
              }
              setExistingItems((prev) => prev.filter((row) => row.symptom !== target));
              setExistingSelections((prev) => { const n = { ...prev }; delete n[target]; return n; });
              fetchCategoryCounts();
              message.success('Deleted');
              await handleScan();
            } catch (e: any) {
              message.error(e?.message || 'Delete failed');
            }
          }}
        >
          <Button danger>Delete</Button>
        </Popconfirm>
      </Space>
    ) }
  ], [categories, existingSelections, existingSavingSymptom]);

  const missingData = useMemo(() => pageItems.map((s) => ({ key: s, symptom: s })), [pageItems]);
  const existingData = useMemo(() => existingItems.slice((existingPage - 1) * existingPageSize, (existingPage - 1) * existingPageSize + existingPageSize).map((it) => ({ ...it, key: it.symptom })), [existingItems, existingPage, existingPageSize]);

  function handleMenuClick(key: string) {
    if (key === 'missing') { setActiveTab('missing'); setSelectedCategoryId(null); setExistingCategoryFilter(''); handleScan(); return; }
    if (key === 'all') { setActiveTab('existing'); setSelectedCategoryId(null); setExistingCategoryFilter(''); fetchExisting(''); return; }
    if (key.startsWith('cat-')) { const id = Number(key.slice(4)); if (!Number.isNaN(id)) setSelectedCategoryId(id); }
  }
  const selectedMenuKey = selectedCategoryId !== null ? `cat-${selectedCategoryId}` : (activeTab === 'missing' ? 'missing' : 'all');

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: 20 }}>
      {globalError && (
        <Alert
          type="error"
          showIcon
          message="Error"
          description={globalError}
          closable
          onClose={() => setGlobalError(null)}
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" type="primary" onClick={() => {
              setGlobalError(null);
              fetchCategories();
              fetchCategoryCounts();
            }}>
              Retry
            </Button>
          }
        />
      )}
    <section style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 16, padding: 12, boxShadow: 'var(--shadow-sm)' }}>
    <Layout style={{ background: 'transparent', overflow: 'visible', columnGap: 16 }}>
      <Layout.Sider collapsible={false} width={400} style={{ background: 'transparent', border: 'none', borderRadius: 0, padding: 16, boxShadow: 'none' }}>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <div style={{ fontWeight: 700, fontSize: 16 }}>Category Management</div>
          <Input.Search placeholder="Search categories..." value={categorySearch} onChange={(e) => setCategorySearch(e.target.value)} allowClear />
          {catLoading ? (
            <div><Spin size="small" /></div>
          ) : catError ? (
            <Alert type="error" showIcon message={catError} />
          ) : (
            <Menu 
              mode="inline"
              selectedKeys={[selectedMenuKey]}
              onClick={({ key }) => handleMenuClick(String(key))}
              items={[
                { key: 'missing', label: (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Missing Symptoms</span>
                    <Badge count={missingItems.length} showZero size="small" styles={{ indicator: { backgroundColor: '#ff4d4f' } }} />
                  </div>
                ) },
                { key: 'all', label: (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>All Symptoms</span>
                    <span style={{ color: '#595959', fontVariantNumeric: 'tabular-nums' }}>{symptomTotalCount}</span>
                  </div>
                ) },
                { key: 'header', label: `Database Categories (${categories.length})`, disabled: true },
                ...filteredCategories.map((c) => ({
                  key: `cat-${c.id}`,
                  label: (
                    editCategoryId === c.id ? (
                      <div onClick={(e) => e.stopPropagation()}>
                        <Space.Compact style={{ width: '100%' }}>
                          <Input value={editCategoryName} onChange={(e) => setEditCategoryName(e.target.value)} autoFocus />
                          <Button type="primary" loading={catSavingId === c.id} onClick={(e) => { e.stopPropagation(); saveCategoryName(c.id); }}>Save</Button>
                          <Button onClick={(e) => { e.stopPropagation(); cancelEditCategory(); }}>Cancel</Button>
                        </Space.Compact>
                    </div>
                    ) : (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }} onDoubleClick={(e) => { e.stopPropagation(); startEditCategory(c); }} title="Double-click to rename">
                        <Tooltip title={c.category} mouseEnterDelay={0.3}>
                          <span style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'inline-block' }}>{c.category}</span>
                        </Tooltip>
                        <span style={{ color: '#595959', fontVariantNumeric: 'tabular-nums' }}>{categoryCounts[c.id] || 0}</span>
                    </div>
                    )
                  )
                }))
              ]}
            />
          )}
        </Space>
      </Layout.Sider>
      <Layout.Content style={{ padding: 0 }}>
        <div style={{ padding: 0 }}>
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          {activeTab === 'missing' ? (
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: 240 }}>
                <Input.Search placeholder="Search symptoms..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} allowClear />
              </div>
              <Space size={8} wrap>
                <span style={{ color: '#595959' }}>Auto</span>
                <Switch checked={autoRefresh} onChange={(v) => setAutoRefresh(v)} />
                <span style={{ color: '#595959' }}>Interval</span>
                <Select
                  size="small"
                  value={refreshIntervalSec}
                  onChange={(v) => setRefreshIntervalSec(Number(v))}
                  options={[15, 30, 60, 120].map((v) => ({ value: v, label: `${v}s` }))}
                  style={{ width: 88 }}
                />
                <span style={{ color: '#8c8c8c' }}>{refreshing ? 'Refreshing...' : `Next: ${countdownSec}s`}{lastRefreshedAt ? ` · Updated: ${lastRefreshedAt.toLocaleTimeString()}` : ''}</span>
                <Button size="small" onClick={() => { setCountdownSec(refreshIntervalSec); silentScan(); }} loading={refreshing}>
                  Refresh Now
                </Button>
              </Space>
            </div>
          ) : (
            <DebouncedExistingSearch value={existingSearch} onChange={(v) => { setExistingSearch(v); setExistingPage(1); fetchExisting(); }} />
          )}
          {initialLoading ? (
            <div style={{ padding: 40, textAlign: 'center' }}><Spin tip="Scanning for missing items..." /></div>
          ) : activeTab === 'missing' ? (
            <>
              <Alert
                type="info"
                showIcon
                message="Why do Missing Symptoms appear?"
                description={
                  <div style={{ fontSize: 12, lineHeight: 1.6 }}>
                    <div>The system scans the "risk factors" field to extract symptom terms and compares them with the symptom library:</div>
                    <div>- Terms not found in the library are marked as "missing"</div>
                    <div>- Terms found but without an assigned category are marked as "unassigned"</div>
                    <div>After assigning categories and saving, these items will disappear from the list.</div>
                  </div>
                }
                style={{ marginTop: 4, marginBottom: 12 }}
                closable
              />
              <Card bordered style={{ borderRadius: 12, overflow: 'hidden', boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)' }}>
              <Table 
                dataSource={missingData}
                columns={missingColumns}
                pagination={false}
                size="middle"
                sticky
                scroll={{ y: 'calc(100vh - 460px)' }}
                locale={{ emptyText: <Empty description="No symptoms found. Please adjust filter or add categories" /> }}
              />
              </Card>
              <div style={{ display: 'flex', justifyContent: 'center', marginTop: 12 }}>
                <Pagination current={page} pageSize={pageSize} total={filteredMissing.length} showSizeChanger pageSizeOptions={[10,25,50,100]} onChange={(p, ps) => { setPage(p); setPageSize(ps); }} />
                  </div>
            </>
          ) : (
            <>
              <Card bordered style={{ borderRadius: 12, overflow: 'hidden', boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)', marginBottom: 12 }}>
              <Table 
                dataSource={existingData}
                columns={existingColumns}
                rowKey="symptom"
                pagination={false}
                size="middle"
                sticky
                scroll={{ y: 'calc(100vh - 400px)' }}
                locale={{ emptyText: <Empty description="No symptoms found. Please adjust filter or add categories." /> }}
              />
              </Card>
              <div style={{ display: 'flex', justifyContent: 'center', marginTop: 12 }}>
                <Pagination current={existingPage} pageSize={existingPageSize} total={existingItems.length} showSizeChanger pageSizeOptions={[10,25,50,100]} onChange={(p, ps) => { setExistingPage(p); setExistingPageSize(ps); }} />
            </div>
              <Modal centered title="Edit Symptom" open={!!editModal?.open} onCancel={closeEdit} onOk={saveEdit} okText="Save">
              {editModal && (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <div style={{ marginBottom: 6, fontWeight: 600 }}>Symptom Name</div>
                    <Input value={editModal.name} onChange={(e) => setEditModal((m) => (m ? { ...m, name: e.target.value } : m))} />
                  </div>
                  <div>
                    <div style={{ marginBottom: 6, fontWeight: 600 }}>Category</div>
                      <Select value={editModal.categoryId === '' ? undefined : editModal.categoryId} onChange={(v) => setEditModal((m) => (m ? { ...m, categoryId: v === undefined ? '' : Number(v) } : m))} allowClear style={{ width: '100%' }} placeholder="Unassigned" options={categories.map((c) => ({ value: c.id, label: c.category }))} />
                  </div>
                </Space>
              )}
            </Modal>
            </>
          )}
        </Space>
        </div>
      </Layout.Content>
    </Layout>
    </section>
    </div>
  );
}

function DebouncedExistingSearch({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [inner, setInner] = useState(value);
  useEffect(() => { setInner(value); }, [value]);
  useEffect(() => {
    const t = setTimeout(() => { if (inner !== value) onChange(inner); }, 300);
    return () => clearTimeout(t);
  }, [inner]);
  return (
    <Input.Search placeholder="Search symptoms..." value={inner} onChange={(e) => setInner(e.target.value)} allowClear />
  );
}


