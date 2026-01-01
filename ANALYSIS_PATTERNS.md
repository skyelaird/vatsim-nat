# NAT Traffic Analysis Patterns

Collection of analysis scripts and output formats for VATSIM NAT traffic data.

## Table Output Formats

### Format 1: Clean Frequency Table
**Use case:** Precise numbers, easy comparison across routes

```
CITY PAIR        | B77W | B789 | A359 | A35K | B77L | Others | TOTAL
-----------------+------+------+------+------+------+--------+-------
KJFK-EGLL        |   15 |   12 |    8 |    5 |    3 |      2 |    45
EGLL-KJFK        |   12 |   10 |    7 |    4 |    2 |      1 |    36
CYUL-LFPO        |    8 |    6 |    5 |    3 |    1 |      0 |    23
LFPG-CYUL        |    7 |    5 |    4 |    2 |    1 |      0 |    19
EDDF-KJFK        |    6 |    5 |    3 |    2 |    0 |      1 |    17
```

**Implementation:**
- Columns: Top N aircraft types (by total frequency across all routes)
- Rows: Routes sorted by total crossings (descending)
- "Others": Sum of all types not in top N columns
- Right-aligned numbers for readability

**Python snippet:**
```python
# Build table with top 6 aircraft types
top_aircraft = ['B77W', 'B789', 'A359', 'A35K', 'B77L', 'B788']
print(f"{'CITY PAIR':<17s} | {' | '.join(f'{ac:>4s}' for ac in top_aircraft)} | Others | TOTAL")
print("-" * 17 + "+" + "-" * (6 * len(top_aircraft) + 5) + "+" + "-" * 8 + "+" + "-" * 7)
for route, data in sorted_routes:
    counts = [data['aircraft'].get(ac, 0) for ac in top_aircraft]
    others = data['total'] - sum(counts)
    print(f"{route:<17s} | {' | '.join(f'{c:4d}' for c in counts)} | {others:6d} | {data['total']:5d}")
```

---

### Format 2: Visual Histogram
**Use case:** Quick visual comparison, presentation-friendly

```
NAT Traffic Distribution by Route

KJFK-EGLL (45)  B77W ████████████  B789 █████████  A359 ██████  Others ███
                33%               27%             18%           22%

EGLL-KJFK (36)  B77W ██████████  B789 ████████  A359 █████  Others ████
                33%             28%           19%         20%

CYUL-LFPO (23)  B77W ███████  B789 ██████  A359 █████  Others ███
                35%          26%          22%         17%
```

**Implementation:**
- Bar length proportional to percentage
- Top 3-4 aircraft types + "Others"
- Include percentages for precision

**Python snippet:**
```python
def make_bar(count, total, width=40):
    pct = count / total
    bar_len = int(pct * width)
    return '█' * bar_len

for route, data in sorted_routes[:10]:
    print(f"\n{route} ({data['total']})")
    top_ac = sorted(data['aircraft'].items(), key=lambda x: x[1], reverse=True)[:3]
    
    for actype, count in top_ac:
        pct = (count / data['total']) * 100
        bar = make_bar(count, data['total'])
        print(f"  {actype:6s} {bar} {pct:5.1f}%")
    
    others = data['total'] - sum(c for _, c in top_ac)
    if others > 0:
        bar = make_bar(others, data['total'])
        pct = (others / data['total']) * 100
        print(f"  Others {bar} {pct:5.1f}%")
```

---

### Format 3: Heatmap Grid
**Use case:** Pattern recognition, identifying aircraft-route combinations

