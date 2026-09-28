# SIH26012 India Candidate 01 — Lalpur Geospatial QA Bundle

## 1. Study Area Summary
* **AOI ID:** `SIH26012_INDIA_CANDIDATE_01_LALPUR`
* **Locality:** Lalpur Village, Gujarat, India (LGD Village Code: `511638`)
* **Coordinates (WGS84):** `[72.754522°E, 23.037525°N] to [72.760639°E, 23.043376°N]`
* **Centroid:** `72.757580°E, 23.040450°N`
* **Coordinate Systems:** Native EPSG:3857 (Web Mercator); Working EPSG:4326 & EPSG:3857
* **Raster GSD:** 0.0338 m (~3.38 cm per pixel), 20,137 x 20,886 pixels, 3 bands (RGB)
* **Building Annotations:** 317 verified building footprints (100% overlap with drone raster)
* **Road Network:** 19 village road polygons + 7 OSM road centerlines (including Gujarat SH144)
* **Parcel Polygons:** None available from official self-service sources (blank schema template provided)

## 2. Directory Layout & Artifacts
```text
data/acquisition/SIH26012_INDIA_CANDIDATE_01/
├── README.md                               <-- This master documentation file
├── metadata/
│   ├── data_sources.csv                    <-- Full 18-column asset inventory
│   ├── study_area.yaml                     <-- Formal AOI parameters and bounds
│   ├── raster_metadata.json                <-- Machine-readable ECW header details
│   ├── vector_metadata.json                <-- Feature counts, overlap metrics, and anomalies
│   ├── qa_alignment.md                     <-- Detailed verification report and disposition
│   └── schema-v1.json                      <-- Blueprint JSON schema specification
├── working/
│   ├── sanitized_lalpur_buildings_3857.geojson
│   ├── sanitized_lalpur_buildings_4326.geojson
│   ├── sanitized_lalpur_road_polygons_3857.geojson
│   ├── sanitized_lalpur_road_polygons_4326.geojson
│   ├── osm_roads_lalpur_3857.geojson
│   ├── osm_roads_lalpur_4326.geojson
│   ├── blank_parcel_template_3857.geojson
│   └── blank_parcel_template_4326.geojson
├── qgis/
│   ├── SIH26012_INDIA_CANDIDATE_01.qgs     <-- Native QGIS project (opens with working layers)
│   ├── SIH26012_INDIA_CANDIDATE_01.qgz     <-- Zipped QGIS project
│   ├── qa_full_aoi_overlay.png             <-- Overview QA map (buildings, roads, raster extent)
│   ├── qa_closeup_alignment.png            <-- High-resolution close-up of village core
│   └── qa_village_separation_check.png     <-- Visual proof of 204 km separation of Suragpur
└── source/                                 <-- Read-only local inspection cache (untracked in Git)
```

## 3. Data Authorization & Governance Notice
* **Candidate Drone Orthomosaic & Shapefiles:** Sourced from public GitHub repository [Project Vaayu](https://github.com/Kabeer2004/ProjectVaayu) (SIH PS 1705). The repository has **no explicit open-source license**. The underlying data stems from government hackathon allocations under the SVAMITVA / Gram Manchitra program.
* **Terms Status:** `unknown / permission not established`. Under Blueprint §24.2, this data is restricted to **local technical inspection only**. It must **not** be committed to public Git, redistributed, or used to train public production models without written government authorization.
* **Sanitization:** All personally identifiable and ownership-related attributes (`owner_name`, `name`, `property_id`, `property_card_no`) have been permanently removed from all derivative files in `working/`.
* **OpenStreetMap Data:** Road centerlines extracted via Overpass API on 2026-09-28 are distributed under the Open Data Commons Open Database License (ODbL 1.0). Attribution: © OpenStreetMap contributors.

## 4. Current Go / No-Go Status: CONDITIONAL
* **Technical Fit:** Excellent. Coordinate systems, pixel dimensions, GSD, and spatial overlap between footprints and raster are validated at 100%.
* **Legal Fit:** Unresolved permissions on candidate imagery; official parcel polygon layer is absent across all public portals.
* **Actionable Next Steps:** See Section 5 of `metadata/qa_alignment.md`.
