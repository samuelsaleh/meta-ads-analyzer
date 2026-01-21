"""
app.py
Meta Ads Analyzer - FastAPI Application

Exposes the Meta Ads Analyzer as a web API with endpoints for:
- Brand analysis (extraction + AI analysis + report generation)
- Report listing and download
- Health check
"""

import os
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from src.extractor import MetaAdsExtractor
from src.analyzer import AdsAnalyzer
from src.report import ReportGenerator

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Meta Ads Analyzer",
    description="Analyze Meta Ad Library ads for any brand",
    version="1.0.0"
)

# Paths
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
REPORTS_DIR = BASE_DIR / "data" / "reports"

# Ensure directories exist
STATIC_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files (for future CSS/JS)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Initialize modules ONCE (not per request)
extractor = MetaAdsExtractor()
analyzer = AdsAnalyzer()
report_generator = ReportGenerator()


# =============================================================================
# Routes
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Landing page with analysis form"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api")
async def api_info():
    """API info endpoint"""
    return {
        "name": "Meta Ads Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "POST /analyze",
            "health": "GET /health",
            "reports": "GET /reports",
            "report": "GET /reports/{filename}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/analyze")
async def analyze_brand(
    request: Request,
    brand: str = Form(...),
    country: str = Form(default="ALL"),
    max_ads: int = Form(default=10)
):
    """
    Analyze a brand's Meta ads
    
    Pipeline: Extract → Analyze → Generate Report → Return HTML
    
    Parameters:
    - brand (required): Brand name to search
    - country (optional, default "ALL"): Country code (ALL, FR, US, GB, DE)
    - max_ads (optional, default 10): Maximum ads to extract
    """
    try:
        # Step 1: Extract ads (async)
        print(f"[1/4] Extracting ads for '{brand}' (country={country}, max={max_ads})...")
        extraction_result = await extractor.extract(brand, country, max_ads)
        
        # Check for extraction errors
        if "error" in extraction_result:
            error_msg = f"Failed to extract ads for '{brand}': {extraction_result.get('error')}"
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": error_msg},
                status_code=400
            )
        
        # Check if any ads were found
        ads_count = len(extraction_result.get("ads", []))
        if ads_count == 0:
            error_msg = f"No active ads found for '{brand}' in {country}. Try a different brand or country."
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "error": error_msg},
                status_code=404
            )
        
        print(f"[2/4] Analyzing {ads_count} ads...")
        
        # Step 2: Analyze ads (sync)
        analyzed_result = analyzer.analyze_batch(extraction_result)
        
        # Step 3: Generate insights (sync)
        print("[3/4] Generating insights...")
        analyzed_result["insights"] = analyzer.generate_insights(analyzed_result)
        
        # Step 4: Generate HTML report (sync)
        print("[4/4] Generating report...")
        report_path = report_generator.generate(analyzed_result)
        
        # Also generate JSON export
        report_generator.generate_json_export(analyzed_result)
        
        print(f"✓ Report generated: {report_path}")
        
        # Return the HTML report file
        return FileResponse(
            path=report_path,
            media_type="text/html",
            filename=f"{brand.lower().replace(' ', '_')}_report.html"
        )
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        error_msg = f"An unexpected error occurred: {str(e)}"
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": error_msg},
            status_code=500
        )


@app.get("/reports")
async def list_reports():
    """List all generated reports"""
    reports = []
    
    for file in REPORTS_DIR.glob("*"):
        if file.is_file() and file.suffix in [".html", ".json", ".csv"]:
            reports.append({
                "filename": file.name,
                "type": file.suffix[1:],  # Remove the dot
                "size_kb": round(file.stat().st_size / 1024, 1),
                "created": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
    
    # Sort by creation date (newest first)
    reports.sort(key=lambda x: x["created"], reverse=True)
    
    return {"total": len(reports), "reports": reports}


@app.get("/reports/{filename}")
async def get_report(filename: str):
    """Download a generated report by filename"""
    report_path = REPORTS_DIR / filename
    
    if not report_path.exists():
        return JSONResponse(
            status_code=404,
            content={"status": "error", "error": f"Report '{filename}' not found"}
        )
    
    # Determine media type
    if filename.endswith(".html"):
        media_type = "text/html"
    elif filename.endswith(".json"):
        media_type = "application/json"
    elif filename.endswith(".csv"):
        media_type = "text/csv"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(
        path=report_path,
        media_type=media_type,
        filename=filename
    )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
