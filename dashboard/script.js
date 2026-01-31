// AirAware Dashboard Logic (Leaflet Version)
const API_BASE_URL = 'http://localhost:8000';

// State
let map;
let markersLayer; // LayerGroup for markers
let arrowsLayer;  // LayerGroup for movement vectors
let heatLayer;    // Heatmap layer
let currentGas = 'pm25';

// DOM Elements
const els = {
    gasSelector: document.getElementById('gasSelector'),
    refreshBtn: document.getElementById('refreshBtn'),
    toggleArrowsBtn: document.getElementById('toggleArrowsBtn'),
    toggleHeatmapBtn: document.getElementById('toggleHeatmapBtn'),
    sourceStats: document.getElementById('sourceStats'),
    predictBtn: document.getElementById('predictBtn'),
    alertsContainer: document.getElementById('alertsContainer'),
    locateMeBtn: document.getElementById('locateMeBtn'),

    // Stats
    avgValue: document.getElementById('avgValue'),
    maxValue: document.getElementById('maxValue'),
    stationCount: document.getElementById('stationCount'),

    // AI
    chatbotToggle: document.getElementById('chatbotToggle'),
    chatWindow: document.getElementById('chatWindow'),
    closeChat: document.getElementById('closeChat'),
    chatInput: document.getElementById('chatInput'),
    sendMessage: document.getElementById('sendMessage'),
    chatMessages: document.getElementById('chatMessages')
};

// ==========================================
// Initialization
// ==========================================
document.addEventListener('DOMContentLoaded', async () => {
    initMap();
    await loadSupportedGases();
    setupEventListeners();
    await loadWarnings(); // Load alerts on start
    await loadSourceStats(); // Load data contributions on start
});

// ==========================================
// Leaflet Map Setup
// ==========================================
function initMap() {
    map = L.map('map').setView([20.5937, 78.9629], 5);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    markersLayer = L.layerGroup().addTo(map);
    arrowsLayer = L.layerGroup(); // Not added by default
    heatLayer = L.heatLayer([], {
        radius: 40,
        blur: 25,
        max: 1.0,
        minOpacity: 0.4,
        maxZoom: 8,
        gradient: { 0.4: 'blue', 0.6: 'cyan', 0.7: 'lime', 0.8: 'yellow', 1.0: 'red' }
    });
}

// ==========================================
// Core Logic
// ==========================================

async function loadSupportedGases() {
    try {
        els.gasSelector.innerHTML = '<option>Loading...</option>';
        const response = await fetch(`${API_BASE_URL}/`);
        const data = await response.json();

        els.gasSelector.innerHTML = '';
        data.supported_gases.forEach(gas => {
            const option = document.createElement('option');
            option.value = gas;
            option.textContent = gas.toUpperCase();
            els.gasSelector.appendChild(option);
        });

        els.gasSelector.value = 'pm25';
        loadDashboardData('pm25');

    } catch (error) {
        console.error("API Error", error);
        els.gasSelector.innerHTML = '<option>API Unavailable</option>';
        showToast("Backend API not reachable. Is it running?", "error");
    }
}

async function loadDashboardData(gas) {
    currentGas = gas;

    try {
        const statsRes = await fetch(`${API_BASE_URL}/stats?gas=${gas}`);
        const stats = await statsRes.json();

        animateValue(els.avgValue, stats.mean || 0);
        animateValue(els.maxValue, stats.max || 0);
        els.stationCount.textContent = stats.measurements || 0;

        document.getElementById('avgUnit').textContent = stats.unit || '';
        document.getElementById('maxUnit').textContent = stats.unit || '';

    } catch (e) { console.error("Stats failed", e); }

    updateMapData(gas);
    loadHotspots(gas);
}

