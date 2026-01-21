"""
src/report.py
Module de génération de rapport HTML
"""

import os
import json
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader


class ReportGenerator:
    """Générateur de rapports HTML"""

    def __init__(self):
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.output_dir = Path(__file__).parent.parent / "data" / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, analyzed_result: dict) -> str:
        """
        Génère un rapport HTML à partir des données analysées

        Args:
            analyzed_result: Résultat de l'analyse (de analyzer.py)

        Returns:
            str: Chemin vers le fichier HTML généré
        """
        template = self.env.get_template("report.html")
        
        summary = analyzed_result.get("analysis_summary", {})
        insights = analyzed_result.get("insights", {})

        # Préparer les données pour le template
        context = {
            # Basic info
            "brand": analyzed_result.get("brand", "Unknown"),
            "market": analyzed_result.get("market", analyzed_result.get("country", "ALL")),
            "generation_date": datetime.now().strftime("%d %B %Y"),
            "generation_time": datetime.now().strftime("%H:%M"),
            
            # Metrics
            "total_ads": len(analyzed_result.get("ads", [])),
            "average_score": summary.get("average_score", 0),
            
            # Ads data
            "ads": analyzed_result.get("ads", []),
            
            # Full insights object (contains all distributions and recommendations)
            "insights": insights,
            
            # Legacy fields for backward compatibility
            "hook_distribution": summary.get("hook_distribution", {}),
            "funnel_distribution": summary.get("funnel_distribution", {})
        }

        # Rendre le template
        html_content = template.render(**context)

        # Sauvegarder le fichier
        brand_slug = context['brand'].lower().replace(' ', '_').replace('/', '_')
        filename = f"{brand_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = self.output_dir / filename
        filepath.write_text(html_content, encoding="utf-8")

        print(f"Rapport généré: {filepath}")
        return str(filepath)

    def generate_json_export(self, analyzed_result: dict) -> str:
        """
        Exporte les données en JSON
        """
        brand = analyzed_result.get("brand", "unknown")
        filename = f"{brand.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename

        filepath.write_text(
            json.dumps(analyzed_result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        print(f"Export JSON: {filepath}")
        return str(filepath)


# Fonction utilitaire
def generate_report(analyzed_result: dict) -> dict:
    """
    Génère le rapport HTML et JSON

    Returns:
        dict: Chemins vers les fichiers générés
    """
    generator = ReportGenerator()

    return {
        "html": generator.generate(analyzed_result),
        "json": generator.generate_json_export(analyzed_result)
    }


# Test standalone
if __name__ == "__main__":
    # Données de test Kimai
    test_data = {
        "brand": "Kimai",
        "ads": [
            {
                "id": 1,
                "text": "For the one who has everything - a bracelet he'll never take off",
                "headline": "Crafted for him, chosen by you",
                "cta": "Shop Now",
                "format": "Image",
                "analysis": {
                    "hook_type": "EMOTIONAL",
                    "hook_description": "Joue sur l'émotion du cadeau parfait",
                    "target_audience": {
                        "demographics": "Femmes 25-45 ans",
                        "psychographics": "Valorisent les relations personnelles",
                        "awareness_level": "problem_aware"
                    },
                    "funnel_stage": "CONSIDERATION",
                    "funnel_reasoning": "L'audience recherche une solution cadeau",
                    "score": 7,
                    "score_breakdown": {"clarity": 8, "cta_relevance": 7, "creative_coherence": 6},
                    "key_insight": "Exploite le dilemme du cadeau difficile à trouver"
                }
            },
            {
                "id": 2,
                "text": "Meet our Everyday Icons - timeless jewelry crafted in Antwerp",
                "headline": "Discover Kimai Fine Jewelry",
                "cta": "Shop now",
                "format": "Video",
                "analysis": {
                    "hook_type": "EMOTIONAL",
                    "hook_description": "Everyday Icons évoque l'aspiration",
                    "target_audience": {
                        "demographics": "Femmes 25-40 ans, revenus moyens-supérieurs",
                        "psychographics": "Conscientes de l'impact environnemental",
                        "awareness_level": "unaware"
                    },
                    "funnel_stage": "AWARENESS",
                    "funnel_reasoning": "Phase d'introduction de la marque",
                    "score": 7,
                    "score_breakdown": {"clarity": 8, "cta_relevance": 6, "creative_coherence": 7},
                    "key_insight": "Positionnement premium-responsable efficace"
                }
            }
        ],
        "analysis_summary": {
            "average_score": 7.0,
            "hook_distribution": {"EMOTIONAL": 2},
            "funnel_distribution": {"CONSIDERATION": 1, "AWARENESS": 1},
            "total_analyzed": 2
        },
        "insights": {
            "brand": "Kimai",
            "executive_summary": {
                "total_ads": 2,
                "average_score": 7.0,
                "dominant_hook": "EMOTIONAL",
                "dominant_funnel_stage": "CONSIDERATION"
            },
            "strategic_insights": [
                "La marque Kimai utilise principalement des hooks de type EMOTIONAL",
                "La majorité des publicités ciblent l'étape CONSIDERATION du funnel",
                "Score moyen des créatifs: 7.0/10"
            ],
            "top_performing_ads": [
                {
                    "text_preview": "For the one who has everything...",
                    "score": 7,
                    "key_insight": "Exploite le dilemme du cadeau difficile"
                }
            ]
        }
    }

    result = generate_report(test_data)
    print(f"\nFichiers générés:")
    print(f"  HTML: {result['html']}")
    print(f"  JSON: {result['json']}")
