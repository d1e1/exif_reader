#!/usr/bin/env python3


import os
import sys
import zipfile
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime


def get_exif_data(image_path):
    """Extract EXIF data from image file."""
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if exif_data is None:
                return None
            return exif_data
    except Exception as e:
        print(f"Error reading EXIF from {image_path}: {e}")
        return None


def get_gps_data(exif_data):
    """Extract GPS data from EXIF data."""
    if exif_data is None:
        return None
    
    gps_info = {}
    for tag_id, value in exif_data.items():
        tag = TAGS.get(tag_id, tag_id)
        if tag == 'GPSInfo':
            for gps_tag_id, gps_value in value.items():
                gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                gps_info[gps_tag] = gps_value
    
    return gps_info if gps_info else None


def convert_to_degrees(value):
    """Convert GPS coordinate to decimal degrees."""
    d, m, s = value
    return float(d) + float(m) / 60.0 + float(s) / 3600.0


def get_lat_lon(gps_data):
    """Extract latitude and longitude from GPS data."""
    if gps_data is None:
        return None, None
    
    try:
        lat_data = gps_data.get('GPSLatitude')
        lon_data = gps_data.get('GPSLongitude')
        lat_ref = gps_data.get('GPSLatitudeRef', 'N')
        lon_ref = gps_data.get('GPSLongitudeRef', 'E')
        
        if lat_data is None or lon_data is None:
            return None, None
        
        latitude = convert_to_degrees(lat_data)
        longitude = convert_to_degrees(lon_data)
        
        # Apply reference (N/S, E/W)
        if lat_ref == 'S':
            latitude = -latitude
        if lon_ref == 'W':
            longitude = -longitude
        
        return latitude, longitude
    except Exception as e:
        print(f"Error converting GPS coordinates: {e}")
        return None, None


def get_image_info(image_path):
    """Get GPS coordinates and metadata from image."""
    exif_data = get_exif_data(image_path)
    if exif_data is None:
        return None
    
    gps_data = get_gps_data(exif_data)
    lat, lon = get_lat_lon(gps_data)
    
    if lat is None or lon is None:
        return None
    
    # Get image date/time if available
    date_taken = None
    try:
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'DateTime' or tag == 'DateTimeOriginal':
                date_taken = value
                break
    except:
        pass
    
    return {
        'filename': os.path.basename(image_path),
        'path': str(image_path),
        'latitude': lat,
        'longitude': lon,
        'date_taken': date_taken
    }


def create_kml(photo_data_list, output_path):
    """Create KML file from photo GPS data."""
    # Create root element
    kml = Element('kml')
    kml.set('xmlns', 'http://www.opengis.net/kml/2.2')
    
    document = SubElement(kml, 'Document')
    
    # Add document name
    name = SubElement(document, 'name')
    name.text = 'Photo Locations'
    
    # Add description
    description = SubElement(document, 'description')
    description.text = f'GPS locations extracted from {len(photo_data_list)} photos'
    
    # Create a folder for photos
    folder = SubElement(document, 'Folder')
    folder_name = SubElement(folder, 'name')
    folder_name.text = 'Photos'
    
    # Add placemarks for each photo
    for photo_data in photo_data_list:
        placemark = SubElement(folder, 'Placemark')
        
        # Name
        pm_name = SubElement(placemark, 'name')
        pm_name.text = photo_data['filename']
        
        # Description with path to photo
        pm_description = SubElement(placemark, 'description')
        desc_text = f"<![CDATA[<b>{photo_data['filename']}</b><br/>"
        if photo_data['date_taken']:
            desc_text += f"Date: {photo_data['date_taken']}<br/>"
        desc_text += f"Coordinates: {photo_data['latitude']:.6f}, {photo_data['longitude']:.6f}<br/>"
        desc_text += f"Path: {photo_data['path']}<br/>"
        desc_text += f"<a href='file:///{photo_data['path'].replace(os.sep, '/')}'>Open Photo</a>]]>"
        pm_description.text = desc_text
        
        # Point coordinates
        point = SubElement(placemark, 'Point')
        coordinates = SubElement(point, 'coordinates')
        coordinates.text = f"{photo_data['longitude']},{photo_data['latitude']},0"
        
        # Style
        style = SubElement(placemark, 'Style')
        icon_style = SubElement(style, 'IconStyle')
        icon = SubElement(icon_style, 'Icon')
        href = SubElement(icon, 'href')
        href.text = 'http://maps.google.com/mapfiles/kml/shapes/camera.png'
        scale = SubElement(icon_style, 'scale')
        scale.text = '1.2'
    
    # Pretty print XML
    xml_string = tostring(kml, encoding='unicode')
    dom = minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent='  ')
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    return output_path


