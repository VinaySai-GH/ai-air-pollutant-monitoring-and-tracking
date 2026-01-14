/**
 * Air Pollution Monitoring Dashboard - Frontend
 * Gas-specific visualization with honest data representation
 */

// Configuration
const API_BASE_URL = 'http://localhost:8000';
const MAPBOX_TOKEN = 'pk.eyJ1IjoidmluYXkzNDgxIiwiYSI6ImNtazlqeDNyYTA2bHUzZHNlazlmZWh0aWkifQ.tuf_24XQdW4Ryiml4FcgBg';

// Gas-specific scales for normalization
const GAS_SCALES = {
    'pm25': 250,
    'pm10': 350,
    'no2': 200,
    'so2': 100,
    'co': 10,
    'o3': 200
};

// State
let map = null;
let currentGas = 'pm25';
let heatmapData = [];
let coverageInfo = null;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    checkAPIStatus();
    loadAvailableGases();
    
    if (MAPBOX_TOKEN && MAPBOX_TOKEN !== 'YOUR_MAPBOX_TOKEN') {
        initMap();
    } else {
        document.getElementById('map').innerHTML = 
            '<div style="padding: 50px; text-align: center; color: #666;">⚠️ Please configure Mapbox token in script.js</div>';
    }
    
    setupEventListeners();
    loadAllData();
});

/**
 * Check API health
 */
async function checkAPIStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            document.getElementById('apiStatus').textContent = 'Online';
            document.getElementById('apiStatus').className = 'online';
        } else {
            throw new Error('API error');
        }
    } catch (error) {
        document.getElementById('apiStatus').textContent = 'Offline';
        document.getElementById('apiStatus').className = 'offline';
        console.error('API health check failed:', error);
    }
}

/**
 * Load available gases from API
 */
async function loadAvailableGases() {
    try {
        const response = await fetch(`${API_BASE_URL}/gases`);
        const gases = await response.json();
        
        const selector = document.getElementById('gasSelector');
        selector.innerHTML = '';
        
        gases.forEach(gas => {
            const option = document.createElement('option');
            option.value = gas.parameter;
            option.textContent = `${gas.name} (${gas.unit})${gas.available ? '' : ' - No data'}`;
            option.disabled = !gas.available;
            selector.appendChild(option);
        });
        
        console.log('Available gases loaded:', gases);
    } catch (error) {
        console.error('Error loading gases:', error);
    }
}

/**
 * Initialize Mapbox map centered on India
 */
function initMap() {
    map = new mapboxgl.Map({
        container: 'map',
        style: 'mapbox://styles/mapbox/dark-v11',
        center: [78.9629, 20.5937],  // Center of India
        zoom: 4.5,  // Show all of India
        accessToken: MAPBOX_TOKEN
    });
    
    map.addControl(new mapboxgl.NavigationControl());
    
    map.on('load', function() {
        console.log('Map loaded - centered on India');
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Gas selector
    document.getElementById('gasSelector').addEventListener('change', function(e) {
        currentGas = e.target.value;
        console.log(`Gas changed to: ${currentGas}`);
        loadAllData();
    });
    
    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', function() {
        loadAllData();
    });
    
    // Toggle heatmap
    document.getElementById('toggleHeatmapBtn').addEventListener('click', function() {
        toggleHeatmap();
    });
    
    // Prediction
    document.getElementById('predictBtn').addEventListener('click', function() {
        makePrediction();
    });
}

/**
 * Load all data for current gas
 */
async function loadAllData() {
    await loadCoverage();
    await loadStatistics();
    await loadHeatmapData();
    await loadHotspots();
}

/**
 * Load data coverage information
 */
async function loadCoverage() {
    try {
        const response = await fetch(`${API_BASE_URL}/coverage?gas=${currentGas}`);
        coverageInfo = await response.json();
        
        const coverageEl = document.getElementById('coverageStatus');
        const qualityEl = document.getElementById('dataQuality');
        
        if (coverageInfo.coverage_quality === 'insufficient') {
            coverageEl.textContent = `⚠️ Insufficient data for ${currentGas.toUpperCase()}`;
            coverageEl.className = 'coverage-warning';
            qualityEl.textContent = 'No analysis possible';
        } else if (coverageInfo.coverage_quality === 'sparse') {
            coverageEl.textContent = `⚠️ Limited coverage: ${coverageInfo.total_points} points`;
            coverageEl.className = 'coverage-warning';
            qualityEl.textContent = 'Use with caution';
        } else {
            coverageEl.textContent = `✓ ${coverageInfo.total_points} data points`;
            coverageEl.className = 'coverage-good';
            qualityEl.textContent = coverageInfo.coverage_quality;
        }
        
        console.log('Coverage:', coverageInfo);
    } catch (error) {
        console.error('Error loading coverage:', error);
    }
}

