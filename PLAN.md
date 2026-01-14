# Meta Ads Analyzer - Plan d'Implémentation Détaillé

> Plan complet pour construire une mini-app web d'analyse de publicités Meta

---

## Vue d'Ensemble du Projet

### Objectif
Créer une application web qui :
1. Extrait automatiquement les publicités d'une marque depuis Meta Ad Library
2. Analyse chaque publicité avec l'IA (hook, audience, funnel, score)
3. Génère un rapport stratégique professionnel

### Stack Technique
| Composant | Technologie | Rôle |
|-----------|-------------|------|
| Backend | FastAPI | API et rendu web |
| Extraction | Browser-Use + GPT-5.2 | Navigation et scraping |
| Analyse | Claude Sonnet | Analyse marketing |
| Frontend | Jinja2 + CSS | Interface utilisateur |

### Coût Estimé par Rapport
- Extraction (GPT-5.2) : ~$0.10-0.25
- Analyse (Claude) : ~$0.30-0.50
- **Total : ~$0.40-0.75 par marque**

---

## Structure du Projet

```
meta-ads-analyzer/
├── app.py                      # Point d'entrée FastAPI
├── src/
│   ├── __init__.py
│   ├── extractor.py            # Browser-Use + GPT-5.2
│   ├── analyzer.py             # Claude Sonnet
│   ├── report.py               # Génération rapport
│   └── prompts/
│       └── analysis.txt        # Prompt d'analyse
├── templates/
│   ├── index.html              # Page d'accueil
│   ├── loading.html            # Page de chargement
│   └── report.html             # Template rapport
├── static/
│   └── style.css               # Styles CSS
├── data/
│   └── reports/                # Rapports générés
├── tests/
│   ├── test_extractor.py
│   ├── test_analyzer.py
│   └── test_report.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── PLAN.md                     # Ce fichier
```

---

# PHASE 1 : Setup du Projet

## 1.1 Initialisation

### Fichiers à créer

**requirements.txt**
```txt
# Web Framework
fastapi>=0.109.0
uvicorn>=0.27.0
jinja2>=3.1.0
python-multipart>=0.0.6

# Browser Automation
browser-use>=0.1.0
playwright>=1.40.0

# LLM APIs
langchain-openai>=0.3.0
anthropic>=0.39.0

# Utilities
python-dotenv>=1.0.0
aiofiles>=23.0.0
```

**.env.example**
```bash
# OpenAI (GPT-5.2 pour extraction)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.2

# Anthropic (Claude pour analyse)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

**.gitignore**
```
# Environment
.env
venv/
__pycache__/

