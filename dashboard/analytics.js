// NAT Analytics JavaScript

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

document.addEventListener('DOMContentLoaded', function() {
    initializeMenu();
    loadAllAnalytics();

    // Auto-refresh every 5 minutes
    setInterval(loadAllAnalytics, 5 * 60 * 1000);
});

function initializeMenu() {
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', function() {
            // Update active menu item
            menuItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding section
            const section = this.dataset.section;
            document.querySelectorAll('.analytics-section').forEach(s => s.classList.remove('active'));
            document.getElementById(`${section}-section`).classList.add('active');
        });
    });
}

function loadAllAnalytics() {
    loadQA();
    loadTrafficFlow();
    loadFlightLevels();
    loadEntryPoints();
}

function loadQA() {
    fetch('/api/qa')
        .then(response => response.json())
        .then(data => {
            updateTimestamp(data.timestamp);
            
            // Stats grid
            const statsHtml = `
                <div class="stat-card">
                    <div class="stat-value">${data.summary.total_flights}</div>
                    <div class="stat-label">Total Flights</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.summary.trajectory_success_rate}%</div>
                    <div class="stat-label">Trajectory Success</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: ${data.summary.total_issues > 0 ? '#ff6b6b' : '#4caf50'}">${data.summary.total_issues}</div>
                    <div class="stat-label">Total Issues</div>
                </div>
            `;
            document.getElementById('qa-stats').innerHTML = statsHtml;
            
            // Issues
            let issuesHtml = '';
            
            if (data.issues.trajectory_failures.length > 0) {
                issuesHtml += '<div class="issue-list"><div class="chart-title">Trajectory Build Failures</div>';
                data.issues.trajectory_failures.forEach(issue => {
                    issuesHtml += `<div class="issue-item"><strong>${escapeHtml(issue.callsign)}</strong>: ${escapeHtml(issue.route)} - ${escapeHtml(issue.reason || '')}</div>`;
                });
                issuesHtml += '</div>';
            }
            
            if (data.issues.invalid_speeds.length > 0) {
                issuesHtml += '<div class="issue-list"><div class="chart-title">Invalid Speeds</div>';
                data.issues.invalid_speeds.forEach(issue => {
                    issuesHtml += `<div class="issue-item warning"><strong>${escapeHtml(issue.callsign)}</strong>: ${issue.gs} kts</div>`;
                });
                issuesHtml += '</div>';
            }

            if (data.issues.stuck_flights.length > 0) {
                issuesHtml += '<div class="issue-list"><div class="chart-title">Stuck Flights (>12h in DB)</div>';
                data.issues.stuck_flights.forEach(issue => {
                    issuesHtml += `<div class="issue-item warning"><strong>${escapeHtml(issue.callsign)}</strong>: ${issue.hours_in_db} hours</div>`;
                });
                issuesHtml += '</div>';
            }

            if (data.issues.coordinate_anomalies.length > 0) {
                issuesHtml += '<div class="issue-list"><div class="chart-title">Coordinate Anomalies</div>';
                data.issues.coordinate_anomalies.forEach(issue => {
                    issuesHtml += `<div class="issue-item info"><strong>${escapeHtml(issue.callsign)}</strong>: ${escapeHtml(issue.reason)}</div>`;
                });
                issuesHtml += '</div>';
            }

            if (data.issues.missing_fields.length > 0) {
                issuesHtml += '<div class="issue-list"><div class="chart-title">Missing Fields</div>';
                data.issues.missing_fields.forEach(issue => {
                    issuesHtml += `<div class="issue-item"><strong>${escapeHtml(issue.callsign)}</strong>: Missing ${escapeHtml(issue.field)}</div>`;
                });
                issuesHtml += '</div>';
            }

            if (data.issues.prediction_errors.length > 0) {
                issuesHtml += '<div class="issue-list"><div class="chart-title">Position Prediction Errors</div>';
                data.issues.prediction_errors.forEach(issue => {
                    const reason = issue.reason || `${issue.error_nm}nm error over ${issue.time_span} min (predicted ${issue.predicted_speed} kts, actual ${issue.actual_speed} kts)`;
                    issuesHtml += `<div class="issue-item warning"><strong>${escapeHtml(issue.callsign)}</strong>: ${escapeHtml(reason)}</div>`;
                });
                issuesHtml += '</div>';
            }
            
            if (issuesHtml === '') {
                issuesHtml = '<div class="issue-list"><div class="chart-title">✅ No Issues Found</div></div>';
            }
            
            document.getElementById('qa-issues').innerHTML = issuesHtml;
        })
        .catch(error => console.error('QA Error:', error));
}

