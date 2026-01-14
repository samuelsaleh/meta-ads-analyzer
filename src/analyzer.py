"""
src/analyzer.py
Module d'analyse stratégique des publicités avec Claude
"""

import os
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
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
    cleaned = ""
    for char in text:
        code_point = ord(char)
        if 0xD800 <= code_point <= 0xDFFF:
            continue
        cleaned += char

    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."

    return cleaned


class AdsAnalyzer:
    """Analyseur stratégique de publicités avec Claude"""

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Charge le template de prompt depuis le fichier"""
        prompt_path = Path(__file__).parent / "prompts" / "analysis.txt"
        if prompt_path.exists():
            return prompt_path.read_text()
        else:
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Prompt par défaut si le fichier n'existe pas"""
        return """Analyse cette publicité. Marque: {brand}, Texte: {primary_text}, Headline: {headline}, CTA: {cta}"""

    def _format_prompt(self, ad: dict, brand: str, market: str = "ALL") -> str:
        """Formate le prompt avec les données de la publicité"""
        return self.prompt_template.format(
            brand=brand,
            market=market,
            primary_text=sanitize_text(ad.get("primary_text", ad.get("text", ""))),
            headline=sanitize_text(ad.get("headline", ""), max_length=500),
            cta=sanitize_text(ad.get("cta", ""), max_length=100),
            format=sanitize_text(ad.get("format", ""), max_length=100),
            first_seen=ad.get("first_seen", "N/A")
        )

    def analyze_ad(self, ad: dict, brand: str, market: str = "ALL") -> dict:
        """
        Analyse une seule publicité

        Args:
            ad: Données de la publicité
            brand: Nom de la marque
            market: Code pays du marché

        Returns:
            dict: Analyse de la publicité
        """
        prompt = self._format_prompt(ad, brand, market)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extraire le JSON de la réponse
            content = response.content[0].text
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start != -1 and json_end > json_start:
                analysis = json.loads(content[json_start:json_end])
            else:
                analysis = {"error": "Could not parse JSON", "raw": content}

            return analysis

        except Exception as e:
            return {"error": str(e)}

    def analyze_batch(self, extraction_result: dict) -> dict:
        """
        Analyse un lot de publicités extraites

        Args:
            extraction_result: Résultat de l'extraction (de extractor.py)

        Returns:
            dict: Résultat avec analyses ajoutées
        """
        brand = extraction_result.get("brand", "Unknown")
        market = extraction_result.get("market", "ALL")
        ads = extraction_result.get("ads", [])

        analyzed_ads = []
        total_score = 0
        hook_types = {}
        funnel_stages = {}
        market_strategies = {}
        languages = {}

        print(f"Analyse de {len(ads)} publicités pour {brand} (market: {market})...")

        for i, ad in enumerate(ads):
            print(f"  Analyse pub {i+1}/{len(ads)}...")
            analysis = self.analyze_ad(ad, brand, market)

            # Combiner les données originales avec l'analyse
            analyzed_ad = {**ad, "analysis": analysis}
            analyzed_ads.append(analyzed_ad)

            # Statistiques
            if "error" not in analysis:
                score = analysis.get("score", 0)
                total_score += score

                hook = analysis.get("hook_type", "UNKNOWN")
                hook_types[hook] = hook_types.get(hook, 0) + 1

                funnel = analysis.get("funnel_stage", "UNKNOWN")
                funnel_stages[funnel] = funnel_stages.get(funnel, 0) + 1

                strategy = analysis.get("market_strategy", "UNKNOWN")
                market_strategies[strategy] = market_strategies.get(strategy, 0) + 1

                lang = analysis.get("language", "UNKNOWN")
                languages[lang] = languages.get(lang, 0) + 1

        # Calculer les statistiques globales
        num_ads = len(analyzed_ads)
        avg_score = round(total_score / num_ads, 1) if num_ads > 0 else 0

        return {
            **extraction_result,
            "ads": analyzed_ads,
            "analysis_summary": {
                "average_score": avg_score,
                "hook_distribution": hook_types,
                "funnel_distribution": funnel_stages,
                "market_strategy_distribution": market_strategies,
                "language_distribution": languages,
                "total_analyzed": num_ads
            }
        }

    def generate_insights(self, analyzed_result: dict) -> dict:
        """
        Génère des insights globaux basés sur toutes les analyses
        """
        summary = analyzed_result.get("analysis_summary", {})
        ads = analyzed_result.get("ads", [])
        brand = analyzed_result.get("brand", "Unknown")

        # Trouver les dominants
        hooks = summary.get("hook_distribution", {})
        dominant_hook = max(hooks, key=hooks.get) if hooks else "N/A"

        funnels = summary.get("funnel_distribution", {})
        dominant_funnel = max(funnels, key=funnels.get) if funnels else "N/A"

        strategies = summary.get("market_strategy_distribution", {})
        dominant_strategy = max(strategies, key=strategies.get) if strategies else "N/A"

        # Top 3 publicités par score
        sorted_ads = sorted(
            [a for a in ads if "error" not in a.get("analysis", {})],
            key=lambda x: x.get("analysis", {}).get("score", 0),
            reverse=True
        )
        top_ads = sorted_ads[:3]

        return {
            "brand": brand,
            "executive_summary": {
                "total_ads": len(ads),
                "average_score": summary.get("average_score", 0),
                "dominant_hook": dominant_hook,
                "dominant_funnel_stage": dominant_funnel,
                "dominant_market_strategy": dominant_strategy
            },
            "strategic_insights": [
                f"La marque {brand} utilise principalement des hooks de type {dominant_hook}",
                f"Stratégie dominante: {dominant_strategy}",
                f"La majorité des publicités ciblent l'étape {dominant_funnel} du funnel",
                f"Score moyen des créatifs: {summary.get('average_score', 0)}/10"
            ],
            "top_performing_ads": [
                {
                    "text_preview": ad.get("primary_text", ad.get("text", ""))[:100] + "...",
                    "score": ad.get("analysis", {}).get("score", 0),
                    "key_insight": ad.get("analysis", {}).get("key_insight", "N/A")
                }
                for ad in top_ads
            ]
        }

    def export_csv(self, analyzed_result: dict, output_path: str = None) -> str:
        """
        Exporte les résultats en CSV (format spreadsheet)
        """
        brand = analyzed_result.get("brand", "unknown")
        market = analyzed_result.get("market", "ALL")
        ads = analyzed_result.get("ads", [])

        if output_path is None:
            output_dir = Path(__file__).parent.parent / "data" / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{brand.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # Colonnes du CSV
        fieldnames = [
            "Brand", "Market", "Platform", "Format", "Headline",
            "Primary Text", "CTA", "First Seen", "Language",
            "Hook Type", "Market Strategy", "Funnel Stage", "Score", "Key Insight"
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for ad in ads:
                analysis = ad.get("analysis", {})
                writer.writerow({
                    "Brand": brand,
                    "Market": market,
                    "Platform": "Meta",
                    "Format": ad.get("format", ""),
                    "Headline": ad.get("headline", ""),
                    "Primary Text": ad.get("primary_text", ad.get("text", "")),
                    "CTA": ad.get("cta", ""),
                    "First Seen": ad.get("first_seen", ""),
                    "Language": analysis.get("language", ""),
                    "Hook Type": analysis.get("hook_type", ""),
                    "Market Strategy": analysis.get("market_strategy", ""),
                    "Funnel Stage": analysis.get("funnel_stage", ""),
                    "Score": analysis.get("score", ""),
                    "Key Insight": analysis.get("key_insight", "")
                })

        print(f"CSV exporté: {output_path}")
        return str(output_path)


# Fonction utilitaire
def analyze_extraction(extraction_result: dict) -> dict:
    """
    Fonction simple pour analyser un résultat d'extraction

    Usage:
        analyzed = analyze_extraction(extraction_result)
    """
    analyzer = AdsAnalyzer()
    result = analyzer.analyze_batch(extraction_result)
    result["insights"] = analyzer.generate_insights(result)
    return result


# Test standalone
if __name__ == "__main__":
    # Données de test Kimai enrichies
    test_data = {
        "brand": "Kimai",
        "market": "UK",
        "platform": "Meta",
        "ads": [
            {
                "id": 1,
                "primary_text": "Experience ethical luxury in person. Book an appointment at our Marylebone boutique.",
                "headline": "Visit our London Flagship",
                "cta": "Book Now",
                "format": "Video",
                "first_seen": "2025-03-10"
            },
            {
                "id": 2,
                "primary_text": "Our new LA boutique is here. Discover lab-grown diamonds in the heart of West Hollywood.",
                "headline": "Now Open in Melrose Place",
                "cta": "Get Directions",
                "format": "Static Image",
                "first_seen": "2025-11-07"
            }
        ]
    }

    result = analyze_extraction(test_data)

    # Export CSV
    analyzer = AdsAnalyzer()
    csv_path = analyzer.export_csv(result)

    print("\n" + "="*50)
    print(json.dumps(result["insights"], indent=2, ensure_ascii=False))
