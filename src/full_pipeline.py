"""
src/full_pipeline.py
Pipeline complet: Extraction detaillee + Analyse + Export CSV
"""

import asyncio
import json
import csv
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from browser_use import Agent
from browser_use.llm import ChatOpenAI
from anthropic import Anthropic

load_dotenv()


def sanitize_text(text: str, max_length: int = 2000) -> str:
    """
    Sanitize text to remove invalid Unicode surrogates and truncate if needed.
    This prevents JSON encoding errors when sending to APIs.
    """
    if not text:
        return "N/A"

    # Remove invalid Unicode surrogates (characters in range U+D800 to U+DFFF)
    # These cause "no low surrogate" errors in JSON encoding
    cleaned = ""
    for char in text:
        code_point = ord(char)
        # Skip surrogate pairs (0xD800-0xDFFF)
        if 0xD800 <= code_point <= 0xDFFF:
            continue
        cleaned += char

    # Truncate if too long to avoid huge API payloads
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."

    return cleaned


async def extract_detailed_ads(brand: str, max_ads: int = 10, timeout_minutes: int = 10):
    """
    Extrait les publicités avec tous les détails (ciblage, impressions, etc.)
    Focuses on best performing ads (highest impressions) first.
    """
    llm = ChatOpenAI(model='gpt-4o-mini')  # Much cheaper than gpt-4o

    task = f'''Go to https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q=Kimaï

Wait 3 seconds for ads to load.

CRITICAL RULES:
1. ONLY extract ads where the advertiser name is EXACTLY "Kimaï" (the ethical jewelry brand)
2. SKIP any ads from: Kimai.Arica, Chinese characters, Spanish text, or non-jewelry brands

For {max_ads} ads from "Kimaï":

1. Click "See ad details" on an ad from Kimaï
2. Extract these fields from the detail panel:
   - library_id (the Ad Library ID number)
   - start_date (when the ad started running)
   - platforms (Facebook, Instagram, etc.)
   - impressions (the impression count shown, e.g. "<1000" or "1K-5K")
   - primary_text (the main ad copy/body text)
   - headline (the headline text)
   - cta (call to action button text like "Shop Now")
   - format (Video, Image, Carousel, etc.)
3. Close the panel and repeat for the next ad

Extract {max_ads} ads total, then return the JSON.

Return JSON:
{{"brand": "Kimaï", "ads": [
  {{"library_id": "...", "start_date": "...", "platforms": ["facebook", "instagram"], "impressions": "...", "primary_text": "...", "headline": "...", "cta": "...", "format": "..."}}
]}}'''

    print(f"Extraction des publicités {brand}...")
    print(f"Timeout: {timeout_minutes} minutes, Max ads: {max_ads}")

    agent = Agent(task=task, llm=llm)
    # Add timeout to prevent runaway costs - max_steps limits LLM calls
    max_steps = timeout_minutes * 6  # ~10 seconds per step average
    history = await agent.run(max_steps=max_steps)

    final = history.final_result()
    if final:
        # Try to extract JSON from markdown code block first
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', final, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_start = final.find('{')
            json_end = final.rfind('}') + 1
            if json_start != -1:
                json_str = final[json_start:json_end]
            else:
                json_str = None

        if json_str:
            try:
                data = json.loads(json_str)
                # Filter out ads with null library_id or null primary_text
                if "ads" in data:
                    data["ads"] = [ad for ad in data["ads"]
                                   if ad.get("library_id") and ad.get("primary_text")]
                return data
            except json.JSONDecodeError as e:
                print(f"JSON parse failed: {e}")
                print(f"Raw output: {final[:500]}...")

    return {"brand": brand, "ads": [], "error": "Extraction failed"}


def analyze_ad(ad: dict, brand: str) -> dict:
    """
    Analyse une publicité avec Claude
    """
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    # Sanitize all text fields to prevent Unicode encoding errors
    primary_text = sanitize_text(ad.get('primary_text', ''))
    headline = sanitize_text(ad.get('headline', ''), max_length=500)
    cta = sanitize_text(ad.get('cta', ''), max_length=100)
    ad_format = sanitize_text(ad.get('format', ''), max_length=100)
    target_location = sanitize_text(ad.get('target_location', ''), max_length=200)
    target_age = sanitize_text(ad.get('target_age', ''), max_length=100)
    target_gender = sanitize_text(ad.get('target_gender', ''), max_length=100)
    impressions = sanitize_text(ad.get('impressions', ''), max_length=100)

    prompt = f"""Tu es un expert en stratégie publicitaire. Analyse cette publicité:

Marque: {brand}
Texte: {primary_text}
Headline: {headline}
CTA: {cta}
Format: {ad_format}
Ciblage: {target_location}, Age {target_age}, Genre {target_gender}
Impressions: {impressions}

Retourne UNIQUEMENT ce JSON:
{{
    "language": "English|French|Spanish|Other",
    "hook_type": "EMOTIONAL|RATIONAL|SOCIAL_PROOF|URGENCY|CURIOSITY",
    "market_strategy": "Brand Awareness|Product Launch|Retail Traffic|E-commerce|Lead Gen|Expansion|Influencer|Retargeting",
    "funnel_stage": "TOFU|MOFU|BOFU",
    "performance_indicator": "LOW|MEDIUM|HIGH",
    "score": 7,
    "key_insight": "..."
}}"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start != -1:
            return json.loads(content[json_start:json_end])
    except Exception as e:
        return {"error": str(e)}

    return {}


def export_csv(analyzed_data: dict, output_path: str = None) -> str:
    """
    Exporte en CSV avec toutes les colonnes
    """
    brand = analyzed_data.get("brand", "unknown")
    ads = analyzed_data.get("ads", [])

    if output_path is None:
        output_dir = Path(__file__).parent.parent / "data" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{brand.lower()}_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    fieldnames = [
        "Brand", "Library ID", "Start Date", "Platforms", "Impressions",
        "Versions", "Target Location", "Target Age", "Target Gender",
        "Format", "Headline", "Primary Text", "CTA",
        "Language", "Hook Type", "Market Strategy", "Funnel Stage",
        "Performance", "Score", "Key Insight"
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for ad in ads:
            analysis = ad.get("analysis", {})
            writer.writerow({
                "Brand": brand,
                "Library ID": ad.get("library_id", ""),
                "Start Date": ad.get("start_date", ""),
                "Platforms": ", ".join(ad.get("platforms", [])) if isinstance(ad.get("platforms"), list) else ad.get("platforms", ""),
                "Impressions": ad.get("impressions", ""),
                "Versions": ad.get("versions", ""),
                "Target Location": ad.get("target_location", ""),
                "Target Age": ad.get("target_age", ""),
                "Target Gender": ad.get("target_gender", ""),
                "Format": ad.get("format", ""),
                "Headline": ad.get("headline", ""),
                "Primary Text": ad.get("primary_text", ""),
                "CTA": ad.get("cta", ""),
                "Language": analysis.get("language", ""),
                "Hook Type": analysis.get("hook_type", ""),
                "Market Strategy": analysis.get("market_strategy", ""),
                "Funnel Stage": analysis.get("funnel_stage", ""),
                "Performance": analysis.get("performance_indicator", ""),
                "Score": analysis.get("score", ""),
                "Key Insight": analysis.get("key_insight", "")
            })

    return str(output_path)


def export_html(analyzed_data: dict, output_path: str = None) -> str:
    """
    Exporte en HTML avec un design moderne
    """
    brand = analyzed_data.get("brand", "unknown")
    ads = analyzed_data.get("ads", [])

    if output_path is None:
        output_dir = Path(__file__).parent.parent / "data" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{brand.lower()}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    # Calculate summary stats
    scores = [ad.get("analysis", {}).get("score", 0) for ad in ads if ad.get("analysis", {}).get("score")]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    hook_types = {}
    strategies = {}
    for ad in ads:
        analysis = ad.get("analysis", {})
        hook = analysis.get("hook_type", "Unknown")
        strategy = analysis.get("market_strategy", "Unknown")
        hook_types[hook] = hook_types.get(hook, 0) + 1
        strategies[strategy] = strategies.get(strategy, 0) + 1

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{brand} - Ad Analysis Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; border-radius: 12px; margin-bottom: 30px; }}
        header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        header p {{ opacity: 0.9; font-size: 1.1rem; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); text-align: center; }}
        .stat-card h3 {{ font-size: 2rem; color: #667eea; }}
        .stat-card p {{ color: #666; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }}
        .ads-grid {{ display: grid; gap: 20px; }}
        .ad-card {{ background: white; border-radius: 12px; padding: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }}
        .ad-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 15px; }}
        .ad-score {{ font-size: 1.8rem; font-weight: bold; color: #667eea; }}
        .ad-meta {{ display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 15px; }}
        .ad-meta span {{ background: #f0f0f0; padding: 5px 12px; border-radius: 20px; font-size: 0.85rem; }}
        .ad-text {{ font-size: 1.1rem; margin-bottom: 15px; padding: 15px; background: #f9f9f9; border-radius: 8px; border-left: 4px solid #667eea; }}
        .ad-insight {{ color: #666; font-style: italic; padding: 15px; background: #fff8e1; border-radius: 8px; }}
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
        .badge-emotional {{ background: #ffebee; color: #c62828; }}
        .badge-rational {{ background: #e3f2fd; color: #1565c0; }}
        .badge-social {{ background: #e8f5e9; color: #2e7d32; }}
        .badge-urgency {{ background: #fff3e0; color: #ef6c00; }}
        .badge-curiosity {{ background: #f3e5f5; color: #7b1fa2; }}
        footer {{ text-align: center; padding: 30px; color: #999; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{brand} Ad Analysis</h1>
            <p>Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')} | {len(ads)} ads analyzed</p>
        </header>

        <div class="stats">
            <div class="stat-card">
                <h3>{len(ads)}</h3>
                <p>Total Ads</p>
            </div>
            <div class="stat-card">
                <h3>{avg_score}/10</h3>
                <p>Average Score</p>
            </div>
            <div class="stat-card">
                <h3>{max(hook_types, key=hook_types.get) if hook_types else "N/A"}</h3>
                <p>Top Hook Type</p>
            </div>
            <div class="stat-card">
                <h3>{max(strategies, key=strategies.get) if strategies else "N/A"}</h3>
                <p>Top Strategy</p>
            </div>
        </div>

        <div class="ads-grid">
'''

    for i, ad in enumerate(ads, 1):
        analysis = ad.get("analysis", {})
        hook_type = analysis.get("hook_type", "Unknown")
        badge_class = f"badge-{hook_type.lower().replace('_', '-')}" if hook_type else ""

        html_content += f'''
            <div class="ad-card">
                <div class="ad-header">
                    <div>
                        <strong>Ad #{i}</strong> - Library ID: {ad.get("library_id", "N/A")}
                    </div>
                    <div class="ad-score">{analysis.get("score", "N/A")}/10</div>
                </div>
                <div class="ad-meta">
                    <span class="badge {badge_class}">{hook_type}</span>
                    <span>{analysis.get("market_strategy", "N/A")}</span>
                    <span>{analysis.get("funnel_stage", "N/A")}</span>
                    <span>{ad.get("impressions", "N/A")} impressions</span>
                    <span>Started: {ad.get("start_date", "N/A")}</span>
                </div>
                <div class="ad-text">
                    "{ad.get("primary_text", "N/A")}"
                </div>
                <div class="ad-insight">
                    <strong>Insight:</strong> {analysis.get("key_insight", "No insight available")}
                </div>
            </div>
'''

    html_content += '''
        </div>

        <footer>
            <p>Report generated by Meta Ads Analyzer</p>
        </footer>
    </div>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    return str(output_path)


async def run_full_pipeline(brand: str, max_ads: int = 10, timeout_minutes: int = 10):
    """
    Pipeline complet: Extraction + Analyse + Export

    Args:
        brand: Brand name to search for
        max_ads: Maximum number of ads to extract
        timeout_minutes: Maximum time for browser extraction (default 10 min)
    """
    # 1. Extraction détaillée
    print(f"\n{'='*50}")
    print(f"EXTRACTION: {brand}")
    print(f"{'='*50}")

    extraction = await extract_detailed_ads(brand, max_ads, timeout_minutes)

    if "error" in extraction or len(extraction.get("ads", [])) == 0:
        print(f"Erreur d'extraction: {extraction.get('error', 'No ads found')}")
        return None

    print(f"✓ {len(extraction['ads'])} publicités extraites")

    # 2. Analyse avec Claude
    print(f"\n{'='*50}")
    print("ANALYSE")
    print(f"{'='*50}")

    for i, ad in enumerate(extraction["ads"]):
        print(f"  Analyse {i+1}/{len(extraction['ads'])}...")
        ad["analysis"] = analyze_ad(ad, brand)

    # 3. Trier par performance (impressions)
    def get_impression_rank(ad):
        imp = (ad.get("impressions") or "").lower()
        if ">1m" in imp or "1m+" in imp:
            return 5
        elif ">100k" in imp or "100k" in imp:
            return 4
        elif ">10k" in imp or "10k" in imp:
            return 3
        elif ">1k" in imp or "1000" in imp or "1k" in imp:
            return 2
        elif "<100" in imp:
            return 0
        return 1

    extraction["ads"] = sorted(extraction["ads"], key=get_impression_rank, reverse=True)

    # 4. Export CSV
    print(f"\n{'='*50}")
    print("EXPORT")
    print(f"{'='*50}")

    csv_path = export_csv(extraction)
    print(f"✓ CSV: {csv_path}")

    html_path = export_html(extraction)
    print(f"✓ HTML: {html_path}")

    # 5. Résumé
    print(f"\n{'='*50}")
    print("RÉSUMÉ")
    print(f"{'='*50}")

    print(f"Marque: {brand}")
    print(f"Total publicités: {len(extraction['ads'])}")

    # Top 3 pubs par performance
    print("\nTop 3 publicités (par impressions):")
    for i, ad in enumerate(extraction["ads"][:3]):
        print(f"  {i+1}. {ad.get('headline', 'N/A')[:40]}...")
        print(f"     Impressions: {ad.get('impressions', 'N/A')}")
        print(f"     Score: {ad.get('analysis', {}).get('score', 'N/A')}/10")

    return extraction


# Main
if __name__ == "__main__":
    # Test with 2 best-performing ads, 5 minute timeout
    result = asyncio.run(run_full_pipeline("Kimaï", max_ads=2, timeout_minutes=5))

    if result:
        print(f"\n\nDonnées extraites:")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:2000] + "...")
