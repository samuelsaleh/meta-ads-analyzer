#!/usr/bin/env python3
"""
Script to redo analysis on existing CSV data with Claude 4
"""

import csv
import json
from pathlib import Path
from src.analyzer import AdsAnalyzer
from src.report import ReportGenerator

def csv_to_extraction_result(csv_path: str) -> dict:
    """Convert CSV data to extraction result format"""
    ads = []
    brand = None
    market = "ALL"
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not brand:
                brand = row.get('Brand', 'Unknown')
            
            # Extract ad data
            ad = {
                "id": len(ads) + 1,
                "primary_text": row.get('Primary Text', row.get('text', '')),
                "headline": row.get('Headline', ''),
                "cta": row.get('CTA', ''),
                "format": row.get('Format', 'Not specified'),
                "first_seen": row.get('Start Date', ''),
                "library_id": row.get('Library ID', ''),
                "impressions": row.get('Impressions', ''),
                "platforms": row.get('Platforms', '').split(', ') if row.get('Platforms') else []
            }
            ads.append(ad)
    
    return {
        "brand": brand or "Unknown",
        "market": market,
        "platform": "Meta",
        "ads": ads
    }


def main():
    # Path to the CSV file
    csv_path = Path("data/reports/kimaï_detailed_20260114_162705.csv")
    
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        return
    
    print(f"Reading CSV data from {csv_path}...")
    extraction_result = csv_to_extraction_result(str(csv_path))
    
    print(f"Found {len(extraction_result['ads'])} ads for {extraction_result['brand']}")
    
    # Initialize analyzer and report generator
    analyzer = AdsAnalyzer()
    report_generator = ReportGenerator()
    
    # Step 1: Analyze ads with Claude 4
    print("\n" + "="*50)
    print("STEP 1: Analyzing ads with Claude 4...")
    print("="*50)
    analyzed_result = analyzer.analyze_batch(extraction_result)
    
    # Step 2: Generate strategic insights and narratives
    print("\n" + "="*50)
    print("STEP 2: Generating strategic insights and narratives...")
    print("="*50)
    analyzed_result["insights"] = analyzer.generate_insights(analyzed_result)
    
    # Step 3: Generate HTML report
    print("\n" + "="*50)
    print("STEP 3: Generating HTML report...")
    print("="*50)
    report_path = report_generator.generate(analyzed_result)
    
    # Step 4: Generate JSON export
    json_path = report_generator.generate_json_export(analyzed_result)
    
    # Step 5: Export updated CSV
    print("\n" + "="*50)
    print("STEP 4: Exporting updated CSV...")
    print("="*50)
    csv_output_path = analyzer.export_csv(analyzed_result)
    
    print("\n" + "="*50)
    print("ANALYSIS COMPLETE!")
    print("="*50)
    print(f"✓ HTML Report: {report_path}")
    print(f"✓ JSON Export: {json_path}")
    print(f"✓ CSV Export: {csv_output_path}")
    print("\nOpen the HTML report to see the enhanced strategic interpretations!")


if __name__ == "__main__":
    main()