# Data
data/reports/*.html
data/reports/*.json

# IDE
.vscode/
.idea/

# OS
.DS_Store
```

### Commandes d'installation
```bash
# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Mac/Linux
# ou: venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Installer Playwright
playwright install chromium

# Copier et configurer .env
cp .env.example .env
# Éditer .env avec vos clés API
```

### Critères de validation Phase 1
- [ ] Environnement virtuel créé
- [ ] Dépendances installées sans erreur
- [ ] Playwright chromium installé
- [ ] Fichier .env configuré avec les clés API

---

# PHASE 2 : Module d'Extraction (Browser-Use)

## 2.1 Fichier : src/extractor.py

### Objectif
Extraire automatiquement les publicités depuis Meta Ad Library en utilisant Browser-Use avec GPT-5.2.

### Code complet

```python
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
from langchain_openai import ChatOpenAI

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

    def _build_extraction_task(self, brand: str, max_ads: int = 20) -> str:
        """Construit la tâche d'extraction pour l'agent"""
        return f"""
        MISSION: Extraire les publicités de "{brand}" depuis Meta Ad Library.

        ÉTAPES:
        1. La page Meta Ad Library est déjà ouverte avec la recherche "{brand}"
        2. Attends que les publicités se chargent (2-3 secondes)
        3. Si un popup cookies apparaît, clique sur "Decline optional cookies" ou ferme-le
        4. Scroll vers le bas lentement (500px) et attends 2 secondes
        5. Répète le scroll 3-4 fois pour charger plus de publicités
        6. Pour chaque publicité visible (maximum {max_ads}), extrais:
           - text: Le texte principal de la publicité
           - headline: Le titre/accroche (souvent en gras)
           - cta: Le bouton d'action (Shop Now, Learn More, etc.)
           - format: image, video, ou carousel
           - advertiser: Nom de l'annonceur
           - start_date: Date de début si visible
           - platforms: facebook, instagram, etc.

        FORMAT DE SORTIE (JSON):
        {{
            "brand": "{brand}",
            "extraction_date": "YYYY-MM-DD",
            "total_ads": X,
            "ads": [
                {{
                    "id": 1,
                    "text": "...",
                    "headline": "...",
                    "cta": "...",
                    "format": "...",
                    "advertiser": "...",
                    "start_date": "...",
                    "platforms": ["..."]
                }}
            ]
        }}

        IMPORTANT:
        - Agis lentement comme un humain (délais entre actions)
        - Si le texte est tronqué avec "...", note ce qui est visible
        - Déduplique les publicités identiques
        - Retourne UNIQUEMENT le JSON, pas de texte supplémentaire
        """

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
        task = self._build_extraction_task(brand, max_ads)

        try:
            agent = Agent(
                task=task,
                llm=self.llm,
                browser_config={
                    "headless": False,  # Visible pour debug
                    "slow_mo": 100,     # Ralentir les actions
                }
            )

            # Naviguer vers l'URL et exécuter la tâche
            result = await agent.run(starting_url=url)

            # Parser le résultat JSON
            if isinstance(result, str):
                # Extraire le JSON de la réponse
                json_start = result.find("{")
                json_end = result.rfind("}") + 1
                if json_start != -1 and json_end > json_start:
                    result = json.loads(result[json_start:json_end])

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
```

### Tests : tests/test_extractor.py

```python
"""
tests/test_extractor.py
Tests pour le module d'extraction
"""

import pytest
import asyncio
from src.extractor import MetaAdsExtractor, extract_meta_ads


class TestMetaAdsExtractor:

    def test_build_url(self):
        extractor = MetaAdsExtractor()
        url = extractor._build_url("Notion", "FR")
        assert "facebook.com/ads/library" in url
        assert "q=Notion" in url
        assert "country=FR" in url

    def test_build_task(self):
        extractor = MetaAdsExtractor()
        task = extractor._build_extraction_task("TestBrand", 10)
        assert "TestBrand" in task
        assert "maximum 10" in task

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires API keys and browser")
    async def test_extract_real(self):
        """Test réel d'extraction (skip par défaut)"""
        result = await extract_meta_ads("Notion")
        assert "brand" in result
        assert "ads" in result
```

### Critères de validation Phase 2
- [ ] Le fichier src/extractor.py est créé
- [ ] Le test `python -m src.extractor` fonctionne
- [ ] L'extraction retourne un JSON valide
- [ ] Au moins 5 publicités sont extraites pour une marque connue

---

# PHASE 3 : Module d'Analyse (Claude)

## 3.1 Fichier : src/prompts/analysis.txt

### Prompt d'analyse stratégique

```
Tu es un expert en stratégie publicitaire et marketing digital avec 15 ans d'expérience.
Analyse cette publicité et fournis des insights stratégiques actionnables.

PUBLICITÉ À ANALYSER:
- Marque: {brand}
- Texte: {text}
- Headline: {headline}
- CTA: {cta}
- Format: {format}

ANALYSE REQUISE (niveau Essentiel):

1. HOOK TYPE
Identifie le type d'accroche principal:
- EMOTIONAL: Joue sur les émotions (peur, désir, fierté, appartenance)
- RATIONAL: Utilise la logique (faits, chiffres, comparaisons, preuves)
- SOCIAL_PROOF: S'appuie sur la preuve sociale (témoignages, popularité, reviews)
- URGENCY: Crée un sentiment d'urgence (temps limité, stock limité, offre spéciale)
- CURIOSITY: Suscite la curiosité (question, mystère, teaser, révélation)

2. TARGET AUDIENCE
Décris l'audience cible:
- Démographie: tranche d'âge, genre, revenus, localisation
- Psychographie: valeurs, intérêts, style de vie
- Niveau de conscience: unaware / problem-aware / solution-aware / product-aware

3. FUNNEL STAGE
Identifie l'étape du funnel:
- AWARENESS: Découverte de la marque, éducation du marché
- CONSIDERATION: Comparaison, évaluation des options
- CONVERSION: Achat immédiat, action directe

4. SCORE GLOBAL
Note la publicité de 1 à 10 basé sur:
- Clarté du message (le bénéfice est-il clair ?)
- Pertinence du CTA (pousse-t-il à l'action ?)
- Cohérence créative (le message et le format sont-ils alignés ?)

FORMAT DE SORTIE (JSON uniquement):
{
    "hook_type": "EMOTIONAL|RATIONAL|SOCIAL_PROOF|URGENCY|CURIOSITY",
    "hook_description": "Explication courte du hook utilisé",
    "target_audience": {
        "demographics": "Description démographique",
        "psychographics": "Description psychographique",
        "awareness_level": "unaware|problem_aware|solution_aware|product_aware"
    },
    "funnel_stage": "AWARENESS|CONSIDERATION|CONVERSION",
    "funnel_reasoning": "Pourquoi cette étape du funnel",
    "score": 7,
    "score_breakdown": {
        "clarity": 8,
        "cta_relevance": 7,
        "creative_coherence": 6
    },
    "key_insight": "L'insight le plus important en une phrase"
}
```

## 3.2 Fichier : src/analyzer.py

### Code complet

```python
"""
src/analyzer.py
Module d'analyse stratégique des publicités avec Claude
"""

import os
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()


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
            # Fallback prompt inline
            return self._get_default_prompt()

    def _get_default_prompt(self) -> str:
        """Prompt par défaut si le fichier n'existe pas"""
        return """
        Analyse cette publicité et retourne un JSON avec:
        - hook_type: EMOTIONAL|RATIONAL|SOCIAL_PROOF|URGENCY|CURIOSITY
        - target_audience: demographics, psychographics, awareness_level
        - funnel_stage: AWARENESS|CONSIDERATION|CONVERSION
        - score: 1-10
        - key_insight: insight principal

        Publicité:
        - Marque: {brand}
        - Texte: {text}
        - Headline: {headline}
        - CTA: {cta}
        """

    def _format_prompt(self, ad: dict, brand: str) -> str:
        """Formate le prompt avec les données de la publicité"""
        return self.prompt_template.format(
            brand=brand,
            text=ad.get("text", "N/A"),
            headline=ad.get("headline", "N/A"),
            cta=ad.get("cta", "N/A"),
            format=ad.get("format", "N/A")
        )

    def analyze_ad(self, ad: dict, brand: str) -> dict:
        """
        Analyse une seule publicité

        Args:
            ad: Données de la publicité
            brand: Nom de la marque

        Returns:
            dict: Analyse de la publicité
        """
        prompt = self._format_prompt(ad, brand)

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
        ads = extraction_result.get("ads", [])

        analyzed_ads = []
        total_score = 0
        hook_types = {}
        funnel_stages = {}

        for ad in ads:
            analysis = self.analyze_ad(ad, brand)

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

        # Trouver le hook dominant
        hooks = summary.get("hook_distribution", {})
        dominant_hook = max(hooks, key=hooks.get) if hooks else "N/A"

        # Trouver l'étape funnel dominante
        funnels = summary.get("funnel_distribution", {})
        dominant_funnel = max(funnels, key=funnels.get) if funnels else "N/A"

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
                "dominant_funnel_stage": dominant_funnel
            },
            "strategic_insights": [
                f"La marque {brand} utilise principalement des hooks de type {dominant_hook}",
                f"La majorité des publicités ciblent l'étape {dominant_funnel} du funnel",
                f"Score moyen des créatifs: {summary.get('average_score', 0)}/10"
            ],
            "top_performing_ads": [
                {
                    "text_preview": ad.get("text", "")[:100] + "...",
                    "score": ad.get("analysis", {}).get("score", 0),
                    "key_insight": ad.get("analysis", {}).get("key_insight", "N/A")
                }
                for ad in top_ads
            ]
        }


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
    # Exemple de données pour test
    test_data = {
        "brand": "TestBrand",
        "ads": [
            {
                "id": 1,
                "text": "Découvrez notre nouvelle collection. Livraison gratuite !",
                "headline": "Nouvelle Collection 2025",
                "cta": "Shop Now",
                "format": "image"
            }
        ]
    }

    result = analyze_extraction(test_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

### Critères de validation Phase 3
- [ ] Le fichier src/prompts/analysis.txt est créé
- [ ] Le fichier src/analyzer.py est créé
- [ ] Le test `python -m src.analyzer` fonctionne
- [ ] L'analyse retourne hook_type, target_audience, funnel_stage, score
- [ ] Les insights globaux sont générés correctement

---

# PHASE 4 : Génération de Rapport

## 4.1 Fichier : src/report.py

### Code complet

```python
"""
src/report.py
Module de génération de rapport HTML
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
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

        # Préparer les données pour le template
        context = {
            "brand": analyzed_result.get("brand", "Unknown"),
            "generation_date": datetime.now().strftime("%d %B %Y"),
            "generation_time": datetime.now().strftime("%H:%M"),
            "total_ads": len(analyzed_result.get("ads", [])),
            "average_score": analyzed_result.get("analysis_summary", {}).get("average_score", 0),
            "ads": analyzed_result.get("ads", []),
            "insights": analyzed_result.get("insights", {}),
            "hook_distribution": analyzed_result.get("analysis_summary", {}).get("hook_distribution", {}),
            "funnel_distribution": analyzed_result.get("analysis_summary", {}).get("funnel_distribution", {})
        }

        # Rendre le template
        html_content = template.render(**context)

        # Sauvegarder le fichier
        filename = f"{context['brand'].lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = self.output_dir / filename
        filepath.write_text(html_content, encoding="utf-8")

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
```

## 4.2 Fichier : templates/report.html

### Template HTML complet

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ brand }} - Ad Intelligence Report</title>
    <link rel="stylesheet" href="../static/style.css">
    <style>
        /* Styles inline pour rapport standalone */
        :root {
            --primary: #1a1a2e;
            --secondary: #e8b931;
            --background: #f8f9fa;
            --card: #ffffff;
            --text: #333333;
            --muted: #6c757d;
            --success: #28a745;
            --border: #dee2e6;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--background);
            color: var(--text);
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }

        /* Header */
        .header {
            background: var(--primary);
            color: white;
            padding: 60px 0;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .header .subtitle {
            opacity: 0.8;
            font-size: 1.1rem;
        }

        /* Stats Bar */
        .stats-bar {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px 0;
            background: white;
            border-bottom: 1px solid var(--border);
        }

        .stat-item {
            text-align: center;
            padding: 20px;
        }

        .stat-number {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--secondary);
        }

        .stat-label {
            font-size: 0.875rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Section */
        section {
            padding: 40px 0;
        }

        section h2 {
            font-size: 1.75rem;
            margin-bottom: 30px;
            color: var(--primary);
            border-bottom: 3px solid var(--secondary);
            padding-bottom: 10px;
            display: inline-block;
        }

        /* Ad Cards */
        .ads-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }

        .ad-card {
            background: var(--card);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 15px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .ad-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.12);
        }

        .ad-card-header {
            background: var(--primary);
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .ad-card-header .ad-number {
            font-weight: 600;
        }

        .ad-card-header .ad-score {
            background: var(--secondary);
            color: var(--primary);
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: 700;
        }

        .ad-card-body {
            padding: 20px;
        }

        .ad-text {
            font-size: 0.95rem;
            margin-bottom: 15px;
            color: var(--text);
        }

        .ad-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 15px;
        }

        .tag {
            display: inline-block;
            padding: 4px 12px;
            background: #e9ecef;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .tag.hook {
            background: #fff3cd;
            color: #856404;
        }

        .tag.funnel {
            background: #d4edda;
            color: #155724;
        }

        .tag.cta {
            background: var(--secondary);
            color: var(--primary);
        }

        .ad-insight {
            background: #f8f9fa;
            padding: 12px;
            border-radius: 8px;
            font-size: 0.875rem;
            border-left: 3px solid var(--secondary);
        }

        /* Insights Section */
        .insights-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .insight-card {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }

        .insight-card h3 {
            color: var(--primary);
            margin-bottom: 15px;
            font-size: 1.1rem;
        }

        .insight-card ul {
            list-style: none;
        }

        .insight-card li {
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
        }

        .insight-card li:last-child {
            border-bottom: none;
        }

        /* Footer */
        footer {
            background: var(--primary);
            color: white;
            padding: 30px 0;
            text-align: center;
            margin-top: 40px;
        }

        footer p {
            opacity: 0.8;
            font-size: 0.875rem;
        }

        /* Print styles */
        @media print {
            .header {
                padding: 30px 0;
            }
            .ad-card {
                break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="container">
            <h1>{{ brand }}</h1>
            <p class="subtitle">Ad Intelligence Report - {{ generation_date }}</p>
        </div>
    </header>

    <div class="stats-bar">
        <div class="container" style="display: contents;">
            <div class="stat-item">
                <div class="stat-number">{{ total_ads }}</div>
                <div class="stat-label">Publicités analysées</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{{ average_score }}/10</div>
                <div class="stat-label">Score moyen</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{{ insights.executive_summary.dominant_hook }}</div>
                <div class="stat-label">Hook dominant</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{{ insights.executive_summary.dominant_funnel_stage }}</div>
                <div class="stat-label">Étape funnel</div>
            </div>
        </div>
    </div>

    <main class="container">
        <section id="insights">
            <h2>Insights Stratégiques</h2>
            <div class="insights-grid">
                <div class="insight-card">
                    <h3>Résumé Exécutif</h3>
                    <ul>
                        {% for insight in insights.strategic_insights %}
                        <li>{{ insight }}</li>
                        {% endfor %}
                    </ul>
                </div>

                <div class="insight-card">
                    <h3>Distribution des Hooks</h3>
                    <ul>
                        {% for hook, count in hook_distribution.items() %}
                        <li><strong>{{ hook }}:</strong> {{ count }} publicité(s)</li>
                        {% endfor %}
                    </ul>
                </div>

                <div class="insight-card">
                    <h3>Étapes du Funnel</h3>
                    <ul>
                        {% for stage, count in funnel_distribution.items() %}
                        <li><strong>{{ stage }}:</strong> {{ count }} publicité(s)</li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </section>

        <section id="ads">
            <h2>Analyse des Publicités</h2>
            <div class="ads-grid">
                {% for ad in ads %}
                <div class="ad-card">
                    <div class="ad-card-header">
                        <span class="ad-number">Publicité #{{ loop.index }}</span>
                        <span class="ad-score">{{ ad.analysis.score | default(0) }}/10</span>
                    </div>
                    <div class="ad-card-body">
                        <p class="ad-text">{{ ad.text[:200] }}{% if ad.text|length > 200 %}...{% endif %}</p>

                        <div class="ad-meta">
                            {% if ad.headline %}
                            <span class="tag">{{ ad.headline[:30] }}{% if ad.headline|length > 30 %}...{% endif %}</span>
                            {% endif %}
                            {% if ad.cta %}
                            <span class="tag cta">{{ ad.cta }}</span>
                            {% endif %}
                            {% if ad.analysis.hook_type %}
                            <span class="tag hook">{{ ad.analysis.hook_type }}</span>
                            {% endif %}
                            {% if ad.analysis.funnel_stage %}
                            <span class="tag funnel">{{ ad.analysis.funnel_stage }}</span>
                            {% endif %}
                        </div>

                        {% if ad.analysis.key_insight %}
                        <div class="ad-insight">
                            <strong>Insight:</strong> {{ ad.analysis.key_insight }}
                        </div>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </section>
    </main>

    <footer>
        <div class="container">
            <p>Rapport généré le {{ generation_date }} à {{ generation_time }}</p>
            <p>Meta Ads Analyzer - Ad Intelligence Tool</p>
        </div>
    </footer>
</body>
</html>
```

### Critères de validation Phase 4
- [ ] Le fichier src/report.py est créé
- [ ] Le fichier templates/report.html est créé
- [ ] Le rapport HTML s'affiche correctement dans un navigateur
- [ ] Les données sont bien injectées dans le template
- [ ] Le fichier JSON est exporté

---

# PHASE 5 : Interface Web (FastAPI)

## 5.1 Fichier : app.py

### Code complet

```python
"""
app.py
Application FastAPI principale
"""

import os
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from src.extractor import MetaAdsExtractor
from src.analyzer import AdsAnalyzer
from src.report import ReportGenerator

load_dotenv()

# Initialisation
app = FastAPI(title="Meta Ads Analyzer", version="1.0.0")

# Static files et templates
static_path = Path(__file__).parent / "static"
templates_path = Path(__file__).parent / "templates"

app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# Instances des modules
extractor = MetaAdsExtractor()
analyzer = AdsAnalyzer()
report_generator = ReportGenerator()

# Store pour les jobs en cours
jobs = {}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Page d'accueil avec formulaire"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze")
async def analyze_brand(
    request: Request,
    brand: str = Form(...),
    country: str = Form(default="ALL")
):
    """
    Lance l'analyse d'une marque
    """
    job_id = f"{brand}_{country}_{asyncio.get_event_loop().time()}"
    jobs[job_id] = {"status": "processing", "brand": brand}

    try:
        # 1. Extraction
        jobs[job_id]["step"] = "extraction"
        extraction_result = await extractor.extract(brand, country)

        if "error" in extraction_result or len(extraction_result.get("ads", [])) == 0:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = extraction_result.get("error", "No ads found")
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error": "Impossible d'extraire les publicités. Réessayez plus tard."
                }
            )

        # 2. Analyse
        jobs[job_id]["step"] = "analysis"
        analyzed_result = analyzer.analyze_batch(extraction_result)
        analyzed_result["insights"] = analyzer.generate_insights(analyzed_result)

        # 3. Génération du rapport
        jobs[job_id]["step"] = "report"
        report_path = report_generator.generate(analyzed_result)
        json_path = report_generator.generate_json_export(analyzed_result)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["report_path"] = report_path
        jobs[job_id]["json_path"] = json_path

        # Retourner le rapport directement
        return FileResponse(
            report_path,
            media_type="text/html",
            filename=f"{brand}_report.html"
        )

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": str(e)}
        )


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Récupère le statut d'un job"""
    if job_id in jobs:
        return JSONResponse(jobs[job_id])
    return JSONResponse({"error": "Job not found"}, status_code=404)