```
Aircraft Type Distribution by Route (count)

                | A35K | A359 | A388 | B77L | B77W | B788 | B789 | B78X
----------------+------+------+------+------+------+------+------+------
KJFK-EGLL       |    5 |    8 |    1 |    3 |   15 |    1 |   12 |    0
EGLL-KJFK       |    4 |    7 |    0 |    2 |   12 |    2 |   10 |    1
CYUL-LFPO       |    3 |    5 |    0 |    1 |    8 |    0 |    6 |    0
LFPG-CYUL       |    2 |    4 |    0 |    1 |    7 |    1 |    5 |    0
EDDF-KJFK       |    2 |    3 |    0 |    0 |    6 |    1 |    5 |    0
KJFK-EDDF       |    2 |    3 |    0 |    1 |    5 |    0 |    4 |    1
EGLL-CYYZ       |    1 |    2 |    0 |    1 |    4 |    0 |    3 |    0

TOTALS          |   19 |   32 |    1 |    9 |   57 |    5 |   45 |    2
```

**With color intensity (for terminal output):**
```
Using background colors:
  0     = no color (empty cell)
  1-5   = light intensity
  6-10  = medium intensity  
  11+   = high intensity
```

**Implementation:**
```python
# Get all unique aircraft types
all_types = sorted(set(ac for route_data in city_pairs.values() 
                      for ac in route_data['aircraft'].keys()))

# Print header
header = " " * 16 + " | " + " | ".join(f"{ac:>4s}" for ac in all_types)
print(header)
print("-" * 16 + "+" + "-" * (6 * len(all_types) + len(all_types) - 1))

# Print rows
for route, data in sorted_routes[:20]:
    row = f"{route:<16s}"
    for actype in all_types:
        count = data['aircraft'].get(actype, 0)
        row += f" | {count:4d}"
    print(row)

# Print totals
totals = [sum(d['aircraft'].get(ac, 0) for d in city_pairs.values()) 
          for ac in all_types]
total_row = f"{'TOTALS':<16s}"
for t in totals:
    total_row += f" | {t:4d}"
print("-" * 16 + "+" + "-" * (6 * len(all_types) + len(all_types) - 1))
print(total_row)
```

---

## Analysis Query Patterns

### Top Routes by Volume
```sql
SELECT 
    departure || '-' || destination as route,
    COUNT(*) as crossings,
    COUNT(DISTINCT aircraft_type) as unique_types,
    AVG(crossing_duration) as avg_duration
FROM nat_crossings
WHERE exit_time IS NOT NULL
GROUP BY route
ORDER BY crossings DESC
LIMIT 20;
```

### Aircraft Type Diversity
```sql
SELECT 
    departure || '-' || destination as route,
    COUNT(DISTINCT aircraft_type) as aircraft_diversity,
    COUNT(*) as total_crossings,
    GROUP_CONCAT(DISTINCT SUBSTR(aircraft_type, 1, 4)) as types_used
FROM nat_crossings
GROUP BY route
HAVING total_crossings >= 5
ORDER BY aircraft_diversity DESC;
```

### Fleet Mix by Operator
```sql
SELECT 
    operator,
    SUBSTR(aircraft_type, 1, INSTR(aircraft_type, '/') - 1) as ac_type,
    COUNT(*) as flights
FROM nat_crossings
WHERE operator IS NOT NULL
GROUP BY operator, ac_type
ORDER BY operator, flights DESC;
```

### Time-Based Distribution
```sql
-- Busiest routes by hour (UTC)
SELECT 
    CAST(SUBSTR(entry_time, 12, 2) AS INTEGER) as hour_utc,
    departure || '-' || destination as route,
    COUNT(*) as crossings
FROM nat_crossings
WHERE entry_time IS NOT NULL
GROUP BY hour_utc, route
ORDER BY hour_utc, crossings DESC;
```

---

## Visualization Patterns

### Traffic Flow Sankey Diagram
**Data needed:**
- Departure airport → Aircraft type → Destination airport
- Width = frequency

**Query:**
```sql
SELECT 
    departure as source,
    SUBSTR(aircraft_type, 1, 4) as via,
    destination as target,
    COUNT(*) as value
FROM nat_crossings
GROUP BY source, via, target
HAVING value >= 2;
```

