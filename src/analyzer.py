"""
src/analyzer.py
Module d'analyse stratégique des publicités avec GPT-4
"""

import os
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

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
    """Analyseur stratégique de publicités avec GPT-4"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_ANALYSIS_MODEL", "gpt-4o")
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
        Analyse une seule publicité avec GPT-4

        Args:
            ad: Données de la publicité
            brand: Nom de la marque
            market: Code pays du marché

        Returns:
            dict: Analyse de la publicité
        """
        prompt = self._format_prompt(ad, brand, market)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert advertising strategist. Always respond with valid JSON only, no markdown formatting."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extraire le JSON de la réponse
            content = response.choices[0].message.content
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
        
        # Distribution tracking
        hook_types = {}
        funnel_stages = {}
        message_strategies = {}
        headline_themes = {}
        visual_themes = {}
        languages = {}
        formats = {}
        ctas = {}
        
        # Unique variations tracking
        unique_primary_texts = set()
        unique_headlines = set()
        
        # Timeline tracking
        timeline = {}

        print(f"Analyse de {len(ads)} publicités pour {brand} (market: {market})...")

        for i, ad in enumerate(ads):
            print(f"  Analyse pub {i+1}/{len(ads)}...")
            analysis = self.analyze_ad(ad, brand, market)

            # Combiner les données originales avec l'analyse
            analyzed_ad = {**ad, "analysis": analysis}
            analyzed_ads.append(analyzed_ad)
            
            # Track unique variations (raw data)
            primary_text = ad.get("primary_text", ad.get("text", ""))
            headline = ad.get("headline", "")
            if primary_text:
                unique_primary_texts.add(primary_text[:200])  # Truncate for comparison
            if headline:
                unique_headlines.add(headline)
            
            # Track format distribution
            fmt = ad.get("format", "Unknown")
            formats[fmt] = formats.get(fmt, 0) + 1
            
            # Track CTA distribution
            cta = ad.get("cta", "Unknown")
            ctas[cta] = ctas.get(cta, 0) + 1
            
            # Track timeline
            first_seen = ad.get("first_seen", "")
            if first_seen:
                month = first_seen[:7]  # YYYY-MM
                timeline[month] = timeline.get(month, 0) + 1

            # Analysis-based statistics
            if "error" not in analysis:
                score = analysis.get("score", 0)
                total_score += score

                hook = analysis.get("hook_type", "UNKNOWN")
                hook_types[hook] = hook_types.get(hook, 0) + 1

                funnel = analysis.get("funnel_stage", "UNKNOWN")
                funnel_stages[funnel] = funnel_stages.get(funnel, 0) + 1

                msg_strategy = analysis.get("message_strategy", "UNKNOWN")
                message_strategies[msg_strategy] = message_strategies.get(msg_strategy, 0) + 1
                
                hl_theme = analysis.get("headline_theme", "UNKNOWN")
                headline_themes[hl_theme] = headline_themes.get(hl_theme, 0) + 1
                
                vis_theme = analysis.get("visual_theme", "UNKNOWN")
                visual_themes[vis_theme] = visual_themes.get(vis_theme, 0) + 1

                lang = analysis.get("language", "UNKNOWN")
                languages[lang] = languages.get(lang, 0) + 1

        # Calculer les statistiques globales
        num_ads = len(analyzed_ads)
        avg_score = round(total_score / num_ads, 1) if num_ads > 0 else 0

        return {
            **extraction_result,
            "ads": analyzed_ads,
            "analysis_summary": {
                "total_analyzed": num_ads,
                "average_score": avg_score,
                "unique_primary_texts": len(unique_primary_texts),
                "unique_headlines": len(unique_headlines),
                "hook_distribution": hook_types,
                "funnel_distribution": funnel_stages,
                "message_strategy_distribution": message_strategies,
                "headline_theme_distribution": headline_themes,
                "visual_theme_distribution": visual_themes,
                "language_distribution": languages,
                "format_distribution": formats,
                "cta_distribution": ctas,
                "timeline_distribution": timeline,
                "primary_text_list": list(unique_primary_texts),
                "headline_list": list(unique_headlines)
            }
        }

    def generate_insights(self, analyzed_result: dict) -> dict:
        """
        Génère des insights globaux basés sur toutes les analyses
        """
        summary = analyzed_result.get("analysis_summary", {})
        ads = analyzed_result.get("ads", [])
        brand = analyzed_result.get("brand", "Unknown")
        market = analyzed_result.get("market", "ALL")

        # Helper to get dominant from distribution
        def get_dominant(dist):
            return max(dist, key=dist.get) if dist else "N/A"
        
        # Get all distributions
        hooks = summary.get("hook_distribution", {})
        funnels = summary.get("funnel_distribution", {})
        msg_strategies = summary.get("message_strategy_distribution", {})
        hl_themes = summary.get("headline_theme_distribution", {})
        vis_themes = summary.get("visual_theme_distribution", {})
        formats = summary.get("format_distribution", {})
        ctas = summary.get("cta_distribution", {})
        timeline = summary.get("timeline_distribution", {})
        
        # Calculate format percentages
        total_ads = sum(formats.values()) if formats else 0
        format_percentages = {
            fmt: round((count / total_ads) * 100) if total_ads > 0 else 0
            for fmt, count in formats.items()
        }

        # Top 3 publicités par score
        sorted_ads = sorted(
            [a for a in ads if "error" not in a.get("analysis", {})],
            key=lambda x: x.get("analysis", {}).get("score", 0),
            reverse=True
        )
        top_ads = sorted_ads[:3]
        
        # Build strategic insights list
        strategic_insights = []
        
        # Hook insight
        dominant_hook = get_dominant(hooks)
        if dominant_hook != "N/A":
            hook_count = hooks.get(dominant_hook, 0)
            hook_pct = round((hook_count / total_ads) * 100) if total_ads > 0 else 0
            strategic_insights.append(f"{brand} uses {dominant_hook} hooks in {hook_pct}% of their ads, focusing on {dominant_hook.lower().replace('_', ' ')} messaging to engage their audience.")
        
        # Message strategy insight
        dominant_msg = get_dominant(msg_strategies)
        if dominant_msg != "N/A":
            strategic_insights.append(f"Primary messaging approach: '{dominant_msg}' - this indicates a focus on {dominant_msg.lower()} communication.")
        
        # Funnel insight
        dominant_funnel = get_dominant(funnels)
        if dominant_funnel != "N/A":
            funnel_desc = {
                "TOFU": "brand awareness and discovery",
                "MOFU": "consideration and evaluation",
                "BOFU": "conversion and direct action"
            }.get(dominant_funnel, dominant_funnel.lower())
            strategic_insights.append(f"Campaign targets {dominant_funnel} stage - optimized for {funnel_desc}.")
        
        # Format insight
        dominant_format = get_dominant(formats)
        if dominant_format != "N/A":
            format_pct = format_percentages.get(dominant_format, 0)
            strategic_insights.append(f"Creative format: {format_pct}% {dominant_format} - indicates {('rapid A/B testing approach' if dominant_format == 'Static Image' else 'investment in high-impact content')}.")
        
        # Testing velocity insight
        unique_texts = summary.get("unique_primary_texts", 0)
        unique_hls = summary.get("unique_headlines", 0)
        if total_ads > 0 and unique_texts > 0:
            strategic_insights.append(f"Testing velocity: {total_ads} ads with {unique_texts} unique message variations and {unique_hls} headline variations.")

        return {
            "brand": brand,
            "market": market,
            "executive_summary": {
                "total_ads": total_ads,
                "unique_creatives": unique_texts,
                "unique_headlines": unique_hls,
                "average_score": summary.get("average_score", 0),
                "dominant_hook": dominant_hook,
                "dominant_funnel_stage": dominant_funnel,
                "dominant_message_strategy": dominant_msg,
                "dominant_headline_theme": get_dominant(hl_themes),
                "dominant_visual_theme": get_dominant(vis_themes)
            },
            "format_distribution": formats,
            "format_percentages": format_percentages,
            "cta_distribution": ctas,
            "timeline_distribution": timeline,
            "hook_distribution": hooks,
            "funnel_distribution": funnels,
            "message_strategy_distribution": msg_strategies,
            "headline_theme_distribution": hl_themes,
            "primary_text_list": summary.get("primary_text_list", []),
            "headline_list": summary.get("headline_list", []),
            "strategic_insights": strategic_insights,
            "top_performing_ads": [
                {
                    "id": ad.get("id", i+1),
                    "primary_text": ad.get("primary_text", ad.get("text", ""))[:150],
                    "headline": ad.get("headline", ""),
                    "cta": ad.get("cta", ""),
                    "format": ad.get("format", ""),
                    "first_seen": ad.get("first_seen", ""),
                    "score": ad.get("analysis", {}).get("score", 0),
                    "hook_type": ad.get("analysis", {}).get("hook_type", ""),
                    "message_strategy": ad.get("analysis", {}).get("message_strategy", ""),
                    "key_insight": ad.get("analysis", {}).get("key_insight", "N/A")
                }
                for i, ad in enumerate(top_ads)
            ],
            "recommendations": self._generate_recommendations(summary, brand, dominant_hook, dominant_funnel, dominant_msg)
        }
    
    def _generate_recommendations(self, summary, brand, hook, funnel, msg_strategy):
        """Generate actionable recommendations based on the analysis"""
        recs = []
        
        # Based on hook type
        if hook == "URGENCY":
            recs.append("Consider testing EMOTIONAL or SOCIAL_PROOF hooks to diversify messaging and reduce audience fatigue from urgency tactics.")
        elif hook == "EMOTIONAL":
            recs.append("Test adding VALUE_ANCHOR messaging to complement emotional appeal with concrete benefits.")
        elif hook == "RATIONAL":
            recs.append("Consider adding SOCIAL_PROOF elements (testimonials, reviews) to build trust alongside rational arguments.")
        
        # Based on funnel stage
        if funnel == "TOFU":
            recs.append("For TOFU-focused campaigns, consider creating MOFU content to nurture awareness into consideration.")
        elif funnel == "BOFU":
            recs.append("Strong conversion focus. Ensure retargeting and TOFU awareness campaigns support the funnel.")
        
        # Based on format distribution
        formats = summary.get("format_distribution", {})
        if formats.get("Video", 0) == 0:
            recs.append("No video content detected. Consider testing video ads for higher engagement, especially testimonials.")
        
        # General recommendation
        recs.append(f"Monitor {brand}'s creative evolution and landing page strategies for competitive intelligence updates.")
        
        return recs

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