@app.get("/download/{filename}")
async def download_report(filename: str):
    """Télécharge un rapport généré"""
    report_path = Path(__file__).parent / "data" / "reports" / filename
    if report_path.exists():
        return FileResponse(
            report_path,
            media_type="application/octet-stream",
            filename=filename
        )
    return JSONResponse({"error": "File not found"}, status_code=404)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


# Run avec: uvicorn app:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 5.2 Fichier : templates/index.html

### Template de la page d'accueil

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meta Ads Analyzer</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="landing">
        <div class="landing-content">
            <h1>Meta Ads Analyzer</h1>
            <p class="subtitle">Analysez les publicités de n'importe quelle marque sur Meta Ad Library</p>

            <form action="/analyze" method="POST" class="analyze-form" id="analyzeForm">
                <div class="form-group">
                    <label for="brand">Nom de la marque</label>
                    <input
                        type="text"
                        id="brand"
                        name="brand"
                        placeholder="Ex: Notion, Nike, Apple..."
                        required
                    >
                </div>

                <div class="form-group">
                    <label for="country">Pays</label>
                    <select id="country" name="country">
                        <option value="ALL">Tous les pays</option>
                        <option value="FR">France</option>
                        <option value="US">États-Unis</option>
                        <option value="GB">Royaume-Uni</option>
                        <option value="DE">Allemagne</option>
                    </select>
                </div>

                <button type="submit" class="btn-primary" id="submitBtn">
                    <span class="btn-text">Analyser</span>
                    <span class="btn-loading" style="display: none;">
                        <span class="spinner"></span>
                        Analyse en cours...
                    </span>
                </button>
            </form>

            <div class="features">
                <div class="feature">
                    <div class="feature-icon">🔍</div>
                    <h3>Extraction automatique</h3>
                    <p>Récupère toutes les publicités actives depuis Meta Ad Library</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">🤖</div>
                    <h3>Analyse IA</h3>
                    <p>Hook, audience cible, étape funnel et score pour chaque pub</p>
                </div>
                <div class="feature">
                    <div class="feature-icon">📊</div>
                    <h3>Rapport professionnel</h3>
                    <p>Insights stratégiques et recommandations actionnables</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('analyzeForm').addEventListener('submit', function() {
            document.querySelector('.btn-text').style.display = 'none';
            document.querySelector('.btn-loading').style.display = 'inline-flex';
            document.getElementById('submitBtn').disabled = true;
        });
    </script>