async function updateMapData(gas) {
    if (!map) return;

    try {
        const res = await fetch(`${API_BASE_URL}/data/recent?gas=${gas}&limit=500`);
        const points = await res.json();

        markersLayer.clearLayers();

        points.forEach(p => {
            // FILTER: Skip Unknown locations and unrealistic values (sensor errors)
            if (p.location === 'Unknown' || !p.location || p.value > 1000) {
                return; // Skip this point
            }

            const color = p.color || '#cccccc';
            L.circleMarker([p.latitude, p.longitude], {
                radius: 6,
                fillColor: color,
                color: '#fff',
                weight: 1,
                opacity: 1,
                fillOpacity: 0.8
            })
                .bindPopup(`
                <div style="color:black; font-family:'Inter',sans-serif;">
                    <strong>${p.location}</strong><br>
                    ${gas.toUpperCase()}: <b>${p.value.toFixed(1)}</b><br>
                    Status: <span style="color:${color}; font-weight:bold">${p.category}</span>
                </div>
            `)
                .addTo(markersLayer);
        });

        // Update Heatmap with robust normalization
        if (points.length > 0) {
            // Filter out bad data for heatmap too
            const validPoints = points.filter(p =>
                p.location !== 'Unknown' && p.location && p.value < 1000
            );

            // Use a sensible max for normalization to ensure visible gradients
            // PM2.5: 150+ is Very Unhealthy. 
            const maxValHeuristic = gas === 'pm25' ? 120 : (gas === 'co' ? 8 : 200);
            const dataMax = Math.max(...validPoints.map(p => p.value));
            const normMax = Math.max(dataMax, maxValHeuristic * 0.4);

            const heatPoints = validPoints.map(p => [
                p.latitude,
                p.longitude,
                Math.min((p.value / normMax) * 1.5, 1.0) // Boost weight slightly for visibility
            ]);
            heatLayer.setLatLngs(heatPoints);
        } else {
            heatLayer.setLatLngs([]);
        }

    } catch (e) { console.error("Map data failed", e); }
}

async function loadHotspots(gas) {
    const list = document.getElementById('hotspotsList');
    list.innerHTML = '<div style="color:var(--text-muted)">Scanning...</div>';

    try {
        const res = await fetch(`${API_BASE_URL}/hotspots?gas=${gas}&top_n=5`);
        const data = await res.json();

        // Filter out only Unknown from hotspots (keep high values!)
        const filteredData = data.filter(h => h.city_name !== 'Unknown');

        if (filteredData.length === 0) {
            list.innerHTML = '<div style="padding:10px">No major hotspots detected.</div>';
            return;
        }

        // Clear the list first
        list.innerHTML = '';

        filteredData.forEach(h => {
            const item = document.createElement('div');
            item.style.display = 'flex';
            item.style.justifyContent = 'space-between';
            item.style.padding = '12px';
            item.style.background = 'rgba(255,255,255,0.05)';
            item.style.borderRadius = '8px';
            item.style.marginBottom = '8px';
            item.innerHTML = `
                <div>
                    <div style="font-weight:600">${h.city_name}</div>
                    <div style="font-size:0.8rem; color:${h.color}">Cluster #${h.rank}</div>
                </div>
                <div style="text-align:right">
                    <div style="font-size:1.1rem; font-weight:700">${h.avg_value.toFixed(0)}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted)">Avg</div>
                </div>
            `;
            list.appendChild(item);
        });

    } catch (e) { list.innerText = "Error loading hotspots"; }
}

// ==========================================
// NEW FEATURES: Arrows & Warnings
// ==========================================

// 1. Arrows (Tracking)
// 1. Arrows (Tracking)
async function fetchAndDrawArrows(force = false) {
    // If not forced and already has layers, skip to avoid flicker
    if (!force && arrowsLayer.getLayers().length > 0) return;

    arrowsLayer.clearLayers();
    showToast("Updating pollution vectors...", "info");

    try {
        const res = await fetch(`${API_BASE_URL}/tracking`);
        const points = await res.json();

        console.log(`Loaded ${points.length} tracking points`);

        points.forEach(p => {
            const length = 0.8 * p.speed;
            const rad = (p.angle - 90) * (Math.PI / 180);
            const endLat = p.latitude + (length * Math.cos(rad) * 0.01);
            const endLon = p.longitude + (length * Math.sin(rad) * 0.01);

            L.polyline([[p.latitude, p.longitude], [endLat, endLon]], {
                color: 'rgba(50, 255, 255, 0.8)',
                weight: 3
            }).addTo(arrowsLayer);

            L.circle([endLat, endLon], {
                radius: 300,
                color: 'rgba(50, 255, 255, 0.8)',
                fill: true,
                fillColor: '#32ffff',
                fillOpacity: 0.8
            }).addTo(arrowsLayer);
        });

    } catch (e) {
        console.error("Error drawing arrows", e);
        showToast("Error loading movement data", "error");
    }
}

