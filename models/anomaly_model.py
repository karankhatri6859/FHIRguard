import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

MODEL_PATH = "isolation_forest_model.joblib"

def generate_synthetic_data():
    """Generates a synthetic dataset for model training."""
    np.random.seed(42)
    # Simulate normal systolic blood pressure values (e.g., 90-140 mmHg)
    normal_data = np.random.normal(loc=120, scale=10, size=(1000, 1))
    return normal_data

def train_and_save_model():
    """Trains and saves the IsolationForest model."""
    if not os.path.exists(MODEL_PATH):
        print("Training new IsolationForest model...")
        normal_data = generate_synthetic_data()
        model = IsolationForest(random_state=42).fit(normal_data)
        joblib.dump(model, MODEL_PATH)
        print("Model trained and saved.")
    else:
        print("Loading existing IsolationForest model.")

def get_anomaly_model():
    """Loads and returns the trained anomaly detection model."""
    train_and_save_model()
    return joblib.load(MODEL_PATH)
