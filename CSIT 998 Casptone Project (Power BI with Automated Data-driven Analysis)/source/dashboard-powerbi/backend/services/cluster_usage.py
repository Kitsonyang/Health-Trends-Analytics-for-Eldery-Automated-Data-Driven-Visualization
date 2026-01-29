import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from sklearn.metrics.pairwise import euclidean_distances

# Fixed model loader for patient clustering
# ========================================

# Get ML models directory
ML_MODELS_DIR = Path(__file__).parent.parent / "ml" / "models"

class PatientClusteringPipeline:
    """Dummy class to handle pickle loading"""
    def __init__(self, svd_model=None, clustering_model=None, rf_columns=None):
        self.svd_model = svd_model
        self.clustering_model = clustering_model
        self.rf_columns = rf_columns
    
    def predict(self, new_patient_data):
        pass  # We won't use this, just need it to exist for pickle

def load_patient_models(filename='patient_classifier_model.pkl'):
    """
    Load the saved patient clustering models
    """
    # Use full path to ML models directory
    model_path = ML_MODELS_DIR / filename
    print(f"Loading models from: {model_path}")
    
    try:
        # Now pickle can find the PatientClusteringPipeline class
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        print("Models loaded successfully")
        
        # Extract the components we actually need
        svd_model = model_data.get('svd_model')
        
        # Try different keys for the clustering model
        clustering_model = (model_data.get('best_clustering_model') or 
                          model_data.get('kmeans_model') or 
                          model_data.get('clustering_model'))
        
        rf_columns = model_data.get('rf_columns', [])
        cluster_interpretations = model_data.get('cluster_interpretations', {})
        
        print("Extracted components:")
        print(f"  SVD model: {type(svd_model).__name__}")
        print(f"  Clustering model: {type(clustering_model).__name__}")
        print(f"  RF columns: {len(rf_columns)}")
        print(f"  Clusters: {len(cluster_interpretations)}")
        
        return svd_model, clustering_model, rf_columns, cluster_interpretations
        
    except Exception as e:
        print(f"Loading failed: {e}")
        return None, None, None, None

def classify_patient(patient_data, svd_model, clustering_model, rf_columns, cluster_interpretations, patient_id="Unknown"):
    """
    Classify a new patient using the loaded models
    """
    print(f"\nClassifying patient: {patient_id}")
    
    # Prepare patient data
    if isinstance(patient_data, dict):
        patient_df = pd.DataFrame([patient_data])
    else:
        patient_df = patient_data.copy()
    
    # Add missing RF columns as 0
    for col in rf_columns:
        if col not in patient_df.columns:
            patient_df[col] = 0
    
    # Extract RF features
    rf_features = patient_df[rf_columns].fillna(0).values
    
    # Apply SVD transformation
    svd_features = svd_model.transform(rf_features)
    
    # Predict cluster
    predicted_cluster = clustering_model.predict(svd_features)[0]
    
    # Calculate confidence (if K-means)
    confidence = None
    if hasattr(clustering_model, 'cluster_centers_'):
        distances = euclidean_distances(svd_features, clustering_model.cluster_centers_)[0]
        assigned_distance = distances[predicted_cluster]
        other_distances = [d for i, d in enumerate(distances) if i != predicted_cluster]
        min_other = min(other_distances) if other_distances else assigned_distance
        confidence = 1 - (assigned_distance / (assigned_distance + min_other))
    
    # Get cluster info
    cluster_info = cluster_interpretations.get(predicted_cluster, {})
    
    # Count active conditions
    active_conditions = int(rf_features.sum())
    
    result = {
        'patient_id': patient_id,
        'predicted_cluster': predicted_cluster,
        'cluster_phenotype': cluster_info.get('phenotype', 'Unknown'),
        'confidence_score': confidence,
        'active_conditions_count': active_conditions,
        'cluster_size': cluster_info.get('size', 'Unknown')
    }
    
    print(f"Result: Cluster {predicted_cluster} - {result['cluster_phenotype']}")
    if confidence:
        print(f"Confidence: {confidence:.3f}")
    
    return result

# Globals populated lazily by shared.ensure_models_loaded
svd_model = None
clustering_model = None
rf_columns = []
cluster_interpretations = {}