#!/usr/bin/env python3
"""
增强版老年护理数据分析仪表板启动脚本
"""

import subprocess
import sys
import os

def print_banner():
    """打印欢迎横幅"""
    print("=" * 60)
    print("🏥 增强版老年护理数据分析仪表板")
    print("=" * 60)
    print("基于181名患者的19,460条医疗记录")
    print("包含461个详细风险因素的深度分析")
    print("=" * 60)

def check_dependencies():
    """检查依赖包是否已安装"""
    try:
        import streamlit
        import pandas
        import plotly
        import numpy
        import openpyxl
        print("✅ 所有依赖包已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def run_dashboard():
    """运行增强版仪表板"""
    print("🚀 启动增强版仪表板...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "enhanced_dashboard.py"])

def main():
    """主函数"""
    print_banner()
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 检查数据文件
    if not os.path.exists("UpdatedDataFile_preprocessed.xlsx"):
        print("❌ 找不到数据文件 UpdatedDataFile_preprocessed.xlsx")
        print("请确保数据文件在当前目录中")
        return
    
    print("\n📊 增强版仪表板特色功能:")
    print("• 基于461个详细风险因素的深度分析")
    print("• 智能风险评分系统")
    print("• 风险分类分析（认知、行动、营养等）")
    print("• 患者个体风险档案")
    print("• 风险因素热力图")
    print("• 多维度数据可视化")
    print()
    
    input("按回车键启动增强版仪表板...")
    run_dashboard()

if __name__ == "__main__":
    main()
