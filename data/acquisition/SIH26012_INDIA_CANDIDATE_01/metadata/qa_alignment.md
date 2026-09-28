# SIH26012 Geospatial QA & Alignment Report: Candidate 01 (Lalpur)

**Author:** Geospatial Data Acquisition & QA Engineer, SIH26012  
**Date:** 2026-09-28  
**AOI Identifier:** `SIH26012_INDIA_CANDIDATE_01_LALPUR`  
**Locality:** Lalpur Village, Gujarat, India (LGD Code: 511638)  
**Overall Disposition:** **CONDITIONAL** (Technical overlap verified 100%; legal reuse terms unestablished; parcel polygon data absent)

---

## 1. Executive Summary & Verification Metrics

| Verification Check | Target / Requirement | Local Revalidation Result | Status |
|---|---|---|---|
| **Raster Embedded CRS** | EPSG:3857 | EPSG:3857 (Embedded in ECW v2 header, confirmed via binary parse) | **PASS** |
| **Raster Dimensions & GSD** | Sub-meter drone orthophoto | 20,137 x 20,886 px, 3 bands (RGB), GSD = 0.0338 m (~3.38 cm/px) | **PASS** |
| **Raster Spatial Extent (3857)** | Must encompass Lalpur abadi | `[8098996.38, 2636558.41, 8099677.16, 2637264.51]` | **PASS** |
| **Lalpur Building Footprint Overlap** | 100% inside raster bounds | **317 / 317 features (100.0%)** intersect candidate raster footprint | **PASS** |
| **Lalpur Road Polygon Overlap** | 100% inside raster bounds | **19 / 19 features (100.0%)** intersect candidate raster footprint | **PASS** |
| **Source Village Split Anomaly** | 550 records total in source | Revalidated: **317 Lalpur** vs. **233 Suragpur** (204 km offset) | **RESOLVED** (Suragpur isolated & excluded) |
| **OSM Road Network Alignment** | Dated extract, valid topology | 7 ways (including State Highway 144) extracted via Overpass on 2026-09-28 | **PASS** |
| **Cadastral Parcel Polygons** | Official parcel layer | **NONE FOUND** in self-service official channels | **FAIL / BLOCKED** (Documented honestly) |
| **Privacy / Ownership Sanitization** | Zero PII or ownership fields | Removed `owner_name`, `name`, `property_id`, `property_card_no` | **PASS** |
| **ECW GDAL Driver Availability** | Standard open-source GDAL | Fails on stock GDAL (requires proprietary Hexagon ERDAS SDK) | **BLOCKER (Guardrail 8)** |
| **Data Reuse Permissions** | Explicit redistributable license | Unknown / Permission not established in Project Vaayu repository | **CONDITIONAL** |

---

## 2. In-Depth Technical Verification

### 2.1 Raster Header Analysis (`ortho_lalpur(511638)_3857.ecw`)
* **Size:** 22,984,504 bytes (~21.92 MB).
* **SHA-256:** `1e6cc91b5bfa12b3f5c167a8713c5a89f6b4a045c71dd6230eaaeb704efa48d6`.
* **Driver Behavior:** `rasterio.open()` returns `RasterioIOError: not recognized as being in a supported file format`. This occurs because standard open-source GDAL/rasterio wheels are intentionally compiled without the proprietary Hexagon Geospatial ECW SDK due to licensing restrictions. In accordance with Hard Guardrail 8, no unlicensed or pirated SDK was fetched.
* **Header Byte Verification:** A direct binary parsing of the NCS ECW v2 header (offsets 0x00 to 0x40) revealed the exact internal metadata:
  - Width: **20,137** pixels.
  - Height: **20,886** pixels.
  - Number of Bands: **3** (RGB).
  - Cell Increment X: **+0.0338072687 m** (~3.38 cm ground sample distance).
  - Cell Increment Y: **-0.0338072687 m** (standard top-down raster).
  - Origin X: **8,098,996.378 m** (EPSG:3857).
  - Origin Y: **2,637,264.506 m** (EPSG:3857).
  - Projection / Datum strings: `EPSG:3857` embedded explicitly at offsets 0x39 and 0x49.

