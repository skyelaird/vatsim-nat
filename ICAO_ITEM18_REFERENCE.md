# ICAO Doc 4444 - Flight Plan Item 18 Reference
## For NAT Traffic Analysis

Source: ICAO Doc 4444 (Air Traffic Management), 16th Edition 2016

---

## Item 18 Structure

Item 18 contains **Other Information** in structured format using indicators followed by data.

**Format:** `INDICATOR/data INDICATOR/data ...`

---

## Key Indicators for NAT Traffic Analysis

### PBN/ - Performance Based Navigation

Indicates RNAV and/or RNP capabilities. Maximum 8 entries (16 characters).

**RNAV Specifications:**
- `A1` - RNAV 10 (RNP 10)
- `B1` - RNAV 5 all permitted sensors
- `B2` - RNAV 5 GNSS
- `B3` - RNAV 5 DME/DME
- `B4` - RNAV 5 VOR/DME
- `B5` - RNAV 5 INS or IRS
- `B6` - RNAV 5 LORANC
- `C1` - RNAV 2 all permitted sensors
- `C2` - RNAV 2 GNSS
- `C3` - RNAV 2 DME/DME
- `C4` - RNAV 2 DME/DME/IRU

**RNP Specifications:**
- `D1` - RNP 4
- `D2` - RNP 2
- `D3` - RNP 1
- `D4` - RNP 0.3
- `L1` - RNP AR APCH
- `O1` - Basic RNP 1 all permitted sensors
- `O2` - Basic RNP 1 GNSS
- `O3` - Basic RNP 1 DME/DME
- `O4` - Basic RNP 1 DME/DME/IRU
- `S1` - RNP APCH
- `S2` - RNP APCH with BARO-VNAV
- `T1` - RNP AR APCH with RF (special authorization required)
- `T2` - RNP AR APCH without RF (special authorization required)

**Example:** `PBN/A1B1C1D1L1O1S2T1` = RNAV 10, RNAV 5, RNAV 2, RNP 4, RNP AR, Basic RNP 1, RNP APCH with BARO

---

### NAV/ - Navigation Equipment

Used when Item 10a includes "Z" - specifies other navigation equipment.

**Common codes:**
- `Z1` - Additional navigation equipment/capabilities
- `GBAS` - Ground Based Augmentation System
- `SBAS` - Satellite Based Augmentation System

---

### SUR/ - Surveillance Capability

Specifies surveillance equipment beyond Item 10b.

**Common codes:**
- `260B` - ADS-B with 1090ES
- `282B` - ADS-B with UAT
- `RSP180` - Required Surveillance Performance 180 seconds
- `RSP400` - Required Surveillance Performance 400 seconds
- `CANMANDATE` - Canadian ADS-B mandate compliance

**Example:** `SUR/260B RSP180 RSP400 CANMANDATE`

---

### COM/ - Communication Capability

Specifies communication equipment when Item 10a includes "Z".

---

### DAT/ - Data Link Capability

Specifies data link equipment when Item 10a includes "Z".

---

### EET/ - Estimated Elapsed Times

**Format:** `EET/boundary1 time1 boundary2 time2 ...`

Times in 4 digits (HHMM) from departure.

**Common NAT boundaries:**
- FIR codes: `CZQM`, `CZQX`, `EGGX`, `ENOB`, `BIRD`, `KZNY`, `LPPO`
- Oceanic waypoints: `47N050W`, `49N040W`, `51N030W`, `51N020W`, etc.

**Example:** `EET/CZQM0023 CZQX0114 47N050W0145 EGGX0318`

---

### SEL/ - SELCAL Code

4-letter code for selective calling.

**Format:** `SEL/XXXX` (e.g., `SEL/ERMP`)

**Code structure:** Two pairs of letters from approved list (A-S except I,N,O)

---

### OPR/ - Operator

3-letter airline designator or operator name.

**Example:** `OPR/BAW` (British Airways), `OPR/QTR` (Qatar Airways)

---

### REG/ - Aircraft Registration

**Format:** `REG/XXXXXX`

**Example:** `REG/N772RR`, `REG/G-STBC`

---

### DOF/ - Date of Flight

**Format:** `DOF/YYMMDD`

**Example:** `DOF/251231` (31 December 2025)

---

### PER/ - Aircraft Performance Category

ICAO aircraft approach category (A/B/C/D/E).