function updateArrowButtonState() {
    const isVisible = map.hasLayer(arrowsLayer);
    els.toggleArrowsBtn.textContent = isVisible ? "Hide Movement" : "Show Movement";
    els.toggleArrowsBtn.classList.toggle('btn-primary', isVisible);
    els.toggleArrowsBtn.classList.toggle('btn-secondary', !isVisible);
}

// Initial Load
setTimeout(async () => {
    // Add layer and fetch data initially
    if (!map.hasLayer(arrowsLayer)) {
        arrowsLayer.addTo(map);
    }
    await fetchAndDrawArrows();
    updateArrowButtonState();
}, 1000);

// Toggle Button Listener
els.toggleArrowsBtn.addEventListener('click', () => {
    if (map.hasLayer(arrowsLayer)) {
        map.removeLayer(arrowsLayer);
    } else {
        arrowsLayer.addTo(map);
        // Only fetch if we haven't already (e.g. if initial load failed or was skipped)
        fetchAndDrawArrows();
    }
    updateArrowButtonState();
});

// 2. Heatmap
function updateHeatmapButtonState() {
    const isVisible = map.hasLayer(heatLayer);
    els.toggleHeatmapBtn.textContent = isVisible ? "Hide Heat Map" : "Show Heat Map";
    els.toggleHeatmapBtn.classList.toggle('btn-primary', isVisible);
    els.toggleHeatmapBtn.classList.toggle('btn-secondary', !isVisible);
}

els.toggleHeatmapBtn.addEventListener('click', () => {
    if (map.hasLayer(heatLayer)) {
        map.removeLayer(heatLayer);
    } else {
        heatLayer.addTo(map);
    }
    updateHeatmapButtonState();
});

// 3. Source Statistics
async function loadSourceStats() {
    try {
        const res = await fetch(`${API_BASE_URL}/stats/sources`);
        const stats = await res.json();

        els.sourceStats.innerHTML = '';
        stats.forEach(s => {
            const item = document.createElement('div');
            item.className = 'source-item-container';
            item.innerHTML = `
                <div class="source-item">
                    <span class="source-name">${s.source}</span>
                    <span class="source-value">${s.percentage}%</span>
                </div>
                <div class="source-bar-container">
                    <div class="source-bar" style="width: ${s.percentage}%"></div>
                </div>
            `;
            els.sourceStats.appendChild(item);
        });
    } catch (e) { console.error("Source stats failed", e); }
}

// 4. Warnings
async function loadWarnings() {
    try {
        const res = await fetch(`${API_BASE_URL}/warnings`);
        const alerts = await res.json();

        els.alertsContainer.innerHTML = '';
        if (alerts.length === 0) return;

        alerts.forEach(alert => {
            const card = document.createElement('div');
            card.className = `alert-card ${alert.type}`;

            const icon = alert.type === 'influence' ? '🌪️' : '🌦️';

            card.innerHTML = `
                <div class="alert-icon">${icon}</div>
                <div class="alert-content">
                    <h3>${alert.title}</h3>
                    <p>${alert.message}</p>
                </div>
            `;
            els.alertsContainer.appendChild(card);
        });
    } catch (e) { console.error("Error loading alerts", e); }
}

// ==========================================
// Chatbot Logic
// ==========================================

els.chatbotToggle.addEventListener('click', () => {
    els.chatWindow.classList.toggle('active');
});

els.closeChat.addEventListener('click', () => {
    els.chatWindow.classList.remove('active');
});