### Time Series Plot
**Aircraft type popularity over time:**
```sql
SELECT 
    DATE(entry_time) as date,
    SUBSTR(aircraft_type, 1, 4) as ac_type,
    COUNT(*) as crossings
FROM nat_crossings
WHERE entry_time IS NOT NULL
GROUP BY date, ac_type
ORDER BY date, crossings DESC;
```

### Geographic Heatmap
**Entry/Exit point usage:**
```sql
SELECT 
    ROUND(entry_lat, 0) || 'N ' || ROUND(ABS(entry_lon), 0) || 'W' as entry_point,
    ROUND(exit_lat, 0) || 'N ' || ROUND(ABS(exit_lon), 0) || 'W' as exit_point,
    COUNT(*) as crossings
FROM nat_crossings
WHERE entry_lat IS NOT NULL AND exit_lat IS NOT NULL
GROUP BY entry_point, exit_point
ORDER BY crossings DESC;
```

---

## Output Format Guidelines

**For terminal/console output:**
- Use ASCII box-drawing characters for clarity
- Right-align numbers, left-align text
- Include totals row/column where meaningful
- Max width ~120 characters for standard terminals

**For CSV export:**
- Simple comma-delimited
- No formatting characters
- Include header row
- One data point per cell

**For reports/documentation:**
- Use markdown tables
- Include metadata (date range, filters applied)
- Add summary statistics
- Link to source queries

---

## Common Filters

**Quality filters:**
```python
# Complete crossings only
WHERE exit_time IS NOT NULL

# Minimum duration (exclude glitches)
WHERE crossing_duration > 120  # 2+ hours

# Maximum duration (exclude disconnects)
WHERE crossing_duration < 600  # < 10 hours

# High quality data
WHERE mid_time IS NOT NULL  # Crossed midpoint
  AND crossing_duration BETWEEN 180 AND 480
```

**Temporal filters:**
```python
# Last 24 hours
WHERE entry_time >= datetime('now', '-1 day')

# Specific date range
WHERE DATE(entry_time) BETWEEN '2025-01-01' AND '2025-01-07'

# Eastbound OTS hours (0100-0800 UTC at 30W)
WHERE CAST(SUBSTR(mid_time, 12, 2) AS INTEGER) BETWEEN 1 AND 8

# Westbound OTS hours (1130-1900 UTC at 30W)
WHERE CAST(SUBSTR(mid_time, 12, 2) AS INTEGER) BETWEEN 11 AND 19
```

**Geographic filters:**
```python
# North Atlantic core (exclude Caribbean)
WHERE entry_lat > 40 OR exit_lat > 40

# True oceanic (wide crossing)
WHERE ABS(entry_lon - exit_lon) > 30

# Specific FIR
WHERE inferred_fir = 'CZQX'
```

---

## Analysis Script Template

```python
#!/usr/bin/env python3
"""
NAT Traffic Analysis: [Description]
Author: [Your name]
Date: [Date]
"""
import sqlite3
from datetime import datetime

# Database connection
conn = sqlite3.connect('nat_traffic.db', timeout=30.0)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Quality filters
QUALITY_FILTER = """
    WHERE exit_time IS NOT NULL
      AND crossing_duration BETWEEN 120 AND 600
      AND aircraft_type IS NOT NULL
"""

# Your analysis query
cursor.execute(f"""
    SELECT ... 
    FROM nat_crossings
    {QUALITY_FILTER}
    ...
""")

results = cursor.fetchall()

# Format output
print("=" * 80)
print(f"NAT Traffic Analysis: [Title]")
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print(f"Records analyzed: {len(results)}")
print("=" * 80)
print()

# [Your table/chart output here]

# Cleanup
conn.close()
```

---

**Document maintained in:** `D:\GitHub\vatsim-nat\ANALYSIS_PATTERNS.md`

**Last updated:** 2026-01-01