</body>
</html>
```

## 5.3 Fichier : static/style.css

### Styles CSS complets

```css
/* Meta Ads Analyzer - Styles */

:root {
    --primary: #1a1a2e;
    --secondary: #e8b931;
    --background: #f8f9fa;
    --card: #ffffff;
    --text: #333333;
    --muted: #6c757d;
    --border: #dee2e6;
    --error: #dc3545;
    --success: #28a745;
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: var(--background);
    color: var(--text);
    line-height: 1.6;
}

/* Landing Page */
.landing {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--primary) 0%, #16213e 100%);
    padding: 40px 20px;
}

.landing-content {
    max-width: 600px;
    width: 100%;
    text-align: center;
}

.landing h1 {
    color: white;
    font-size: 2.5rem;
    margin-bottom: 10px;
}

.landing .subtitle {
    color: rgba(255, 255, 255, 0.8);
    font-size: 1.1rem;
    margin-bottom: 40px;
}

/* Form */
.analyze-form {
    background: white;
    padding: 40px;
    border-radius: 16px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
    margin-bottom: 40px;
}

.form-group {
    margin-bottom: 20px;
    text-align: left;
}

.form-group label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: var(--text);
}

.form-group input,
.form-group select {
    width: 100%;
    padding: 14px 16px;
    border: 2px solid var(--border);
    border-radius: 8px;
    font-size: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.form-group input:focus,
.form-group select:focus {
    outline: none;
    border-color: var(--secondary);
    box-shadow: 0 0 0 3px rgba(232, 185, 49, 0.2);
}

.btn-primary {
    width: 100%;
    padding: 16px 24px;
    background: var(--secondary);
    color: var(--primary);
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s, transform 0.2s;
}

.btn-primary:hover {
    background: #d4a82a;
    transform: translateY(-2px);
}

.btn-primary:disabled {
    opacity: 0.7;
    cursor: not-allowed;
    transform: none;
}

.btn-loading {
    display: inline-flex;
    align-items: center;
    gap: 10px;
}

.spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--primary);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Features */
.features {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
}