**Format:** `PER/X`

**Categories:**
- A: < 91 kt
- B: 91-120 kt
- C: 121-140 kt
- D: 141-165 kt
- E: > 165 kt

---

### RVR/ - Minimum RVR

Minimum Runway Visual Range (metres).

**Format:** `RVR/XXX`

**Example:** `RVR/050` (50 metres), `RVR/200` (200 metres)

---

### RALT/ - Alternate Aerodromes

En-route and/or destination alternates beyond Item 16.

**Format:** `RALT/ICAO1 ICAO2`

**Example:** `RALT/BIKF CYJT` (Reykjavik and St. John's)

---

### RMK/ - Remarks

Free text remarks.

**Common entries:**
- `RMK/TCAS` - Traffic Collision Avoidance System equipped
- `RMK/SIMBRIEF` - SimBrief flight planning
- Other operational notes

---

## ICAO Aircraft Type Field (Item 9)

**Format:** `TYPE/WAKE-EQUIPMENT/SUR`

**Example:** `B77L/H-SDE1E2E3FGHIJ2J3J4J5M1RWXY/LB1D1`

### Components:

1. **Aircraft Type:** `B77L` (Boeing 777-200LR)

2. **Wake Turbulence Category:**
   - `L` - Light (< 7,000 kg)
   - `M` - Medium (7,000 - 136,000 kg)
   - `H` - Heavy (> 136,000 kg)
   - `J` - Super (A380)

3. **Equipment Codes:** (after the hyphen)
   - `S` - Standard COM/NAV/approach equipment
   - `D` - DME
   - `E1`, `E2`, `E3` - FMC WPR ACARS
   - `F` - ADF
   - `G` - GNSS
   - `H` - HF RTF
   - `I` - Inertial navigation
   - `J1`-`J7` - CPDLC capabilities
   - `M1`-`M3` - ATC RTF capabilities
   - `R` - PBN approved (triggers PBN/ in Item 18)
   - `W` - RVSM approved
   - `X` - MNPS approved
   - `Y` - VHF with 8.33 kHz spacing
   - `Z` - Other equipment (triggers NAV/, COM/, DAT/ in Item 18)

4. **Surveillance Codes:** (after second slash)
   - `L` - ADS-B
   - `B1` - ADS-B with dedicated 1090 MHz capability
   - `D1` - ADS-C with capabilities

**Example Breakdown:**
```
B77L/H-SDE1E2E3FGHIJ2J3J4J5M1RWXY/LB1D1
│    │  └────── Equipment ──────┘  └──── SUR
│    └─ Heavy wake turbulence
└─ Boeing 777-200LR
```

---

## Analysis Applications

### Equipage Studies
- **PBN capability trends** - What percentage have RNP 4? RNP AR?
- **GNSS reliance** - B2, C2, O2 codes indicate GNSS-only
- **Legacy vs modern** - Track adoption of newer PBN specs

### Surveillance Analysis
- **ADS-B equipage** - 260B prevalence
- **RSP compliance** - RSP180 vs RSP400

### Operational Capability
- **Low visibility operations** - RVR minimums
- **Performance category** - Speed-based analysis
- **SELCAL equipped** - Percentage for oceanic ops

### Route Analysis
- **EET boundaries** - Which FIRs are crossed
- **Oceanic waypoints** - Track usage patterns
- **Filed vs actual** - Compare EET to actual times

---

## Parsing Strategy

**Current approach:** Store full strings, mine later ✅

**Fields already extracted:**
- `eet_string` - EET/ data
- `selcal` - SEL/ code
- `operator` - OPR/ code  
- `registration` - REG/ code
- `pbn_capability` - PBN/ string
- `com_capability` - COM/ string (if present)
- `sur_capability` - SUR/ string (if present)

**Available for future mining:**
- NAV/ capabilities
- RVR/ minimums
- PER/ category
- RALT/ alternates
- DOF/ date validation
- RMK/ operational notes

---

## References

- ICAO Doc 4444, Appendix 2 (Flight Plan)
- ICAO Doc 9613 (Performance-based Navigation Manual)
- ICAO Doc 9869 (Performance-based Communication and Surveillance Manual)

---

**Document created:** 2026-01-01  
**For:** VATSIM NAT Traffic Analyzer  
**Purpose:** Parse and analyze NAT crossing equipage data
