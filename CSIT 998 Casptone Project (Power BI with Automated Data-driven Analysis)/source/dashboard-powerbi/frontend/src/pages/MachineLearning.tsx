/**
 * Machine Learning Analysis Page Component
 * 
 * Interactive ML prediction interface for patient clustering and risk assessment
 * using pre-trained Random Forest and K-Means models.
 * 
 * @component
 */

import { useEffect, useMemo, useState, useCallback, useRef } from 'react';
import { apiGet, apiPost, imageUrl } from '../api/client';
import { message, Input, InputNumber, Select, Button, Space, Steps, Form, Collapse, Checkbox, Descriptions, Card, Tag, Progress, Row, Col, Image, Typography, Spin, Statistic, Modal, Alert } from 'antd';
import { ClusterOutlined, SafetyCertificateOutlined, AppstoreOutlined, IdcardOutlined, UserOutlined, CalendarOutlined } from '@ant-design/icons';

type RFColumnsResp = { rf_columns: string[] };
type ClusterPredictReq = { patient_id?: string; features: Record<string, any> };
type ClusterPredictResp = any;
type RiskPatient = { name: string; age: number; gender: string; conditions_dict: Record<string, any> };

export default function MachineLearning() {
  const [rfColumns, setRfColumns] = useState<string[]>([]);
  const [features, setFeatures] = useState<Record<string, number>>({});
  const [patientId, setPatientId] = useState<string>('demo-001');
  const [clusterResult, setClusterResult] = useState<ClusterPredictResp | null>(null);
  const [riskInput, setRiskInput] = useState<RiskPatient>({ name: 'John', age: 78, gender: 'male', conditions_dict: {} });
  const [riskResult, setRiskResult] = useState<any[] | null>(null);
  const [clusterImgTs, setClusterImgTs] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rfSearch, setRfSearch] = useState('');
  const [loadProgress, setLoadProgress] = useState(0);
  const [loadingStage, setLoadingStage] = useState<string>('');
  const progressTimerRef = useRef<any>(null);
  const cancelAnalysisRef = useRef<boolean>(false);
  const [rfLoaded, setRfLoaded] = useState(false);
  const [symptomsLoaded, setSymptomsLoaded] = useState(false);
  
  const [symptomItems, setSymptomItems] = useState<Array<{ symptom: string; category_id: number | null; category?: string }>>([]);

  const [selectedCount, setSelectedCount] = useState(0);
  const [currentStep, setCurrentStep] = useState<number>(0);

  // Utility: normalize percentage [0,100]
  const toPercent = useCallback((v: any): number | null => {
    if (v == null) return null;
    const num = Number(v);
    if (Number.isNaN(num)) return null;
    const pct = num <= 1 ? num * 100 : num;
    const clamped = Math.max(0, Math.min(100, pct));
    return Math.round(clamped);
  }, []);

  useEffect(() => {
    apiGet<RFColumnsResp>('/cluster/usage/rf-columns')
      .then((data) => {
        setRfColumns(data.rf_columns || []);
        const init: Record<string, number> = {};
        (data.rf_columns || []).forEach((k) => (init[k] = 0));
        setFeatures(init);
        setRiskInput((prev) => ({ ...prev, conditions_dict: init }));
      })
      .catch((e) => {
        console.error('Failed to load RF columns:', e);
        const errorMessage = `Failed to load RF columns: ${e.message || 'Unknown error'}. Please refresh the page.`;
        setError(errorMessage);
        message.error(errorMessage);
      })
      .finally(() => setRfLoaded(true));
  }, []);

  useEffect(() => {
    apiGet<any>('/api/symptoms')
      .then((data) => {
        if (data && data.ok) setSymptomItems(data.items || []);
      })
      .catch((error: any) => {
        console.error('Failed to load symptoms:', error);
        const errorMessage = `Failed to load symptoms: ${error.message || 'Unknown error'}. Please refresh the page.`;
        setError(errorMessage);
        message.error(errorMessage);
      })
      .finally(() => setSymptomsLoaded(true));
  }, []);

  type MatchInfo = { symptom?: string; category_id?: number | null; category?: string };
  const rfMatchMap = useMemo(() => {
    // Normalize helpers
    const normalize = (s: string) => (s || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
    const rfNormalize = (s: string) => normalize(s.replace(/^rf_/i, '').replace(/_/g, ' '));
    const symptoms = symptomItems.map((it) => ({
      norm: normalize(it.symptom),
      raw: it.symptom,
      category_id: it.category_id,
      category: it.category,
    })).filter((x) => x.norm);
    const byNorm: Record<string, { raw: string; category_id: number | null; category?: string }> = {};
    for (const s of symptoms) {
      if (!byNorm[s.norm]) byNorm[s.norm] = { raw: s.raw, category_id: s.category_id ?? null, category: s.category };
    }

    const result: Record<string, MatchInfo> = {};
    for (const rf of rfColumns) {
      const key = rfNormalize(rf);
      if (byNorm[key]) {
        result[rf] = { symptom: byNorm[key].raw, category_id: byNorm[key].category_id ?? null, category: byNorm[key].category };
      } else {
        result[rf] = {};
      }
    }
    return result;
  }, [rfColumns, symptomItems]);

  const matchedRfKeys = useMemo(() => rfColumns.filter((k) => !!(rfMatchMap[k] && rfMatchMap[k].symptom)), [rfColumns, rfMatchMap]);
  const unmatchedRfKeys = useMemo(() => rfColumns.filter((k) => !(rfMatchMap[k] && rfMatchMap[k].symptom)), [rfColumns, rfMatchMap]);

  const filteredRfKeys = useMemo(() => {
    const q = rfSearch.trim().toLowerCase();
    return matchedRfKeys.filter((k) => {
      if (!q) return true;
      const mi = rfMatchMap[k] || {} as any;
      const symptom = (mi.symptom || '').toLowerCase();
      return k.toLowerCase().includes(q) || symptom.includes(q);
    });
  }, [matchedRfKeys, rfSearch, features, rfMatchMap]);

  const filteredUnmatchedKeys = useMemo(() => {
    const q = rfSearch.trim().toLowerCase();
    return unmatchedRfKeys.filter((k) => {
      if (!q) return true;
      return k.toLowerCase().includes(q);
    });
  }, [unmatchedRfKeys, rfSearch, features]);

  const groupedByCategory = useMemo(() => {
    if (!(rfLoaded && symptomsLoaded)) return [] as Array<{ key: string; label: string; items: Array<{ rfKey: string; symptom: string }> }>;
    const groups: Array<{ key: string; label: string; items: Array<{ rfKey: string; symptom: string }> }> = [];
    const map: Record<string, { key: string; label: string; items: Array<{ rfKey: string; symptom: string }> }> = {};
    for (const k of filteredRfKeys) {
      const mi = rfMatchMap[k] || {} as any;
      const catKey = (mi.category_id == null ? 'null' : String(mi.category_id));
      const catLabel = mi.category || 'Unassigned';
      if (!map[catKey]) {
        map[catKey] = { key: catKey, label: catLabel, items: [] };
      }
      if (mi.symptom) map[catKey].items.push({ rfKey: k, symptom: mi.symptom });
    }
    for (const g of Object.values(map)) {
      g.items.sort((a, b) => a.symptom.localeCompare(b.symptom));
      groups.push(g);
    }
    // Category sorting: named categories first, unassigned last; same type by name
    groups.sort((a, b) => {
      if (a.key === 'null' && b.key !== 'null') return 1;
      if (a.key !== 'null' && b.key === 'null') return -1;
      return a.label.localeCompare(b.label);
    });
    return groups;
  }, [filteredRfKeys, rfMatchMap, rfLoaded, symptomsLoaded]);

  const handleGroupChange = useCallback((groupKey: string, values: string[]) => {
    const valueSet = new Set(values);
      const group = groupedByCategory.find((g) => g.key === groupKey);
    const next: Record<string, number> = { ...features };
      if (group) {
        for (const it of group.items) {
          next[it.rfKey] = valueSet.has(it.rfKey) ? 1 : 0;
        }
      }
    setFeatures(next);
    setRiskInput((p) => ({ ...p, conditions_dict: next }));
  }, [groupedByCategory, features]);

  useEffect(() => {
    const count = matchedRfKeys.filter((k) => !!features[k]).length;
    setSelectedCount(count);
  }, [matchedRfKeys, features]);

  const selectedList = useMemo(() => {
    return matchedRfKeys
      .filter((k) => !!features[k])
      .map((k) => {
        const mi = rfMatchMap[k] || ({} as any);
        const fallback = k.replace(/^RF_/, '').replaceAll('_', ' ');
        return { rfKey: k, label: mi.symptom || fallback };
      });
  }, [matchedRfKeys, features, rfMatchMap]);

  const [clusterDetailOpen, setClusterDetailOpen] = useState(false);
  const [riskDetailOpen, setRiskDetailOpen] = useState(false);

  const runAllPredict = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    setError(null);
    cancelAnalysisRef.current = false;
    setLoadProgress(0);
    setLoadingStage('Initializing analysis...');
    
    if (progressTimerRef.current) clearInterval(progressTimerRef.current);
    progressTimerRef.current = setInterval(() => {
      setLoadProgress((p) => Math.min(p + 8, 85));
    }, 200);
    
    const minDelay = new Promise((resolve) => setTimeout(resolve, 1000));
    
    try {
      setLoadingStage('Analyzing patient clustering...');
      const clusterPayload: ClusterPredictReq = { patient_id: patientId, features };
      
      setLoadingStage('Calculating risk assessment...');
      const [clusterRes, riskRes] = await Promise.allSettled([
        apiPost<ClusterPredictResp>('/cluster/usage/predict', clusterPayload),
        apiPost<any[]>('/risk/predict', [riskInput])
      ]);
      
      setLoadingStage('Processing results...');
      
      if (!cancelAnalysisRef.current && clusterRes.status === 'fulfilled') {
        setClusterResult(clusterRes.value);
        setClusterImgTs(Date.now());
      } else if (clusterRes.status === 'rejected') {
        const msg = (clusterRes as any)?.reason?.message || 'Cluster prediction failed';
        setClusterResult(null);
        setError((prev) => prev || msg);
        message.error(msg);
      }
      
      if (!cancelAnalysisRef.current && riskRes.status === 'fulfilled') {
        setRiskResult(riskRes.value);
      } else if (riskRes.status === 'rejected') {
        const msg = (riskRes as any)?.reason?.message || 'Risk assessment failed';
        setRiskResult(null);
        setError((prev) => prev || msg);
        message.error(msg);
      }
      
      setLoadingStage('Finalizing analysis...');
      await minDelay;
      
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current);
        progressTimerRef.current = null;
      }
      
      if (!cancelAnalysisRef.current) {
        setLoadProgress(100);
        setLoadingStage('Analysis complete!');
        
        // Briefly show completion status before hiding loading
        setTimeout(() => {
          setLoading(false);
          setLoadingStage('');
        }, 800);
      } else {
        setLoadProgress(0);
        setLoadingStage('');
        setLoading(false);
      }
    } catch (e: any) {
      if (cancelAnalysisRef.current) return;
      console.error('Prediction failed:', e);
      setError(e.message || 'Analysis failed');
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current);
        progressTimerRef.current = null;
      }
      setLoadProgress(0);
      setLoadingStage('');
      setLoading(false);
    }
  }, [patientId, features, riskInput, loading]);

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: 20 }}>
      {error && (
        <Alert
          type="error"
          showIcon
          message="Error"
          description={error}
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 16 }}
        />
      )}
      {currentStep === 0 && (
          <Card title={<Steps current={currentStep} items={[{ title: 'Patient Information' }, { title: 'Symptom Selection' }, { title: 'Analysis Results' }]} />} bordered={false}>
            <Form layout="vertical" onFinish={() => setCurrentStep(1)}>
              <Form.Item label="Patient ID" required>
                <Input 
                  value={patientId} 
                  onChange={(e) => setPatientId(e.target.value)} 
                  placeholder="Enter patient ID, e.g. P001" 
                  prefix={<IdcardOutlined style={{ color: '#1677ff' }} />}
                />
              </Form.Item>
              
              <Form.Item label="Name">
                <Input 
                  value={riskInput.name} 
                  onChange={(e) => setRiskInput((p) => ({ ...p, name: e.target.value }))} 
                  placeholder="Enter patient name"
                  prefix={<UserOutlined style={{ color: '#52c41a' }} />}
                />
              </Form.Item>
              
              <Form.Item label="Gender" required>
                <Select 
                  value={riskInput.gender} 
                  onChange={(v) => setRiskInput((p) => ({ ...p, gender: v }))} 
                  options={[{ value: 'male', label: 'Male' }, { value: 'female', label: 'Female' }]} 
                />
              </Form.Item>
              
              <Form.Item label="Age" required>
                <InputNumber 
                  value={riskInput.age} 
                  onChange={(v) => setRiskInput((p) => ({ ...p, age: Number(v || 0) }))} 
                  style={{ width: '100%' }} 
                  min={0} 
                  max={150}
                  precision={0}
                  placeholder="Enter age"
                  prefix={<CalendarOutlined style={{ color: '#fa8c16' }} />}
                />
              </Form.Item>
              
              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" size="large">Next: Select Symptoms</Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>
        )}
        {currentStep === 1 && (
            <Card title={<Steps current={currentStep} items={[{ title: 'Patient Information' }, { title: 'Symptom Selection' }, { title: 'Analysis Results' }]} />} bordered={false}>
              <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Symptom Selection <Tag color="blue">{selectedCount} selected</Tag></div>
              <Input.Search placeholder="Search symptoms or categories..." value={rfSearch} onChange={(e) => setRfSearch(e.target.value)} allowClear style={{ marginBottom: 12 }} />
              
              {/* Selected Symptoms Section - Fixed Height */}
              <Card 
                size="small" 
                title="Selected Symptoms" 
                style={{ marginBottom: 16 }}
                bodyStyle={{ 
                  minHeight: selectedCount === 0 ? 60 : 'auto',
                  padding: '12px 16px',
                  backgroundColor: selectedCount === 0 ? '#fafafa' : '#fff'
                }}
              >
                {selectedList.length > 0 ? (
                  <Space wrap size={[8, 8]}>
                    {selectedList.map((it) => (
                      <Tag
                        key={it.rfKey}
                        color="blue"
                        closable
                        onClose={(e) => {
                          e.preventDefault();
                          const next: Record<string, number> = { ...features, [it.rfKey]: 0 };
                          setFeatures(next);
                          setRiskInput((p) => ({ ...p, conditions_dict: next }));
                        }}
                      >
                        {it.label}
                      </Tag>
                    ))}
                  </Space>
                ) : (
                  <div style={{ 
                    color: '#999', 
                    fontStyle: 'italic', 
                    textAlign: 'center',
                    padding: '8px 0'
                  }}>
                    No symptoms selected yet. Choose symptoms from the categories below.
                  </div>
                )}
              </Card>

              {/* Available Symptoms Section */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#666' }}>
                  Available Symptoms by Category
                </div>
                <Collapse bordered>
                  {groupedByCategory.map((group) => (
                    <Collapse.Panel header={`${group.label} (${group.items.length})`} key={group.key}>
                      <Checkbox.Group
                        style={{ width: '100%' }}
                        value={group.items.filter((it) => !!features[it.rfKey]).map((it) => it.rfKey)}
                        onChange={(vals) => handleGroupChange(group.key, vals as string[])}
                      >
                        <Space size={[8, 8]} wrap style={{ width: '100%' }}>
                          {group.items.map((it) => {
                            const mi = rfMatchMap[it.rfKey] || ({} as any);
                            const label = mi.symptom || it.symptom;
                            const tip = `${it.symptom} ← ${it.rfKey.replace(/^RF_/, '').replaceAll('_', ' ')}`;
                            return (
                              <Checkbox key={it.rfKey} value={it.rfKey} title={tip}>{label}</Checkbox>
                            );
                          })}
                        </Space>
                      </Checkbox.Group>
                    </Collapse.Panel>
                  ))}
                </Collapse>
              </div>

              {/* Unmatched Features */}
              {filteredUnmatchedKeys.length > 0 && (
                <Card size="small" type="inner" title={`Unmatched Features (${filteredUnmatchedKeys.length})`} style={{ marginBottom: 16 }}>
                  <Space wrap>
                    {filteredUnmatchedKeys.map((k) => (
                      <span key={k} style={{ background: '#fff7e6', border: '1px dashed #faad14', padding: '2px 8px', borderRadius: 8 }}>{k}</span>
                    ))}
                  </Space>
                </Card>
              )}

              {/* Action Buttons */}
              <Space style={{ marginTop: 16 }} size="middle">
                <Button onClick={() => setCurrentStep(0)} size="large">Previous</Button>
                <Button 
                  type="primary" 
                  onClick={() => { setCurrentStep(2); runAllPredict(); }} 
                  disabled={loading || selectedCount === 0}
                  size="large"
                >
                  {selectedCount === 0 ? 'Please select symptoms' : `Start Analysis (${selectedCount} symptoms)`}
                </Button>
              </Space>
            </Card>
      )}
      {currentStep === 2 && (
                <Card bordered={false} title={<Steps current={currentStep} items={[{ title: 'Patient Information' }, { title: 'Symptom Selection' }, { title: 'Analysis Results' }]} />}>
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Card bordered={false} bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <Space wrap>
                <Button onClick={() => setCurrentStep(1)}>← Modify Symptoms</Button>
                <Button onClick={() => setCurrentStep(0)}>← Back to Patient Info</Button>
              </Space>
              <div style={{ flex: 1 }} />
              <Button type="primary" onClick={runAllPredict} disabled={loading}>Re-analyze</Button>
            </div>
          </Card>
          {error && (
            <Alert 
              message="Analysis Error" 
              description={error} 
              type="error" 
              showIcon 
              closable 
              onClose={() => setError(null)}
            />
          )}
          {loading && (
            <Card 
              style={{ 
                width: '100%', 
                textAlign: 'center',
                border: '1px solid #e8e8e8',
                borderRadius: 12,
                marginBottom: 24
              }}
              bodyStyle={{ padding: '40px 24px' }}
            >
              <div style={{ marginBottom: 24 }}>
                <Spin size="large" />
              </div>
              
              <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#1677ff' }}>
                {loadingStage || 'Analyzing...'}
              </div>
              
              <div style={{ fontSize: 14, color: '#666', marginBottom: 16 }}>
                Processing {selectedCount} selected symptoms
              </div>
              
              <Progress 
                percent={loadProgress} 
                strokeWidth={8}
                style={{ marginBottom: 16 }}
              />
              
              <div style={{ fontSize: 12, color: '#999' }}>
                This may take a few moments...
              </div>
            </Card>
          )}
          {!loading && ((riskResult && Array.isArray(riskResult) && riskResult[0]) || clusterResult) && (
            <>
              {/* Patient Information */}
              <Card bordered={false} style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Patient Information</div>
                <Row gutter={[16, 8]}>
                  <Col xs={24} sm={12} md={6}>
                    <div style={{ color: '#8c8c8c', marginBottom: 4 }}><Space><IdcardOutlined style={{ color: '#1677ff' }} />Patient ID</Space></div>
                    <div>{patientId}</div>
                  </Col>
                  <Col xs={24} sm={12} md={6}>
                    <div style={{ color: '#8c8c8c', marginBottom: 4 }}><Space><UserOutlined style={{ color: '#52c41a' }} />Name</Space></div>
                    <div>{riskInput.name || '—'}</div>
                  </Col>
                  <Col xs={24} sm={12} md={6}>
                    <div style={{ color: '#8c8c8c', marginBottom: 4 }}><Space><UserOutlined style={{ color: '#52c41a' }} />Gender</Space></div>
                    <div>{String((riskResult && Array.isArray(riskResult) && riskResult[0] && riskResult[0].gender) || riskInput.gender) === 'male' ? 'Male' : 'Female'}</div>
                  </Col>
                  <Col xs={24} sm={12} md={6}>
                    <div style={{ color: '#8c8c8c', marginBottom: 4 }}><Space><CalendarOutlined style={{ color: '#fa8c16' }} />Age</Space></div>
                    <div>{(riskResult && Array.isArray(riskResult) && riskResult[0] && (riskResult[0].age as any)) ?? riskInput.age} years</div>
                  </Col>
                </Row>
              </Card>

              {/* Cluster, Risk, and Recommendations */}
              <Row gutter={16}>
                {/* Cluster Information */}
                <Col xs={24} md={8}>
                  <Card 
                    title={
                      <Space>
                        <ClusterOutlined style={{ color: '#fa8c16' }} />
                        Cluster Information
                        {clusterResult && <Tag color="orange">#{clusterResult.predicted_cluster}</Tag>}
                      </Space>
                    }
                    bordered={false}
                    style={{ marginBottom: 16, height: '100%' }}
                    extra={clusterResult ? <Button type="link" size="small" onClick={() => setClusterDetailOpen(true)}>View Details</Button> : undefined}
                  >
                    {clusterResult ? (
                      <>
                        {clusterResult.cluster_phenotype && (
                          <div style={{ marginBottom: 16 }}>
                            <Tag color="#e6f4ff" style={{ color: '#1677ff', fontSize: 14 }}>
                              Phenotype: {clusterResult.cluster_phenotype}
                            </Tag>
                          </div>
                        )}
                        <Row gutter={[12, 12]}>
                          <Col span={12}>
                            <Statistic 
                              title="Active Factors" 
                              value={clusterResult.active_conditions_count ?? 0}
                              prefix={<AppstoreOutlined style={{ color: '#fa8c16' }} />}
                            />
                          </Col>
                          <Col span={12}>
                            <Statistic 
                              title="Sample Size" 
                              value={clusterResult.cluster_size ?? 0}
                              prefix={<AppstoreOutlined />}
                            />
                          </Col>
                        </Row>
                        <div style={{ marginTop: 16 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                            <span style={{ color: '#8c8c8c', fontSize: 14 }}>Cluster Confidence</span>
                            <span style={{ fontSize: 16, fontWeight: 600, color: '#fa8c16' }}>
                              {toPercent(clusterResult.confidence_score) ?? 0}%
                            </span>
                          </div>
                          <Progress 
                            percent={toPercent(clusterResult.confidence_score) ?? 0} 
                            strokeColor="#fa8c16"
                            status="active"
                            showInfo={false}
                          />
                        </div>
                      </>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '48px 0', color: '#8c8c8c' }}>
                        <ClusterOutlined style={{ fontSize: 48, marginBottom: 16, opacity: 0.3 }} />
                        <div>No cluster analysis data</div>
                      </div>
                    )}
                  </Card>
                </Col>

                {/* Risk Information */}
                <Col xs={24} md={8}>
                  <Card
                    title={
                      <Space>
                        <SafetyCertificateOutlined style={{ color: '#52c41a' }} />
                        Risk Assessment
                      </Space>
                    }
                    bordered={false}
                    style={{ marginBottom: 16, height: '100%' }}
                    extra={(riskResult && Array.isArray(riskResult) && riskResult[0]) ? <Button type="link" size="small" onClick={() => setRiskDetailOpen(true)}>View Details</Button> : undefined}
                  >
                    {riskResult && Array.isArray(riskResult) && riskResult[0] ? (
                      <>
                        <div style={{ textAlign: 'center' }}>
                          <Tag color={
                            String(riskResult[0].risk_level || '').toLowerCase() === 'high' ? 'red' :
                            String(riskResult[0].risk_level || '').toLowerCase() === 'medium' ? 'orange' : 'green'
                          } style={{ fontSize: 16, padding: '4px 16px' }}>
                            {String(riskResult[0].risk_level || '—').toUpperCase()}
                          </Tag>
                          <div style={{ marginTop: 16 }}>
                            <Progress
                              type="circle"
                              percent={toPercent(riskResult[0].risk_probability) ?? 0}
                              strokeColor={
                                String(riskResult[0].risk_level || '').toLowerCase() === 'high' ? '#ff4d4f' :
                                String(riskResult[0].risk_level || '').toLowerCase() === 'medium' ? '#faad14' : '#52c41a'
                              }
                              format={(p) => `${p}%`}
                              width={120}
                            />
                          </div>
                          <div style={{ color: '#8c8c8c', marginTop: 12, fontSize: 14 }}>Risk Probability</div>
                        </div>
                      </>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '48px 0', color: '#8c8c8c' }}>
                        <SafetyCertificateOutlined style={{ fontSize: 48, marginBottom: 16, opacity: 0.3 }} />
                        <div>No risk assessment data</div>
                      </div>
                    )}
                  </Card>
                </Col>

                {/* Recommendations and Interventions */}
                <Col xs={24} md={8}>
                  <Card
                    title="Recommendations & Interventions"
                    bordered={false}
                    style={{ marginBottom: 16, height: '100%' }}
                  >
                    {riskResult && Array.isArray(riskResult) && riskResult[0] && Array.isArray(riskResult[0].recommendations) && riskResult[0].recommendations.length > 0 ? (
                      <ul style={{ paddingLeft: 20, margin: 0, fontSize: 14, lineHeight: 1.8 }}>
                        {riskResult[0].recommendations.map((r: string, i: number) => (
                          <li key={i} style={{ marginBottom: 12 }}>
                            <Typography.Text strong={i === 0}>{r}</Typography.Text>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '48px 0', color: '#8c8c8c' }}>
                        <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.3 }}>—</div>
                        <div>No recommendations available</div>
                      </div>
                    )}
                  </Card>
                </Col>
              </Row>

              {/* Visualization Charts */}
              <Card title="Analysis Results" bordered={false} style={{ marginBottom: 16 }}>
                <Image.PreviewGroup>
                  <Row gutter={[16, 16]} style={{ marginTop: 0 }}>
                    <Col xs={24} md={8}>
                      <div style={{ marginBottom: 8, fontWeight: 600 }}>Cluster Distribution</div>
                      <Image 
                        src={`${imageUrl('/cluster/display/cluster_sizes.png')}?t=${clusterImgTs}`} 
                        alt="Cluster Size Distribution" 
                        height={240} 
                        width={'100%'} 
                        style={{ objectFit: 'contain', background: '#fafafa', borderRadius: 8 }} 
                        preview={{ mask: 'Click to preview' }}
                      />
                    </Col>
                    <Col xs={24} md={8}>
                      <div style={{ marginBottom: 8, fontWeight: 600 }}>Age & MUST Score Comparison</div>
                      <Image 
                        src={`${imageUrl('/cluster/display/demographics.png')}?t=${clusterImgTs}`} 
                        alt="Demographic Analysis" 
                        height={240} 
                        width={'100%'} 
                        style={{ objectFit: 'contain', background: '#fafafa', borderRadius: 8 }} 
                        preview={{ mask: 'Click to preview' }}
                      />
                    </Col>
                    <Col xs={24} md={8}>
                      <div style={{ marginBottom: 8, fontWeight: 600 }}>Risk Factors Prevalence</div>
                      <Image 
                        src={`${imageUrl('/cluster/display/heatmap.png')}?t=${clusterImgTs}`} 
                        alt="Risk Factors Heatmap" 
                        height={240} 
                        width={'100%'} 
                        style={{ objectFit: 'contain', background: '#fafafa', borderRadius: 8 }} 
                        preview={{ mask: 'Click to preview' }}
                      />
                    </Col>
                  </Row>
                </Image.PreviewGroup>
              </Card>

              {/* Cluster Details Modal */}
              <Modal centered open={clusterDetailOpen} title="Cluster Raw Data" onCancel={() => setClusterDetailOpen(false)} footer={<Button onClick={() => setClusterDetailOpen(false)}>Close</Button>} width={720}>
                {clusterResult ? (
                        <Descriptions bordered size="small" column={2}>
                          <Descriptions.Item label="Patient ID">{clusterResult.patient_id ?? 'Unknown'}</Descriptions.Item>
                          <Descriptions.Item label="Cluster">{clusterResult.predicted_cluster}</Descriptions.Item>
                          <Descriptions.Item label="Phenotype" span={2}>{clusterResult.cluster_phenotype || '—'}</Descriptions.Item>
                          <Descriptions.Item label="Confidence">{clusterResult.confidence_score != null ? `${Math.round(clusterResult.confidence_score * 100)}%` : '—'}</Descriptions.Item>
                          <Descriptions.Item label="Active Factors">{clusterResult.active_conditions_count ?? '—'}</Descriptions.Item>
                          <Descriptions.Item label="Cluster Size">{clusterResult.cluster_size ?? '—'}</Descriptions.Item>
                        </Descriptions>
                ) : (
                  <Typography.Text type="secondary">No data available</Typography.Text>
                )}
              </Modal>

              {/* Risk Details Modal */}
              <Modal centered open={riskDetailOpen} title="Risk Raw Data" onCancel={() => setRiskDetailOpen(false)} footer={<Button onClick={() => setRiskDetailOpen(false)}>Close</Button>} width={720}>
                {riskResult && Array.isArray(riskResult) && riskResult[0] ? (
                        <Descriptions bordered size="small" column={2}>
                          <Descriptions.Item label="Risk Level">{riskResult[0].risk_level} ({riskResult[0].risk_category})</Descriptions.Item>
                          <Descriptions.Item label="Probability">{Math.round((riskResult[0].risk_probability ?? 0) * 100)}%</Descriptions.Item>
                          <Descriptions.Item label="Confidence">{riskResult[0].model_confidence}</Descriptions.Item>
                          <Descriptions.Item label="Gender / Age">{(riskResult[0].gender || '').toString()} / {riskResult[0].age}</Descriptions.Item>
                    {Object.keys(riskResult[0]).filter((k) => !['risk_level','risk_category','risk_probability','model_confidence','gender','age','recommendations'].includes(k)).map((k) => (
                      <Descriptions.Item key={k} label={k}>{String((riskResult[0] as any)[k])}</Descriptions.Item>
                    ))}
                        </Descriptions>
                ) : (
                  <Typography.Text type="secondary">No data available</Typography.Text>
                )}
              </Modal>
            </>
          )}
        </Space>
        </Card>
      )}
    </div>
  );
}


