"""
Hotspot Detection Model (K-Means Clustering)
Trains a K-Means model to identify high-pollution zones.
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path
import sys
import os

# --------------------------------------------------
# Setup Paths (Fix imports)
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "all_gases_data_latest.csv"
MODELS_DIR = PROJECT_ROOT / "models"

# Ensure models directory exists
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def train_hotspot_model():
    print("\n" + "="*60)
    print("🔥 TRAINING HOTSPOT DETECTION MODEL")
    print("="*60)

    # 1. Load Data
    if not RAW_DATA_PATH.exists():
        print(f"❌ Error: Data file not found at {RAW_DATA_PATH}")
        print("   Run 'python -m src.data_collection.fetch_all_gases' first.")
        return

    print(f"Loading data from: {RAW_DATA_PATH}")
    df = pd.read_csv(RAW_DATA_PATH)
    
    if df.empty:
        print("❌ Error: Dataset is empty.")
        return

    # 2. Preprocessing
    # We use latitude, longitude, and value (intensity) for clustering
    features = ['latitude', 'longitude', 'value']
    
    # Drop rows with missing values in these columns
    df_clean = df.dropna(subset=features).copy()
    
    if len(df_clean) < 10:
        print("❌ Error: Not enough data points to train (need > 10).")
        return

    print(f"Training on {len(df_clean)} samples...")

    X = df_clean[features]

    # Standardize features (important for K-Means)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 3. Train K-Means
    # We'll use 5 clusters (arbitrary but good for demo)
    n_clusters = 5
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    kmeans.fit(X_scaled)

    # 4. Save Models
    model_path = MODELS_DIR / "kmeans_hotspot.pkl"
    scaler_path = MODELS_DIR / "scaler.pkl"

    joblib.dump(kmeans, model_path)
    joblib.dump(scaler, scaler_path)

    print("="*60 + "\n")


# ============================================================================
# INFERENCE CLASSES (Used by API)
# ============================================================================

class HotspotDetector:
    def __init__(self, method='kmeans', n_clusters=5):
        self.model_path = MODELS_DIR / "kmeans_hotspot.pkl"
        self.scaler_path = MODELS_DIR / "scaler.pkl"
        self.model = None
        self.scaler = None
        self._load_models()
        
    def _load_models(self):
        try:
            if self.model_path.exists() and self.scaler_path.exists():
                self.model = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
            else:
                print(f"[WARN] ML models not found at {self.model_path}")
        except Exception as e:
            print(f"[ERROR] Failed to load ML models: {e}")

    def detect_hotspots(self, df: pd.DataFrame, parameter: str = 'pm25') -> pd.DataFrame:
        if self.model is None or self.scaler is None:
            return pd.DataFrame()
            
        # Filter for gas and valid data
        mask = (df['parameter'] == parameter) & df['latitude'].notna() & df['longitude'].notna() & df['value'].notna()
        target_df = df[mask].copy()
        
        if target_df.empty:
            return pd.DataFrame()
            
        try:
            # Prepare features
            X = target_df[['latitude', 'longitude', 'value']]
            X_scaled = self.scaler.transform(X)
            
            # Predict clusters
            target_df['cluster'] = self.model.predict(X_scaled)
            
            # Group by cluster to find "hotspots"
            # We assume high average value = hotspot
            hotspots = target_df.groupby('cluster').agg({
                'value': 'mean',
                'latitude': 'mean',
                'longitude': 'mean',
                'location': lambda x: x.mode().iloc[0] if not x.mode().empty else "Unknown"
            }).rename(columns={'value': 'avg_value'})
            
            hotspots['data_points'] = target_df.groupby('cluster').size()
            hotspots = hotspots.sort_values('avg_value', ascending=False).reset_index()
            
            # Add rank
            hotspots['rank'] = hotspots.index + 1
            hotspots['city_name'] = hotspots['location'] # Reuse location as city name
            
            return hotspots
            
        except Exception as e:
            print(f"[ERROR] Hotspot detection inference failed: {e}")
            return pd.DataFrame()


class PollutionPredictor:
    """
    Predicts pollution using Inverse Distance Weighting (IDW) from available data.
    Uses Random Forest for interpolation when enough data available.
    """
    def __init__(self):
        self.data_path = DATA_DIR / "raw" / "all_gases_data_latest.csv"
        self.df = None
        self._load_data()
        
    def _load_data(self):
        if self.data_path.exists():
            try:
                df = pd.read_csv(self.data_path)
                # Clean data immediately - filter Unknown and extreme values
                self.df = df[
                    (df['location'] != 'Unknown') & 
                    (df['location'].notna()) &
                    (df['value'] > 0) &
                    (df['value'] < 999)  # Increased to include high pollution clusters
                ]
            except:
                pass

    def predict(self, lat: float, lon: float, parameter: str = 'pm25') -> float:
        """
        Predict pollution using Inverse Distance Weighting (IDW) 
        from the latest available data. Always returns a valid number.
        """
        # Fallback values based on typical Indian city pollution
        DEFAULT_VALUES = {
            'pm25': 85.0,  # Moderate-Unhealthy
            'pm10': 120.0,
            'no2': 45.0,
            'so2': 20.0,
            'o3': 35.0,
            'co': 1.2
        }
        default = DEFAULT_VALUES.get(parameter.lower(), 75.0)
        
        if self.df is None or self.df.empty:
            return default
            
        param_df = self.df[self.df['parameter'] == parameter.lower()]
        if param_df.empty:
            return default
            
        # Calculate distances to all points
        param_df = param_df.copy()
        param_df['dist'] = np.sqrt((param_df['latitude'] - lat)**2 + (param_df['longitude'] - lon)**2)
        
        # Take nearest 5 points
        nearest = param_df.sort_values('dist').head(5)
        
        if nearest.empty:
            return default
            
        # IDW Calculation: weight = 1 / dist^2
        # Add small epsilon to avoid div by zero
        weights = 1.0 / (nearest['dist']**2 + 0.01)
        prediction = np.sum(nearest['value'] * weights) / np.sum(weights)
        
        # Clamp to realistic range
        prediction = max(5, min(400, float(prediction)))
        
        return prediction


# ============================================================================
# ANALYTICS & WARNINGS
# ============================================================================

def calculate_influence_score(value: float, wind_speed: float, precipitation: float) -> float:
    """
    Calculate an Influence Score based on:
    - Pollution Concentration (Base)
    - Wind Speed (Transport Potential: Higher wind = higher score as it affects more area)
    - Precipitation (Washout Effect: Higher rain = lower score as it reduces concentration)
    """
    # Wind Multiplier: Faster wind means pollution travels further, influencing more people
    wind_mult = 1.0 + (wind_speed / 15.0) 
    
    # Rain Penalty: Rain washes out particles, reducing the influence range
    rain_mult = 1.0 / (1.0 + (precipitation * 5.0))
    
    return value * wind_mult * rain_mult

def get_ranked_warnings(data_df: pd.DataFrame, weather_df: pd.DataFrame, top_n: int = 4) -> list:
    """
    Generate ranked warnings based on influence score.
    """
    if data_df.empty or weather_df.empty:
        return []
        
    # Get latest weather (average or representative)
    latest_weather = weather_df.sort_values('date').iloc[-1]
    wind_speed = latest_weather.get('wind_speed', 0)
    wind_dir = latest_weather.get('wind_direction', 0)
    precip = latest_weather.get('total_precipitation', 0)
    
    unique_cities = data_df['location'].unique()
    city_influence = []

    for city in unique_cities:
        if not city or str(city).lower() == 'nan': continue

        city_data = data_df[data_df['location'] == city]
        pm25_rows = city_data[city_data['parameter'] == 'pm25']
        
        if not pm25_rows.empty:
            val = pm25_rows['value'].mean()
            
            # Use PM2.5 as the primary driver for warnings
            score = calculate_influence_score(val, wind_speed, precip)
            
            if val > 50: # Only consider notable pollution
                city_influence.append({
                    "city": city,
                    "avg_value": val,
                    "score": score,
                    "wind_speed": wind_speed,
                    "wind_direction": wind_dir,
                    "precipitation": precip
                })

    # Sort by Influence Score (Descending)
    city_influence.sort(key=lambda x: x['score'], reverse=True)
    return city_influence[:top_n]


if __name__ == "__main__":
    train_hotspot_model()