### 2.2 Vector Anomaly Investigation (`Gujarat_Build_Up_Area_Type.shp`)
* **The Two-Village Discovery:**
  The source shapefile from Project Vaayu contains 550 total records. Our inspection verified that this file was created by an un-curated export from a parent ArcSDE database (`grammancgitra.sde`). It combines two completely distinct administrative entities into one file:
  1. **Lalpur (LGD Code 511638):** 317 building polygons. Extent in WGS84: `[72.755404°E, 23.039135°N] to [72.758612°E, 23.042565°N]`. Located near Kheda/Ahmedabad district border.
  2. **Suragpur (LGD Code 515578):** 233 building polygons. Extent in WGS84: `[71.307358°E, 21.684341°N] to [71.315937°E, 21.698704°N]`. Located in Amreli district.
* **Geographic Offset:** The two clusters are separated by approximately **204 kilometers**.
* **Overlap Check:** 
  - **Lalpur:** 317 / 317 (100%) lie directly within the `ortho_lalpur(511638)_3857.ecw` bounds.
  - **Suragpur:** 0 / 233 (0%) overlap the raster.
* **Resolution:** Suragpur features were permanently filtered out and excluded from the working bundle to prevent geographic pollution.

### 2.3 Road Layer Corroboration
* **Village Roads Shapefile:** 19 features in Lalpur (49 total in source; 30 Suragpur features excluded). These represent narrow internal village passages (widths ranging from 2.0 m to 6.5 m).
* **OpenStreetMap Live Query (2026-09-28):** Overpass API extraction returned 7 road centerlines:
  - Way `653919189`: State Highway 144 (`ref: SH144`), a primary asphalt arterial running along the western periphery of the Lalpur settlement.
  - Way `668421750`: Tertiary road connecting adjacent rural hamlets.
  - Ways `1306611448`, `1306611451`, `1306611452`, `1306611453`: Residential village paths.
  - Alignment between the OSM highway network and the village road polygons confirms general geographic agreement, though OSM lines follow centerlines while the shapefile represents road corridor polygons.

### 2.4 Cadastral Parcel Investigation (The Ground Truth Gap)
* Tested `https://sih.gov.in/dataset/Data_set.pdf`: Status 200 (Index only).
* Tested `https://svamitva.nic.in/DownloadPDF/TifFile/Gujarat_5.zip`: Returns **HTTP 404 Not Found**.
* Tested `https://revenuedepartment.gujarat.gov.in/maps`: Returns administrative district/taluka PDF maps only; no parcel GIS vectors.
* Tested Bhuvan viewer (`https://bhuvan-app1.nrsc.gov.in/bhuvan2d/bhuvan/bhuvan2d.php`): Visual portal only; strict disclaimer prohibiting measurement or legal cadastral use.
* **Conclusion:** **No self-service official Indian cadastral parcel polygon vector exists for this study area.**
* **Action:** Created `working/blank_parcel_template_3857.geojson` conforming to the Blueprint schema. Under Hard Guardrail 6, building rooftops were **never** converted to parcel boundaries.

---

## 3. Privacy and Data Governance Compliance

1. **Stripped Sensitive Fields:** The source shapefiles included schema fields for `owner_name`, `name`, `property_i` (property_id), and `property_c` (property_card_no). While individual values were largely unpopulated in this sample, these fields were completely stripped from the GeoJSON working assets.
2. **Untracked Local Source:** The raw ECW and source shapefiles are placed in local inspection directories and strictly ignored by Git.
3. **Retained Attributes:** Only anonymous physical attributes (`building_id`, `area_sqm`, `roof_type`, `no_floors`, `lgd_village_code`) were retained.

---

## 4. Final Recommendation & Go/No-Go Disposition

### Disposition: **CONDITIONAL**
* **Technical Feasibility (GO):** The Lalpur study area is technically viable for a proof-of-concept AI cadastral review demo. The raster GSD (3.38 cm), embedded CRS (EPSG:3857), building footprints (317 features), and OSM roads align consistently.
* **Legal & Cadastral Reality (NO-GO for Autonomous Cadastre):**
  1. The Project Vaayu raster and shapefiles lack an explicit open license and stem from competition-specific government data.
  2. No ground-truth cadastral parcel boundaries exist.
* **Recommended Demo Architecture:**
  Position the prototype honestly as an **"AI-Assisted Rural Built-Up & Road Review Tool"**. Demonstrate:
  1. Automated detection of building footprints and comparison against unverified visual annotations.
  2. Conflict detection: buildings encroaching on road corridors (e.g. B-012 encroaching on SH144 right-of-way).
  3. Interactive human review workflow where a surveyor digitizes or approves preliminary boundaries using the provided blank parcel template.
