/**
 * Frontend JavaScript for Air Pollution Monitoring Dashboard
 * 
 * Features:
 * - Real-time data from OpenAQ API v3
 * - Heatmap visualization with color-coded pollution intensity
 * - Interactive map with pollution data points
 * - Multiple pollutant tracking (PM2.5, NO2, SO2, CO)
 */

// Configuration
const API_BASE_URL = 'http://localhost:8000';
const MAPBOX_TOKEN = 'pk.eyJ1IjoidmluYXkzNDgxIiwiYSI6ImNtazlqeDNyYTA2bHUzZHNlazlmZWh0aWkifQ.tuf_24XQdW4Ryiml4FcgBg';

// Map and data
let map = null;
let markers = [];
let heatmapLayerId = 'pollution-heatmap';
let hotspotsLayer = null;
let hotspotsVisible = true;
let currentParameter = 'pm25';
let heatmapData = [];

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    checkAPIStatus();
    
    if (MAPBOX_TOKEN && MAPBOX_TOKEN !== 'YOUR_MAPBOX_TOKEN') {
        initMap();
    } else {
        document.getElementById('map').innerHTML = 
            '<div style="padding: 50px; text-align: center; color: #666;">⚠️ Please configure your Mapbox token</div>';
    }
    
    setupEventListeners();
    loadHotspots();
    loadRecentData();
});

/**
 * Check API status
 */
async function checkAPIStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (response.ok) {
            document.getElementById('apiStatus').textContent = 'Online';
            document.getElementById('apiStatus').className = 'online';
        } else {
            throw new Error('API returned error');
        }
    } catch (error) {
        document.getElementById('apiStatus').textContent = 'Offline';
        document.getElementById('apiStatus').className = 'offline';
        console.error('API health check failed:', error);
    }
}

/**
 * Initialize Mapbox map
 */
function initMap() {
    map = new mapboxgl.Map({
        container: 'map',
        style: 'mapbox://styles/mapbox/dark-v11',  // Dark style for better heatmap visibility
        center: [77.2090, 28.6139],  // Delhi
        zoom: 10,
        accessToken: MAPBOX_TOKEN
    });
    
    map.addControl(new mapboxgl.NavigationControl());
    
    map.on('load', function() {
        console.log('Map loaded successfully');
        // Heatmap will be added when data is loaded
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    document.getElementById('refreshBtn').addEventListener('click', function() {
        loadHotspots();
        loadRecentData();
    });
    
    document.getElementById('toggleHotspotsBtn').addEventListener('click', function() {
        toggleHotspots();
    });
    
    document.getElementById('predictBtn').addEventListener('click', function() {
        makePrediction();
    });
    
    // Pollutant selector (if exists)
    const paramSelector = document.getElementById('parameterSelector');
    if (paramSelector) {
        paramSelector.addEventListener('change', function(e) {
            currentParameter = e.target.value;
            loadRecentData();
        });
    }
}

/**
 * Load and display hotspots with color coding
 */
async function loadHotspots() {
    const hotspotsListEl = document.getElementById('hotspotsList');
    hotspotsListEl.innerHTML = '<p class="loading">Loading hotspots...</p>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/hotspots`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const hotspots = await response.json();
        document.getElementById('hotspotCount').textContent = hotspots.length;
        
        if (hotspots.length === 0) {
            hotspotsListEl.innerHTML = '<p class="loading">No hotspots found.</p>';
            return;
        }
        
        // Display hotspots with color coding
        hotspotsListEl.innerHTML = hotspots.map(hotspot => {
            const bgColor = hotspot.color || '#dc3545';
            return `
                <div class="hotspot-item" style="border-left-color: ${bgColor};">
                    <div class="hotspot-info">
                        <div class="hotspot-location">
                            Lat: ${hotspot.latitude.toFixed(4)}, Lon: ${hotspot.longitude.toFixed(4)}
                        </div>
                        <div class="hotspot-details">
                            ${hotspot.category || 'Unknown'} • Cluster: ${hotspot.cluster}
                        </div>
                    </div>
                    <div class="hotspot-pm25" style="color: ${bgColor};">
                        ${hotspot.avg_pm25.toFixed(1)} µg/m³
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading hotspots:', error);
        hotspotsListEl.innerHTML = '<p class="loading" style="color: #dc3545;">Error loading hotspots.</p>';
    }
}

/**
 * Load recent data and create heatmap
 */
async function loadRecentData() {
    try {
        const response = await fetch(`${API_BASE_URL}/data/recent?limit=200&parameter=${currentParameter}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data && data.length > 0) {
            // Calculate average PM2.5
            const values = data.map(d => d.value).filter(v => v !== null && v !== undefined);
            
            if (values.length > 0) {
                const avgPM25 = values.reduce((a, b) => a + b, 0) / values.length;
                const avgEl = document.getElementById('avgPM25');
                avgEl.textContent = avgPM25.toFixed(1);
                
                // Color code the average value
                const avgColor = data[0].color || '#667eea';
                avgEl.style.color = avgColor;
            }
            
            // Update station count
            const uniqueStations = new Set(data.map(d => d.location || `${d.latitude}-${d.longitude}`));
            document.getElementById('stationCount').textContent = uniqueStations.size;
            
            // Prepare heatmap data
            heatmapData = data.map(point => ({
                location: [point.longitude, point.latitude],
                value: point.value || 0,
                color: point.color || '#667eea'
            }));
            
            // Add heatmap to map
            if (map && map.loaded()) {
                addHeatmapToMap(heatmapData);
            } else if (map) {
                map.on('load', function() {
                    addHeatmapToMap(heatmapData);
                });
            }
        }
        
    } catch (error) {
        console.error('Error loading recent data:', error);
    }
}

/**
 * Add heatmap layer to Mapbox map
 */
function addHeatmapToMap(dataPoints) {
    if (!map || !map.loaded() || dataPoints.length === 0) {
        return;
    }
    
    // Remove existing heatmap layer if it exists
    if (map.getLayer(heatmapLayerId)) {
        map.removeLayer(heatmapLayerId);
    }
    if (map.getSource(heatmapLayerId)) {
        map.removeSource(heatmapLayerId);
    }
    
    // Prepare GeoJSON data for heatmap
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
                intensity: normalizeValue(point.value)  // Normalize value for heatmap intensity
            }
        }))
    };
    
    // Add source
    map.addSource(heatmapLayerId, {
        type: 'geojson',
        data: geojsonData
    });
    
    // Add heatmap layer
    map.addLayer({
        id: heatmapLayerId,
        type: 'heatmap',
        source: heatmapLayerId,
        maxzoom: 15,
        paint: {
            // Increase the heatmap weight based on value
            'heatmap-weight': [
                'interpolate',
                ['linear'],
                ['get', 'intensity'],
                0, 0,
                1, 1
            ],
            // Increase the heatmap color weight by zoom level
            'heatmap-intensity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 1,
                9, 3,
                15, 5
            ],
            // Color gradient for heatmap
            'heatmap-color': [
                'interpolate',
                ['linear'],
                ['get', 'intensity'],
                0, 'rgba(0, 228, 0, 0)',      // Green (Good) - transparent
                0.2, 'rgba(255, 255, 0, 0.5)', // Yellow (Moderate)
                0.4, 'rgba(255, 126, 0, 0.7)', // Orange (Unhealthy for Sensitive)
                0.6, 'rgba(255, 0, 0, 0.8)',   // Red (Unhealthy)
                0.8, 'rgba(143, 63, 151, 0.9)', // Purple (Very Unhealthy)
                1, 'rgba(126, 0, 35, 1)'       // Dark Red (Hazardous)
            ],
            // Adjust the heatmap radius by zoom level
            'heatmap-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 2,
                9, 20,
                15, 30
            ],
            // Transition from heatmap to circle layer by zoom level
            'heatmap-opacity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                7, 1,
                9, 0.8
            ]
        }
    });
    
    // Add circle layer for higher zoom levels
    const circleLayerId = heatmapLayerId + '-circles';
    if (!map.getLayer(circleLayerId)) {
        map.addLayer({
            id: circleLayerId,
            type: 'circle',
            source: heatmapLayerId,
            minzoom: 9,
            paint: {
                'circle-radius': [
                    'interpolate',
                    ['linear'],
                    ['get', 'value'],
                    0, 4,
                    100, 8,
                    200, 12,
                    300, 16
                ],
                'circle-color': [
                    'interpolate',
                    ['linear'],
                    ['get', 'value'],
                    0, '#00E400',      // Green
                    12, '#FFFF00',     // Yellow
                    35, '#FF7E00',     // Orange
                    55, '#FF0000',     // Red
                    150, '#8F3F97',    // Purple
                    250, '#7E0023'     // Dark Red
                ],
                'circle-stroke-width': 1,
                'circle-stroke-color': '#fff',
                'circle-opacity': 0.8
            }
        });
    }
    
    console.log(`Heatmap added with ${dataPoints.length} data points`);
}

