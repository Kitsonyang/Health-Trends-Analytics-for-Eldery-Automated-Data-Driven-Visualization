/**
 * CSV Data Import Page Component
 * 
 * Multi-step wizard for importing patient data from CSV files with validation,
 * preview, and optional Power BI refresh trigger.
 * 
 * @component
 */

import { useEffect, useRef, useState } from 'react';
import { Upload, Button, Steps, message, Table, Input, InputNumber, Select, DatePicker, Spin, Result, Card, Statistic, Checkbox, Popconfirm, Space, Radio, Modal, App, Alert, Tooltip } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { API_BASE } from '../api/client';

async function fetchWithTimeout(url: string, options: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
        throw new Error(`Request timeout after 60000ms`);
    }
    throw error;
  }
}

import dayjs from 'dayjs';
import { usePBIRefresh } from '../context/PBIRefreshContext';
 

type Step = 'select' | 'preview' | 'mode' | 'importing' | 'done' | 'manual';
type Mode = 'overwrite' | 'append';

interface PreviewResp {
  ok: boolean;
  token: string;
  filename: string;
  total_rows: number;
  csv_columns: string[];
  expected_columns: string[];
  missing_in_csv: string[];
  missing_in_db: string[];
  csv_to_expected: Record<string, string | null>;
  expected_to_db: Record<string, string | null>;
  can_import: boolean;
  preview: Array<Record<string, any>>;
}