// Theme Toggle (Day/Night Mode)
document.getElementById('toggleThemeBtn').addEventListener('click', () => {
    document.body.classList.toggle('light-theme');
    const btn = document.getElementById('toggleThemeBtn');
    if (document.body.classList.contains('light-theme')) {
        btn.innerHTML = '☀️';
    } else {
        btn.innerHTML = '🌙';
    }
});

els.sendMessage.addEventListener('click', sendChatMessage);
els.chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatMessage();
});

async function sendChatMessage() {
    const text = els.chatInput.value.trim();
    if (!text) return;

    // Use selected city coords if available
    const lat = selectedCity.lat || null;
    const lon = selectedCity.lon || null;

    addMessage(text, 'user');
    els.chatInput.value = '';

    const loadingId = addMessage("Thinking...", 'bot', true);

    try {
        const res = await fetch(`${API_BASE_URL}/chatbot`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                latitude: lat,
                longitude: lon
            })
        });
        const data = await res.json();

        document.getElementById(loadingId).remove();

        // Simple markdown parsing
        let formatted = data.response
            .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
            .replace(/\n/g, '<br>');

        addMessage(formatted, 'bot', false, true);

    } catch (e) {
        document.getElementById(loadingId).innerHTML = "Error communicating with AI. <br>Check backend logs.";
    }
}

function addMessage(text, type, isLoading = false, isHtml = false) {
    const div = document.createElement('div');
    div.className = `message ${type}`;

    if (isHtml) div.innerHTML = text;
    else div.innerText = text;

    if (isLoading) div.id = 'msg-loading-' + Date.now();

    els.chatMessages.appendChild(div);
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;

    return div.id;
}

// ==========================================
// ==========================================
// Prediction & Forecasting Logic
// ==========================================

const citySelector = document.getElementById('citySelector');
const selectedCoords = document.getElementById('selectedCoords');
const forecastBtn = document.getElementById('forecastBtn');
const forecastModal = document.getElementById('forecastModal');
const closeForecast = document.getElementById('closeForecast');
let forecastChartInstance = null;

// Store selected city data
let selectedCity = { name: '', lat: null, lon: null };

// Update coordinates display when city is selected
citySelector.addEventListener('change', (e) => {
    const option = e.target.selectedOptions[0];
    if (option.value) {
        selectedCity.name = option.value;
        selectedCity.lat = parseFloat(option.dataset.lat);
        selectedCity.lon = parseFloat(option.dataset.lon);
        selectedCoords.innerText = `📍 ${selectedCity.lat.toFixed(2)}°N, ${selectedCity.lon.toFixed(2)}°E`;
        selectedCoords.style.color = 'var(--accent-purple)';
    } else {
        selectedCity = { name: '', lat: null, lon: null };
        selectedCoords.innerText = 'Select a city to see coordinates';
        selectedCoords.style.color = 'var(--text-muted)';
    }
});

forecastBtn.addEventListener('click', async () => {
    if (!selectedCity.lat || !selectedCity.lon) {
        showToast("Please select a city first", "warning");
        return;
    }

    forecastModal.style.display = 'flex';
    document.getElementById('forecastStatus').innerText = 'Running Random Forest Model...';
    document.getElementById('forecastTitle').innerText = `AI Forecast for ${selectedCity.name}`;

    try {
        // Fetch Forecast using city name directly
        const res = await fetch(`${API_BASE_URL}/predict/forecast/${selectedCity.name}`);
        const data = await res.json();

        if (data.error) {
            document.getElementById('forecastStatus').innerText = `Error: ${data.error}`;
            return;
        }

        document.getElementById('forecastStatus').innerText = '';
        renderForecastChart(data);

    } catch (e) {
        document.getElementById('forecastStatus').innerText = 'Failed to fetch forecast.';
        console.error(e);
    }
});

closeForecast.addEventListener('click', () => {
    forecastModal.style.display = 'none';
});