def create_kmz(kml_path, kmz_path, photo_paths=None):
    """Create KMZ file (zipped KML) with optional photo files."""
    with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as kmz:
        # Add KML file
        kmz.write(kml_path, 'doc.kml')
        
        # Optionally add photos to KMZ (for portability)
        if photo_paths:
            for photo_path in photo_paths:
                if os.path.exists(photo_path):
                    # Store photos in a 'files' folder within the KMZ
                    arcname = os.path.join('files', os.path.basename(photo_path))
                    kmz.write(photo_path, arcname)
    
    return kmz_path


def generate_qc_report(photo_data_list, photos_without_gps, output_path, directory_path):
    """Generate a Quality Control report."""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("PHOTO GPS TO KMZ - QUALITY CONTROL REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Source Directory: {directory_path}")
    report_lines.append("")
    
    # Summary Statistics
    report_lines.append("-" * 80)
    report_lines.append("SUMMARY STATISTICS")
    report_lines.append("-" * 80)
    total_photos = len(photo_data_list) + len(photos_without_gps)
    report_lines.append(f"Total Photos Processed: {total_photos}")
    report_lines.append(f"Photos with GPS Data: {len(photo_data_list)} ({len(photo_data_list)/total_photos*100:.1f}%)")
    report_lines.append(f"Photos without GPS Data: {len(photos_without_gps)} ({len(photos_without_gps)/total_photos*100:.1f}%)")
    report_lines.append("")
    
    if photo_data_list:
        # GPS Coordinate Statistics
        report_lines.append("-" * 80)
        report_lines.append("GPS COORDINATE STATISTICS")
        report_lines.append("-" * 80)
        latitudes = [p['latitude'] for p in photo_data_list]
        longitudes = [p['longitude'] for p in photo_data_list]
        
        report_lines.append(f"Latitude Range:")
        report_lines.append(f"  Minimum: {min(latitudes):.6f}")
        report_lines.append(f"  Maximum: {max(latitudes):.6f}")
        report_lines.append(f"  Average: {sum(latitudes)/len(latitudes):.6f}")
        report_lines.append(f"  Span: {max(latitudes) - min(latitudes):.6f} degrees")
        report_lines.append("")
        
        report_lines.append(f"Longitude Range:")
        report_lines.append(f"  Minimum: {min(longitudes):.6f}")
        report_lines.append(f"  Maximum: {max(longitudes):.6f}")
        report_lines.append(f"  Average: {sum(longitudes)/len(longitudes):.6f}")
        report_lines.append(f"  Span: {max(longitudes) - min(longitudes):.6f} degrees")
        report_lines.append("")
        
        # Calculate approximate coverage area (rough estimate)
        lat_span_km = (max(latitudes) - min(latitudes)) * 111.0  # ~111 km per degree
        lon_span_km = (max(longitudes) - min(longitudes)) * 111.0 * abs(sum(latitudes)/len(latitudes)) / 90.0
        coverage_area_km2 = lat_span_km * lon_span_km
        report_lines.append(f"Approximate Coverage Area: {coverage_area_km2:.2f} km²")
        report_lines.append(f"  (Latitude span: {lat_span_km:.2f} km, Longitude span: {lon_span_km:.2f} km)")
        report_lines.append("")
        
        # Date Statistics
        dates = [p['date_taken'] for p in photo_data_list if p['date_taken']]
        if dates:
            report_lines.append("-" * 80)
            report_lines.append("DATE/TIME STATISTICS")
            report_lines.append("-" * 80)
            report_lines.append(f"Photos with Date/Time: {len(dates)} ({len(dates)/len(photo_data_list)*100:.1f}%)")
            try:
                # Parse dates and find range
                parsed_dates = []
                for date_str in dates:
                    try:
                        # Try common EXIF date formats
                        for fmt in ['%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S']:
                            try:
                                parsed_dates.append(datetime.strptime(date_str, fmt))
                                break
                            except:
                                continue
                    except:
                        pass
                
                if parsed_dates:
                    min_date = min(parsed_dates)
                    max_date = max(parsed_dates)
                    report_lines.append(f"Date Range:")
                    report_lines.append(f"  Earliest: {min_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    report_lines.append(f"  Latest: {max_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    duration = max_date - min_date
                    total_seconds = duration.total_seconds()
                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    seconds = int(total_seconds % 60)
                    if duration.days > 0:
                        report_lines.append(f"  Duration: {duration.days} days, {hours} hours, {minutes} minutes")
                    elif hours > 0:
                        report_lines.append(f"  Duration: {hours} hours, {minutes} minutes, {seconds} seconds")
                    elif minutes > 0:
                        report_lines.append(f"  Duration: {minutes} minutes, {seconds} seconds")
                    else:
                        report_lines.append(f"  Duration: {seconds} seconds")
            except Exception as e:
                report_lines.append(f"  (Could not parse date range: {e})")
            report_lines.append("")
        
        # Coordinate Quality Checks
        report_lines.append("-" * 80)
        report_lines.append("QUALITY CHECKS")
        report_lines.append("-" * 80)
        
        # Check for duplicate coordinates
        coord_pairs = [(p['latitude'], p['longitude']) for p in photo_data_list]
        unique_coords = len(set(coord_pairs))
        duplicates = len(coord_pairs) - unique_coords
        if duplicates > 0:
            report_lines.append(f"⚠ WARNING: {duplicates} photos have duplicate coordinates")
        else:
            report_lines.append("✓ All photos have unique coordinates")
        
        # Check for coordinates that seem invalid (0,0 or extreme values)
        invalid_coords = [p for p in photo_data_list 
                         if abs(p['latitude']) < 0.0001 and abs(p['longitude']) < 0.0001]
        if invalid_coords:
            report_lines.append(f"⚠ WARNING: {len(invalid_coords)} photos have coordinates near (0,0) - may be invalid")
        
        # Check coordinate spread
        if max(latitudes) - min(latitudes) < 0.0001:
            report_lines.append("⚠ WARNING: Very small latitude spread - photos may be clustered")
        if max(longitudes) - min(longitudes) < 0.0001:
            report_lines.append("⚠ WARNING: Very small longitude spread - photos may be clustered")
        
        report_lines.append("")
    
    # Photos without GPS
    if photos_without_gps:
        report_lines.append("-" * 80)
        report_lines.append(f"PHOTOS WITHOUT GPS DATA ({len(photos_without_gps)} files)")
        report_lines.append("-" * 80)
        for photo in sorted(photos_without_gps):
            report_lines.append(f"  - {photo}")
        report_lines.append("")
    
    # File List
    if photo_data_list:
        report_lines.append("-" * 80)
        report_lines.append(f"PHOTOS WITH GPS DATA ({len(photo_data_list)} files)")
        report_lines.append("-" * 80)
        report_lines.append("Filename | Latitude | Longitude | Date Taken")
        report_lines.append("-" * 80)
        for photo in sorted(photo_data_list, key=lambda x: x['filename']):
            date_str = photo['date_taken'] if photo['date_taken'] else 'N/A'
            report_lines.append(f"{photo['filename']:40} | {photo['latitude']:9.6f} | {photo['longitude']:10.6f} | {date_str}")
        report_lines.append("")
    
    report_lines.append("=" * 80)
    report_lines.append("END OF REPORT")
    report_lines.append("=" * 80)
    
    # Write report to file
    report_text = "\n".join(report_lines)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    return output_path


def process_photos(directory_path, output_kmz_path=None, include_photos_in_kmz=False):
    """Process all photos in directory and create KMZ file."""
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"Error: Directory '{directory_path}' does not exist.")
        return False
    
    # Find all image files
    image_extensions = {'.jpg', '.jpeg', '.JPG', '.JPEG', '.png', '.PNG', '.tiff', '.TIFF'}
    image_files = [f for f in directory.iterdir() 
                   if f.is_file() and f.suffix in image_extensions]
    
    if not image_files:
        print(f"No image files found in '{directory_path}'")
        return False
    
    print(f"Found {len(image_files)} image files. Processing...")
    
    # Extract GPS data from photos
    photo_data_list = []
    photos_without_gps = []
    
    for image_file in sorted(image_files):
        print(f"Processing: {image_file.name}...", end=' ')
        photo_info = get_image_info(image_file)
        
        if photo_info:
            photo_data_list.append(photo_info)
            print(f"[OK] GPS: {photo_info['latitude']:.6f}, {photo_info['longitude']:.6f}")
        else:
            photos_without_gps.append(image_file.name)
            print("[SKIP] No GPS data")
    
    if not photo_data_list:
        print("\nError: No photos with GPS data found.")
        return False
    
    print(f"\nSuccessfully extracted GPS data from {len(photo_data_list)} photos")
    if photos_without_gps:
        print(f"Skipped {len(photos_without_gps)} photos without GPS data")
    
    # Create output paths
    if output_kmz_path is None:
        output_kmz_path = directory / 'photo_locations.kmz'
    else:
        output_kmz_path = Path(output_kmz_path)
    
    kml_path = output_kmz_path.with_suffix('.kml')
    qc_report_path = output_kmz_path.with_suffix('.qc_report.txt')
    
    # Create KML file
    print(f"\nCreating KML file: {kml_path}")
    create_kml(photo_data_list, kml_path)
    
    # Create KMZ file
    print(f"Creating KMZ file: {output_kmz_path}")
    photo_paths = [photo_data['path'] for photo_data in photo_data_list] if include_photos_in_kmz else None
    create_kmz(kml_path, output_kmz_path, photo_paths)
    
    # Generate QC Report
    print(f"Generating QC Report: {qc_report_path}")
    generate_qc_report(photo_data_list, photos_without_gps, qc_report_path, str(directory))
    
    # Clean up temporary KML file
    if kml_path.exists():
        os.remove(kml_path)
    
    print(f"\n[SUCCESS] Created KMZ file: {output_kmz_path}")
    print(f"  Contains {len(photo_data_list)} photo locations")
    print(f"  QC Report: {qc_report_path}")
    print(f"  Open in Google Earth to view the locations")
    
    return True


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python create_kmz_from_photos.py <directory> [output_kmz_path] [--include-photos]")
        print("\nArguments:")
        print("  directory          Path to directory containing photos")
        print("  output_kmz_path    Optional: Path for output KMZ file (default: photo_locations.kmz)")
        print("  --include-photos   Optional: Include photos in KMZ file (makes file larger)")
        print("\nExample:")
        print("  python create_kmz_from_photos.py .")
        print("  python create_kmz_from_photos.py ./photos output.kmz --include-photos")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else None
    include_photos = '--include-photos' in sys.argv
    
    success = process_photos(directory_path, output_path, include_photos)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

