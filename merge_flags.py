#!/usr/bin/env python3
"""
Merge script for combining ./public/flags and ./out directories into merged_new_flags
This script creates a unified flag structure with ISO codes and comprehensive metadata
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional

# ISO 3166-1 Alpha-2 to country name mapping (partial - for existing countries in public/flags)
COUNTRY_NAME_MAP = {
    'BR': 'brazil',
    'CA': 'canada',
    'GB': 'england',  # Note: England is part of GB
    'DE': 'germany',
    'ID': 'indonesia',
    'MH': 'marshall-islands',
    'MX': 'mexico',
    'RU': 'russia',
    'KR': 'south-korea',
    'US': 'usa'
}

# Reverse mapping: country name to ISO code
NAME_TO_ISO = {v: k for k, v in COUNTRY_NAME_MAP.items()}

class FlagMerger:
    def __init__(self, public_dir='./public/flags', out_dir='./out', merged_dir='./merged_new_flags'):
        self.public_dir = Path(public_dir)
        self.out_dir = Path(out_dir)
        self.merged_dir = Path(merged_dir)
        self.stats = {
            'from_public': 0,
            'from_out': 0,
            'merged': 0,
            'conflicts': 0
        }

    def create_merged_structure(self):
        """Create the merged directory structure"""
        if self.merged_dir.exists():
            print(f"Warning: {self.merged_dir} already exists. Removing...")
            shutil.rmtree(self.merged_dir)
        self.merged_dir.mkdir(parents=True, exist_ok=True)

    def normalize_region_name(self, name: str) -> str:
        """Normalize region names to lowercase with hyphens"""
        return name.lower().replace('_', '-').replace(' ', '-')

    def get_region_name_from_iso(self, iso_code: str) -> str:
        """Extract region name from ISO code (e.g., US-CA -> california)"""
        # This is a simplified version - in production you'd want a full ISO mapping
        parts = iso_code.split('-')
        if len(parts) == 2:
            return parts[1].lower()
        return iso_code.lower()

    def process_public_flags(self) -> Dict:
        """Process flags from ./public/flags directory"""
        print("\n=== Processing ./public/flags directory ===")
        flags_data = {}

        for country_dir in self.public_dir.iterdir():
            if not country_dir.is_dir():
                continue

            country_name = country_dir.name
            if country_name in ['much-flags.zip', 'usa.rar']:
                continue

            print(f"Processing country: {country_name}")
            iso_country = NAME_TO_ISO.get(country_name, country_name.upper())

            for flag_file in country_dir.glob('*.svg'):
                region_name = flag_file.stem
                region_normalized = self.normalize_region_name(region_name)

                # Create ISO code
                iso_code = f"{iso_country}-{region_name[:2].upper()}"

                # Store flag data
                key = (iso_country, region_normalized)
                flags_data[key] = {
                    'iso_code': iso_code,
                    'country_iso': iso_country,
                    'country_name': country_name,
                    'region_name': region_name,
                    'region_normalized': region_normalized,
                    'flag_svg_path': str(flag_file),
                    'coat_svg_path': None,
                    'source': 'public'
                }
                self.stats['from_public'] += 1

        print(f"Total flags from public: {self.stats['from_public']}")
        return flags_data

    def process_out_flags(self, existing_flags: Dict) -> Dict:
        """Process flags from ./out directory and merge with existing"""
        print("\n=== Processing ./out directory ===")

        for country_dir in self.out_dir.iterdir():
            if not country_dir.is_dir():
                continue

            iso_country = country_dir.name
            print(f"Processing country ISO: {iso_country}")

            for region_dir in country_dir.iterdir():
                if not region_dir.is_dir():
                    continue

                iso_code = region_dir.name
                region_normalized = self.normalize_region_name(iso_code)

                # Read manifest if exists
                manifest_path = region_dir / 'manifest.json'
                manifest = {}
                if manifest_path.exists():
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)

                # Check for flag and coat files
                flag_svg = region_dir / 'flag.svg'
                coat_svg = region_dir / 'coat.svg'

                key = (iso_country, region_normalized)

                # Merge or create new entry
                if key in existing_flags:
                    # Merge - prefer out/ data for ISO codes
                    existing_flags[key]['iso_code'] = iso_code
                    if coat_svg.exists():
                        existing_flags[key]['coat_svg_path'] = str(coat_svg)
                    existing_flags[key]['manifest'] = manifest
                    existing_flags[key]['source'] = 'merged'
                    self.stats['merged'] += 1
                else:
                    # New entry from out/
                    existing_flags[key] = {
                        'iso_code': iso_code,
                        'country_iso': iso_country,
                        'country_name': COUNTRY_NAME_MAP.get(iso_country, iso_country),
                        'region_name': region_normalized,
                        'region_normalized': region_normalized,
                        'flag_svg_path': str(flag_svg) if flag_svg.exists() else None,
                        'coat_svg_path': str(coat_svg) if coat_svg.exists() else None,
                        'manifest': manifest,
                        'source': 'out'
                    }
                    self.stats['from_out'] += 1

        print(f"Total new flags from out: {self.stats['from_out']}")
        print(f"Total merged entries: {self.stats['merged']}")
        return existing_flags

    def write_merged_data(self, flags_data: Dict):
        """Write merged data to new directory structure"""
        print("\n=== Writing merged data ===")

        for (iso_country, region_normalized), data in flags_data.items():
            # Create directory structure: merged_new_flags/US/US-CA/
            country_dir = self.merged_dir / iso_country
            region_dir = country_dir / data['iso_code']
            region_dir.mkdir(parents=True, exist_ok=True)

            # Copy flag SVG if exists
            if data['flag_svg_path'] and Path(data['flag_svg_path']).exists():
                shutil.copy2(data['flag_svg_path'], region_dir / 'flag.svg')

            # Copy coat SVG if exists
            if data['coat_svg_path'] and Path(data['coat_svg_path']).exists():
                shutil.copy2(data['coat_svg_path'], region_dir / 'coat.svg')

            # Create comprehensive manifest
            manifest = {
                'iso_code': data['iso_code'],
                'country_iso': iso_country,
                'country_name': data['country_name'],
                'region_name': data['region_name'],
                'region_normalized': region_normalized,
                'flag': {
                    'svg': f"{iso_country}/{data['iso_code']}/flag.svg" if data['flag_svg_path'] else None,
                    'source': data.get('manifest', {}).get('flag', {}).get('source_filename')
                },
                'coat': {
                    'svg': f"{iso_country}/{data['iso_code']}/coat.svg" if data['coat_svg_path'] else None,
                    'source': data.get('manifest', {}).get('coat', {}).get('source_filename')
                },
                'data_source': data['source']
            }

            # Write manifest
            with open(region_dir / 'manifest.json', 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)

        print(f"Wrote {len(flags_data)} regions to {self.merged_dir}")

    def generate_summary(self, flags_data: Dict):
        """Generate a summary JSON file"""
        summary = {
            'total_regions': len(flags_data),
            'statistics': self.stats,
            'countries': {}
        }

        for (iso_country, _), data in flags_data.items():
            if iso_country not in summary['countries']:
                summary['countries'][iso_country] = {
                    'name': data['country_name'],
                    'region_count': 0,
                    'has_flags': 0,
                    'has_coats': 0
                }

            summary['countries'][iso_country]['region_count'] += 1
            if data['flag_svg_path']:
                summary['countries'][iso_country]['has_flags'] += 1
            if data['coat_svg_path']:
                summary['countries'][iso_country]['has_coats'] += 1

        summary_path = self.merged_dir / 'MERGE_SUMMARY.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\nSummary written to {summary_path}")
        print(json.dumps(summary['statistics'], indent=2))

    def run(self):
        """Run the complete merge process"""
        print("Starting flag merge process...")

        self.create_merged_structure()
        flags_data = self.process_public_flags()
        flags_data = self.process_out_flags(flags_data)
        self.write_merged_data(flags_data)
        self.generate_summary(flags_data)

        print("\n=== Merge Complete ===")
        print(f"Total regions: {len(flags_data)}")
        print(f"Output directory: {self.merged_dir.absolute()}")

if __name__ == '__main__':
    merger = FlagMerger()
    merger.run()
