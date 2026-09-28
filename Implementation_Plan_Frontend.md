# SIH26012 — Frontend Implementation Plan
## Web-GIS Interface for AI-Assisted Cadastral Review

*This plan covers only the frontend: React/TypeScript application, MapLibre GL JS map, layer management, feature inspection, polygon editing, warning navigation, review workflow, and GeoJSON export. Backend API is assumed to be available.*

---

## Table of Contents

1. [Scope & Assumptions](#1-scope--assumptions)
2. [Tech Stack](#2-tech-stack)
3. [Phase 1 — Project Setup & Design System](#3-phase-1--project-setup--design-system)
4. [Phase 2 — Map Foundation](#4-phase-2--map-foundation)
5. [Phase 3 — Layer Management](#5-phase-3--layer-management)
6. [Phase 4 — Left Panel: Project Controls](#6-phase-4--left-panel-project-controls)
7. [Phase 5 — Right Panel: Feature Inspector](#7-phase-5--right-panel-feature-inspector)
8. [Phase 6 — Warning System & Navigation](#8-phase-6--warning-system--navigation)
9. [Phase 7 — Polygon Editing](#9-phase-7--polygon-editing)
10. [Phase 8 — Review Workflow (Approve/Reject)](#10-phase-8--review-workflow-approvereject)
11. [Phase 9 — Processing Status & Upload](#11-phase-9--processing-status--upload)
12. [Phase 10 — GeoJSON Export](#12-phase-10--geojson-export)
13. [Phase 11 — Stretch: Review Priority Visualization](#13-phase-11--stretch-review-priority-visualization)
14. [Phase 12 — Stretch: Change Detection Overlay](#14-phase-12--stretch-change-detection-overlay)
15. [Phase 13 — Stretch: NDVI/LST Climate Layer](#15-phase-13--stretch-ndvilst-climate-layer)
16. [Component Architecture](#16-component-architecture)
17. [State Management](#17-state-management)
18. [API Integration Layer](#18-api-integration-layer)
19. [Styling & Design Guidelines](#19-styling--design-guidelines)
20. [File Structure](#20-file-structure)
21. [Day-by-Day Frontend Schedule](#21-day-by-day-frontend-schedule)
22. [Acceptance Criteria](#22-acceptance-criteria)

---

## 1. Scope & Assumptions

### 1.1 What This Plan Covers

```text
✅ React + TypeScript application (Vite)
✅ MapLibre GL JS interactive map
✅ Orthomosaic raster display
✅ GeoJSON layer rendering (buildings, roads, parcels, land-use)
✅ Layer toggle controls
✅ Feature click-to-inspect
✅ Warning list with map navigation
✅ Polygon vertex editing
✅ Approve/reject/edit review workflow
✅ Processing status indicator
✅ GeoJSON export/download
✅ Review priority color-coding (stretch)
✅ Change detection overlay (stretch)
✅ NDVI/LST heatmap overlay (stretch)
✅ Responsive three-panel layout
```

### 1.2 What This Plan Does NOT Cover

```text
❌ Backend API implementation
❌ AI model inference
❌ GIS processing pipeline
❌ Database/storage
❌ User authentication/accounts
❌ Mobile responsiveness
❌ Multi-tenant/multi-project dashboards
```

### 1.3 API Contract Assumptions

The frontend consumes these backend endpoints (assumed available):

| Endpoint | Returns |
|---|---|
| `GET /api/projects/{id}/process/status` | `{ status, detail, updated_at }` |
| `GET /api/projects/{id}/layers/buildings` | GeoJSON FeatureCollection |
| `GET /api/projects/{id}/layers/roads` | GeoJSON FeatureCollection |
| `GET /api/projects/{id}/layers/parcels` | GeoJSON FeatureCollection |
| `GET /api/projects/{id}/layers/landuse` | GeoJSON FeatureCollection |
| `GET /api/projects/{id}/warnings` | JSON array of warning objects |
| `GET /api/projects/{id}/scores` | JSON array of review score objects |
| `GET /api/projects/{id}/changes` | JSON array of change indicators |
| `PUT /api/projects/{id}/features/{fid}` | Updated feature |
| `POST /api/projects/{id}/features/{fid}/approve` | `{ status: "approved" }` |
| `POST /api/projects/{id}/features/{fid}/reject` | `{ status: "rejected" }` |
| `POST /api/projects/{id}/revalidate` | Updated warnings + scores |
| `GET /api/projects/{id}/export` | ZIP file download |

---

## 2. Tech Stack

| Concern | Tool | Version | Purpose |
|---|---|---|---|
| Framework | React | 18.x | Component model, hooks |
| Language | TypeScript | 5.x | Type safety |
| Bundler | Vite | 5.x | Fast HMR, simple config |
| Map engine | MapLibre GL JS | 4.x | WebGL-accelerated vector/raster map |
| React binding | react-map-gl | 7.x (MapLibre fork) | React wrapper for MapLibre |
| Geospatial utils | @turf/turf | 7.x | Client-side geometry operations |
| HTTP client | fetch (native) | — | API calls |
| Icons | Lucide React | latest | Consistent icon set |
| Styling | Vanilla CSS (CSS Modules) | — | No framework dependency |

### Installation

```bash
npx -y create-vite@latest ./ --template react-ts
npm install maplibre-gl react-map-gl @turf/turf lucide-react
```

---

## 3. Phase 1 — Project Setup & Design System

> **Timeline: Day 2 (first half)**

### 3.1 Design Tokens

```css
/* src/styles/tokens.css */

:root {
  /* Colors — Dark mode primary */
  --bg-primary: #0f1117;
  --bg-secondary: #1a1d27;
  --bg-panel: #141722;
  --bg-card: #1e2130;
  --bg-hover: #252940;

  --text-primary: #e8eaed;
  --text-secondary: #9aa0b0;
  --text-muted: #6b7280;

  --accent-blue: #4e8cff;
  --accent-green: #34d399;
  --accent-amber: #fbbf24;
  --accent-red: #ef4444;
  --accent-purple: #a78bfa;

  /* Layer colors */
  --layer-parcels: #4e8cff;
  --layer-buildings: #f97316;
  --layer-roads: #a78bfa;
  --layer-landuse: #34d399;
  --layer-warnings: #ef4444;

  /* Priority colors */
  --priority-high: #ef4444;
  --priority-medium: #fbbf24;
  --priority-low: #34d399;

  /* Spacing */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;

  /* Panel widths */
  --panel-left-width: 320px;
  --panel-right-width: 360px;

  /* Border radius */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;

  /* Shadows */
  --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.3);
  --shadow-panel: 0 4px 16px rgba(0, 0, 0, 0.4);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;

  /* Typography */
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --font-size-xs: 11px;
  --font-size-sm: 13px;
  --font-size-md: 14px;
  --font-size-lg: 16px;
  --font-size-xl: 20px;
  --font-size-2xl: 24px;
}
```

### 3.2 Global Styles

```css
/* src/styles/global.css */

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body, #root {
  height: 100%;
  width: 100%;
  overflow: hidden;
}

body {
  font-family: var(--font-family);
  font-size: var(--font-size-md);
  color: var(--text-primary);
  background: var(--bg-primary);
  -webkit-font-smoothing: antialiased;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--text-muted);
  border-radius: 3px;
}

/* Utility classes */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: var(--font-size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.badge--high { background: rgba(239,68,68,0.15); color: var(--priority-high); }
.badge--medium { background: rgba(251,191,36,0.15); color: var(--priority-medium); }
.badge--low { background: rgba(52,211,153,0.15); color: var(--priority-low); }
.badge--info { background: rgba(78,140,255,0.15); color: var(--accent-blue); }
```

---

## 4. Phase 2 — Map Foundation

> **Timeline: Day 2 (second half)**

### 4.1 Component: `MapView.tsx`

```tsx
// src/components/MapView/MapView.tsx

import { useRef, useCallback } from 'react';
import Map, { Source, Layer, NavigationControl, ScaleControl } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { MapRef, MapLayerMouseEvent } from 'react-map-gl/maplibre';

interface MapViewProps {
  layers: LayerState;
  selectedFeatureId: string | null;
  onFeatureClick: (feature: GeoJSONFeature | null) => void;
  onMapReady: (map: MapRef) => void;
}

export function MapView({ layers, selectedFeatureId, onFeatureClick, onMapReady }: MapViewProps) {
  const mapRef = useRef<MapRef>(null);

  const handleClick = useCallback((e: MapLayerMouseEvent) => {
    const features = e.features;
    if (features && features.length > 0) {
      onFeatureClick(features[0] as GeoJSONFeature);
    } else {
      onFeatureClick(null);
    }
  }, [onFeatureClick]);

  return (
    <div className="map-container">
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: 77.59,  // Default: Bangalore area
          latitude: 12.97,
          zoom: 16
        }}
        style={{ width: '100%', height: '100%' }}
        mapStyle={{
          version: 8,
          sources: {},
          layers: [{
            id: 'background',
            type: 'background',
            paint: { 'background-color': '#1a1d27' }
          }]
        }}
        interactiveLayerIds={['parcels-fill', 'buildings-fill', 'roads-line']}
        onClick={handleClick}
        onLoad={() => mapRef.current && onMapReady(mapRef.current)}
        cursor="pointer"
      >
        <NavigationControl position="top-right" />
        <ScaleControl position="bottom-right" />

        {/* Orthomosaic raster layer */}
        {layers.orthomosaic.visible && layers.orthomosaic.url && (
          <Source
            id="orthomosaic"
            type="raster"
            tiles={[layers.orthomosaic.url]}
            tileSize={256}
          >
            <Layer id="orthomosaic-raster" type="raster" paint={{ 'raster-opacity': 0.9 }} />
          </Source>
        )}

        {/* Parcels layer */}
        {layers.parcels.visible && layers.parcels.data && (
          <Source id="parcels" type="geojson" data={layers.parcels.data}>
            <Layer
              id="parcels-fill"
              type="fill"
              paint={{
                'fill-color': [
                  'case',
                  ['==', ['get', 'review_status'], 'approved'], 'rgba(52,211,153,0.15)',
                  ['==', ['get', 'review_status'], 'rejected'], 'rgba(239,68,68,0.15)',
                  'rgba(78,140,255,0.1)'
                ],
                'fill-opacity': 0.6
              }}
            />
            <Layer
              id="parcels-outline"
              type="line"
              paint={{
                'line-color': [
                  'case',
                  ['==', ['get', 'parcel_id'], selectedFeatureId || ''], '#ffffff',
                  'var(--layer-parcels)'
                ],
                'line-width': [
                  'case',
                  ['==', ['get', 'parcel_id'], selectedFeatureId || ''], 3,
                  1.5
                ],
                'line-dasharray': [2, 2]
              }}
            />
          </Source>
        )}

        {/* Buildings layer */}
        {layers.buildings.visible && layers.buildings.data && (
          <Source id="buildings" type="geojson" data={layers.buildings.data}>
            <Layer
              id="buildings-fill"
              type="fill"
              paint={{
                'fill-color': [
                  'interpolate', ['linear'],
                  ['get', 'confidence'],
                  0.0, '#ef4444',  // Low confidence = red
                  0.5, '#fbbf24',  // Medium = amber
                  0.8, '#f97316',  // High = orange
                  1.0, '#34d399'   // Very high = green
                ],
                'fill-opacity': 0.5
              }}
            />
            <Layer
              id="buildings-outline"
              type="line"
              paint={{
                'line-color': '#f97316',
                'line-width': 1.5
              }}
            />
          </Source>
        )}

        {/* Roads layer */}
        {layers.roads.visible && layers.roads.data && (
          <Source id="roads" type="geojson" data={layers.roads.data}>
            <Layer
              id="roads-line"
              type="line"
              paint={{
                'line-color': '#a78bfa',
                'line-width': 2.5,
                'line-opacity': 0.8
              }}
            />
          </Source>
        )}

        {/* Warning highlights */}
        {layers.warnings.visible && layers.warnings.highlightGeometry && (
          <Source id="warning-highlight" type="geojson" data={layers.warnings.highlightGeometry}>
            <Layer
              id="warning-highlight-fill"
              type="fill"
              paint={{
                'fill-color': 'rgba(239,68,68,0.3)',
                'fill-outline-color': '#ef4444'
              }}
            />
            <Layer
              id="warning-highlight-pulse"
              type="line"
              paint={{
                'line-color': '#ef4444',
                'line-width': 3,
                'line-dasharray': [3, 2]
              }}
            />
          </Source>
        )}
      </Map>
    </div>
  );
}
```

### 4.2 Map Interaction Patterns

| User Action | Map Response | Data Action |
|---|---|---|
| Click on parcel | Highlight parcel, show in right panel | Set `selectedFeature` |
| Click on building | Highlight building, show confidence | Set `selectedFeature` |
| Click on road | Highlight road | Set `selectedFeature` |
| Click empty space | Clear selection | Set `selectedFeature(null)` |
| Scroll/pinch | Zoom in/out | — |
| Drag | Pan map | — |
| Click warning in list | Fly to location, highlight feature | Set `activeWarning` |

---

## 5. Phase 3 — Layer Management

> **Timeline: Day 2–3**

### 5.1 Layer State Types

```typescript
// src/types/layers.ts

export interface LayerConfig {
  id: string;
  name: string;
  visible: boolean;
  data: GeoJSON.FeatureCollection | null;
  color: string;
  icon: string;  // Lucide icon name
  featureCount: number;
  loading: boolean;
}

export interface LayerState {
  orthomosaic: {
    visible: boolean;
    url: string | null;
  };
  parcels: LayerConfig;
  buildings: LayerConfig;
  roads: LayerConfig;
  landuse: LayerConfig;
  warnings: {
    visible: boolean;
    data: Warning[];
    highlightGeometry: GeoJSON.FeatureCollection | null;
  };
  // Stretch layers
  priorityOverlay: { visible: boolean };
  changeDetection: { visible: boolean; data: ChangeIndicator[] | null };
  climate: { visible: boolean; data: GeoJSON.FeatureCollection | null };
}
```

### 5.2 Layer Data Fetching

```typescript
// src/hooks/useLayerData.ts

import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

export function useLayerData(projectId: string) {
  const [layers, setLayers] = useState<LayerState>(initialLayerState);
  const [loading, setLoading] = useState(false);

  const fetchLayer = useCallback(async (layerName: string) => {
    try {
      setLayers(prev => ({
        ...prev,
        [layerName]: { ...prev[layerName as keyof LayerState], loading: true }
      }));

      const data = await api.getLayer(projectId, layerName);

      setLayers(prev => ({
        ...prev,
        [layerName]: {
          ...prev[layerName as keyof LayerState],
          data,
          featureCount: data.features?.length || 0,
          loading: false
        }
      }));
    } catch (err) {
      console.error(`Failed to fetch ${layerName}:`, err);
    }
  }, [projectId]);

  const fetchAllLayers = useCallback(async () => {
    setLoading(true);
    await Promise.all([
      fetchLayer('buildings'),
      fetchLayer('roads'),
      fetchLayer('parcels'),
      fetchLayer('landuse'),
    ]);

    // Also fetch warnings and scores
    const warnings = await api.getWarnings(projectId);
    const scores = await api.getScores(projectId);

    setLayers(prev => ({
      ...prev,
      warnings: { ...prev.warnings, data: warnings }
    }));

    setLoading(false);
  }, [fetchLayer, projectId]);

  const toggleLayer = useCallback((layerName: string) => {
    setLayers(prev => ({
      ...prev,
      [layerName]: {
        ...prev[layerName as keyof LayerState],
        visible: !prev[layerName as keyof LayerState].visible
      }
    }));
  }, []);

  return { layers, loading, fetchAllLayers, toggleLayer, fetchLayer };
}
```

---

## 6. Phase 4 — Left Panel: Project Controls

> **Timeline: Day 2–3**

### 6.1 Component: `LeftPanel.tsx`

```tsx
// src/components/LeftPanel/LeftPanel.tsx

import { Layers, AlertTriangle, Download, MapPin, Building, Route } from 'lucide-react';
import { LayerToggle } from './LayerToggle';
import { WarningList } from './WarningList';
import { ProjectStatus } from './ProjectStatus';
import styles from './LeftPanel.module.css';

interface LeftPanelProps {
  layers: LayerState;
  warnings: Warning[];
  processingStatus: ProcessingStatus;
  onToggleLayer: (layerName: string) => void;
  onWarningClick: (warning: Warning) => void;
  onExport: () => void;
}

export function LeftPanel({
  layers, warnings, processingStatus,
  onToggleLayer, onWarningClick, onExport
}: LeftPanelProps) {
  return (
    <aside className={styles.panel}>
      {/* Header */}
      <div className={styles.header}>
        <h2 className={styles.title}>Cadastral Review</h2>
        <ProjectStatus status={processingStatus} />
      </div>

      {/* Layer Toggles */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <Layers size={16} /> Layers
        </h3>
        <LayerToggle
          label="Orthomosaic"
          icon={<MapPin size={14} />}
          color="#94a3b8"
          visible={layers.orthomosaic.visible}
          onToggle={() => onToggleLayer('orthomosaic')}
        />
        <LayerToggle
          label="Parcels"
          icon={<MapPin size={14} />}
          color="var(--layer-parcels)"
          visible={layers.parcels.visible}
          count={layers.parcels.featureCount}
          onToggle={() => onToggleLayer('parcels')}
        />
        <LayerToggle
          label="Buildings"
          icon={<Building size={14} />}
          color="var(--layer-buildings)"
          visible={layers.buildings.visible}
          count={layers.buildings.featureCount}
          onToggle={() => onToggleLayer('buildings')}
        />
        <LayerToggle
          label="Roads"
          icon={<Route size={14} />}
          color="var(--layer-roads)"
          visible={layers.roads.visible}
          count={layers.roads.featureCount}
          onToggle={() => onToggleLayer('roads')}
        />
        <LayerToggle
          label="Land Use"
          icon={<Layers size={14} />}
          color="var(--layer-landuse)"
          visible={layers.landuse.visible}
          count={layers.landuse.featureCount}
          onToggle={() => onToggleLayer('landuse')}
        />
      </section>

      {/* Feature Summary */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>Summary</h3>
        <div className={styles.statGrid}>
          <StatCard label="Parcels" value={layers.parcels.featureCount} color="var(--layer-parcels)" />
          <StatCard label="Buildings" value={layers.buildings.featureCount} color="var(--layer-buildings)" />
          <StatCard label="Roads" value={layers.roads.featureCount} color="var(--layer-roads)" />
          <StatCard label="Warnings" value={warnings.length} color="var(--layer-warnings)" />
        </div>
      </section>

      {/* Warning List */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <AlertTriangle size={16} /> Warnings ({warnings.length})
        </h3>
        <WarningList warnings={warnings} onWarningClick={onWarningClick} />
      </section>

      {/* Export */}
      <div className={styles.footer}>
        <button className={styles.exportButton} onClick={onExport}>
          <Download size={16} />
          Export GeoJSON
        </button>
      </div>
    </aside>
  );
}
```

### 6.2 Component: `LayerToggle.tsx`

```tsx
// src/components/LeftPanel/LayerToggle.tsx

import styles from './LayerToggle.module.css';

interface LayerToggleProps {
  label: string;
  icon: React.ReactNode;
  color: string;
  visible: boolean;
  count?: number;
  onToggle: () => void;
}

export function LayerToggle({ label, icon, color, visible, count, onToggle }: LayerToggleProps) {
  return (
    <button
      className={`${styles.toggle} ${visible ? styles.active : ''}`}
      onClick={onToggle}
    >
      <span className={styles.indicator} style={{ backgroundColor: visible ? color : 'transparent', borderColor: color }} />
      <span className={styles.icon}>{icon}</span>
      <span className={styles.label}>{label}</span>
      {count !== undefined && (
        <span className={styles.count}>{count}</span>
      )}
    </button>
  );
}
```

### 6.3 Component: `WarningList.tsx`

```tsx
// src/components/LeftPanel/WarningList.tsx

import { AlertCircle, AlertTriangle, Info } from 'lucide-react';
import styles from './WarningList.module.css';

const severityIcons = {
  high: <AlertCircle size={14} className={styles.iconHigh} />,
  medium: <AlertTriangle size={14} className={styles.iconMedium} />,
  low: <Info size={14} className={styles.iconLow} />,
};

interface WarningListProps {
  warnings: Warning[];
  onWarningClick: (warning: Warning) => void;
}

export function WarningList({ warnings, onWarningClick }: WarningListProps) {
  // Sort by severity: high → medium → low
  const sorted = [...warnings].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 };
    return (order[a.severity] || 2) - (order[b.severity] || 2);
  });

  return (
    <div className={styles.list}>
      {sorted.map(warning => (
        <button
          key={warning.warning_id}
          className={styles.item}
          onClick={() => onWarningClick(warning)}
          title="Click to zoom to this warning"
        >
          <span className={styles.severity}>
            {severityIcons[warning.severity]}
          </span>
          <div className={styles.content}>
            <span className={styles.type}>
              {warning.warning_type.replace(/_/g, ' ')}
            </span>
            <span className={styles.explanation}>
              {warning.explanation}
            </span>
          </div>
        </button>
      ))}
      {warnings.length === 0 && (
        <p className={styles.empty}>No warnings detected</p>
      )}
    </div>
  );
}
```

### 6.4 Component: `ProjectStatus.tsx`

```tsx
// src/components/LeftPanel/ProjectStatus.tsx

import styles from './ProjectStatus.module.css';

const statusLabels: Record<string, { label: string; color: string }> = {
  queued: { label: 'Queued', color: 'var(--text-muted)' },
  preprocessing: { label: 'Preprocessing...', color: 'var(--accent-blue)' },
  extracting_buildings: { label: 'Extracting Buildings...', color: 'var(--accent-blue)' },
  loading_roads: { label: 'Loading Roads...', color: 'var(--accent-blue)' },
  classifying_landuse: { label: 'Classifying Land Use...', color: 'var(--accent-blue)' },
  loading_parcels: { label: 'Loading Parcels...', color: 'var(--accent-blue)' },
  detecting_changes: { label: 'Detecting Changes...', color: 'var(--accent-blue)' },
  validating_topology: { label: 'Validating Topology...', color: 'var(--accent-amber)' },
  scoring: { label: 'Scoring Parcels...', color: 'var(--accent-amber)' },
  complete: { label: 'Complete', color: 'var(--accent-green)' },
  error: { label: 'Error', color: 'var(--accent-red)' },
};

export function ProjectStatus({ status }: { status: string }) {
  const config = statusLabels[status] || { label: status, color: 'var(--text-muted)' };

  return (
    <div className={styles.status}>
      <span
        className={styles.dot}
        style={{ backgroundColor: config.color }}
      />
      <span className={styles.label}>{config.label}</span>
    </div>
  );
}
```

---

## 7. Phase 5 — Right Panel: Feature Inspector

> **Timeline: Day 3–4**

### 7.1 Component: `RightPanel.tsx`

```tsx
// src/components/RightPanel/RightPanel.tsx

import { FeatureInspector } from './FeatureInspector';
import { ReviewActions } from './ReviewActions';
import { WarningDetails } from './WarningDetails';
import { ConfidenceBadge } from './ConfidenceBadge';
import styles from './RightPanel.module.css';

interface RightPanelProps {
  selectedFeature: GeoJSONFeature | null;
  featureWarnings: Warning[];
  featureScore: ReviewScore | null;
  onApprove: (featureId: string, reason?: string) => void;
  onReject: (featureId: string, reason?: string) => void;
  onStartEdit: () => void;
  onSaveEdit: (geometry: GeoJSON.Geometry) => void;
  isEditing: boolean;
}

export function RightPanel({
  selectedFeature, featureWarnings, featureScore,
  onApprove, onReject, onStartEdit, onSaveEdit, isEditing
}: RightPanelProps) {
  if (!selectedFeature) {
    return (
      <aside className={styles.panel}>
        <div className={styles.placeholder}>
          <p>Click a feature on the map to inspect it</p>
        </div>
      </aside>
    );
  }

  const props = selectedFeature.properties || {};
  const featureId = props.parcel_id || props.building_id || props.road_id || 'Unknown';
  const featureType = props.feature_type || 'unknown';
  const confidence = props.confidence;
  const source = props.source || 'unknown';
  const reviewStatus = props.review_status || 'unverified';

  return (
    <aside className={styles.panel}>
      {/* Feature Header */}
      <div className={styles.header}>
        <h3 className={styles.featureId}>{featureId}</h3>
        <span className={`badge badge--info`}>{featureType}</span>
      </div>

      {/* Attributes Table */}
      <FeatureInspector feature={selectedFeature} />

      {/* Confidence Badge */}
      {confidence !== null && confidence !== undefined && (
        <ConfidenceBadge confidence={confidence} source={source} />
      )}

      {/* Review Score (if parcel) */}
      {featureScore && (
        <div className={styles.section}>
          <h4>Review Priority</h4>
          <div className={styles.scoreBar}>
            <div
              className={styles.scoreFill}
              style={{
                width: `${featureScore.review_score}%`,
                backgroundColor:
                  featureScore.priority === 'high' ? 'var(--priority-high)' :
                  featureScore.priority === 'medium' ? 'var(--priority-medium)' :
                  'var(--priority-low)'
              }}
            />
            <span className={styles.scoreValue}>{featureScore.review_score}</span>
          </div>
          <ul className={styles.reasons}>
            {featureScore.reasons.map((reason, i) => (
              <li key={i}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Warnings for this feature */}
      {featureWarnings.length > 0 && (
        <WarningDetails warnings={featureWarnings} />
      )}

      {/* Review Actions */}
      <ReviewActions
        featureId={featureId}
        currentStatus={reviewStatus}
        onApprove={onApprove}
        onReject={onReject}
        onStartEdit={onStartEdit}
        onSaveEdit={onSaveEdit}
        isEditing={isEditing}
      />
    </aside>
  );
}
```

### 7.2 Component: `FeatureInspector.tsx`

```tsx
// src/components/RightPanel/FeatureInspector.tsx

import styles from './FeatureInspector.module.css';

const DISPLAY_FIELDS = [
  { key: 'parcel_id', label: 'Parcel ID' },
  { key: 'building_id', label: 'Building ID' },
  { key: 'road_id', label: 'Road ID' },
  { key: 'feature_type', label: 'Type' },
  { key: 'source', label: 'Source' },
  { key: 'source_date', label: 'Source Date' },
  { key: 'confidence', label: 'Confidence' },
  { key: 'review_status', label: 'Review Status' },
  { key: 'verification_status', label: 'Verification' },
  { key: 'notes', label: 'Notes' },
];

export function FeatureInspector({ feature }: { feature: GeoJSONFeature }) {
  const props = feature.properties || {};

  return (
    <div className={styles.inspector}>
      <h4 className={styles.title}>Attributes</h4>
      <table className={styles.table}>
        <tbody>
          {DISPLAY_FIELDS.map(({ key, label }) => {
            const value = props[key];
            if (value === undefined || value === null) return null;
            return (
              <tr key={key}>
                <td className={styles.key}>{label}</td>
                <td className={styles.value}>
                  {typeof value === 'number' ? value.toFixed(3) : String(value)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

### 7.3 Component: `ConfidenceBadge.tsx`

```tsx
// src/components/RightPanel/ConfidenceBadge.tsx

import styles from './ConfidenceBadge.module.css';

export function ConfidenceBadge({ confidence, source }: { confidence: number; source: string }) {
  const percentage = Math.round(confidence * 100);
  const level = confidence >= 0.8 ? 'high' : confidence >= 0.5 ? 'medium' : 'low';

  const colors = {
    high: { bar: 'var(--accent-green)', bg: 'rgba(52,211,153,0.1)' },
    medium: { bar: 'var(--accent-amber)', bg: 'rgba(251,191,36,0.1)' },
    low: { bar: 'var(--accent-red)', bg: 'rgba(239,68,68,0.1)' },
  };

  return (
    <div className={styles.badge} style={{ backgroundColor: colors[level].bg }}>
      <div className={styles.header}>
        <span className={styles.label}>AI Confidence</span>
        <span className={styles.value} style={{ color: colors[level].bar }}>
          {percentage}%
        </span>
      </div>
      <div className={styles.barTrack}>
        <div
          className={styles.barFill}
          style={{ width: `${percentage}%`, backgroundColor: colors[level].bar }}
        />
      </div>
      <span className={styles.source}>Source: {source.replace(/_/g, ' ')}</span>
    </div>
  );
}
```

---

## 8. Phase 6 — Warning System & Navigation

> **Timeline: Day 5**

### 8.1 Warning Navigation Logic

When a user clicks a warning in the left panel:

```typescript
// src/hooks/useWarningNavigation.ts

import { useCallback } from 'react';
import * as turf from '@turf/turf';

export function useWarningNavigation(
  mapRef: MapRef | null,
  layers: LayerState,
  setActiveWarning: (w: Warning | null) => void
) {
  const navigateToWarning = useCallback((warning: Warning) => {
    if (!mapRef) return;

    setActiveWarning(warning);

    // Find the affected features across all layers
    const affectedGeometries: GeoJSON.Feature[] = [];

    for (const fid of warning.feature_ids) {
      // Search in parcels
      const parcel = layers.parcels.data?.features.find(
        f => f.properties?.parcel_id === fid
      );
      if (parcel) affectedGeometries.push(parcel);

      // Search in buildings
      const building = layers.buildings.data?.features.find(
        f => f.properties?.building_id === fid
      );
      if (building) affectedGeometries.push(building);

      // Search in roads
      const road = layers.roads.data?.features.find(
        f => f.properties?.road_id === fid
      );
      if (road) affectedGeometries.push(road);
    }

    if (affectedGeometries.length > 0) {
      // Compute bounding box of all affected features
      const collection = turf.featureCollection(affectedGeometries);
      const bbox = turf.bbox(collection);

      // Fly to the affected area
      mapRef.fitBounds(
        [[bbox[0], bbox[1]], [bbox[2], bbox[3]]],
        { padding: 100, duration: 1200 }
      );

      // Highlight affected features (update warning overlay source)
      // This updates the warning-highlight layer on the map
    }
  }, [mapRef, layers, setActiveWarning]);

  return { navigateToWarning };
}
```

### 8.2 Warning Highlight Styling

Affected features get a pulsing red border when a warning is active:

```css
/* Animated warning highlight */
@keyframes warningPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.warning-highlight {
  animation: warningPulse 1.5s ease-in-out infinite;
}
```

---

## 9. Phase 7 — Polygon Editing

> **Timeline: Day 6**

### 9.1 Editing Approach

For the MVP, implement **simple vertex dragging** without a full drawing library:

```typescript
// src/hooks/usePolygonEdit.ts

import { useState, useCallback } from 'react';

export interface EditState {
  isEditing: boolean;
  originalGeometry: GeoJSON.Geometry | null;
  editedGeometry: GeoJSON.Geometry | null;
  featureId: string | null;
  vertices: [number, number][];
  dragIndex: number | null;
}

export function usePolygonEdit(
  mapRef: MapRef | null,
  onSave: (featureId: string, geometry: GeoJSON.Geometry) => void
) {
  const [editState, setEditState] = useState<EditState>({
    isEditing: false,
    originalGeometry: null,
    editedGeometry: null,
    featureId: null,
    vertices: [],
    dragIndex: null,
  });

  const startEditing = useCallback((feature: GeoJSONFeature) => {
    const geom = feature.geometry;
    if (geom.type !== 'Polygon') return;

    const vertices = geom.coordinates[0].slice(0, -1); // Remove closing vertex
    setEditState({
      isEditing: true,
      originalGeometry: geom,
      editedGeometry: geom,
      featureId: feature.properties?.parcel_id || feature.properties?.building_id,
      vertices: vertices as [number, number][],
      dragIndex: null,
    });
  }, []);

  const moveVertex = useCallback((index: number, lngLat: [number, number]) => {
    setEditState(prev => {
      const newVertices = [...prev.vertices];
      newVertices[index] = lngLat;

      // Rebuild polygon (close the ring)
      const coordinates = [...newVertices, newVertices[0]];
      const editedGeometry: GeoJSON.Geometry = {
        type: 'Polygon',
        coordinates: [coordinates]
      };

      return { ...prev, vertices: newVertices, editedGeometry };
    });
  }, []);

  const saveEdit = useCallback(() => {
    if (editState.featureId && editState.editedGeometry) {
      onSave(editState.featureId, editState.editedGeometry);
    }
    setEditState({
      isEditing: false,
      originalGeometry: null,
      editedGeometry: null,
      featureId: null,
      vertices: [],
      dragIndex: null,
    });
  }, [editState, onSave]);

  const cancelEdit = useCallback(() => {
    setEditState({
      isEditing: false,
      originalGeometry: null,
      editedGeometry: null,
      featureId: null,
      vertices: [],
      dragIndex: null,
    });
  }, []);

  return { editState, startEditing, moveVertex, saveEdit, cancelEdit };
}
```

### 9.2 Vertex Markers on the Map

When editing, render draggable markers at each polygon vertex:

```tsx
// src/components/MapView/EditVertices.tsx

import { Marker } from 'react-map-gl/maplibre';
import styles from './EditVertices.module.css';

interface EditVerticesProps {
  vertices: [number, number][];
  onVertexDrag: (index: number, lngLat: [number, number]) => void;
}

export function EditVertices({ vertices, onVertexDrag }: EditVerticesProps) {
  return (
    <>
      {vertices.map((vertex, i) => (
        <Marker
          key={i}
          longitude={vertex[0]}
          latitude={vertex[1]}
          draggable
          onDragEnd={(e) => onVertexDrag(i, [e.lngLat.lng, e.lngLat.lat])}
        >
          <div className={styles.vertexHandle} />
        </Marker>
      ))}
    </>
  );
}
```

```css
/* EditVertices.module.css */
.vertexHandle {
  width: 12px;
  height: 12px;
  background: #ffffff;
  border: 2px solid var(--accent-blue);
  border-radius: 50%;
  cursor: grab;
  transition: transform var(--transition-fast);
}

.vertexHandle:hover {
  transform: scale(1.4);
  background: var(--accent-blue);
}

.vertexHandle:active {
  cursor: grabbing;
}
```

---

## 10. Phase 8 — Review Workflow (Approve/Reject)

> **Timeline: Day 6**

### 10.1 Component: `ReviewActions.tsx`

```tsx
// src/components/RightPanel/ReviewActions.tsx

import { Check, X, Edit3, Save, RotateCcw, MapPin } from 'lucide-react';
import { useState } from 'react';
import styles from './ReviewActions.module.css';

interface ReviewActionsProps {
  featureId: string;
  currentStatus: string;
  onApprove: (featureId: string, reason?: string) => void;
  onReject: (featureId: string, reason?: string) => void;
  onStartEdit: () => void;
  onSaveEdit: () => void;
  isEditing: boolean;
}

export function ReviewActions({
  featureId, currentStatus,
  onApprove, onReject, onStartEdit, onSaveEdit, isEditing
}: ReviewActionsProps) {
  const [reason, setReason] = useState('');

  return (
    <div className={styles.actions}>
      <h4 className={styles.title}>Review</h4>

      {/* Current status */}
      <div className={styles.currentStatus}>
        Status: <span className={`badge badge--${currentStatus === 'approved' ? 'low' : currentStatus === 'rejected' ? 'high' : 'info'}`}>
          {currentStatus}
        </span>
      </div>

      {/* Reason input */}
      <textarea
        className={styles.reasonInput}
        placeholder="Optional: reason for decision..."
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        rows={2}
      />

      {/* Action buttons */}
      <div className={styles.buttonGroup}>
        {!isEditing ? (
          <>
            <button
              className={`${styles.btn} ${styles.btnApprove}`}
              onClick={() => onApprove(featureId, reason)}
              disabled={currentStatus === 'approved'}
            >
              <Check size={16} /> Approve
            </button>
            <button
              className={`${styles.btn} ${styles.btnReject}`}
              onClick={() => onReject(featureId, reason)}
              disabled={currentStatus === 'rejected'}
            >
              <X size={16} /> Reject
            </button>
            <button
              className={`${styles.btn} ${styles.btnEdit}`}
              onClick={onStartEdit}
            >
              <Edit3 size={16} /> Edit
            </button>
          </>
        ) : (
          <>
            <button
              className={`${styles.btn} ${styles.btnSave}`}
              onClick={onSaveEdit}
            >
              <Save size={16} /> Save
            </button>
            <button
              className={`${styles.btn} ${styles.btnCancel}`}
              onClick={onStartEdit}  // toggles off
            >
              <RotateCcw size={16} /> Cancel
            </button>
          </>
        )}
      </div>

      {/* Disclaimer */}
      <p className={styles.disclaimer}>
        ⚠️ All parcel boundaries are preliminary AI-assisted suggestions
        and require field verification by an authorized surveyor.
      </p>
    </div>
  );
}
```

### 10.2 Review API Calls

```typescript
// src/api/review.ts

export async function approveFeature(projectId: string, featureId: string, reason?: string) {
  const res = await fetch(`/api/projects/${projectId}/features/${featureId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'approve', reason })
  });
  return res.json();
}

export async function rejectFeature(projectId: string, featureId: string, reason?: string) {
  const res = await fetch(`/api/projects/${projectId}/features/${featureId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'reject', reason })
  });
  return res.json();
}

export async function updateFeatureGeometry(
  projectId: string,
  featureId: string,
  geometry: GeoJSON.Geometry,
  notes?: string
) {
  const res = await fetch(`/api/projects/${projectId}/features/${featureId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ geometry, notes })
  });
  return res.json();
}

export async function revalidateProject(projectId: string) {
  const res = await fetch(`/api/projects/${projectId}/revalidate`, {
    method: 'POST'
  });
  return res.json();
}
```

---

## 11. Phase 9 — Processing Status & Upload

> **Timeline: Day 3**

### 11.1 Processing Status Polling

```typescript
// src/hooks/useProcessingStatus.ts

import { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';

export function useProcessingStatus(projectId: string) {
  const [status, setStatus] = useState<string>('unknown');
  const [detail, setDetail] = useState<string>('');
  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    const poll = async () => {
      try {
        const result = await api.getProcessingStatus(projectId);
        setStatus(result.status);
        setDetail(result.detail || '');

        // Stop polling when complete or error
        if (result.status === 'complete' || result.status === 'error') {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch {
        // Ignore transient errors during polling
      }
    };

    // Poll every 2 seconds
    intervalRef.current = setInterval(poll, 2000);
    poll(); // Initial fetch

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [projectId]);

  return { status, detail };
}
```

### 11.2 Upload Component (simplified)

```tsx
// src/components/Upload/UploadPanel.tsx

import { Upload, FileCheck } from 'lucide-react';
import styles from './UploadPanel.module.css';

export function UploadPanel({ onProjectSelect }: { onProjectSelect: (id: string) => void }) {
  // For MVP: just select the pre-loaded project
  return (
    <div className={styles.panel}>
      <h2>Select Study Area</h2>
      <p>Choose the prepared study area to begin review.</p>
      <button
        className={styles.selectButton}
        onClick={() => onProjectSelect('demo_project')}
      >
        <FileCheck size={20} />
        Load Demo Study Area
      </button>
    </div>
  );
}
```

---

## 12. Phase 10 — GeoJSON Export

> **Timeline: Day 6**

### 12.1 Export Handler

```typescript
// src/hooks/useExport.ts

export function useExport(projectId: string) {
  const exportProject = async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/export`);
      if (!response.ok) throw new Error('Export failed');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${projectId}_export.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Export failed. Please try again.');
    }
  };

  return { exportProject };
}
```

---

## 13. Phase 11 — Stretch: Review Priority Visualization

> **Timeline: Day 7 (if core is stable)**

### 13.1 Priority-Colored Parcels

Update the parcels layer paint to use review scores:

```typescript
// When review scores are available, color parcels by priority
const parcelPaint = {
  'fill-color': [
    'match',
    ['get', 'priority'],
    'high', 'rgba(239,68,68,0.25)',
    'medium', 'rgba(251,191,36,0.2)',
    'low', 'rgba(52,211,153,0.15)',
    'rgba(78,140,255,0.1)'  // default/unscored
  ],
  'fill-opacity': 0.6
};
```

### 13.2 Review Queue Component

```tsx
// src/components/LeftPanel/ReviewQueue.tsx

export function ReviewQueue({
  scores,
  onParcelClick
}: {
  scores: ReviewScore[];
  onParcelClick: (parcelId: string) => void;
}) {
  return (
    <div className={styles.queue}>
      <h4>Review Queue</h4>
      {scores
        .filter(s => s.priority !== 'low')
        .map(score => (
          <button
            key={score.parcel_id}
            className={styles.queueItem}
            onClick={() => onParcelClick(score.parcel_id)}
          >
            <span className={`badge badge--${score.priority}`}>
              {score.review_score}
            </span>
            <span className={styles.parcelId}>{score.parcel_id}</span>
            <span className={styles.reasonPreview}>
              {score.reasons[0] || 'Review recommended'}
            </span>
          </button>
        ))}
    </div>
  );
}
```

---

## 14. Phase 12 — Stretch: Change Detection Overlay

> **Timeline: Day 7 (if prior data available)**

### 14.1 Change Indicators on Map

```typescript
// Color change indicators by type
const changeColors = {
  new_construction: '#34d399',   // Green
  possible_removal: '#ef4444',   // Red
  geometry_change: '#fbbf24',    // Amber
};

// Render as a separate GeoJSON source with circle/fill markers
```

---

## 15. Phase 13 — Stretch: NDVI/LST Climate Layer

> **Timeline: Day 7 (if available from backend)**

### 15.1 Climate Overlay

- Render as a semi-transparent heatmap or choropleth layer
- Add a dedicated toggle with a clear label
- **Never** shown alongside warning highlights

```tsx
<LayerToggle
  label="🌡️ Heat Vulnerability (Planning)"
  color="#ff6b35"
  visible={layers.climate.visible}
  onToggle={() => onToggleLayer('climate')}
  subtitle="Optional urban planning layer"
/>
```

> **Important UI note:** Include a persistent label when this layer is active:
> *"Optional urban-planning and climate-resilience layer — not part of the cadastral review."*

---

## 16. Component Architecture

```text
<App>
├── <Header />
│   ├── Project title
│   └── Status badge
│
├── <MainLayout>
│   ├── <LeftPanel>
│   │   ├── <ProjectStatus />
│   │   ├── <LayerToggles>
│   │   │   └── <LayerToggle /> × N
│   │   ├── <FeatureSummary>
│   │   │   └── <StatCard /> × 4
│   │   ├── <WarningList>
│   │   │   └── <WarningItem /> × N
│   │   ├── <ReviewQueue />         (stretch)
│   │   └── <ExportButton />
│   │
│   ├── <MapView>
│   │   ├── <MapLibreMap />
│   │   │   ├── <Source /> + <Layer /> per data layer
│   │   │   ├── <NavigationControl />
│   │   │   └── <ScaleControl />
│   │   ├── <EditVertices />        (when editing)
│   │   └── <EditingToolbar />
│   │
│   └── <RightPanel>
│       ├── <FeatureInspector />
│       │   └── Attribute table
│       ├── <ConfidenceBadge />
│       ├── <ReviewScoreBar />      (stretch)
│       ├── <WarningDetails />
│       └── <ReviewActions />
│           ├── Approve button
│           ├── Reject button
│           ├── Edit button
│           └── Disclaimer text
│
└── <UploadPanel />                 (initial state only)
```

---

## 17. State Management

Use React's built-in state management (no Redux needed for MVP):

### 17.1 Top-Level State

```typescript
// src/App.tsx — top-level state

const [projectId, setProjectId] = useState<string | null>(null);
const [selectedFeature, setSelectedFeature] = useState<GeoJSONFeature | null>(null);
const [activeWarning, setActiveWarning] = useState<Warning | null>(null);
const [isEditing, setIsEditing] = useState(false);

// Custom hooks manage their own state:
const { layers, loading, fetchAllLayers, toggleLayer } = useLayerData(projectId);
const { status, detail } = useProcessingStatus(projectId);
const { editState, startEditing, moveVertex, saveEdit, cancelEdit } = usePolygonEdit(mapRef, handleSaveGeometry);
const { navigateToWarning } = useWarningNavigation(mapRef, layers, setActiveWarning);
const { exportProject } = useExport(projectId);
```

### 17.2 Data Flow

```text
API → useLayerData hook → layers state → MapView (renders layers)
                                        → LeftPanel (shows counts, toggles)

User click on map → selectedFeature state → RightPanel (shows attributes)
                                           → find related warnings
                                           → find review score

User clicks warning → navigateToWarning → map flies to location
                                         → warning highlight updates

User edits polygon → usePolygonEdit hook → EditVertices (draggable markers)
                                          → API update → re-fetch layers

User approves/rejects → API call → re-fetch layers → map re-renders
```

---

## 18. API Integration Layer

```typescript
// src/api/client.ts

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    return response.json();
  }

  // --- Layers ---
  getLayer(projectId: string, layerName: string): Promise<GeoJSON.FeatureCollection> {
    return this.request(`/api/projects/${projectId}/layers/${layerName}`);
  }

  // --- Warnings ---
  getWarnings(projectId: string): Promise<Warning[]> {
    return this.request(`/api/projects/${projectId}/warnings`);
  }

  // --- Scores ---
  getScores(projectId: string): Promise<ReviewScore[]> {
    return this.request(`/api/projects/${projectId}/scores`);
  }

  // --- Changes ---
  getChanges(projectId: string): Promise<ChangeIndicator[]> {
    return this.request(`/api/projects/${projectId}/changes`);
  }

  // --- Processing ---
  getProcessingStatus(projectId: string): Promise<ProcessingStatusResponse> {
    return this.request(`/api/projects/${projectId}/process/status`);
  }

  startProcessing(projectId: string, config?: ProcessingConfig): Promise<{ status: string }> {
    return this.request(`/api/projects/${projectId}/process`, {
      method: 'POST',
      body: JSON.stringify(config || {}),
    });
  }

  // --- Features ---
  updateFeature(projectId: string, featureId: string, update: FeatureUpdate): Promise<any> {
    return this.request(`/api/projects/${projectId}/features/${featureId}`, {
      method: 'PUT',
      body: JSON.stringify(update),
    });
  }

  approveFeature(projectId: string, featureId: string, reason?: string): Promise<any> {
    return this.request(`/api/projects/${projectId}/features/${featureId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ action: 'approve', reason }),
    });
  }

  rejectFeature(projectId: string, featureId: string, reason?: string): Promise<any> {
    return this.request(`/api/projects/${projectId}/features/${featureId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ action: 'reject', reason }),
    });
  }

  revalidate(projectId: string): Promise<any> {
    return this.request(`/api/projects/${projectId}/revalidate`, { method: 'POST' });
  }
}

export const api = new ApiClient();
```

---

## 19. Styling & Design Guidelines

### 19.1 Visual Language

| Element | Style |
|---|---|
| Background | Dark (#0f1117) with subtle card elevation |
| Panels | Semi-transparent dark panels with backdrop blur |
| Text | White primary, gray secondary |
| Accents | Blue (parcels), Orange (buildings), Purple (roads), Green (approved), Red (warnings) |
| Borders | Subtle 1px borders in rgba(255,255,255,0.08) |
| Interactive | Hover states with subtle background change |
| Transitions | 150–250ms ease for all interactive elements |

### 19.2 Map Styling Consistency

Every GeoJSON layer must have:
- A **distinct color** that does not conflict with other layers
- A **semi-transparent fill** so underlying imagery is visible
- A **visible outline** for shape clarity
- A **selected state** (brighter, thicker border) when clicked
- A **hover state** with cursor change

### 19.3 Responsiveness

For the MVP:
- **Do NOT** build mobile responsiveness
- Design for a **minimum 1280 × 720** screen
- The map should consume all available space between the two panels
- Panels have fixed widths (320px left, 360px right)

### 19.4 Accessibility

- All buttons have visible labels (not icon-only)
- Color coding is supplemented by text labels and patterns
- Warning severity uses icons in addition to color
- Sufficient contrast on all text

---

## 20. File Structure

```text
frontend/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
│
├── public/
│   └── favicon.svg
│
├── src/
│   ├── main.tsx                         # Entry point
│   ├── App.tsx                          # Root component, state orchestration
│   ├── vite-env.d.ts
│   │
│   ├── api/
│   │   ├── client.ts                    # API client (fetch wrapper)
│   │   └── review.ts                    # Approve/reject/edit helpers
│   │
│   ├── hooks/
│   │   ├── useLayerData.ts              # Fetch and manage GeoJSON layers
│   │   ├── useProcessingStatus.ts       # Poll processing status
│   │   ├── useWarningNavigation.ts      # Navigate map to warning location
│   │   ├── usePolygonEdit.ts            # Polygon vertex editing state
│   │   └── useExport.ts                 # GeoJSON export download
│   │
│   ├── components/
│   │   ├── Header/
│   │   │   ├── Header.tsx
│   │   │   └── Header.module.css
│   │   │
│   │   ├── LeftPanel/
│   │   │   ├── LeftPanel.tsx
│   │   │   ├── LeftPanel.module.css
│   │   │   ├── LayerToggle.tsx
│   │   │   ├── LayerToggle.module.css
│   │   │   ├── WarningList.tsx
│   │   │   ├── WarningList.module.css
│   │   │   ├── ProjectStatus.tsx
│   │   │   ├── ProjectStatus.module.css
│   │   │   ├── ReviewQueue.tsx          # Stretch
│   │   │   └── ReviewQueue.module.css
│   │   │
│   │   ├── MapView/
│   │   │   ├── MapView.tsx
│   │   │   ├── MapView.module.css
│   │   │   ├── EditVertices.tsx
│   │   │   ├── EditVertices.module.css
│   │   │   └── EditingToolbar.tsx
│   │   │
│   │   ├── RightPanel/
│   │   │   ├── RightPanel.tsx
│   │   │   ├── RightPanel.module.css
│   │   │   ├── FeatureInspector.tsx
│   │   │   ├── FeatureInspector.module.css
│   │   │   ├── ConfidenceBadge.tsx
│   │   │   ├── ConfidenceBadge.module.css
│   │   │   ├── WarningDetails.tsx
│   │   │   ├── ReviewActions.tsx
│   │   │   └── ReviewActions.module.css
│   │   │
│   │   └── Upload/
│   │       ├── UploadPanel.tsx
│   │       └── UploadPanel.module.css
│   │
│   ├── types/
│   │   ├── layers.ts                    # Layer state types
│   │   ├── features.ts                  # GeoJSON feature types
│   │   ├── warnings.ts                  # Warning types
│   │   └── api.ts                       # API response types
│   │
│   └── styles/
│       ├── tokens.css                   # Design tokens (colors, spacing)
│       └── global.css                   # Global styles, resets
```

---

## 21. Day-by-Day Frontend Schedule

| Day | Frontend Tasks | Deliverable |
|---:|---|---|
| **2** | Project setup, design tokens, global styles, MapLibre basic map, orthomosaic display, panel layout skeleton | Map visible with base layer, three-panel layout |
| **3** | Layer toggles, GeoJSON layer rendering (parcels, buildings, roads), feature counts, API client | All layers visible on map, toggles working |
| **4** | Click-to-select features, right panel inspector, confidence badge, attribute table | Click a building → see its details |
| **5** | Warning list, warning navigation (click → zoom), warning highlights on map | Click a warning → fly to location |
| **6** | Polygon editing (vertex markers, drag), approve/reject buttons, export button, save/revalidate flow | Full review workflow: select → edit → approve → export |
| **7** | Stretch: priority colors on parcels, review queue, change detection overlay, NDVI toggle | Color-coded priority, sorted review queue |
| **8** | Feature freeze, visual polish, test all interactions, screenshot/record demo | Clean demo-ready UI |

---

## 22. Acceptance Criteria

### Core (must pass for demo)

- [ ] Map loads and displays the orthomosaic raster layer
- [ ] Parcel, building, and road GeoJSON layers render correctly on the map
- [ ] Layer toggles show/hide each layer
- [ ] Feature counts are displayed and accurate
- [ ] Clicking a building shows its ID, confidence, source, and review status
- [ ] Clicking a parcel shows its attributes and any associated warnings
- [ ] Warning list is populated and sorted by severity
- [ ] Clicking a warning in the list zooms the map to the affected location
- [ ] Affected features are visually highlighted when a warning is selected
- [ ] A parcel polygon can be edited (vertices dragged) and saved
- [ ] Approve/Reject buttons update the feature status
- [ ] After edit → re-validation → warnings update
- [ ] Export button downloads a valid GeoJSON file
- [ ] The UI displays a disclaimer: "Preliminary — requires surveyor verification"
- [ ] No unexplained blank screens, infinite loading states, or crashes

### Stretch (nice to have)

- [ ] Parcels are color-coded by review priority (Red/Amber/Green)
- [ ] Review queue lists parcels sorted by score
- [ ] Change indicators appear on the map when prior data exists
- [ ] NDVI/LST layer toggles on/off with a clear "planning only" label
- [ ] Processing status indicator shows pipeline progress

### Performance

- [ ] Map renders smoothly with 200+ features
- [ ] Layer toggle response time < 100ms
- [ ] API calls complete within 2 seconds
- [ ] No visible jank during polygon editing
