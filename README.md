# 🌍 AI AirAware Pro
### Advanced Pollution Monitoring & Intelligence Platform

[![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)](/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![ML](https://img.shields.io/badge/ML-Scikit--Learn-orange?style=for-the-badge&logo=scikitlearn)](https://scikit-learn.org)
[![Leaflet](https://img.shields.io/badge/Maps-Leaflet-199900?style=for-the-badge&logo=leaflet)](https://leafletjs.com)

> **Real-time air quality monitoring for India with AI-powered forecasting and intelligent insights.**

---

## ✨ Key Features

| Feature | Description | Technology |
|---------|-------------|------------|
| 🗺️ **Interactive Map** | Color-coded pollution markers across India | Leaflet + Heatmap |
| 🔥 **Hotspot Detection** | AI identifies top 5 pollution clusters | K-Means Clustering |
| 📈 **City-Specific Forecast** | 24-hour predictions with unique city baselines | Random Forest |
| 🤖 **Smart Chatbot** | Context-aware answers about air quality | RAG + Llama 3.3 (Groq) |
| 🌡️ **Multi-Gas Support** | PM2.5, PM10, NO2, SO2, O3, CO | Real-time API data |
| 🌬️ **Wind Tracking** | See pollution movement arrows | ERA5 Weather Data |
| 🌙 **Day/Night Mode** | Toggle between dark & light themes | CSS Theme Switcher |

---

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/your-repo/ai-air-pollution-monitoring.git
cd ai-air-pollution-monitoring
pip install -r requirements.txt
```

### 2. Configure API Keys
Create a `.env` file:
```env
WAQI_API_TOKEN=your_waqi_token
GROQ_API_KEY=your_groq_key
# Optional
OPENAQ_API_KEY=your_openaq_key
```

### 3. Fetch Data & Run
```bash
# Fetch latest pollution data
python src/data_collection/fetch_all_gases.py

# Start the server
python api/main.py
```

### 4. Open Dashboard
Navigate to `http://localhost:8000` or open `dashboard/index.html`

---

## 🧠 AI/ML Components

### 1. K-Means Clustering (Hotspot Detection)
- **Input:** [lat, lon, pollution_value] for 1000+ stations
- **Output:** Top 5 high-pollution clusters ranked by severity
- **Use Case:** Identify pollution hotspots for intervention

### 2. Random Forest (City-Specific Forecast)
- **Features:** Hour of day, city baseline, metro/industrial patterns
- **Output:** 24-hour PM2.5 predictions per city
- **City Baselines:** Delhi ~180, Mumbai ~95, Bangalore ~65 µg/m³

### 3. RAG + LLM (AI Chatbot)
- **Architecture:** Real-time data → Prompt injection → Llama 3.3 70B
- **Capability:** Context-aware answers about local air quality

---

## 📁 Project Structure

```
ai-air-pollution-monitoring/
├── api/
│   └── main.py              # FastAPI backend (all endpoints)
├── dashboard/
│   ├── index.html           # Main UI
│   ├── script.js            # Frontend logic
│   └── style.css            # Glassmorphism + Day/Night themes
├── src/
│   ├── data_collection/     # Data fetchers (WAQI, OpenAQ, Satellite)
│   ├── models/
│   │   ├── hotspot_detection.py  # K-Means + IDW Predictor
│   │   └── forecasting.py        # City-Specific Forecaster
│   └── utils/               # Config files
├── data/raw/                # Downloaded CSV data
├── requirements.txt
└── README.md
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check + supported gases |
| `/data/recent` | GET | Latest pollution readings |
| `/stats` | GET | Aggregated statistics |
| `/hotspots` | GET | Top pollution clusters |
| `/predict/forecast/{city}` | GET | 24-hour city forecast |
| `/chatbot` | POST | AI assistant |
| `/tracking` | GET | Wind direction data |
| `/warnings` | GET | Pollution alerts |

---

## 📊 Data Sources

| Source | Data Type | Coverage |
|--------|-----------|----------|
| **WAQI** | Real-time AQI | Global (India focus) |
| **OpenAQ** | Historical PM2.5/PM10 | 150+ countries |
| **ERA5** | Wind, Precipitation | Global meteorological |
| **Sentinel-5P** | NO2, SO2 columns | Satellite-based |

---

## 🎨 Dashboard Features

- **🌙 Day/Night Toggle** - Click moon icon (top-right) to switch themes
- **🔥 Heatmap Toggle** - Visualize pollution intensity
- **↗️ Wind Arrows** - Show pollution movement direction
- **📊 City Selector** - 15 major Indian cities with coordinates
- **💬 AI Chatbot** - Click chat bubble for natural language queries

---

## 🛠️ Tech Stack

**Backend:** FastAPI, Uvicorn, Python 3.11+  
**ML/AI:** Scikit-Learn, NumPy, Pandas  
**LLM:** Groq API (Llama 3.3 70B)  
**Frontend:** HTML5, CSS3, JavaScript, Leaflet, Chart.js  
**Data:** WAQI, OpenAQ, ERA5, Google Earth Engine

---

## 👤 Author

**Vinay Sai**  
*Advancing Environmental Intelligence for a Greener India* 🇮🇳

---

## 📄 License

MIT License - Feel free to use and modify for your projects.
