import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Get ML models and data directories
ML_MODELS_DIR = Path(__file__).parent.parent / "ml" / "models"
DATA_SAMPLES_DIR = Path(__file__).parent.parent / "data" / "samples"

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        new_args = []
        for a in args:
            if isinstance(a, str):
                try:
                    new_args.append(a.encode('ascii', 'ignore').decode('ascii'))
                except Exception:
                    new_args.append('')
            else:
                new_args.append(a)
        try:
            print(*new_args, **kwargs)
        except Exception:
            pass

class SVDNutritionalRiskPredictor:

    def __init__(self):
        self.model_package = None
        self.svd_transformer = None
        self.rf_columns = None
        self.feature_columns = None
        self.scaler = None
        self.model = None
        self.requires_scaling = False
        
    def load_trained_components(self, model_filename="patient_predictor_model.pkl", clustering_data_path="UpdatedDataFile_aggregated.csv"):
        # Use full paths
        model_path = ML_MODELS_DIR / model_filename
        data_path = DATA_SAMPLES_DIR / clustering_data_path
        
        safe_print("\n1. LOADING TRAINED MODEL AND SVD COMPONENTS")
        safe_print("-" * 50)
        
        try:
            # Load the trained model package
            self.model_package = joblib.load(model_path)
            self.model = self.model_package['model_object']
            self.requires_scaling = self.model_package['requires_scaling']
            self.feature_columns = self.model_package['feature_names']
            
            if self.requires_scaling:
                self.scaler = self.model_package['scaler']
                safe_print("Loaded trained model with scaling")
            else:
                safe_print("Loaded trained model (no scaling required)")
                
            safe_print(f"   Model Type: {self.model_package['model_type']}")
            safe_print(f"   Performance: F1={self.model_package['performance_metrics']['high_risk_f1']:.3f}")
            safe_print(f"   Features: {len(self.feature_columns)} total")
            
        except FileNotFoundError:
            safe_print(f"Model file not found: {model_filename}")
            return False
        except Exception as e:
            safe_print(f"Error loading model: {e}")
            return False
        
        # Load the original clustering data to reconstruct SVD transformer
        try:
            df_original = pd.read_csv(data_path)
            safe_print(f"Loaded original clustering data: {df_original.shape}")
            
            # Get RF columns
            self.rf_columns = [col for col in df_original.columns if col.startswith('RF_')]
            safe_print(f"   RF columns: {len(self.rf_columns)}")
            
            # Reconstruct the SVD transformer
            rf_matrix = df_original[self.rf_columns].fillna(0).values
            
            # Use the same number of components as in the saved feature columns
            svd_component_cols = [col for col in self.feature_columns if col.startswith('SVD_Component')]
            n_components = len(svd_component_cols)
            
            # Fit SVD transformer on original data
            self.svd_transformer = TruncatedSVD(n_components=n_components, random_state=42)
            self.svd_transformer.fit(rf_matrix)
            
            safe_print(f"Reconstructed SVD transformer with {n_components} components")
            safe_print(f"   Variance explained: {self.svd_transformer.explained_variance_ratio_.sum():.3f}")
            
            return True
            
        except FileNotFoundError:
            safe_print(f"Clustering data file not found: {data_path}")
            return False
        except Exception as e:
            safe_print(f"Error reconstructing SVD: {e}")
            return False
    
    def prepare_patient_rf_data(self, patient_conditions):
        """
        Convert patient's medical conditions to RF factor binary vector
        
        Parameters:
        patient_conditions: dict or list of medical conditions/risk factors
        """
        
        # Initialize RF vector with zeros
        rf_vector = np.zeros(len(self.rf_columns))
        
        if isinstance(patient_conditions, dict):
            # Patient conditions provided as dict with RF column names
            for i, rf_col in enumerate(self.rf_columns):
                rf_vector[i] = patient_conditions.get(rf_col, 0)
                
        elif isinstance(patient_conditions, list):
            # Patient conditions provided as list of condition names
            # Map condition names to RF columns
            for condition in patient_conditions:
                # Find matching RF columns (flexible matching)
                for i, rf_col in enumerate(self.rf_columns):
                    # Remove RF_ prefix and convert to lowercase for matching
                    rf_name = rf_col.replace('RF_', '').lower().replace('_', ' ')
                    if condition.lower() in rf_name or rf_name in condition.lower():
                        rf_vector[i] = 1
                        break
        
        return rf_vector.reshape(1, -1)  # Return as 2D array for SVD
    
    def transform_to_svd_space(self, rf_vector):
        """
        Transform RF factors to SVD component space
        """
        if self.svd_transformer is None:
            raise ValueError("SVD transformer not loaded. Call load_trained_components() first.")
        
        # Transform to SVD space
        svd_components = self.svd_transformer.transform(rf_vector)
        return svd_components[0]  # Return 1D array
    
    def prepare_full_feature_vector(self, age, gender, patient_conditions):
        """
        Prepare complete feature vector for model prediction
        """
        
        # Convert patient conditions to RF factors and then to SVD space
        rf_vector = self.prepare_patient_rf_data(patient_conditions)
        svd_components = self.transform_to_svd_space(rf_vector)
        
        # Prepare demographic features
        gender_male = 1 if gender.lower() == 'male' else 0
        
        # Combine features in the same order as training
        feature_vector = np.zeros(len(self.feature_columns))
        
        for i, feature_name in enumerate(self.feature_columns):
            if feature_name == 'Gender':
                feature_vector[i] = gender_male
            elif feature_name == 'Age':
                feature_vector[i] = age
            elif feature_name.startswith('SVD_Component_'):
                # Extract component number
                comp_num = int(feature_name.split('_')[-1]) - 1  # Convert to 0-based index
                if comp_num < len(svd_components):
                    feature_vector[i] = svd_components[comp_num]
        
        return feature_vector.reshape(1, -1)  # Return as 2D array for model
    
    def predict_patient_risk(self, age, gender, patient_conditions, include_details=True):
        """
        Complete prediction pipeline for a new patient
        
        Parameters:
        - age: patient age (years)
        - gender: 'male' or 'female'
        - patient_conditions: dict or list of medical conditions
        - include_details: whether to include detailed explanation
        
        Returns:
        - dict with prediction results
        """
        
        if self.model is None:
            raise ValueError("Model not loaded. Call load_trained_components() first.")
        
        try:
            # Prepare feature vector
            feature_vector = self.prepare_full_feature_vector(age, gender, patient_conditions)
            
            # Apply scaling if required
            if self.requires_scaling:
                feature_vector = self.scaler.transform(feature_vector)
            
            # Get predictions
            risk_probability = self.model.predict_proba(feature_vector)[0, 1]
            risk_prediction = self.model.predict(feature_vector)[0]
            
            # Determine risk level
            risk_assessment = self._assess_risk_level(risk_probability)
            
            results = {
                'age': age,
                'gender': gender,
                'risk_probability': round(risk_probability, 3),
                'risk_prediction': int(risk_prediction),
                'risk_level': risk_assessment['level'],
                'risk_category': risk_assessment['category'],
                'recommendations': risk_assessment['recommendations'],
                'model_confidence': self._calculate_confidence(risk_probability)
            }
            
            if include_details:
                # Get SVD components for interpretation
                rf_vector = self.prepare_patient_rf_data(patient_conditions)
                svd_components = self.transform_to_svd_space(rf_vector)
                
                results['technical_details'] = {
                    'svd_components': {f'Component_{i+1}': round(comp, 3) 
                                     for i, comp in enumerate(svd_components[:5])},
                    'model_type': self.model_package['model_type'],
                    'requires_scaling': self.requires_scaling,
                    'feature_vector_length': len(feature_vector[0])
                }
                
                results['clinical_interpretation'] = self._generate_clinical_interpretation(
                    age, gender, svd_components, risk_probability
                )
            
            return results
            
        except Exception as e:
            return {'error': f"Prediction failed: {e}"}
    
    def _assess_risk_level(self, probability):
        """Assess risk level and generate recommendations"""
        
        if probability >= 0.80:
            level = "VERY HIGH"
            category = "Immediate Intervention Required"
            recommendations = [
                "🚨 Complete comprehensive nutritional assessment within 24 hours",
                "🍎 Schedule immediate dietitian consultation",
                "📊 Initiate daily weight monitoring",
                "💊 Consider nutritional supplements",
                "👥 Coordinate multidisciplinary care team"
            ]
        elif probability >= 0.60:
            level = "HIGH"
            category = "Enhanced Monitoring Required"
            recommendations = [
                "⚠️ Complete MUST assessment within 48 hours",
                "🍎 Schedule dietitian consultation within 1 week",
                "📊 Implement bi-weekly weight monitoring",
                "🍽️ Review dietary intake patterns"
            ]
        elif probability >= 0.40:
            level = "MODERATE"
            category = "Routine Enhanced Screening"
            recommendations = [
                "📋 Complete standard MUST assessment",
                "🍽️ Review dietary preferences and intake",
                "📊 Monthly weight monitoring",
                "👀 Staff awareness of nutritional concerns"
            ]
        else:
            level = "LOW"
            category = "Standard Care"
            recommendations = [
                "✅ Continue routine nutritional care",
                "📊 Quarterly weight checks",
                "📅 Routine MUST screening per protocol"
            ]
        
        return {'level': level, 'category': category, 'recommendations': recommendations}
    
    def _calculate_confidence(self, probability):
        """Calculate prediction confidence"""
        distance_from_threshold = abs(probability - 0.5)
        if distance_from_threshold >= 0.4:
            return "High"
        elif distance_from_threshold >= 0.2:
            return "Medium"
        else:
            return "Low"
    
    def _generate_clinical_interpretation(self, age, gender, svd_components, probability):
        """Generate clinical explanation"""
        
        interpretation = {
            'risk_factors': [],
            'protective_factors': [],
            'key_patterns': []
        }
        
        # Age-related factors
        if age >= 85:
            interpretation['risk_factors'].append(f"Advanced age ({age}) - increased frailty risk")
        elif age < 70:
            interpretation['protective_factors'].append(f"Younger age ({age}) - lower baseline risk")
        
        # SVD component interpretation (based on typical patterns)
        if len(svd_components) > 0:
            if svd_components[0] > 1.5:
                interpretation['key_patterns'].append("High medical complexity pattern (Component 1)")
            if len(svd_components) > 1 and svd_components[1] > 1.2:
                interpretation['key_patterns'].append("Care dependency indicators (Component 2)")
            if len(svd_components) > 2 and abs(svd_components[2]) > 1.0:
                interpretation['key_patterns'].append("Specific condition clustering (Component 3)")
        
        # Overall assessment
        if probability >= 0.7:
            interpretation['overall'] = "Multiple strong risk indicators present"
        elif probability >= 0.4:
            interpretation['overall'] = "Some risk indicators present"
        else:
            interpretation['overall'] = "Low risk profile detected"
        
        return interpretation

