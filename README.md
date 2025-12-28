# Photo GPS to KMZ Converter

A Python tool to extract GPS coordinates from photo EXIF data and create a KMZ file for viewing in Google Earth or other mapping applications.

## Features

- Extracts GPS coordinates (latitude/longitude) from photo EXIF data
- Creates a KMZ file with placemarks for each photo location
- Generates a comprehensive Quality Control (QC) report with statistics
- Displays photo paths and metadata in Google Earth
- Handles photos without GPS data gracefully
- Supports JPG, JPEG, PNG, and TIFF formats

## Installation

1. Install Python 3.7 or higher
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Process all photos in the current directory:

```bash
python create_kmz_from_photos.py .
```

### Specify Directory

Process photos in a specific directory:

```bash
python create_kmz_from_photos.py /path/to/photos
```

### Custom Output File

Specify a custom output KMZ file name:

```bash
python create_kmz_from_photos.py . my_photos.kmz
```

### Include Photos in KMZ

Include the actual photo files in the KMZ (makes the file larger but portable):

```bash
python create_kmz_from_photos.py . output.kmz --include-photos
```

## Output

The tool creates two files:

1. **KMZ file** - Can be opened in:
   - Google Earth
   - Google Maps (upload KMZ)
   - Other KML/KMZ compatible mapping applications

   Each placemark includes:
   - Photo filename
   - GPS coordinates
   - Date taken (if available in EXIF)
   - Full file path
   - Link to open the original photo

2. **QC Report** (`.qc_report.txt`) - Contains:
   - Summary statistics (total photos, GPS coverage percentage)
   - GPS coordinate statistics (min/max/average, coverage area)
   - Date/time range analysis
   - Quality checks (duplicate coordinates, invalid data warnings)
   - Complete list of photos with and without GPS data

## Requirements

- Python 3.7+
- Pillow (PIL) library for EXIF extraction

## Notes

- Only photos with GPS data in their EXIF will be included in the KMZ
- Photos without GPS coordinates will be skipped with a notification
- The tool processes images in alphabetical order
- The QC report is automatically generated alongside the KMZ file
- Photos are NOT embedded in the KMZ by default (only paths are included)