export default function ImportFiles() {
  App.useApp();
  // Robustly parse MAX upload size: treat missing/empty/invalid as default 100MB
  const __rawMaxUpload = (import.meta as any).env?.VITE_MAX_UPLOAD_MB;
  const MAX_UPLOAD_MB = (() => {
    const n = Number(__rawMaxUpload);
    return Number.isFinite(n) && n > 0 ? n : 100;
  })();
  const [step, setStep] = useState<Step>('select');
  const [token, setToken] = useState<string>('');
  const [filename, setFilename] = useState<string>('');
  const [totalRows, setTotalRows] = useState<number>(0);
  const [csvColumns, setCsvColumns] = useState<string[]>([]);
  const [expectedColumns, setExpectedColumns] = useState<string[]>([]);
  const [missingCsv, setMissingCsv] = useState<string[]>([]);
  const [missingDb, setMissingDb] = useState<string[]>([]);
  const [canImport, setCanImport] = useState<boolean>(false);
  const [previewRows, setPreviewRows] = useState<Array<Record<string, any>>>([]);
  const [csvMap, setCsvMap] = useState<Record<string, string | null>>({}); // expected -> CSV
  const [dbMap, setDbMap] = useState<Record<string, string | null>>({});    // expected -> DB
  const [mode, setMode] = useState<Mode>('append');
  const [loading, setLoading] = useState<boolean>(false);
  // messages via antd message
  // DB statistics
  const [dbTotalRows, setDbTotalRows] = useState<number | null>(null);
  const [dbUniquePersons, setDbUniquePersons] = useState<number | null>(null);
  const [statsLoading, setStatsLoading] = useState<boolean>(false);

  const fileRef = useRef<HTMLInputElement | null>(null);
  const [overwriteConfirmed, setOverwriteConfirmed] = useState<boolean>(false);
  // Power BI refresh flow
  const [refreshModalOpen, setRefreshModalOpen] = useState<boolean>(false);
  const [refreshMessage, setRefreshMessage] = useState<string>('');
  const pollingRef = useRef<{ active: boolean; attempts: number } | null>(null);
  const { triggerRefresh: triggerRefreshGlobal } = usePBIRefresh();
  // manual input
  const [manualColumns] = useState<string[]>([
    'PersonID',
    'Start date',
    'End date',
    'M-Risk Factors',
    'Gender',
    'Age',
    'MNA',
    'BMI',
    'Weight',
  ]);
  const [manualRows, setManualRows] = useState<Array<Record<string, string>>>([
    Object.fromEntries([
      'PersonID','Start date','End date','M-Risk Factors','Gender','Age','MNA','BMI','Weight',
    ].map((k) => [k, ''])) as Record<string, string>,
  ]);
  const manualMinWidth: Record<string, number> = {
    'PersonID': 160,
    'Start date': 180,
    'End date': 180,
    'M-Risk Factors': 420,
    'Gender': 140,
    'Age': 120,
    'MNA': 120,
    'BMI': 120,
    'Weight': 140,
  };
  const [manualErrors, setManualErrors] = useState<Array<Record<string, string | null>>>([
    Object.fromEntries([
      'PersonID','Start date','End date','M-Risk Factors','Gender','Age','MNA','BMI','Weight',
    ].map((k) => [k, null])) as Record<string, string | null>,
  ]);

  useEffect(() => {
    if (mode === 'append') setOverwriteConfirmed(false);
  }, [mode]);

  useEffect(() => {
    fetchDbStats();
  }, []);

  useEffect(() => {
    return () => {
      if (pollingRef.current) pollingRef.current.active = false;
    };
  }, []);

  function resetAll() {
    setStep('select');
    setToken('');
    setFilename('');
    setTotalRows(0);
    setCsvColumns([]);
    setExpectedColumns([]);
    setMissingCsv([]);
    setMissingDb([]);
    setCanImport(false);
    setPreviewRows([]);
    setMode('append');
    setLoading(false);
    
    if (fileRef.current) fileRef.current.value = '';
    setManualRows([
      Object.fromEntries(manualColumns.map((c) => [c, ''])) as Record<string, string>,
    ]);
    setManualErrors([
      Object.fromEntries(manualColumns.map((c) => [c, null])) as Record<string, string | null>,
    ]);
    fetchDbStats();
  }

  async function fetchDbStats() {
    setStatsLoading(true);
    try {
      const res = await fetchWithTimeout(`${API_BASE}/api/data/stats`);
      const data = await res.json();
      if (res.ok && data?.ok) {
        setDbTotalRows(Number(data.total_rows) || 0);
        setDbUniquePersons(Number(data.unique_persons) || 0);
      }
    } catch (e) {
      // ignore stats failure; do not block page
    } finally {
      setStatsLoading(false);
    }
  }

  async function handleUpload(file: File) {
    setLoading(true);
    try {
      if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
        throw new Error(`File too large. Max ${MAX_UPLOAD_MB} MB`);
      }
      const form = new FormData();
      form.append('file', file);
      const res = await fetchWithTimeout(`${API_BASE}/api/import/preview`, { method: 'POST', body: form });
      if (res.status === 413) {
        throw new Error(`File too large. Max ${MAX_UPLOAD_MB} MB`);
      }
      
      // Check response status
      if (!res.ok) {
        const errorText = await res.text();
        try {
          const errorData = JSON.parse(errorText);
          throw new Error(errorData.detail?.error || errorData.detail || `Server error (${res.status})`);
        } catch (parseError) {
          throw new Error(`Server error (${res.status}): ${errorText}`);
        }
      }
      
      // Try parse JSON
      let data;
      try {
        data = await res.json();
      } catch (jsonError) {
        throw new Error('Server returned invalid response format. Please verify your file.');
      }
      
      if (!data?.ok) {
        throw new Error(typeof data?.detail === 'string' ? data.detail : (data?.detail?.error || 'Upload failed'));
      }
      
      const d = data as PreviewResp;
      setToken(d.token);
      setFilename(d.filename);
      setTotalRows(d.total_rows);
      setCsvColumns(d.csv_columns || []);
      setExpectedColumns(d.expected_columns || []);
      setMissingCsv(d.missing_in_csv || []);
      setMissingDb(d.missing_in_db || []);
      setCanImport(!!d.can_import);
      setPreviewRows(d.preview || []);
      setCsvMap(d.csv_to_expected || {} as any);
      setDbMap(d.expected_to_db || {} as any);
      setStep('preview');
    } catch (e: any) {
      console.error('Upload error:', e);
      message.error(e.message || 'Upload failed, please try again');
    } finally {
      setLoading(false);
    }
  }

  function addManualRow() {
    setManualRows((rows) => [...rows, Object.fromEntries(manualColumns.map(c => [c, ''])) as Record<string, string>]);
    setManualErrors((errs) => [...errs, Object.fromEntries(manualColumns.map((c) => [c, null])) as Record<string, string | null>]);
  }
  function removeManualRow(idx: number) {
    setManualRows((rows) => rows.filter((_, i) => i !== idx));
    setManualErrors((errs) => errs.filter((_, i) => i !== idx));
  }
  function formatDate(d: Date) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }
  function addDays(base: string, days: number): string {
    const t = Date.parse(base);
    if (Number.isNaN(t)) return '';
    const d = new Date(t);
    d.setDate(d.getDate() + days);
    return formatDate(d);
  }
  function updateManualCell(idx: number, key: string, val: string) {
    setManualRows((rows) => rows.map((r, i) => {
      if (i !== idx) return r;
      if (key === 'Start date') {
        const next: Record<string, string> = { ...r, [key]: val };
        next['End date'] = val ? addDays(val, 6) : '';
        return next;
      }
      return { ...r, [key]: val };
    }));
    // validations
    setManualErrors((errs) => errs.map((eRow, i) => {
      if (i !== idx) return eRow;
      const next: Record<string, string | null> = { ...eRow };
      const v = (val || '').trim();
      if (key === 'Gender') {
        next[key] = (v === '' || v === 'male' || v === 'female') ? null : 'Gender must be male or female';
      } else if (key === 'Age') {
        next[key] = v === '' || /^\d+$/.test(v) ? null : 'Age must be an integer';
      } else if (key === 'MNA' || key === 'BMI' || key === 'Weight') {
        next[key] = v === '' || /^\d+(\.\d{1,2})?$/.test(v) ? null : 'Up to two decimal places';
      } else if (key === 'Start date') {
        next[key] = v === '' || /^\d{4}-\d{2}-\d{2}$/.test(v) ? null : 'Date format YYYY-MM-DD';
        next['End date'] = null; // auto-generated
      } else if (key === 'M-Risk Factors') {
        // Check M-Risk Factors format
        if (v === '') {
          next[key] = null; // can be empty
        } else {
          // Check for Chinese comma
          if (v.includes('，')) {
            next[key] = 'Please use English comma (,) instead of Chinese comma (，)';
          } else {
            // Check format (separated by English comma)
            const factors = v.split(',').map(f => f.trim()).filter(f => f.length > 0);
            if (factors.length === 0) {
              next[key] = 'Please enter valid risk factors';
            } else {
              next[key] = null; // format is correct
            }
          }
        }
      } else {
        next[key] = null;
      }
      return next;
    }));
  }

  // Format M-Risk Factors display
  function formatMRiskFactors(value: string): string[] {
    if (!value || value.trim() === '') return [];
    return value.split(',').map(f => f.trim()).filter(f => f.length > 0);
  }

  // Check M-Risk Factors for issues
  function getMRiskFactorsStatus(value: string): { hasIssues: boolean, issues: string[] } {
    const issues: string[] = [];
    
    if (!value || value.trim() === '') {
      return { hasIssues: false, issues: [] };
    }
    
    // Check for Chinese comma
    if (value.includes('，')) {
      issues.push('Contains Chinese comma (，)');
    }
    
    // Check for duplicate risk factors
    const factors = formatMRiskFactors(value);
    const uniqueFactors = [...new Set(factors)];
    if (factors.length !== uniqueFactors.length) {
      issues.push('Contains duplicate risk factors');
    }
    
    // Check for empty risk factors
    if (factors.some(f => f.length === 0)) {
      issues.push('Contains empty risk factors');
    }
    
    return { hasIssues: issues.length > 0, issues };
  }

  // Check row validation status
  function getRowValidationStatus(rowIndex: number): { status: 'valid' | 'warning' | 'error', message: string } {
    const row = manualRows[rowIndex];
    const errors = manualErrors[rowIndex];
    
    if (!row) return { status: 'error', message: 'Row not found' };
    
    // Check if row is empty
    const isEmpty = manualColumns.every(col => !row[col] || row[col].trim() === '');
    if (isEmpty) return { status: 'error', message: 'Empty row' };
    
    // Check required fields
    const requiredFields = ['PersonID', 'Start date', 'Gender', 'Age', 'MNA', 'BMI', 'Weight'];
    const missingFields = requiredFields.filter(field => !row[field] || row[field].trim() === '');
    if (missingFields.length > 0) {
      return { status: 'error', message: `Missing: ${missingFields.join(', ')}` };
    }
    
    // Check validation errors
    const hasErrors = Object.values(errors).some(error => error !== null);
    if (hasErrors) {
      const errorFields = Object.entries(errors)
        .filter(([_, error]) => error !== null)
        .map(([field, _]) => field);
      return { status: 'error', message: `Invalid: ${errorFields.join(', ')}` };
    }
    
    return { status: 'valid', message: 'Valid' };
  }

  // Check overall validation status
  function getOverallValidationStatus(): { canSubmit: boolean, errorCount: number, warningCount: number, errorDetails: string[] } {
    let errorCount = 0;
    let warningCount = 0;
    const errorDetails: string[] = [];
    
    // If no rows, cannot submit
    if (manualRows.length === 0) {
      return {
        canSubmit: false,
        errorCount: 0,
        warningCount: 0,
        errorDetails: ['No data rows available']
      };
    }
    
    manualRows.forEach((_, index) => {
      const status = getRowValidationStatus(index);
      if (status.status === 'error') {
        errorCount++;
        errorDetails.push(`Row ${index + 1}: ${status.message}`);
      } else if (status.status === 'warning') {
        warningCount++;
      }
    });
    
    return {
      canSubmit: errorCount === 0 && warningCount === 0,
      errorCount,
      warningCount,
      errorDetails
    };
  }
  async function submitManualAsCsv() {
    // Check empty rows
    const emptyRows: number[] = [];
    manualRows.forEach((row, index) => {
      const isEmpty = manualColumns.every(col => !row[col] || row[col].trim() === '');
      if (isEmpty) {
        emptyRows.push(index + 1);
      }
    });
    
    if (emptyRows.length > 0) {
      message.error(`Rows ${emptyRows.join(', ')} are empty. Please fill data or remove those rows.`);
      return;
    }

    // Check required fields
    const requiredFields = ['PersonID', 'Start date', 'Gender', 'Age', 'MNA', 'BMI', 'Weight'];
    const missingFields: Array<{row: number, fields: string[]}> = [];
    
    manualRows.forEach((row, index) => {
      const missingInRow = requiredFields.filter(field => !row[field] || row[field].trim() === '');
      if (missingInRow.length > 0) {
        missingFields.push({row: index + 1, fields: missingInRow});
      }
    });
    
    if (missingFields.length > 0) {
      const errorMessages = missingFields.map(({row, fields}) => 
        `Row ${row} missing: ${fields.join(', ')}`
      );
      message.error(errorMessages.join('; '));
      return;
    }

    // Check validation errors
    const validationErrors: Array<{row: number, field: string, error: string}> = [];
    manualErrors.forEach((rowErrors, index) => {
      Object.entries(rowErrors).forEach(([field, error]) => {
        if (error) {
          validationErrors.push({row: index + 1, field, error});
        }
      });
    });
    
    if (validationErrors.length > 0) {
      const errorMessages = validationErrors.map(({row, field, error}) => 
        `Row ${row} ${field}: ${error}`
      );
      message.error(errorMessages.join('; '));
      return;
    }

    try {
      // Generate simple CSV; can be extended to expectedColumns
      const headers = manualColumns.join(',');
      const lines = manualRows.map(r => manualColumns.map((k) => {
        let value = (r[k] ?? '').trim();
        if (k === 'M-Risk Factors' && value === '') value = 'none';
        value = value.replace(/"/g, '""');
        return /[",\n]/.test(value) ? `"${value}"` : value;
      }).join(','));
      const csvText = [headers, ...lines].join('\n');
      const blob = new Blob([csvText], { type: 'text/csv;charset=utf-8;' });
      const file = new File([blob], 'manual_input.csv', { type: 'text/csv' });
      await handleUpload(file);
    } catch (error) {
      console.error('Error generating CSV:', error);
      message.error('Failed to generate CSV file. Please try again.');
    }
  }

  async function handleCommit() {
    if (!token) return;
    setLoading(true);
    
    try {
      const res = await fetchWithTimeout(`${API_BASE}/api/import/commit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ token, mode }),
      });
      
      // Check response status
      if (!res.ok) {
        const errorText = await res.text();
        try {
          const errorData = JSON.parse(errorText);
          throw new Error(errorData.detail?.error || errorData.detail || `Server error (${res.status})`);
        } catch (parseError) {
          throw new Error(`Server error (${res.status}): ${errorText}`);
        }
      }
      
      // Try parse JSON
      let data;
      try {
        data = await res.json();
      } catch (jsonError) {
        throw new Error('Server returned invalid response format. Please try again.');
      }
      
      if (!data?.ok) {
        throw new Error((data?.detail && (data.detail.error || data.detail)) || 'Import failed');
      }
      
      message.success(`Import successful: ${data.inserted} rows (file total ${data.total_rows_in_file})`);
      setStep('done');
      // Refresh statistics after import
      fetchDbStats();
      // Ask if user wants to refresh Power BI dataset now
      setRefreshMessage('Do you want to refresh the Power BI dataset now?');
      setRefreshModalOpen(true);
    } catch (e: any) {
      console.error('Import error:', e);
      message.error(e.message || 'Import failed, please try again');
      // Reset step to 'mode' to allow user to retry
      setStep('mode');
    } finally {
      setLoading(false);
    }
  }

  async function triggerPowerBIRefresh() {
    // close modal immediately; use global context to trigger refresh
    setRefreshModalOpen(false);
    try {
      await triggerRefreshGlobal();
    } catch (e: any) {
      message.error('Power BI refresh failed to start');
    }
  }

  async function startImport() {
    if (!canImport) return;
    setStep('importing');
    await handleCommit();
  }

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: 20, display: 'grid', gap: 24 }}>
      {/* Header */}
      <section style={{ 
        background: 'var(--color-surface)', 
        border: '1px solid var(--color-border)', 
        borderRadius: 16, 
        padding: 24, 
        display: 'grid', 
        gap: 20,
        boxShadow: 'var(--shadow-sm)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ 
              width: 56, 
              height: 56, 
              borderRadius: 16, 
              background: 'var(--color-primary-50)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 16,
              color: 'var(--color-primary)',
              fontWeight: 700
            }}>IM</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 28, color: '#0f172a', marginBottom: 4 }}>Import Data</div>
              <div style={{ color: '#64748b', fontSize: 16 }}>Upload CSV files or enter data manually with validation</div>
            </div>
          </div>
          <Button onClick={resetAll}>Reset All</Button>
        </div>
        
        {/* DB stats */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', 
          gap: 20, 
          marginTop: 8 
        }}>
          <Card bordered>
            <Statistic title="Total Rows" valueRender={() => (
              statsLoading ? <Spin /> : <span style={{ fontWeight: 700 }}>{dbTotalRows ?? 'N/A'}</span>
            )} />
          </Card>
          <Card bordered>
            <Statistic title="Unique Persons" valueRender={() => (
              statsLoading ? <Spin /> : <span style={{ fontWeight: 700 }}>{dbUniquePersons ?? 'N/A'}</span>
            )} />
          </Card>
        </div>
      </section>

      {/* Steps */}
      <section style={{ 
        background: '#fff', 
        border: '1px solid var(--color-border)', 
        borderRadius: 16, 
        padding: '24px 20px',
        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
        overflow: 'visible'
      }}>
        {(() => {
          const displaySteps: Array<{ key: 'first' | 'preview' | 'mode' | 'importing' | 'done'; label: string }> = [
            { key: 'first', label: 'Upload or Manual Input' },
            { key: 'preview', label: 'Preview & Check' },
            { key: 'mode', label: 'Import Mode' },
            { key: 'importing', label: 'Importing' },
            { key: 'done', label: 'Result' },
          ];
          const currentIndex = (step === 'select' || step === 'manual') ? 0
            : step === 'preview' ? 1
            : step === 'mode' ? 2
            : step === 'importing' ? 3
            : 4;
          return (
            <Steps
              current={currentIndex}
              responsive
              items={displaySteps.map((s, idx) => ({
                title: s.label,
                status: idx < currentIndex ? 'finish' : idx === currentIndex ? 'process' : 'wait',
                disabled: idx > currentIndex,
              }))}
              onChange={(next) => {
                if (next === 0) {
                  // stay on the first step branch; default to 'select' if not already there
                  if (!(step === 'select' || step === 'manual')) setStep('select');
                  return;
                }
                if (next <= currentIndex) {
                  const map = ['first','preview','mode','importing','done'] as const;
                  const key = map[next];
                  if (key === 'preview') setStep('preview');
                  else if (key === 'mode') setStep('mode');
                  else if (key === 'importing') setStep('importing');
                  else if (key === 'done') setStep('done');
                }
              }}
            />
          );
        })()}
      </section>

      {(step === 'select') && (
        <section style={{ 
          background: '#fff', 
          border: '1px solid var(--color-border)', 
          borderRadius: 16, 
          padding: 24, 
          display: 'grid', 
          gap: 24,
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)'
        }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, alignItems: 'start' }}>
            {/* Left: Choose file */}
            <div style={{ 
              background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)', 
              border: '1px solid var(--color-border)', 
              borderRadius: 16, 
              padding: 24, 
              display: 'flex', 
              flexDirection: 'column',
              gap: 16,
              position: 'relative',
              overflow: 'hidden',
              height: '420px'
            }}>
              <div style={{ 
                position: 'absolute', 
                top: -20, 
                right: -20, 
                width: 80, 
                height: 80, 
                background: 'rgba(59, 130, 246, 0.05)', 
                borderRadius: '50%' 
              }} />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ fontWeight: 700, fontSize: 18, color: '#0f172a' }}>Upload CSV File</div>
                <span style={{ 
                  color: '#64748b', 
                  fontSize: 12, 
                  background: '#e2e8f0', 
                  padding: '4px 8px', 
                  borderRadius: 6,
                  fontWeight: 500
                }}>
                  Supports CSV
                </span>
              </div>
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Upload.Dragger
                  accept=".csv,.tsv,text/csv,text/tab-separated-values"
                  multiple={false}
                  maxCount={1}
                  disabled={loading}
                  showUploadList={false}
                  beforeUpload={(file) => {
                    handleUpload(file);
                    return Upload.LIST_IGNORE;
                  }}
                  onDrop={(e) => {
                    const f = e.dataTransfer.files?.[0];
                    if (f) handleUpload(f);
                  }}
                  style={{ borderRadius: 16, width: '100%', maxWidth: 420 }}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined />
                  </p>
                  <p className="ant-upload-text" style={{ fontWeight: 700, color: '#0f172a' }}>
                    Drag and drop CSV here, or click to select
                  </p>
                  <p className="ant-upload-hint" style={{ color: '#64748b' }}>
                    Max {MAX_UPLOAD_MB} MB. We will validate columns and show the first 20 rows for preview.
                  </p>
                  <Button type="primary" disabled={loading}>Select File</Button>
                </Upload.Dragger>
              </div>
            </div>

            {/* Right: Manual input */}
            <div style={{ 
              background: 'linear-gradient(135deg, #fefce8 0%, #fef3c7 100%)', 
              border: '1px solid #fde68a', 
              borderRadius: 16, 
              padding: 24, 
              display: 'flex', 
              flexDirection: 'column',
              gap: 16,
              position: 'relative',
              overflow: 'hidden',
              height: '420px'
            }}>
              <div style={{ 
                position: 'absolute', 
                top: -20, 
                right: -20, 
                width: 80, 
                height: 80, 
                background: 'rgba(245, 158, 11, 0.05)', 
                borderRadius: '50%' 
              }} />
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ fontWeight: 700, fontSize: 18, color: '#0f172a' }}>Manual Input</div>
                <span style={{ 
                  color: '#92400e', 
                  fontSize: 12, 
                  background: '#fef3c7', 
                  padding: '4px 8px', 
                  borderRadius: 6,
                  fontWeight: 500
                }}>
                  Best for small data
                </span>
              </div>
              <div style={{ color: '#92400e', fontSize: 14, lineHeight: 1.5 }}>
                Fill data directly in the table. We validate formats and can generate a CSV to continue to preview & checks.
              </div>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontWeight: 700, marginBottom: 8, color: '#0f172a' }}>Required columns</div>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', maxHeight: '120px', overflowY: 'auto' }}>
                    {["PersonID","Start date","End date","M-Risk Factors","Gender","Age","MNA","BMI","Weight"].map((c) => (
                      <span key={c} style={{ 
                        border: '1px solid #fde68a', 
                        background: '#fff', 
                        color: '#92400e', 
                        padding: '4px 8px', 
                        borderRadius: 6, 
                        fontSize: 11,
                        fontWeight: 500
                      }}>
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div style={{ marginTop: 'auto', paddingTop: 16 }}>
                <Button type="primary" block onClick={() => setStep('manual')}>Enter Manual Input</Button>
              </div>
            </div>
          </div>
        </section>
      )}

      {step === 'manual' && (
        <section style={{ 
          background: '#fff', 
          border: '1px solid var(--color-border)', 
          borderRadius: 16, 
          padding: 24, 
          display: 'grid', 
          gap: 20,
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)'
        }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ 
                width: 40, 
                height: 40, 
                borderRadius: 12, 
                background: 'var(--color-primary-50)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 12,
                fontWeight: 700,
                color: 'var(--color-primary)'
              }}>MI</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 20, color: '#0f172a' }}>Manual Input Data</div>
                <div style={{ color: '#64748b', fontSize: 14 }}>Fill in patient data manually</div>
              </div>
            </div>
            <Button onClick={() => setStep('select')}>Back to Upload</Button>
          </div>

          {/* Table */}
          <div style={{ 
            overflowX: 'auto', 
            border: '1px solid var(--color-border)', 
            borderRadius: 12,
            background: '#fff',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
          }}>
            {(() => {
              const data = manualRows.map((r, idx) => ({ ...r, _rowIndex: idx }));
              const nonMRisk = manualColumns.filter((c) => c !== 'M-Risk Factors');
              const columns = [
                {
                  title: 'Status',
                  key: 'status',
                  width: 80,
                  fixed: 'left' as any,
                  render: (_: any, record: any) => {
                    const idx = record._rowIndex as number;
                    const status = getRowValidationStatus(idx);
                    const statusColor = status.status === 'valid' ? '#52c41a' : status.status === 'warning' ? '#faad14' : '#ff4d4f';
                    return (
                      <Tooltip title={status.message}>
                        <div style={{ 
                          width: 12, 
                          height: 12, 
                          borderRadius: '50%', 
                          backgroundColor: statusColor,
                          margin: '0 auto'
                        }} />
                      </Tooltip>
                    );
                  }
                },
                ...nonMRisk.map((c) => ({
                  title: c,
                  dataIndex: c,
                  key: c,
                  width: manualMinWidth[c] || 160,
                  render: (_: any, record: any) => {
                    const idx = record._rowIndex as number;
                    const val = manualRows[idx]?.[c] || '';
                    const error = manualErrors[idx]?.[c];
                    const commonStyle = { width: '100%' } as React.CSSProperties;
                    const errorStyle = error ? { borderColor: '#ff4d4f' } : {};
                    
                    if (c === 'Start date') {
                      const v = val ? dayjs(val) : undefined;
                      return (
                        <DatePicker 
                          value={v}
                          onChange={(d) => updateManualCell(idx, c, d ? d.format('YYYY-MM-DD') : '')}
                          style={{ ...commonStyle, ...errorStyle }}
                          status={error ? 'error' : undefined}
                        />
                      );
                    } else if (c === 'End date') {
                      return <Input disabled value={val} style={{ ...commonStyle }} />;
                    } else if (c === 'Gender') {
                      return (
                        <Select 
                          value={val}
                          onChange={(v) => updateManualCell(idx, c, v)}
                          style={{ ...commonStyle, ...errorStyle }}
                          status={error ? 'error' : undefined}
                          options={[{ value: '', label: 'Please select' }, { value: 'male', label: 'male' }, { value: 'female', label: 'female' }]}
                        />
                      );
                    } else if (c === 'Age') {
                      return (
                        <InputNumber 
                          value={val ? Number(val) : undefined}
                          onChange={(v) => updateManualCell(idx, c, v !== null && v !== undefined ? String(v) : '')}
                          style={{ ...commonStyle, ...errorStyle }}
                          status={error ? 'error' : undefined}
                          min={0}
                          precision={0}
                        />
                      );
                    } else if (c === 'MNA' || c === 'BMI' || c === 'Weight') {
                      return (
                        <InputNumber 
                          value={val === '' ? undefined : Number(val)}
                          onChange={(v) => updateManualCell(idx, c, v !== null && v !== undefined ? String(v) : '')}
                          style={{ ...commonStyle, ...errorStyle }}
                          status={error ? 'error' : undefined}
                          step={0.01}
                          min={0}
                        />
                      );
                    }
                    return (
                      <Input 
                        value={val} 
                        onChange={(e) => updateManualCell(idx, c, e.target.value)} 
                        style={{ ...commonStyle, ...errorStyle }}
                        status={error ? 'error' : undefined}
                      />
                    );
                  }
                })),
                {
                  title: 'Actions',
                  key: 'actions',
                  fixed: 'right' as any,
                  width: 100,
                  render: (_: any, record: any) => (
                    <Popconfirm title="Delete this row?" onConfirm={() => removeManualRow(record._rowIndex)}>
                      <Button danger size="small">Delete</Button>
                    </Popconfirm>
                  )
                }
              ];
              return (
                <Table 
                  size="small"
                  bordered
                  pagination={false}
                  dataSource={data}
                  columns={columns as any}
                  rowKey="_rowIndex"
                  expandable={{
                    expandedRowRender: (record: any) => {
                      const rowIndex = record._rowIndex;
                      const mRiskValue = manualRows[rowIndex]?.['M-Risk Factors'] || '';
                      const mRiskError = manualErrors[rowIndex]?.['M-Risk Factors'];
                      const factors = formatMRiskFactors(mRiskValue);
                      const status = getMRiskFactorsStatus(mRiskValue);
                      
                      return (
                        <div style={{ padding: 8 }}>
                          <div style={{ marginBottom: 6, fontWeight: 600 }}>M-Risk Factors</div>
                          
                          {/* Display parsed risk factors */}
                          {factors.length > 0 && (
                            <div style={{ marginBottom: 8 }}>
                              <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>Parsed factors ({factors.length}):</div>
                              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                {factors.map((factor, index) => (
                                  <span 
                                    key={index}
                                    style={{ 
                                      background: '#f0f0f0', 
                                      padding: '2px 6px', 
                                      borderRadius: 4, 
                                      fontSize: 11,
                                      border: '1px solid #d9d9d9'
                                    }}
                                  >
                                    {factor}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          
                          {/* Display issue warnings */}
                          {status.hasIssues && (
                            <div style={{ marginBottom: 8 }}>
                              <div style={{ fontSize: 12, color: '#ff4d4f', marginBottom: 4 }}>Issues detected:</div>
                              {status.issues.map((issue, index) => (
                                <div key={index} style={{ fontSize: 11, color: '#ff4d4f', marginBottom: 2 }}>
                                  • {issue}
                                </div>
                              ))}
                            </div>
                          )}
                          
                          <Input.TextArea 
                            rows={4}
                            value={mRiskValue}
                            onChange={(e) => updateManualCell(rowIndex, 'M-Risk Factors', e.target.value)}
                            placeholder="Enter risk factors separated by commas, e.g.: constipation, discomfort, fluid intake deficiency, hearing loss, infection, irregular bowels, irritable bowel syndrome, mobility and care dependency, reduced mobility, urinary incontinence"
                            status={mRiskError ? 'error' : undefined}
                          />
                          
                          {/* Help tip */}
                          <div style={{ marginTop: 4, fontSize: 11, color: '#999' }}>
                             Tip: Use English comma (,) to separate factors. Leave empty if no risk factors.
                          </div>
                        </div>
                      );
                    },
                    defaultExpandAllRows: true
                  }}
                  scroll={{ x: true }}
                />
              );
            })()}
          </div>

          {/* Validation Summary */}
          {(() => {
            const validationStatus = getOverallValidationStatus();
            if (validationStatus.errorCount > 0 || validationStatus.warningCount > 0 || !validationStatus.canSubmit) {
              return (
                <Alert
                  type={validationStatus.errorCount > 0 || !validationStatus.canSubmit ? 'error' : 'warning'}
                  message={
                    !validationStatus.canSubmit && manualRows.length === 0
                      ? `No data to process`
                      : validationStatus.errorCount > 0 
                        ? `Please fix the following errors:`
                        : validationStatus.warningCount > 0
                          ? `${validationStatus.warningCount} row(s) have warnings`
                          : `Please fix the following errors:`
                  }
                  description={
                    !validationStatus.canSubmit && manualRows.length === 0 ? (
                      "Please add at least one row of data before proceeding"
                    ) : validationStatus.errorCount > 0 ? (
                      <div style={{ marginTop: 8 }}>
                        {validationStatus.errorDetails.map((detail, index) => (
                          <div key={index} style={{ marginBottom: 4, fontSize: 13 }}>
                            • {detail}
                          </div>
                        ))}
                      </div>
                    ) : validationStatus.warningCount > 0 ? (
                      "You can proceed, but consider fixing warnings for better data quality"
                    ) : (
                      <div style={{ marginTop: 8 }}>
                        {validationStatus.errorDetails.map((detail, index) => (
                          <div key={index} style={{ marginBottom: 4, fontSize: 13 }}>
                            • {detail}
                          </div>
                        ))}
                      </div>
                    )
                  }
                  showIcon
                  style={{ marginBottom: 16 }}
                />
              );
            }
            return null;
          })()}

          {/* Action Buttons */}
          <div style={{ 
            display: 'flex', 
            gap: 12, 
            alignItems: 'center',
            padding: '16px 0',
            borderTop: '1px solid var(--color-border)'
          }}>
            <Space style={{ width: '100%' }}>
              <Button type="dashed" onClick={addManualRow}>Add Row</Button>
              <div style={{ flex: 1 }} />
              <Button 
                type="primary" 
                onClick={submitManualAsCsv}
                disabled={!getOverallValidationStatus().canSubmit}
              >
                Generate & Preview
              </Button>
            </Space>
          </div>
        </section>
      )}

      {step === 'preview' && (
        <section style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 12, padding: 16, display: 'grid', gap: 12 }}>
          <div style={{ display: 'grid', gap: 4 }}>
            <div style={{ fontWeight: 700 }}>File: {filename}</div>
            <div style={{ color: '#64748b', fontSize: 13 }}>Rows: {totalRows}</div>
          </div>
          <div style={{ display: 'grid', gap: 10 }}>
            <div style={{ fontWeight: 700 }}>Column check</div>

            {(missingCsv.length > 0 || missingDb.length > 0) && (
              <div style={{ display: 'grid', gap: 8 }}>
                {missingCsv.length > 0 && (
                  <div style={{ color: '#991b1b', background: '#fee2e2', border: '1px solid #fecaca', padding: 10, borderRadius: 8 }}>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>Missing required columns (CSV)</div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {missingCsv.map((c) => (
                        <span key={c} style={{ background: '#fecaca', color: '#7f1d1d', border: '1px solid #fca5a5', padding: '4px 8px', borderRadius: 999, fontSize: 12 }}>{c}</span>
                      ))}
                    </div>
              </div>
                )}
                {missingDb.length > 0 && (
                  <div style={{ color: '#7c2d12', background: '#ffedd5', border: '1px solid #fed7aa', padding: 10, borderRadius: 8 }}>
                    <div style={{ fontWeight: 600, marginBottom: 6 }}>Missing in database (data table)</div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {missingDb.map((c) => (
                        <span key={c} style={{ background: '#fed7aa', color: '#7c2d12', border: '1px solid #fdba74', padding: '4px 8px', borderRadius: 999, fontSize: 12 }}>{c}</span>
                      ))}
              </div>
              </div>
                )}
              </div>
            )}

            <div style={{ border: '1px solid var(--color-border)', borderRadius: 10, overflow: 'hidden' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', background: '#f8fafc', color: '#334155', fontWeight: 600, fontSize: 13 }}>
                <div style={{ padding: 10, borderRight: '1px solid var(--color-border)' }}>Expected</div>
                <div style={{ padding: 10, borderRight: '1px solid var(--color-border)' }}>CSV Match</div>
                <div style={{ padding: 10 }}>Database</div>
              </div>
              <div>
                {expectedColumns.map((exp) => {
                  const csvMatch = csvMap[exp] ?? null;
                  const dbMatch = dbMap[exp] ?? null;
                  const okCsv = !!csvMatch;
                  const okDb = !!dbMatch;
                  return (
                    <div key={exp} style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr', borderTop: '1px solid var(--color-border)', fontSize: 13 }}>
                      <div style={{ padding: 10 }}>{exp}</div>
                      <div style={{ padding: 10, color: okCsv ? '#065f46' : '#991b1b' }}>
                        {okCsv ? (
                          <span style={{ background: '#d1fae5', border: '1px solid #a7f3d0', color: '#065f46', padding: '2px 8px', borderRadius: 999 }}>{csvMatch}</span>
                        ) : (
                          <span style={{ background: '#fee2e2', border: '1px solid #fecaca', color: '#991b1b', padding: '2px 8px', borderRadius: 999 }}>Not found</span>
                        )}
              </div>
                      <div style={{ padding: 10, color: okDb ? '#065f46' : '#7c2d12' }}>
                        {okDb ? (
                          <span style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', color: '#065f46', padding: '2px 8px', borderRadius: 999 }}>{dbMatch}</span>
                        ) : (
                          <span style={{ background: '#ffedd5', border: '1px solid #fed7aa', color: '#7c2d12', padding: '2px 8px', borderRadius: 999 }}>Missing</span>
                        )}
              </div>
            </div>
                  );
                })}
              </div>
            </div>

            <div style={{ color: '#64748b', fontSize: 12 }}>
              Tip: All expected columns must match to continue. If names differ, adjust the CSV or the backend schema.
            </div>
          </div>

          <div>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>Preview (first 20 rows)</div>
            {(() => {
              const columns = csvColumns.map((c) => ({
                title: c,
                dataIndex: c,
                key: c,
                ellipsis: true,
                width: Math.max(120, Math.min(200, (c.length + 2) * 8)), // Set reasonable width based on column name length
                resizable: false,
              }));
              const data = previewRows.map((r, idx) => ({ key: idx, ...r }));
              return (
                <div style={{ 
                  overflowX: 'auto', 
                  border: '1px solid var(--color-border)', 
                  borderRadius: 8,
                  maxWidth: '100%'
                }}>
                  <Table 
                    size="small"
                    bordered
                    pagination={false}
                    columns={columns as any}
                    dataSource={data}
                    scroll={{ y: 360, x: Math.max(800, csvColumns.length * 150) }} // Set minimum table width
                    style={{ minWidth: `${Math.max(800, csvColumns.length * 150)}px` }}
                  />
                </div>
              );
            })()}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <Button onClick={() => setStep('select')}>Back</Button>
            <div style={{ flex: 1 }} />
            <Button type="primary" disabled={!canImport} onClick={() => setStep('mode')}>Next: choose import mode</Button>
          </div>
        </section>
      )}

      {step === 'mode' && (
        <section style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 12, padding: 16, display: 'grid', gap: 12 }}>
          <div style={{ fontWeight: 700 }}>Choose import mode</div>
          <Radio.Group value={mode} onChange={(e) => setMode(e.target.value)}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Card hoverable onClick={() => setMode('append')} style={{ borderColor: mode === 'append' ? '#0ea5e9' : undefined }}>
                <Radio value={'append'}>Append</Radio>
                <div style={{ color: '#6b7280', marginTop: 6 }}>Insert to the end of `data` table without deleting existing data. Safer option.</div>
              </Card>
              <Card hoverable onClick={() => setMode('overwrite')} style={{ borderColor: mode === 'overwrite' ? '#ef4444' : undefined }}>
                <Radio value={'overwrite'}>Overwrite</Radio>
                <div style={{ color: '#991b1b', marginTop: 6 }}>This will TRUNCATE the `data` table before import. Proceed with caution.</div>
                {mode === 'overwrite' && (
                  <div style={{ marginTop: 12 }}>
                    <Checkbox checked={overwriteConfirmed} onChange={(e) => setOverwriteConfirmed(e.target.checked)}>I confirm to clear the data table and overwrite with this import</Checkbox>
                  </div>
                )}
              </Card>
            </Space>
          </Radio.Group>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <Button onClick={() => setStep('preview')}>Back</Button>
            <div style={{ flex: 1 }} />
            <Button type="primary" onClick={() => startImport()} disabled={!canImport || loading || (mode === 'overwrite' && !overwriteConfirmed)}>
              {loading ? 'Preparing...' : 'Start import'}
            </Button>
          </div>
        </section>
      )}

      {step === 'importing' && (
        <section style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 12, padding: 16, display: 'grid', gap: 12, placeItems: 'center' }}>
          <div style={{ fontWeight: 700 }}>Importing, please wait...</div>
          <Spin />
          <div style={{ color: '#64748b', fontSize: 12 }}>Depending on file size and network, this may take seconds to tens of seconds</div>
        </section>
      )}

      {step === 'done' && (
        <section style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 12, padding: 16, display: 'grid', gap: 12 }}>
          <Result status="success" title="Import completed" extra={<Button onClick={resetAll}>Import more</Button>} />
        </section>
      )}

      {/* Power BI Refresh Modal */}
      <Modal
        title="Sync Power BI data"
        open={refreshModalOpen}
        onCancel={() => {
          setRefreshModalOpen(false);
          setRefreshMessage('');
        }}
        footer={[
          <Button key="later" onClick={() => setRefreshModalOpen(false)}>Later</Button>,
          <Button key="now" type="primary" onClick={triggerPowerBIRefresh}>Refresh now</Button>,
        ]}
      >
        <Result status="info" title="Refresh Power BI dataset?" subTitle={refreshMessage || 'We can refresh the dataset in background and notify you when it is done.'} />
      </Modal>
      
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
        
        @keyframes slideIn {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        /* Reduced motion (user preference) */
        @media (prefers-reduced-motion: reduce) {
          * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
          }
        }
        
        /* Scrollbar styles */
        ::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        
        ::-webkit-scrollbar-track {
          background: #f1f5f9;
          border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
          background: var(--color-primary);
        }
      `}</style>
    </div>
  );
}

