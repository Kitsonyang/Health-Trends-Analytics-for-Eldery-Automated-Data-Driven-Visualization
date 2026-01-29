import pandas as pd
import numpy as np
import matplotlib

# Use non-GUI backend for servers/headless environments
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Use shared absolute output paths to ensure files are saved where the API serves them
try:
    from utils.shared import HEATMAP_PATH, SIZES_PATH, DEMOS_PATH
except Exception:
    # Fallback to relative paths if shared utils are unavailable at import time
    HEATMAP_PATH = Path('rf_conditions_heatmap.png')
    SIZES_PATH = Path('cluster_sizes.png')
    DEMOS_PATH = Path('demographics_comparison.png')

# Visualization functions (rely on passed-in cluster_interpretations from caller)
def _write_placeholder_png(path: Path | str, message: str):
    target_path = Path(path)
    plt.figure(figsize=(10, 6), facecolor='#f3f4f6')
    ax = plt.gca()
    ax.set_facecolor('#f3f4f6')
    plt.text(0.5, 0.55, message, ha='center', va='center', fontsize=28, color='#374151', fontweight='bold')
    plt.text(0.5, 0.40, 'Please verify models and data are properly loaded', ha='center', va='center', fontsize=14, color='#6b7280')
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('#9ca3af')
        spine.set_linewidth(1.5)
    plt.axis('off')
    plt.tight_layout()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(target_path), dpi=150, bbox_inches='tight')
    plt.close()

def show_cluster_heatmap(cluster_interpretations):
    """Create and show the RF conditions heatmap"""
    
    # Prepare data
    condition_data = []
    
    for cluster_id, info in cluster_interpretations.items():
        top_conditions = info.get('top_rf_conditions', {})
        for condition, prevalence in top_conditions.items():
            clean_name = condition.replace('RF_', '').replace('_', ' ').title()
            condition_data.append({
                'Cluster': f"Cluster {cluster_id}",
                'Condition': clean_name,
                'Prevalence': prevalence * 100  # Convert to percentage
            })
    
    if not condition_data:
        print("No condition data found for visualization; writing placeholder")
        _write_placeholder_png(HEATMAP_PATH, 'No RF condition data to display')
        return
    
    condition_df = pd.DataFrame(condition_data)
    
    # Create pivot table for heatmap
    heatmap_data = condition_df.pivot(index='Condition', columns='Cluster', values='Prevalence')
    
    # Create the heatmap
    plt.figure(figsize=(12, 10))
    sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='Reds', 
                cbar_kws={'label': 'Prevalence (%)'})
    
    plt.title('RF Conditions Prevalence Across Clusters\n(>10% prevalence)', 
              fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Patient Clusters', fontsize=12)
    plt.ylabel('Medical Conditions', fontsize=12)
    
    # Rotate labels for better readability
    plt.xticks(rotation=0)
    plt.yticks(rotation=0)
    
    plt.tight_layout()
    Path(HEATMAP_PATH).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(HEATMAP_PATH), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Heatmap saved as: {HEATMAP_PATH}")

def show_cluster_sizes(cluster_interpretations):
    """Create and show cluster size distribution"""
    
    cluster_ids = []
    sizes = []
    phenotypes = []
    
    for cluster_id, info in cluster_interpretations.items():
        cluster_ids.append(f"Cluster {cluster_id}")
        sizes.append(info.get('size', 0))
        phenotypes.append(info.get('phenotype', 'Unknown')[:30])  # Truncate long names
    
    if len(cluster_ids) == 0 or sum(sizes) <= 0:
        print("No cluster size data; writing placeholder")
        _write_placeholder_png(SIZES_PATH, 'No cluster size data to display')
        return

    # Create pie chart
    plt.figure(figsize=(10, 8))
    colors = plt.cm.Set3(np.linspace(0, 1, len(cluster_ids)))
    
    wedges, texts, autotexts = plt.pie(sizes, labels=cluster_ids, autopct='%1.1f%%', 
                                       colors=colors, startangle=90)
    
    plt.title('Patient Cluster Size Distribution', fontsize=16, fontweight='bold')
    
    # Add legend with phenotypes
    legend_labels = [f"{cluster_ids[i]}: {phenotypes[i]}" for i in range(len(cluster_ids))]
    plt.legend(legend_labels, loc='center left', bbox_to_anchor=(1, 0.5))
    
    plt.tight_layout()
    Path(SIZES_PATH).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(SIZES_PATH), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Cluster sizes chart saved as: {SIZES_PATH}")

def show_demographics(cluster_interpretations):
    """Show demographics comparison"""
    
    cluster_ids = []
    ages = []
    must_scores = []
    
    for cluster_id, info in cluster_interpretations.items():
        cluster_ids.append(f"C{cluster_id}")
        ages.append(info.get('avg_age', 0) if info.get('avg_age') else 0)
        must_scores.append(info.get('must_score', 0) if info.get('must_score') else 0)
    
    if len(cluster_ids) == 0:
        print("No demographics data; writing placeholder")
        _write_placeholder_png(DEMOS_PATH, 'No demographics data to display')
        return

    # Create subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Age comparison
    bars1 = ax1.bar(cluster_ids, ages, color=plt.cm.Set3(np.linspace(0, 1, len(cluster_ids))))
    ax1.set_title('Average Age by Cluster', fontweight='bold')
    ax1.set_ylabel('Age (years)')
    ax1.set_xlabel('Cluster')
    
    # Add value labels
    for bar, age in zip(bars1, ages):
        if age > 0:
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{age:.1f}', ha='center', va='bottom', fontweight='bold')
    
    # MUST score comparison
    bars2 = ax2.bar(cluster_ids, must_scores, color=plt.cm.Set3(np.linspace(0, 1, len(cluster_ids))))
    ax2.set_title('MUST Score by Cluster', fontweight='bold')
    ax2.set_ylabel('MUST Score')
    ax2.set_xlabel('Cluster')
    
    # Add risk zones
    ax2.axhline(y=2, color='red', linestyle='--', alpha=0.7, label='High Risk (≥2)')
    ax2.axhline(y=1, color='orange', linestyle='--', alpha=0.7, label='Medium Risk (1-2)')
    
    # Add value labels
    for bar, score in zip(bars2, must_scores):
        if score > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                    f'{score:.2f}', ha='center', va='bottom', fontweight='bold')
    
    ax2.legend()
    
    plt.tight_layout()
    Path(DEMOS_PATH).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(DEMOS_PATH), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Demographics chart saved as: {DEMOS_PATH}")

# Optional CLI usage retained (requires user to pass interpretations manually)
if __name__ == "__main__":
    print("This module provides plotting functions for the API.\n"
          "Invoke from FastAPI endpoints or pass interpretations manually here.")
