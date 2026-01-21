"""
src/extractor.py
Module d'extraction des publicités Meta Ad Library
Utilise Browser-Use avec GPT-5.2 pour la navigation
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus
from dotenv import load_dotenv

from browser_use import Agent
from browser_use.llm import ChatOpenAI

load_dotenv()


class MetaAdsExtractor:
    """Extracteur de publicités Meta Ad Library"""

    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.2")
        self.llm = ChatOpenAI(
            model=self.model,
            api_key=os.getenv("OPENAI_API_KEY")
        )

    def _build_url(self, brand: str, country: str = "ALL") -> str:
        """Construit l'URL de Meta Ad Library"""
        base = "https://www.facebook.com/ads/library/"
        # URL-encode brand name to handle spaces and special characters
        encoded_brand = quote_plus(brand)
        params = f"?active_status=active&ad_type=all&country={country}&q={encoded_brand}"
        return base + params

    def _build_extraction_task(self, brand: str, url: str, country: str, max_ads: int = 30) -> str:
        """Construit la tâche d'extraction pour l'agent"""
        return f"""Go to {url}

If a cookie popup appears, click "Decline optional cookies".

STEP 1 - SELECT THE ADVERTISER:
The search results show ads from MANY advertisers. You MUST select the specific advertiser:
1. Click inside the search box to trigger the dropdown
2. Look for "Advertisers" section in the dropdown
3. Click on the advertiser that matches "{brand}" (look for the one with follower count or verified badge)
4. Wait for the page to reload with ONLY that advertiser's ads

STEP 2 - LOAD ALL ADS:
Scroll down the page slowly and thoroughly:
- Scroll down, wait 3 seconds
- Repeat at least 10 times
- Keep scrolling until you see no more new ads loading
- The goal is to load ALL available ads on the page

STEP 3 - EXTRACT ALL ADS:
Look at the page and count how many ad cards are visible. 
Extract up to {max_ads} ads. For EACH ad card you see, extract:

- advertiser: the advertiser name (e.g., "Arte")
- primary_text: the ad copy text shown on the ad card (e.g., "Spring/Summer '26")
- headline: any headline text visible
- cta: the button text (e.g., "Shop Now")
- format: "Video" if it has a play button, otherwise "Static Image" or "Carousel"
- first_seen: the date shown (convert to YYYY-MM-DD format, e.g., "17 jan 2026" → "2026-01-17")
- platforms: look at the platform icons (Facebook, Instagram icons)

CRITICAL: Extract EVERY ad you can see, not just the first one. If you see 16 ads, extract all 16 (up to {max_ads}).

Return this JSON format:
{{"brand": "{brand}", "market": "{country}", "platform": "Meta", "total_ads": NUMBER_OF_ADS_EXTRACTED, "ads": [{{"id": 1, "advertiser": "...", "primary_text": "...", "headline": "...", "cta": "...", "format": "...", "first_seen": "YYYY-MM-DD", "platforms": ["facebook", "instagram"]}}, {{"id": 2, ...}}, ...]}}"""

    async def extract(
        self,
        brand: str,
        country: str = "ALL",
        max_ads: int = 20
    ) -> dict:
        """
        Extrait les publicités d'une marque

        Args:
            brand: Nom de la marque à rechercher
            country: Code pays (ALL, FR, US, etc.)
            max_ads: Nombre maximum de publicités à extraire

        Returns:
            dict: Données extraites avec les publicités
        """
        url = self._build_url(brand, country)
        task = self._build_extraction_task(brand, url, country, max_ads)

        try:
            agent = Agent(
                task=task,
                llm=self.llm,
            )

            # Exécuter la tâche (l'URL est incluse dans la tâche)
            history = await agent.run()

            # Extraire le contenu du résultat
            result = None

            # Helper to parse JSON safely (handles truncated/malformed JSON)
            def try_parse_json(content: str) -> dict | None:
                import re
                if not content:
                    return None
                
                # Find JSON start
                json_start = content.find("{")
                if json_start == -1:
                    return None
                
                # Method 1: Try to find properly matched braces
                brace_count = 0
                json_end = -1
                for i, char in enumerate(content[json_start:], json_start):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                # Method 2: If no match, try last closing brace
                if json_end == -1:
                    json_end = content.rfind("}") + 1
                
                if json_end > json_start:
                    json_str = content[json_start:json_end]
                    
                    # Try direct parse first
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
                    
                    # Fix common issues
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)  # trailing commas
                    json_str = re.sub(r'\.\.\.[^"]*', '', json_str)  # remove ... truncation
                    
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
                    
                    # Method 3: Try to salvage partial ads array
                    # Find "ads": [ and extract what we can
                    ads_match = re.search(r'"ads"\s*:\s*\[', content)
                    if ads_match:
                        ads_start = ads_match.end()
                        # Find complete ad objects
                        ads = []
                        ad_pattern = r'\{[^{}]*"id"\s*:\s*\d+[^{}]*\}'
                        for match in re.finditer(ad_pattern, content[ads_start:]):
                            try:
                                ad = json.loads(match.group())
                                ads.append(ad)
                            except json.JSONDecodeError:
                                continue
                        
                        if ads:
                            # Extract brand from content
                            brand_match = re.search(r'"brand"\s*:\s*"([^"]+)"', content)
                            brand_name = brand_match.group(1) if brand_match else "Unknown"
                            market_match = re.search(r'"market"\s*:\s*"([^"]+)"', content)
                            market_name = market_match.group(1) if market_match else "ALL"
                            
                            return {
                                "brand": brand_name,
                                "market": market_name,
                                "platform": "Meta",
                                "total_ads": len(ads),
                                "ads": ads
                            }
                
                return None

            # Essayer d'abord le résultat final
            final = history.final_result()
            if final:
                result = try_parse_json(final)

            # Sinon, parcourir les résultats d'actions
            if result is None:
                for action_result in history.action_results():
                    if action_result.extracted_content:
                        parsed = try_parse_json(action_result.extracted_content)
                        if parsed and "ads" in parsed:
                            result = parsed
                            break

            # Si pas de JSON trouvé, créer un résultat vide
            if result is None:
                result = {
                    "brand": brand,
                    "ads": [],
                    "error": "No valid JSON found in extraction result"
                }

            # Ajouter les métadonnées
            result["extraction_timestamp"] = datetime.now().isoformat()
            result["source"] = "meta_ad_library"
            result["country"] = country

            return result

        except Exception as e:
            return {
                "error": str(e),
                "brand": brand,
                "extraction_timestamp": datetime.now().isoformat(),
                "ads": []
            }

    async def extract_with_retry(
        self,
        brand: str,
        country: str = "ALL",
        max_ads: int = 20,
        max_retries: int = 3
    ) -> dict:
        """
        Extraction avec retry en cas d'échec
        """
        for attempt in range(max_retries):
            result = await self.extract(brand, country, max_ads)

            if "error" not in result and len(result.get("ads", [])) > 0:
                return result

            print(f"Tentative {attempt + 1}/{max_retries} échouée, retry...")
            await asyncio.sleep(5)

        return result


# Fonction utilitaire pour usage direct
async def extract_meta_ads(brand: str, country: str = "ALL") -> dict:
    """
    Fonction simple pour extraire les publicités

    Usage:
        result = await extract_meta_ads("Notion")
    """
    extractor = MetaAdsExtractor()
    return await extractor.extract(brand, country)


# Test standalone
if __name__ == "__main__":
    async def main():
        result = await extract_meta_ads("Notion")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(main())