@media (max-width: 768px) {
    .features {
        grid-template-columns: 1fr;
    }
}

.feature {
    background: rgba(255, 255, 255, 0.1);
    padding: 25px 20px;
    border-radius: 12px;
    color: white;
}

.feature-icon {
    font-size: 2rem;
    margin-bottom: 10px;
}

.feature h3 {
    font-size: 1rem;
    margin-bottom: 8px;
}

.feature p {
    font-size: 0.875rem;
    opacity: 0.8;
}

/* Error Page */
.error-container {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 40px 20px;
}

.error-content {
    max-width: 500px;
}

.error-icon {
    font-size: 4rem;
    margin-bottom: 20px;
}

.error-content h1 {
    color: var(--error);
    margin-bottom: 15px;
}

.error-content p {
    color: var(--muted);
    margin-bottom: 30px;
}

.btn-secondary {
    display: inline-block;
    padding: 12px 24px;
    background: var(--primary);
    color: white;
    text-decoration: none;
    border-radius: 8px;
    transition: background 0.2s;
}

.btn-secondary:hover {
    background: #2d2d4a;
}
```

## 5.4 Fichier : templates/error.html

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erreur - Meta Ads Analyzer</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="error-container">
        <div class="error-content">
            <div class="error-icon">⚠️</div>
            <h1>Une erreur s'est produite</h1>
            <p>{{ error }}</p>
            <a href="/" class="btn-secondary">Retour à l'accueil</a>
        </div>
    </div>
</body>
</html>
```