function loadTrafficFlow() {
    fetch('/api/analytics/traffic-flow')
        .then(response => response.json())
        .then(data => {
            // Stats
            const statsHtml = `
                <div class="stat-card">
                    <div class="stat-value">${data.current.total}</div>
                    <div class="stat-label">Active Crossings</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.current.eastbound}</div>
                    <div class="stat-label">Eastbound</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.current.westbound}</div>
                    <div class="stat-label">Westbound</div>
                </div>
            `;
            document.getElementById('traffic-stats').innerHTML = statsHtml;
            
            // Hourly chart
            const maxCount = Math.max(...data.hourly.map(h => h.count), 1);
            let chartHtml = '';
            data.hourly.forEach(item => {
                const width = (item.count / maxCount) * 100;
                chartHtml += `
                    <div class="bar-row">
                        <div class="bar-label">${String(item.hour).padStart(2, '0')}:00Z</div>
                        <div class="bar-fill" style="width: ${width}%">${item.count}</div>
                    </div>
                `;
            });
            document.getElementById('hourly-chart').innerHTML = chartHtml || '<p style="color: #aaa;">No data available</p>';
        })
        .catch(error => console.error('Traffic Flow Error:', error));
}

function loadFlightLevels() {
    fetch('/api/analytics/flight-levels')
        .then(response => response.json())
        .then(data => {
            // Stats
            const statsHtml = `
                <div class="stat-card">
                    <div class="stat-value">${data.total_flights}</div>
                    <div class="stat-label">Total Flights</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: ${data.wrong_way_count > 0 ? '#ffa726' : '#4caf50'}">${data.wrong_way_count}</div>
                    <div class="stat-label">Wrong Odd/Even</div>
                </div>
            `;
            document.getElementById('levels-stats').innerHTML = statsHtml;
            
            // FL chart
            const maxCount = Math.max(...data.distribution.map(d => d.count), 1);
            let chartHtml = '';
            data.distribution.forEach(item => {
                const width = (item.count / maxCount) * 100;
                chartHtml += `
                    <div class="bar-row">
                        <div class="bar-label">FL${item.fl}</div>
                        <div class="bar-fill" style="width: ${width}%">${item.count} flight${item.count !== 1 ? 's' : ''}</div>
                    </div>
                `;
            });
            document.getElementById('fl-chart').innerHTML = chartHtml || '<p style="color: #aaa;">No data available</p>';
        })
        .catch(error => console.error('Flight Levels Error:', error));
}

function loadEntryPoints() {
    fetch('/api/analytics/entry-points')
        .then(response => response.json())
        .then(data => {
            // West entries
            const maxWest = Math.max(...data.west_entries.map(e => e.count), 1);
            let westHtml = '';
            data.west_entries.forEach(entry => {
                const width = (entry.count / maxWest) * 100;
                westHtml += `
                    <div class="bar-row">
                        <div class="bar-label">${entry.name}</div>
                        <div class="bar-fill" style="width: ${width}%">${entry.count} flight${entry.count !== 1 ? 's' : ''}</div>
                    </div>
                `;
            });
            document.getElementById('west-entries-chart').innerHTML = westHtml || '<p style="color: #aaa;">No traffic detected</p>';
            
            // East entries
            const maxEast = Math.max(...data.east_entries.map(e => e.count), 1);
            let eastHtml = '';
            data.east_entries.forEach(entry => {
                const width = (entry.count / maxEast) * 100;
                eastHtml += `
                    <div class="bar-row">
                        <div class="bar-label">${entry.name}</div>
                        <div class="bar-fill" style="width: ${width}%">${entry.count} flight${entry.count !== 1 ? 's' : ''}</div>
                    </div>
                `;
            });
            document.getElementById('east-entries-chart').innerHTML = eastHtml || '<p style="color: #aaa;">No traffic detected</p>';
        })
        .catch(error => console.error('Entry Points Error:', error));
}

function updateTimestamp(timestamp) {
    const date = new Date(timestamp);
    const formatted = date.toISOString().substr(11, 5) + 'Z';
    document.getElementById('timestamp').textContent = `Last updated: ${formatted}`;
}
