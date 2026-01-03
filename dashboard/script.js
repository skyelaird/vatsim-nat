// NAT Entry Conflict Dashboard
// Client-side JavaScript for UI interactions and data display

// Configuration
const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes
let refreshTimer = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeUI();
    loadConflictData();
    startAutoRefresh();
});

function initializeUI() {
    // Help modal
    const helpBtn = document.getElementById('help-btn');
    const helpModal = document.getElementById('help-modal');
    const closeBtns = document.getElementsByClassName('modal-close');
    
    helpBtn.onclick = () => helpModal.style.display = 'block';
    
    for (let btn of closeBtns) {
        btn.onclick = function() {
            this.closest('.modal').style.display = 'none';
        };
    }
    
    window.onclick = function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
        }
    };
    
    // Refresh button
    document.getElementById('refresh-btn').onclick = () => {
        loadConflictData();
        resetAutoRefresh();
    };
}

function loadConflictData() {
    // Fetch conflict data from backend
    fetch('/api/entry-conflicts')
        .then(response => response.json())
        .then(data => {
            updateTimestamp(data.timestamp);
            renderEntryPoints(data.eastbound, 'eastbound-entries');
            renderEntryPoints(data.westbound, 'westbound-entries');
        })
        .catch(error => {
            console.error('Error loading conflict data:', error);
            document.getElementById('timestamp').textContent = 'Error loading data';
        });
}

function updateTimestamp(timestamp) {
    const date = new Date(timestamp);
    const formatted = date.toISOString().substr(11, 5) + 'Z';
    document.getElementById('timestamp').textContent = `Updated ${formatted}`;
}

function renderEntryPoints(entryPoints, containerId) {
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    if (!entryPoints || entryPoints.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #aaa;">No traffic detected</p>';
        return;
    }
    
    entryPoints.forEach(entry => {
        const card = createEntryCard(entry);
        container.appendChild(card);
    });
}

function createEntryCard(entry) {
    const card = document.createElement('div');
    card.className = `entry-card status-${entry.status}`;
    card.onclick = () => showStripModal(entry);
    
    const name = document.createElement('div');
    name.className = 'entry-name';
    name.textContent = entry.name;
    
    const count = document.createElement('div');
    count.className = 'entry-count';
    count.textContent = `${entry.flight_count} flight${entry.flight_count !== 1 ? 's' : ''}`;
    
    const status = document.createElement('div');
    status.className = `entry-status ${entry.status}`;
    
    if (entry.status === 'clear') {
        status.textContent = '✓ Clear';
    } else if (entry.status === 'warning') {
        status.textContent = `⚠️ ${entry.conflict_count} warning${entry.conflict_count !== 1 ? 's' : ''}`;
    } else if (entry.status === 'critical') {
        status.textContent = `🚨 ${entry.conflict_count} critical`;
    }
    
    card.appendChild(name);
    card.appendChild(count);
    card.appendChild(status);
    
    return card;
}

function showStripModal(entry) {
    // Fetch detailed strip data for this entry point
    fetch(`/api/entry-strips/${entry.name}`)
        .then(response => response.json())
        .then(data => {
            const modal = document.getElementById('strip-modal');
            const title = document.getElementById('modal-title');
            const container = document.getElementById('strip-container');
            
            title.textContent = `${entry.name} - ${entry.flight_count} Flights`;
            container.innerHTML = '';
            
            if (data.conflicts && data.conflicts.length > 0) {
                data.conflicts.forEach(conflict => {
                    const group = createConflictGroup(conflict);
                    container.appendChild(group);
                });
            }
            
            if (data.all_flights && data.all_flights.length > 0) {
                const allHeader = document.createElement('h3');
                allHeader.textContent = 'All Approaching Flights';
                allHeader.style.color = '#5dade2';
                allHeader.style.marginTop = '20px';
                allHeader.style.marginBottom = '15px';
                container.appendChild(allHeader);
                
                data.all_flights.forEach(flight => {
                    const strip = createATCStrip(flight);
                    container.appendChild(strip);
                });
            }
            
            modal.style.display = 'block';
        })
        .catch(error => {
            console.error('Error loading strip data:', error);
        });
}

function createConflictGroup(conflict) {
    const group = document.createElement('div');
    group.className = 'conflict-group';
    
    const header = document.createElement('div');
    header.className = 'conflict-header';
    
    const severity = conflict.is_overtake ? '🚨 CRITICAL - OVERTAKE' : 
                     conflict.separation < 3 ? '🚨 CRITICAL' : '⚠️ WARNING';
    
    header.textContent = `${severity} - Separation: ${conflict.separation} min at ${conflict.waypoint}`;
    
    group.appendChild(header);
    
    const strip1 = createATCStrip(conflict.flight1, true);
    const strip2 = createATCStrip(conflict.flight2, true);
    
    group.appendChild(strip1);
    group.appendChild(strip2);
    
    return group;
}

function createATCStrip(flight, isConflict = false) {
    const strip = document.createElement('div');
    strip.className = 'atc-strip' + (isConflict ? ' conflict' : '');
    
    // Line 1: Callsign and Aircraft
    const line1 = document.createElement('div');
    line1.className = 'strip-line';
    line1.innerHTML = `<span><strong>${flight.callsign}</strong></span><span>${flight.aircraft}</span>`;
    
    // Line 2: Route waypoints
    const line2 = document.createElement('div');
    line2.className = 'strip-line';
    line2.textContent = flight.route.split(/\s+/).slice(0, 8).map(w => w.split('/')[0]).join(' ');
    
    // Line 3: FL and ETA
    const line3 = document.createElement('div');
    line3.className = 'strip-line';
    line3.innerHTML = `<span>FL${flight.fl}</span><span>ETA ${flight.entry_eta}Z</span>`;
    
    strip.appendChild(line1);
    strip.appendChild(line2);
    strip.appendChild(line3);
    
    return strip;
}

function formatStripText(flight) {
    // Simple strip formatting (backend will provide better version)
    return `${flight.callsign.padEnd(10)} ${flight.aircraft.padEnd(8)} FL${flight.fl} ETA ${flight.entry_eta}`;
}

function startAutoRefresh() {
    refreshTimer = setInterval(loadConflictData, REFRESH_INTERVAL);
}

function resetAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    startAutoRefresh();
}