### Critères de validation Phase 5
- [ ] Le fichier app.py est créé
- [ ] Les templates index.html et error.html sont créés
- [ ] Le fichier static/style.css est créé
- [ ] `uvicorn app:app --reload` lance le serveur sans erreur
- [ ] La page http://localhost:8000 s'affiche correctement
- [ ] Le formulaire envoie une requête POST

---

# PHASE 6 : Tests et Validation

## 6.1 Tests à effectuer

### Test 1 : Installation
```bash
# Dans le dossier du projet
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Éditer .env avec vos clés API
```

### Test 2 : Module Extractor
```bash
python -m src.extractor
# Doit afficher un JSON avec les pubs de "Notion"
```

### Test 3 : Module Analyzer
```bash
python -m src.analyzer
# Doit afficher une analyse de pub test
```

### Test 4 : Application Web
```bash
uvicorn app:app --reload
# Ouvrir http://localhost:8000
# Entrer "Notion" et cliquer Analyser
```

### Test 5 : Rapport généré
- [ ] Le rapport HTML s'ouvre dans le navigateur
- [ ] Les données sont affichées correctement
- [ ] Le score moyen est calculé
- [ ] Les insights sont pertinents

## 6.2 Checklist finale

- [ ] Extraction fonctionne sur Meta Ad Library
- [ ] Analyse retourne hook/audience/funnel/score
- [ ] Rapport HTML est généré et lisible
- [ ] Interface web est fonctionnelle
- [ ] Export JSON fonctionne
- [ ] Gestion des erreurs en place

