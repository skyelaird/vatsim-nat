// NAT Entry Conflict Dashboard
// Client-side JavaScript for UI interactions and data display

// Configuration
const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes
let refreshTimer = null;

// Security: HTML escape function to prevent XSS
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return String(unsafe)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

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
    
    let severity;
    if (conflict.is_overtake) {
        severity = `🚨 CRITICAL OVERTAKE - Separation CLOSING ${conflict.separation_closing.toFixed(1)} min`;
    } else if (conflict.separation < 3) {
        severity = '🚨 CRITICAL';
    } else {
        severity = '⚠️ WARNING';
    }
    
    header.textContent = `${severity} - Separation: ${conflict.separation.toFixed(1)} min at ${conflict.waypoint}`;
    
    group.appendChild(header);
    
    // Pass conflict waypoints to highlight them
    const conflictWaypoints = [conflict.waypoint];
    const strip1 = createATCStrip(conflict.flight1, true, conflictWaypoints);
    const strip2 = createATCStrip(conflict.flight2, true, conflictWaypoints);
    
    group.appendChild(strip1);
    group.appendChild(strip2);
    
    return group;
}

function createATCStrip(flight, isConflict = false, conflictWaypoints = []) {
    const strip = document.createElement('div');
    strip.className = 'atc-strip' + (isConflict ? ' conflict' : '');
    const isEB = flight.is_eastbound;
    
    // LEFT COLUMN (tombstone for WB, SELCAL for EB)
    const leftCol = document.createElement('div');
    if (!isEB) {
        leftCol.className = 'strip-tombstone';
        leftCol.innerHTML = `
            <div class="strip-tombstone-callsign">${escapeHtml(flight.callsign)}</div>
            <div class="strip-tombstone-aircraft">${escapeHtml(flight.aircraft)}</div>
            <div class="strip-tombstone-mach">${escapeHtml(flight.mach_gs)}</div>
            <div class="strip-tombstone-fl">${escapeHtml(flight.fl_display)}</div>
        `;
    } else {
        leftCol.className = 'strip-selcal-column';
        leftCol.textContent = flight.selcal || '';
    }
    
    // CENTER COLUMN (9 data columns)
    const centerCol = document.createElement('div');
    centerCol.className = 'strip-data-area';
    
    // Row 1: Waypoints - Fill cells based on direction
    const wptRow = document.createElement('div');
    wptRow.className = 'strip-waypoints-row';
    
    // Create all 9 cells
    const wptCells = [];
    for (let i = 0; i < 9; i++) {
        wptCells.push(document.createElement('div'));
    }
    
    // Fill cells: EB left-to-right (0-8), WB right-aligned from cell 8
    for (let i = 0; i < flight.waypoints.length && i < 9; i++) {
        const wpt = flight.waypoints[i];
        // EB: fill from left (i), WB: fill from right (rightmost = cell 8)
        const cellIndex = isEB ? i : (9 - flight.waypoints.length + i);
        wptCells[cellIndex].textContent = wpt || '';
        
        // Highlight if this waypoint is in conflict
        if (wpt && conflictWaypoints.includes(wpt)) {
            wptCells[cellIndex].style.backgroundColor = '#8B0000';
            wptCells[cellIndex].style.color = '#fff';
            wptCells[cellIndex].style.fontWeight = 'bold';
            wptCells[cellIndex].style.padding = '2px 4px';
            wptCells[cellIndex].style.borderRadius = '3px';
        }
    }
    
    // Append all cells to row
    wptCells.forEach(cell => wptRow.appendChild(cell));
    centerCol.appendChild(wptRow);
    
    // Row 2: Times - Fill cells based on direction
    const timeRow = document.createElement('div');
    timeRow.className = 'strip-times-row';
    
    // Create all 9 cells
    const timeCells = [];
    for (let i = 0; i < 9; i++) {
        timeCells.push(document.createElement('div'));
    }
    
    // Fill cells: EB left-to-right (0-8), WB right-aligned from cell 8
    for (let i = 0; i < flight.times.length && i < 9; i++) {
        const time = flight.times[i];
        const wpt = flight.waypoints[i];
        // EB: fill from left (i), WB: fill from right (rightmost = cell 8)
        const cellIndex = isEB ? i : (9 - flight.waypoints.length + i);
        timeCells[cellIndex].textContent = time || '';
        
        // Highlight if this waypoint is in conflict
        if (wpt && conflictWaypoints.includes(wpt)) {
            timeCells[cellIndex].style.backgroundColor = '#8B0000';
            timeCells[cellIndex].style.color = '#fff';
            timeCells[cellIndex].style.padding = '2px 4px';
            timeCells[cellIndex].style.borderRadius = '3px';
        }
    }
    
    // Append all cells to row
    timeCells.forEach(cell => timeRow.appendChild(cell));
    centerCol.appendChild(timeRow);
    
    // Row 3: Route - ALWAYS left-justified regardless of direction
    const routeRow = document.createElement('div');
    routeRow.className = 'strip-route-row';
    routeRow.textContent = `${flight.departure} - ${flight.route_filed} - ${flight.destination}`;
    routeRow.style.textAlign = 'left';  // Force left-justify for all
    centerCol.appendChild(routeRow);
    
    // RIGHT COLUMN (SELCAL for WB, tombstone for EB)
    const rightCol = document.createElement('div');
    if (isEB) {
        rightCol.className = 'strip-tombstone right';
        rightCol.innerHTML = `
            <div class="strip-tombstone-callsign">${escapeHtml(flight.callsign)}</div>
            <div class="strip-tombstone-aircraft">${escapeHtml(flight.aircraft)}</div>
            <div class="strip-tombstone-mach">${escapeHtml(flight.mach_gs)}</div>
            <div class="strip-tombstone-fl">${escapeHtml(flight.fl_display)}</div>
        `;
    } else {
        rightCol.className = 'strip-selcal-column';
        rightCol.textContent = flight.selcal || '';
    }
    
    strip.appendChild(leftCol);
    strip.appendChild(centerCol);
    strip.appendChild(rightCol);
    return strip;
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
