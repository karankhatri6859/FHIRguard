# train_comprehensive.py
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib

def generate_full_body_data(n_samples=5000):
    """
    Generates synthetic data for 11 vital signs.
    Features: [Age, Sys, Dia, HR, Resp, Temp, O2, BMI, Gluc, Pain, GCS]
    """
    rng = np.random.RandomState(42)
    data = []

    # --- 1. The "Healthy" Majority (Normal Vitals) ---
    n = int(n_samples * 0.7)
    ages = rng.uniform(18, 70, n)
    sys = rng.normal(120, 10, n)
    dia = rng.normal(80, 8, n)
    hr = rng.normal(72, 8, n)
    resp = rng.normal(16, 2, n)
    temp = rng.normal(36.8, 0.3, n)
    o2 = rng.normal(98, 1, n)
    bmi = rng.normal(25, 4, n)
    gluc = rng.normal(90, 10, n)
    pain = np.zeros(n)          # Healthy people have 0 pain
    gcs = np.full(n, 15)        # Healthy people are fully conscious (GCS 15)
    
    data.append(np.column_stack((ages, sys, dia, hr, resp, temp, o2, bmi, gluc, pain, gcs)))

    # --- 2. The "Metabolic" Risk Group (Diabetic/Obese) ---
    n = int(n_samples * 0.1)
    ages = rng.uniform(40, 80, n)
    sys = rng.normal(140, 15, n)
    dia = rng.normal(90, 10, n)
    hr = rng.normal(80, 10, n)
    resp = rng.normal(18, 3, n)
    temp = rng.normal(36.8, 0.4, n)
    o2 = rng.normal(96, 2, n)
    bmi = rng.normal(35, 5, n)    # High BMI
    gluc = rng.normal(180, 40, n) # High Glucose
    pain = rng.choice([0, 1, 2, 3], n) # Mild discomfort
    gcs = np.full(n, 15)
    
    data.append(np.column_stack((ages, sys, dia, hr, resp, temp, o2, bmi, gluc, pain, gcs)))

    # --- 3. The "Trauma/Acute" Risk Group (Anomalies) ---
    # Simulating accidents: High Pain, Low GCS, Shock (Low BP/High HR)
    n = int(n_samples * 0.05)
    ages = rng.uniform(18, 50, n)
    sys = rng.normal(90, 15, n)   # Hypotension (Shock)
    dia = rng.normal(60, 10, n)
    hr = rng.normal(120, 20, n)   # Tachycardia
    resp = rng.normal(28, 5, n)   # Hyperventilation
    temp = rng.normal(37.0, 1.0, n)
    o2 = rng.normal(92, 5, n)
    bmi = rng.normal(25, 4, n)
    gluc = rng.normal(110, 30, n) # Stress hyperglycemia
    pain = rng.uniform(7, 10, n)  # Severe Pain
    gcs = rng.choice([3, 4, 5, 6, 7, 8, 9, 10, 11, 12], n) # Altered Consciousness
    
    data.append(np.column_stack((ages, sys, dia, hr, resp, temp, o2, bmi, gluc, pain, gcs)))

    return np.vstack(data)

print("🧪 Generating 11-Point Full-Body Dataset...")
X_train = generate_full_body_data()

print("🧠 Training Full-Body Isolation Forest...")
# Features: Age, Sys, Dia, HR, Resp, Temp, O2, BMI, Gluc, Pain, GCS
clf = IsolationForest(n_estimators=200, contamination=0.05, random_state=42)
clf.fit(X_train)

joblib.dump(clf, "comprehensive_model.joblib")
print("✅ Success! 'comprehensive_model.joblib' saved.")

# --- Diagnostic Tests ---
# 1. Healthy Adult
normal = [[35, 120, 80, 70, 16, 37.0, 99, 24, 90, 0, 15]]
print(f"Healthy Adult: {clf.predict(normal)[0]} (Expect 1)")

# 2. Trauma Victim (Pain 9, GCS 10, Low BP)
trauma = [[35, 85, 50, 130, 30, 37.0, 90, 24, 110, 9, 10]]
print(f"Trauma Case:   {clf.predict(trauma)[0]} (Expect -1)")