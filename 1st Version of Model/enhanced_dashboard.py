import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import seaborn as sns
import matplotlib.pyplot as plt

# 设置页面配置
st.set_page_config(
    page_title="增强版老年护理数据分析仪表板",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem;
        background: linear-gradient(90deg, #f0f8ff, #e6f3ff);
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #2c3e50;
        margin: 1.5rem 0;
        padding: 0.8rem;
        border-left: 5px solid #3498db;
        background: linear-gradient(90deg, #f8f9fa, #e9ecef);
        border-radius: 5px;
    }
    .alert-box {
        background: linear-gradient(135deg, #ff6b6b, #ee5a52);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
    }
    .success-box {
        background: linear-gradient(135deg, #4ecdc4, #44a08d);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
    }
    .info-box {
        background: linear-gradient(135deg, #45b7d1, #3498db);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """加载数据并进行预处理"""
    df = pd.read_excel('UpdatedDataFile_preprocessed.xlsx')
    
    # 计算住院天数
    df['住院天数'] = (df['End date'] - df['Start date']).dt.days
    
    # 创建年龄分组
    df['年龄分组'] = pd.cut(df['Age'], 
                        bins=[0, 70, 80, 90, 120], 
                        labels=['<70岁', '70-80岁', '80-90岁', '90+岁'])
    
    # 创建MNA评分分组
    df['MNA分组'] = pd.cut(df['MNA'], 
                        bins=[0, 7, 11, 14, 17], 
                        labels=['营养不良', '营养不良风险', '正常', '良好'])
    
    # 计算BMI
    df['BMI'] = df['Weight'] / ((df['Weight'] / 1000) ** 2)  # 简化计算
    
    # 创建BMI分组
    df['BMI分组'] = pd.cut(df['BMI'], 
                        bins=[0, 18.5, 25, 30, 100], 
                        labels=['偏瘦', '正常', '超重', '肥胖'])
    
    # 计算综合风险评分
    rf_cols = [col for col in df.columns if col.startswith('RF_')]
    
    # 定义高风险因素权重
    high_risk_factors = {
        'RF_dementia': 3,
        'RF_cognitive_disorder': 3,
        'RF_mobility_and_care_dependency': 3,
        'RF_fall_risk': 2,
        'RF_fall': 2,
        'RF_malnutrition': 3,
        'RF_agitation': 2,
        'RF_wandering': 2,
        'RF_lack_of_insight': 2,
        'RF_refusal_of_care': 2,
        'RF_incontinence': 2,
        'RF_urinary_incontinence': 2,
        'RF_double_incontinence': 2,
        'RF_pain': 1,
        'RF_dry_skin': 1,
        'RF_wound': 2,
        'RF_age_related_decline': 1
    }
    
    df['风险评分'] = 0
    for factor, weight in high_risk_factors.items():
        if factor in df.columns:
            df['风险评分'] += df[factor] * weight
    
    # 添加营养风险评分
    df.loc[df['MNA'] < 7, '风险评分'] += 3
    df.loc[df['MNA'] < 11, '风险评分'] += 2
    df.loc[df['Age'] > 85, '风险评分'] += 1
    
    return df

def create_risk_heatmap(df, top_n=20):
    """创建风险因素热力图"""
    rf_cols = [col for col in df.columns if col.startswith('RF_')]
    rf_counts = df[rf_cols].sum().sort_values(ascending=False).head(top_n)
    
    # 创建热力图数据
    heatmap_data = []
    for rf in rf_counts.index:
        rf_name = rf.replace('RF_', '').replace('_', ' ')
        heatmap_data.append({
            '风险因素': rf_name,
            '患者数量': rf_counts[rf],
            '百分比': (rf_counts[rf] / len(df)) * 100
        })
    
    heatmap_df = pd.DataFrame(heatmap_data)
    
    fig = px.bar(
        heatmap_df,
        x='患者数量',
        y='风险因素',
        orientation='h',
        title=f"前{top_n}个最常见风险因素",
        color='百分比',
        color_continuous_scale='Reds',
        text='患者数量'
    )
    
    fig.update_layout(
        xaxis_title="患者数量",
        yaxis_title="风险因素",
        height=600
    )
    
    return fig

def create_patient_risk_profile(df, patient_id):
    """创建患者风险档案"""
    patient_data = df[df['PersonID'] == patient_id]
    if len(patient_data) == 0:
        return None
    
    # 获取患者的风险因素
    rf_cols = [col for col in df.columns if col.startswith('RF_')]
    patient_risks = patient_data[rf_cols].iloc[0]
    active_risks = patient_risks[patient_risks == 1].index.tolist()
    
    # 分类风险因素
    risk_categories = {
        '认知功能': ['RF_dementia', 'RF_cognitive_disorder', 'RF_lack_of_insight', 'RF_agitation', 'RF_wandering'],
        '行动能力': ['RF_mobility_and_care_dependency', 'RF_reduced_mobility', 'RF_fall_risk', 'RF_fall'],
        '营养状况': ['RF_malnutrition', 'RF_suboptimal_intake', 'RF_refusal_to_eat', 'RF_food_modification'],
        '排泄功能': ['RF_incontinence', 'RF_urinary_incontinence', 'RF_double_incontinence', 'RF_bowel_incontinence'],
        '皮肤状况': ['RF_dry_skin', 'RF_wound', 'RF_pressure_ulcer', 'RF_skin_infection'],
        '疼痛管理': ['RF_pain', 'RF_discomfort'],
        '行为问题': ['RF_refusal_of_care', 'RF_restlessness', 'RF_anxiety', 'RF_depression']
    }
    
    # 统计各类风险
    category_counts = {}
    for category, factors in risk_categories.items():
        count = sum(1 for factor in factors if factor in active_risks)
        category_counts[category] = count
    
    return category_counts, active_risks

def main():
    # 主标题
    st.markdown('<h1 class="main-header">🏥 增强版老年护理数据分析仪表板</h1>', unsafe_allow_html=True)
    
    # 加载数据
    df = load_data()
    
    # 侧边栏过滤器
    st.sidebar.markdown("## 🔍 数据过滤器")
    
    # 性别过滤器
    selected_gender = st.sidebar.multiselect(
        "选择性别",
        options=df['Gender'].unique(),
        default=df['Gender'].unique()
    )
    
    # 年龄范围过滤器
    age_range = st.sidebar.slider(
        "选择年龄范围",
        min_value=int(df['Age'].min()),
        max_value=int(df['Age'].max()),
        value=(int(df['Age'].min()), int(df['Age'].max()))
    )
    
    # MNA评分范围过滤器
    mna_range = st.sidebar.slider(
        "选择MNA评分范围",
        min_value=float(df['MNA'].min()),
        max_value=float(df['MNA'].max()),
        value=(float(df['MNA'].min()), float(df['MNA'].max()))
    )
    
    # 风险评分范围过滤器
    risk_range = st.sidebar.slider(
        "选择风险评分范围",
        min_value=int(df['风险评分'].min()),
        max_value=int(df['风险评分'].max()),
        value=(int(df['风险评分'].min()), int(df['风险评分'].max()))
    )
    
    # 应用过滤器
    filtered_df = df[
        (df['Gender'].isin(selected_gender)) &
        (df['Age'] >= age_range[0]) &
        (df['Age'] <= age_range[1]) &
        (df['MNA'] >= mna_range[0]) &
        (df['MNA'] <= mna_range[1]) &
        (df['风险评分'] >= risk_range[0]) &
        (df['风险评分'] <= risk_range[1])
    ]
    
    # 关键指标卡片
    st.markdown("## 📊 关键指标概览")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_patients = filtered_df['PersonID'].nunique()
        st.markdown(f"""
        <div class="metric-card">
            <h3>总患者数</h3>
            <h2>{total_patients:,}</h2>
            <p>筛选后患者数量</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        avg_age = filtered_df['Age'].mean()
        st.markdown(f"""
        <div class="metric-card">
            <h3>平均年龄</h3>
            <h2>{avg_age:.1f}岁</h2>
            <p>年龄范围: {age_range[0]}-{age_range[1]}岁</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        avg_mna = filtered_df['MNA'].mean()
        mna_status = "良好" if avg_mna >= 14 else "正常" if avg_mna >= 11 else "风险" if avg_mna >= 7 else "营养不良"
        st.markdown(f"""
        <div class="metric-card">
            <h3>平均MNA评分</h3>
            <h2>{avg_mna:.1f}</h2>
            <p>营养状况: {mna_status}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_risk = filtered_df['风险评分'].mean()
        risk_level = "低风险" if avg_risk < 5 else "中风险" if avg_risk < 10 else "高风险"
        st.markdown(f"""
        <div class="metric-card">
            <h3>平均风险评分</h3>
            <h2>{avg_risk:.1f}</h2>
            <p>风险等级: {risk_level}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 风险预警
    high_risk_patients = filtered_df[filtered_df['风险评分'] >= 10]['PersonID'].nunique()
    if high_risk_patients > 0:
        risk_percentage = (high_risk_patients / total_patients) * 100
        st.markdown(f"""
        <div class="alert-box">
            <h3>⚠️ 高风险患者预警</h3>
            <p>发现 {high_risk_patients} 名高风险患者 ({risk_percentage:.1f}%)</p>
            <p>建议重点关注这些患者的护理需求</p>
        </div>
        """, unsafe_allow_html=True)
    
    # 第一行图表 - 人口统计学
    st.markdown("## 📈 人口统计学分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 性别分布饼图
        gender_counts = filtered_df['Gender'].value_counts()
        fig_gender = px.pie(
            values=gender_counts.values,
            names=gender_counts.index,
            title="性别分布",
            color_discrete_sequence=['#FF6B6B', '#4ECDC4']
        )
        fig_gender.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_gender, use_container_width=True)
    
    with col2:
        # 年龄分布直方图
        fig_age = px.histogram(
            filtered_df, 
            x='Age', 
            nbins=20,
            title="年龄分布",
            color_discrete_sequence=['#45B7D1']
        )
        fig_age.update_layout(xaxis_title="年龄", yaxis_title="患者数量")
        st.plotly_chart(fig_age, use_container_width=True)
    
    # 第二行图表
    col1, col2 = st.columns(2)
    
    with col1:
        # 年龄分组分布
        age_group_counts = filtered_df['年龄分组'].value_counts()
        fig_age_group = px.bar(
            x=age_group_counts.index,
            y=age_group_counts.values,
            title="年龄分组分布",
            color_discrete_sequence=['#96CEB4']
        )
        fig_age_group.update_layout(xaxis_title="年龄分组", yaxis_title="患者数量")
        st.plotly_chart(fig_age_group, use_container_width=True)
    
    with col2:
        # 性别vs年龄箱线图
        fig_age_gender = px.box(
            filtered_df,
            x='Gender',
            y='Age',
            title="性别与年龄分布对比",
            color='Gender',
            color_discrete_sequence=['#FF6B6B', '#4ECDC4']
        )
        st.plotly_chart(fig_age_gender, use_container_width=True)
    
    # 第三行图表 - 健康指标
    st.markdown("## 🏥 健康指标分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # MNA评分分布
        fig_mna = px.histogram(
            filtered_df,
            x='MNA',
            nbins=15,
            title="MNA营养评分分布",
            color_discrete_sequence=['#FFA07A']
        )
        fig_mna.update_layout(xaxis_title="MNA评分", yaxis_title="患者数量")
        st.plotly_chart(fig_mna, use_container_width=True)
    
    with col2:
        # 体重分布
        fig_weight = px.histogram(
            filtered_df,
            x='Weight',
            nbins=20,
            title="体重分布",
            color_discrete_sequence=['#98D8C8']
        )
        fig_weight.update_layout(xaxis_title="体重(kg)", yaxis_title="患者数量")
        st.plotly_chart(fig_weight, use_container_width=True)
    
    # 第四行图表
    col1, col2 = st.columns(2)
    
    with col1:
        # MNA分组分布
        mna_group_counts = filtered_df['MNA分组'].value_counts()
        fig_mna_group = px.pie(
            values=mna_group_counts.values,
            names=mna_group_counts.index,
            title="MNA营养状况分组",
            color_discrete_sequence=['#FF6B6B', '#FFE66D', '#4ECDC4', '#45B7D1']
        )
        fig_mna_group.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_mna_group, use_container_width=True)
    
    with col2:
        # 风险评分分布
        fig_risk = px.histogram(
            filtered_df,
            x='风险评分',
            nbins=20,
            title="风险评分分布",
            color_discrete_sequence=['#DDA0DD']
        )
        fig_risk.update_layout(xaxis_title="风险评分", yaxis_title="患者数量")
        st.plotly_chart(fig_risk, use_container_width=True)
    
    # 第五行图表 - 多维度分析
    st.markdown("## 🔍 多维度分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 年龄vs MNA散点图
        fig_age_mna = px.scatter(
            filtered_df,
            x='Age',
            y='MNA',
            color='Gender',
            title="年龄与MNA评分关系",
            color_discrete_sequence=['#FF6B6B', '#4ECDC4']
        )
        fig_age_mna.update_layout(xaxis_title="年龄", yaxis_title="MNA评分")
        st.plotly_chart(fig_age_mna, use_container_width=True)
    
    with col2:
        # 年龄vs风险评分散点图
        fig_age_risk = px.scatter(
            filtered_df,
            x='Age',
            y='风险评分',
            color='Gender',
            title="年龄与风险评分关系",
            color_discrete_sequence=['#FF6B6B', '#4ECDC4']
        )
        fig_age_risk.update_layout(xaxis_title="年龄", yaxis_title="风险评分")
        st.plotly_chart(fig_age_risk, use_container_width=True)
    
    # 第六行图表
    col1, col2 = st.columns(2)
    
    with col1:
        # MNA vs风险评分散点图
        fig_mna_risk = px.scatter(
            filtered_df,
            x='MNA',
            y='风险评分',
            color='Gender',
            title="MNA评分与风险评分关系",
            color_discrete_sequence=['#FF6B6B', '#4ECDC4']
        )
        fig_mna_risk.update_layout(xaxis_title="MNA评分", yaxis_title="风险评分")
        st.plotly_chart(fig_mna_risk, use_container_width=True)
    
    with col2:
        # 住院天数分布
        fig_stay = px.histogram(
            filtered_df,
            x='住院天数',
            nbins=20,
            title="住院天数分布",
            color_discrete_sequence=['#FFB6C1']
        )
        fig_stay.update_layout(xaxis_title="住院天数", yaxis_title="患者数量")
        st.plotly_chart(fig_stay, use_container_width=True)
    
    # 第七行图表 - 风险因素分析
    st.markdown("## 🎯 风险因素分析")
    
    # 风险因素热力图
    fig_risk_heatmap = create_risk_heatmap(filtered_df, top_n=25)
    st.plotly_chart(fig_risk_heatmap, use_container_width=True)
    
    # 第八行图表 - 风险分类分析
    st.markdown("## 📊 风险分类分析")
    
    # 定义风险分类
    risk_categories = {
        '认知功能': ['RF_dementia', 'RF_cognitive_disorder', 'RF_lack_of_insight', 'RF_agitation', 'RF_wandering'],
        '行动能力': ['RF_mobility_and_care_dependency', 'RF_reduced_mobility', 'RF_fall_risk', 'RF_fall'],
        '营养状况': ['RF_malnutrition', 'RF_suboptimal_intake', 'RF_refusal_to_eat', 'RF_food_modification'],
        '排泄功能': ['RF_incontinence', 'RF_urinary_incontinence', 'RF_double_incontinence', 'RF_bowel_incontinence'],
        '皮肤状况': ['RF_dry_skin', 'RF_wound', 'RF_pressure_ulcer', 'RF_skin_infection'],
        '疼痛管理': ['RF_pain', 'RF_discomfort'],
        '行为问题': ['RF_refusal_of_care', 'RF_restlessness', 'RF_anxiety', 'RF_depression']
    }
    
    # 计算各类风险的患者数量
    category_data = []
    for category, factors in risk_categories.items():
        # 计算有该类风险的患者数量
        patients_with_risk = filtered_df[factors].any(axis=1).sum()
        percentage = (patients_with_risk / len(filtered_df)) * 100
        category_data.append({
            '风险类别': category,
            '患者数量': patients_with_risk,
            '百分比': percentage
        })
    
    category_df = pd.DataFrame(category_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 风险分类条形图
        fig_category = px.bar(
            category_df,
            x='风险类别',
            y='患者数量',
            title="各类风险患者数量",
            color='百分比',
            color_continuous_scale='Reds',
            text='患者数量'
        )
        fig_category.update_layout(xaxis_title="风险类别", yaxis_title="患者数量")
        st.plotly_chart(fig_category, use_container_width=True)
    
    with col2:
        # 风险分类饼图
        fig_category_pie = px.pie(
            category_df,
            values='患者数量',
            names='风险类别',
            title="风险分类分布",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_category_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_category_pie, use_container_width=True)
    
    # 第九行图表 - 患者个体分析
    st.markdown("## 👤 患者个体分析")
    
    # 选择患者ID
    patient_ids = filtered_df['PersonID'].unique()
    selected_patient = st.selectbox("选择患者ID进行个体分析:", patient_ids)
    
    if selected_patient:
        # 获取患者风险档案
        risk_profile = create_patient_risk_profile(filtered_df, selected_patient)
        
        if risk_profile:
            category_counts, active_risks = risk_profile
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 患者风险分类雷达图
                categories = list(category_counts.keys())
                values = list(category_counts.values())
                
                fig_radar = go.Figure()
                
                fig_radar.add_trace(go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill='toself',
                    name=f'患者 {selected_patient}',
                    line_color='#FF6B6B'
                ))
                
                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, max(values) + 1]
                        )),
                    showlegend=True,
                    title=f"患者 {selected_patient} 风险分类雷达图"
                )
                
                st.plotly_chart(fig_radar, use_container_width=True)
            
            with col2:
                # 患者详细信息
                patient_data = filtered_df[filtered_df['PersonID'] == selected_patient].iloc[0]
                
                st.markdown(f"""
                <div style='background: #f8f9fa; padding: 1rem; border-radius: 10px;'>
                    <h3>患者 {selected_patient} 详细信息</h3>
                    <p><strong>性别:</strong> {patient_data['Gender']}</p>
                    <p><strong>年龄:</strong> {patient_data['Age']}岁</p>
                    <p><strong>MNA评分:</strong> {patient_data['MNA']}</p>
                    <p><strong>体重:</strong> {patient_data['Weight']}kg</p>
                    <p><strong>风险评分:</strong> {patient_data['风险评分']}</p>
                    <p><strong>住院天数:</strong> {patient_data['住院天数']}天</p>
                    <p><strong>活跃风险因素数量:</strong> {len(active_risks)}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 显示活跃的风险因素
                if active_risks:
                    st.markdown("### 活跃的风险因素:")
                    risk_names = [risk.replace('RF_', '').replace('_', ' ') for risk in active_risks]
                    for i, risk_name in enumerate(risk_names[:10]):  # 只显示前10个
                        st.write(f"• {risk_name}")
                    if len(risk_names) > 10:
                        st.write(f"... 还有 {len(risk_names) - 10} 个风险因素")
    
    # 第十行图表 - 时间序列分析
    st.markdown("## 📅 时间序列分析")
    
    # 按时间统计患者数量
    time_series = filtered_df.groupby(filtered_df['Start date'].dt.to_period('M')).size().reset_index()
    time_series.columns = ['月份', '患者数量']
    time_series['月份'] = time_series['月份'].astype(str)
    
    fig_time = px.line(
        time_series,
        x='月份',
        y='患者数量',
        title="患者数量时间趋势",
        markers=True
    )
    fig_time.update_layout(xaxis_title="月份", yaxis_title="患者数量")
    st.plotly_chart(fig_time, use_container_width=True)
    
    # 第十一行图表 - 统计表格
    st.markdown("## 📋 详细统计表格")
    
    # 按性别分组的统计
    gender_stats = filtered_df.groupby('Gender').agg({
        'Age': ['mean', 'std', 'min', 'max'],
        'MNA': ['mean', 'std', 'min', 'max'],
        'Weight': ['mean', 'std', 'min', 'max'],
        '风险评分': ['mean', 'std', 'min', 'max'],
        '住院天数': ['mean', 'std', 'min', 'max']
    }).round(2)
    
    st.subheader("按性别分组的统计信息")
    st.dataframe(gender_stats)
    
    # 按年龄分组统计
    age_stats = filtered_df.groupby('年龄分组').agg({
        'MNA': ['mean', 'std'],
        'Weight': ['mean', 'std'],
        '风险评分': ['mean', 'std'],
        '住院天数': ['mean', 'std']
    }).round(2)
    
    st.subheader("按年龄分组的健康指标统计")
    st.dataframe(age_stats)
    
    # 底部信息
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem;'>
        <p>📊 数据更新时间: {}</p>
        <p>🏥 增强版老年护理数据分析仪表板 | 基于461个风险因素的深度分析</p>
        <p>💡 本仪表板提供全面的患者健康数据分析，支持个性化护理决策</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