/**
 * Normalize pollution value to 0-1 range for heatmap intensity
 */
function normalizeValue(value) {
    // Normalize PM2.5 values (0-300 µg/m³ range)
    // Adjust these ranges based on your data
    const maxValue = 300;
    return Math.min(value / maxValue, 1);
}

/**
 * Toggle hotspots visibility
 */
function toggleHotspots() {
    hotspotsVisible = !hotspotsVisible;
    if (map) {
        const layerId = heatmapLayerId;
        if (map.getLayer(layerId)) {
            const visibility = hotspotsVisible ? 'visible' : 'none';
            map.setLayoutProperty(layerId, 'visibility', visibility);
            const circleLayerId = layerId + '-circles';
            if (map.getLayer(circleLayerId)) {
                map.setLayoutProperty(circleLayerId, 'visibility', visibility);
            }
        }
    }
}

/**
 * Make PM2.5 prediction
 */
async function makePrediction() {
    const latitude = parseFloat(document.getElementById('latitude').value);
    const longitude = parseFloat(document.getElementById('longitude').value);
    const resultEl = document.getElementById('predictionResult');
    
    if (!latitude || !longitude) {
        resultEl.textContent = 'Please enter both latitude and longitude';
        resultEl.className = 'prediction-result error';
        return;
    }
    
    resultEl.textContent = 'Predicting...';
    resultEl.className = 'prediction-result';
    resultEl.style.display = 'block';
    
    try {
        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                latitude: latitude,
                longitude: longitude,
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        resultEl.textContent = `Predicted PM2.5: ${result.predicted_pm25.toFixed(2)} µg/m³`;
        resultEl.className = 'prediction-result success';
        
    } catch (error) {
        console.error('Error making prediction:', error);
        resultEl.textContent = 'Error making prediction. Check console for details.';
        resultEl.className = 'prediction-result error';
    }
}
