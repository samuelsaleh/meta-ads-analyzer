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
        params = f"?active_status=active&ad_type=all&country={country}&q={brand}"
        return base + params

    def _build_extraction_task(self, brand: str, url: str, country: str, max_ads: int = 30) -> str:
        """Construit la tâche d'extraction pour l'agent"""
        return f"""Go to {url}

If a cookie popup appears, click "Decline optional cookies".

Wait 3 seconds for ads to load.

Scroll down slowly 5 times, waiting 2 seconds between scrolls, to load more ads.

Extract ALL ads visible (up to {max_ads}) that contain "{brand}" in the advertiser name.

For EACH ad, extract these details:
- advertiser: exact advertiser name shown
- primary_text: the main ad copy text
- headline: the bold headline/title
- cta: call-to-action button text (Shop Now, Learn More, Book Now, Get Directions, etc.)
- format: Video, Static Image, or Carousel
- first_seen: the start date shown (format: YYYY-MM-DD)
- platforms: list of platform icons visible (facebook, instagram, messenger, audience_network)

Return ONLY this JSON:
{{"brand": "{brand}", "market": "{country}", "platform": "Meta", "total_ads": X, "ads": [{{"id": 1, "advertiser": "...", "primary_text": "...", "headline": "...", "cta": "...", "format": "...", "first_seen": "YYYY-MM-DD", "platforms": ["facebook", "instagram"]}}]}}"""

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

            # Essayer d'abord le résultat final
            final = history.final_result()
            if final:
                content = final
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    try:
                        result = json.loads(content[json_start:json_end])
                    except json.JSONDecodeError:
                        pass

            # Sinon, parcourir les résultats d'actions
            if result is None:
                for action_result in history.action_results():
                    if action_result.extracted_content:
                        content = action_result.extracted_content
                        json_start = content.find("{")
                        json_end = content.rfind("}") + 1
                        if json_start != -1 and json_end > json_start:
                            try:
                                result = json.loads(content[json_start:json_end])
                                if "ads" in result:
                                    break
                            except json.JSONDecodeError:
                                continue

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