# =====================================================
# DEMONSTRATION WITH DIFFERENT PATIENT EXAMPLES
# =====================================================

def demonstrate_svd_prediction_pipeline():
    """Demonstrate the complete SVD prediction pipeline"""
    
    print("\n" + "=" * 55)
    print("DEMONSTRATION: SVD PIPELINE PREDICTION")
    print("=" * 55)
    
    # Initialize predictor
    predictor = SVDNutritionalRiskPredictor()
    
    # Load trained components
    success = predictor.load_trained_components()
    if not success:
        print("Failed to load trained components. Cannot proceed with demonstration.")
        return
    
    # Example patients with different formats of condition data
    example_patients = [
        {
            'name': 'Patient A - High Risk Elderly',
            'age': 89,
            'gender': 'female',
            'conditions_dict': {
                'RF_dementia': 1,
                'RF_frailty': 1,
                'RF_difficulty_swallowing': 1,
                'RF_decreased_appetite': 1,
                'RF_fall_risk': 1,
                'RF_confusion': 1,
                'RF_medication_dependency': 1
            }
        },
        {
            'name': 'Patient B - Low Risk',
            'age': 72,
            'gender': 'female',
            'conditions_dict': {
                'RF_hypertension': 1,
                'RF_vitamin_d': 1  # Only minor conditions
            }
        }
    ]
    
    # Process each patient
    for i, patient in enumerate(example_patients):
        print(f"\n{'=' * 20} {patient['name'].upper()} {'=' * 20}")
        
        conditions = patient['conditions_dict']
        print(f"Input format: RF factor dictionary ({len(conditions)} conditions)")

        # Make prediction
        result = predictor.predict_patient_risk(
            age=patient['age'],
            gender=patient['gender'],
            patient_conditions=conditions,
            include_details=True
        )
        
        if 'error' in result:
            print(f"❌ Prediction failed: {result['error']}")
            continue
        
        # Display results
        print("\nPATIENT SUMMARY:")
        print(f"  Age: {result['age']}, Gender: {result['gender'].title()}")
        print(f"  Risk Probability: {result['risk_probability']:.1%}")
        print(f"  Risk Level: {result['risk_level']}")
        print(f"  Category: {result['risk_category']}")
        print(f"  Model Confidence: {result['model_confidence']}")
        
        # print("\nTECHNICAL DETAILS:")
        # tech_details = result['technical_details']
        # print(f"  Model Type: {tech_details['model_type']}")
        # print(f"  Requires Scaling: {tech_details['requires_scaling']}")
        # print(f"  Top SVD Components:")
        # for comp_name, value in tech_details['svd_components'].items():
        #     print(f"    {comp_name}: {value}")
        
        # print(f"\nCLINICAL INTERPRETATION:")
        # interp = result['clinical_interpretation']
        # print(f"  Overall: {interp['overall']}")
        # if interp['risk_factors']:
        #     print(f"  Risk Factors: {'; '.join(interp['risk_factors'])}")
        # if interp['protective_factors']:
        #     print(f"  Protective Factors: {'; '.join(interp['protective_factors'])}")
        # if interp['key_patterns']:
        #     print(f"  Key Patterns: {'; '.join(interp['key_patterns'])}")
        
        # print(f"\nRECOMMENDED ACTIONS:")
        # for j, rec in enumerate(result['recommendations'][:3], 1):
        #     print(f"  {j}. {rec}")

if __name__ == "__main__":
    
    # # Show what files are needed
    # print("\nREQUIRED FILES:")
    # print("-" * 20)
    # print("✅ patient_predictor_model.pkl (your trained model)")
    # print("✅ Binary_RF_SVD_clustering_results.csv (contains SVD components)")
    # print("✅ Patient SVD component values (for new predictions)")
    
    # Run demonstrations
    demonstrate_svd_prediction_pipeline()