---

# PHASE 7 : Déploiement (Optionnel)

## 7.1 Déploiement sur Render

**render.yaml**
```yaml
services:
  - type: web
    name: meta-ads-analyzer
    env: python
    buildCommand: pip install -r requirements.txt && playwright install chromium
    startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: ANTHROPIC_API_KEY
        sync: false
```

## 7.2 Déploiement sur Railway

```bash
# Installer Railway CLI
npm install -g @railway/cli

# Login et déployer
railway login
railway init
railway up
```

## 7.3 Variables d'environnement en production

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_MODEL=gpt-5.2
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

---

# Résumé des Phases

| Phase | Description | Fichiers | Durée estimée |
|-------|-------------|----------|---------------|
| 1 | Setup projet | requirements.txt, .env, .gitignore | 15 min |
| 2 | Extraction | src/extractor.py | 45 min |
| 3 | Analyse | src/analyzer.py, prompts/analysis.txt | 45 min |
| 4 | Rapport | src/report.py, templates/report.html | 30 min |
| 5 | Interface Web | app.py, templates/*, static/* | 45 min |
| 6 | Tests | - | 30 min |
| 7 | Déploiement | render.yaml (optionnel) | 30 min |

**Durée totale estimée : 3-4 heures**

---

# Notes Importantes

## Limitations connues

1. **Extraction** : Meta peut bloquer si trop de requêtes. Solution : ajouter des délais.
2. **CAPTCHA** : Si un CAPTCHA apparaît, l'extraction échouera. Solution : utiliser le fallback manuel.
3. **Vidéos** : Seule la vignette est analysée, pas le contenu vidéo.

## Coûts API

- GPT-5.2 (extraction) : ~$0.10-0.25 par marque
- Claude (analyse) : ~$0.30-0.50 par marque
- **Total : ~$0.40-0.75 par rapport**

## Évolutions futures possibles

1. Support Google Ads Transparency
2. Support LinkedIn Ad Library
3. Historique des analyses
4. Comparaison entre marques
5. Alertes sur nouvelles publicités

---

*Document créé le {{ date }} - Version 1.0*