/**
 * Load statistics
 */
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats?gas=${currentGas}`);
        const stats = await response.json();
        
        if (!stats.available) {
            document.getElementById('avgValue').textContent = 'N/A';
            document.getElementById('maxValue').textContent = 'N/A';
            document.getElementById('stationCount').textContent = '0';
            return;
        }
        
        // Update stat cards
        document.getElementById('avgValue').textContent = stats.mean;
        document.getElementById('avgValue').style.color = getColorForValue(currentGas, stats.mean);
        
        document.getElementById('maxValue').textContent = stats.max;
        document.getElementById('maxValue').style.color = getColorForValue(currentGas, stats.max);
        
        document.getElementById('stationCount').textContent = stats.count;
        
        // Update labels
        document.querySelectorAll('.gas-label').forEach(el => {
            el.textContent = stats.name;
        });
        document.querySelectorAll('.gas-unit').forEach(el => {
            el.textContent = stats.unit;
        });
        
        console.log('Statistics:', stats);
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

/**
 * Load heatmap data
 */
async function loadHeatmapData() {
    try {
        const response = await fetch(`${API_BASE_URL}/data/recent?gas=${currentGas}&limit=500`);
        const data = await response.json();
        
        if (!data || data.length === 0) {
            console.warn(`No data for ${currentGas}`);
            clearHeatmap();
            return;
        }
        
        heatmapData = data.map(point => ({
            location: [point.longitude, point.latitude],
            value: point.value,
            color: point.color
        }));
        
        if (map && map.loaded()) {
            addHeatmapToMap(heatmapData);
        } else if (map) {
            map.on('load', function() {
                addHeatmapToMap(heatmapData);
            });
        }
        
        console.log(`Heatmap data loaded: ${heatmapData.length} points`);
    } catch (error) {
        console.error('Error loading heatmap data:', error);
    }
}

/**
 * Load hotspots
 */
async function loadHotspots() {
    const hotspotsEl = document.getElementById('hotspotsList');
    hotspotsEl.innerHTML = '<p class="loading">Loading hotspots...</p>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/hotspots?gas=${currentGas}`);
        const hotspots = await response.json();
        
        document.getElementById('hotspotCount').textContent = hotspots.length;
        
        if (hotspots.length === 0) {
            hotspotsEl.innerHTML = '<p class="loading">No hotspots detected for this gas.</p>';
            return;
        }
        
        hotspotsEl.innerHTML = hotspots.map((hotspot, idx) => {
            return `
                <div class="hotspot-item" style="border-left-color: ${hotspot.color};">
                    <div class="hotspot-info">
                        <div class="hotspot-location">
                            #${idx + 1} · ${hotspot.latitude.toFixed(3)}°N, ${hotspot.longitude.toFixed(3)}°E
                        </div>
                        <div class="hotspot-details">
                            ${hotspot.category.replace('_', ' ')} · ${hotspot.data_points} measurements
                        </div>
                    </div>
                    <div class="hotspot-value" style="color: ${hotspot.color};">
                        ${hotspot.avg_value}
                    </div>
                </div>
            `;
        }).join('');
        
        console.log(`Hotspots loaded: ${hotspots.length}`);
    } catch (error) {
        console.error('Error loading hotspots:', error);
        hotspotsEl.innerHTML = '<p class="loading" style="color: #dc3545;">Error loading hotspots</p>';
    }
}

/**
 * Add heatmap to Mapbox
 */