function renderForecastChart(data) {
    const ctx = document.getElementById('forecastChart').getContext('2d');

    if (forecastChartInstance) {
        forecastChartInstance.destroy();
    }

    forecastChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: `Predicted ${data.gas.toUpperCase()} (Next 24h)`,
                data: data.predictions,
                borderColor: '#a78bfa',
                backgroundColor: 'rgba(167, 139, 250, 0.2)',
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { labels: { color: 'white' } }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    ticks: { color: '#ccc' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#ccc' }
                }
            }
        }
    });
}

// Logic for simple point prediction
els.predictBtn.addEventListener('click', async () => {
    if (!selectedCity.lat || !selectedCity.lon) {
        showToast("Please select a city first", "warning");
        return;
    }

    const resultBox = document.getElementById('predictionResult');
    resultBox.style.display = 'block';
    resultBox.innerHTML = 'Calculating...';

    try {
        const res = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                latitude: selectedCity.lat,
                longitude: selectedCity.lon,
                gas: currentGas
            })
        });
        const data = await res.json();

        resultBox.innerHTML = `
            <div style="font-weight:600; color: ${data.color}">
                Predicted ${data.gas.toUpperCase()}: ${data.predicted_value} ${data.unit}
            </div>
            <div style="font-size:0.9rem; margin-top:4px">${data.message}</div>
        `;

    } catch (e) {
        resultBox.innerText = "Prediction Failed";
    }
});

els.locateMeBtn.addEventListener('click', () => {
    if (!navigator.geolocation) {
        showToast("Geolocation not supported", "error");
        return;
    }

    els.locateMeBtn.innerText = "📍 Locating...";

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            // Find nearest city from our list
            const cities = Array.from(citySelector.options).slice(1); // Skip first "Choose city" option
            let nearest = null;
            let minDist = Infinity;

            cities.forEach(option => {
                const cityLat = parseFloat(option.dataset.lat);
                const cityLon = parseFloat(option.dataset.lon);
                const dist = Math.sqrt(
                    Math.pow(pos.coords.latitude - cityLat, 2) +
                    Math.pow(pos.coords.longitude - cityLon, 2)
                );
                if (dist < minDist) {
                    minDist = dist;
                    nearest = option;
                }
            });

            if (nearest) {
                citySelector.value = nearest.value;
                citySelector.dispatchEvent(new Event('change'));
                showToast(`Nearest city: ${nearest.value}`, "success");
            }

            els.locateMeBtn.innerText = "📍 Use My Location";

            // Re-center map optionally
            if (map) map.setView([pos.coords.latitude, pos.coords.longitude], 10);
        },
        (err) => {
            els.locateMeBtn.innerText = "📍 Use My Location";
            showToast("Location access denied", "warning");
        }
    );
});


// ==========================================
// Utilities
// ==========================================

function animateValue(obj, end) {
    let startTimestamp = null;
    const duration = 1000;
    const start = 0;

    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

function setupEventListeners() {
    els.gasSelector.addEventListener('change', (e) => {
        currentGas = e.target.value;
        loadDashboardData(currentGas);
    });

    els.refreshBtn.addEventListener('click', () => {
        loadDashboardData(currentGas);
        loadSourceStats();
        loadWarnings();
        showToast("Data Refreshed", "success");
    });
}

async function loadSourceStats() {
    try {
        const res = await fetch(`${API_BASE_URL}/stats/sources`);
        const data = await res.json();

        els.sourceStats.innerHTML = '';

        data.forEach(source => {
            const div = document.createElement('div');
            div.className = 'source-item';
            div.innerHTML = `
                <div class="source-info">
                    <span class="source-name">${source.source.toUpperCase()}</span>
                    <span class="source-count">${source.count} pts</span>
                </div>
                <div class="source-bar-container">
                    <div class="source-bar" style="width: ${source.percentage}%"></div>
                    <span class="source-percent">${source.percentage}%</span>
                </div>
            `;
            els.sourceStats.appendChild(div);
        });

    } catch (e) {
        console.error("Source stats failed", e);
        els.sourceStats.innerHTML = '<div style="color:var(--accent-error)">Failed to load source stats</div>';
    }
}

function showToast(msg, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerText = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}