function addHeatmapToMap(dataPoints) {
    if (!map || !map.loaded() || dataPoints.length === 0) {
        return;
    }
    
    const layerId = 'pollution-heatmap';
    const circleLayerId = 'pollution-circles';
    
    // Remove existing layers
    if (map.getLayer(circleLayerId)) map.removeLayer(circleLayerId);
    if (map.getLayer(layerId)) map.removeLayer(layerId);
    if (map.getSource(layerId)) map.removeSource(layerId);
    
    // Prepare GeoJSON
    const geojsonData = {
        type: 'FeatureCollection',
        features: dataPoints.map(point => ({
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: point.location
            },
            properties: {
                value: point.value,
                intensity: normalizeValue(point.value, currentGas)
            }
        }))
    };
    
    // Add source
    map.addSource(layerId, {
        type: 'geojson',
        data: geojsonData
    });
    
    // Add heatmap layer
    map.addLayer({
        id: layerId,
        type: 'heatmap',
        source: layerId,
        maxzoom: 12,
        paint: {
            'heatmap-weight': [
                'interpolate',
                ['linear'],
                ['get', 'intensity'],
                0, 0,
                1, 1
            ],
            'heatmap-intensity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 1,
                9, 3
            ],
            'heatmap-color': [
                'interpolate',
                ['linear'],
                ['heatmap-density'],
                0, 'rgba(0, 0, 255, 0)',
                0.2, 'rgba(0, 228, 0, 0.5)',
                0.4, 'rgba(255, 255, 0, 0.7)',
                0.6, 'rgba(255, 126, 0, 0.8)',
                0.8, 'rgba(255, 0, 0, 0.9)',
                1, 'rgba(126, 0, 35, 1)'
            ],
            'heatmap-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 2,
                9, 20
            ],
            'heatmap-opacity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                7, 1,
                9, 0.5
            ]
        }
    });
    
    // Add circle layer for high zoom
    map.addLayer({
        id: circleLayerId,
        type: 'circle',
        source: layerId,
        minzoom: 8,
        paint: {
            'circle-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                8, 4,
                12, 12
            ],
            'circle-color': [
                'interpolate',
                ['linear'],
                ['get', 'value'],
                0, '#00E400',
                GAS_SCALES[currentGas] * 0.2, '#FFFF00',
                GAS_SCALES[currentGas] * 0.5, '#FF7E00',
                GAS_SCALES[currentGas] * 0.8, '#FF0000',
                GAS_SCALES[currentGas], '#7E0023'
            ],
            'circle-stroke-width': 1,
            'circle-stroke-color': '#fff',
            'circle-opacity': 0.8
        }
    });
    
    console.log(`Heatmap rendered: ${dataPoints.length} points for ${currentGas}`);
}

/**
 * Clear heatmap
 */
function clearHeatmap() {
    if (!map || !map.loaded()) return;
    
    const layerId = 'pollution-heatmap';
    const circleLayerId = 'pollution-circles';
    
    if (map.getLayer(circleLayerId)) map.removeLayer(circleLayerId);
    if (map.getLayer(layerId)) map.removeLayer(layerId);
    if (map.getSource(layerId)) map.removeSource(layerId);
}

/**
 * Toggle heatmap visibility
 */
function toggleHeatmap() {
    if (!map || !map.loaded()) return;
    
    const layerId = 'pollution-heatmap';
    const circleLayerId = 'pollution-circles';
    
    if (map.getLayer(layerId)) {
        const visibility = map.getLayoutProperty(layerId, 'visibility');
        const newVisibility = visibility === 'visible' ? 'none' : 'visible';
        
        map.setLayoutProperty(layerId, 'visibility', newVisibility);
        if (map.getLayer(circleLayerId)) {
            map.setLayoutProperty(circleLayerId, 'visibility', newVisibility);
        }
    }
}

/**
 * Normalize value for heatmap (gas-specific)
 */
function normalizeValue(value, gas) {
    const maxScale = GAS_SCALES[gas] || 250;
    return Math.min(value / maxScale, 1);
}

/**
 * Get color for value (gas-specific)
 */
function getColorForValue(gas, value) {
    const config = GAS_SCALES[gas] || 250;
    
    if (value <= config * 0.2) return '#00E400';
    if (value <= config * 0.4) return '#FFFF00';
    if (value <= config * 0.6) return '#FF7E00';
    if (value <= config * 0.8) return '#FF0000';
    return '#7E0023';
}

/**
 * Make prediction
 */
async function makePrediction() {
    const lat = parseFloat(document.getElementById('latitude').value);
    const lon = parseFloat(document.getElementById('longitude').value);
    const resultEl = document.getElementById('predictionResult');
    
    if (!lat || !lon) {
        resultEl.textContent = 'Please enter valid coordinates';
        resultEl.className = 'prediction-result error';
        resultEl.style.display = 'block';
        return;
    }
    
    resultEl.textContent = 'Predicting...';
    resultEl.className = 'prediction-result';
    resultEl.style.display = 'block';
    
    try {
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                latitude: lat,
                longitude: lon,
                gas: currentGas
            })
        });
        
        const result = await response.json();
        
        resultEl.innerHTML = `
            <strong>Predicted ${result.gas.toUpperCase()}:</strong> 
            ${result.predicted_value} ${result.unit}<br>
            <small>${result.message}</small>
        `;
        resultEl.className = 'prediction-result success';
        
    } catch (error) {
        console.error('Prediction error:', error);
        resultEl.textContent = 'Error making prediction';
        resultEl.className = 'prediction-result error';
    }
}