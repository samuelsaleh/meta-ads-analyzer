# Meta Ads Analyzer

> Mini-app web pour analyser les publicités Meta d'une marque et générer un rapport stratégique.

## Fonctionnalités

- **Extraction automatique** des publicités depuis Meta Ad Library
- **Analyse IA** de chaque publicité (hook, audience, funnel, score)
- **Rapport professionnel** HTML avec insights stratégiques

## Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Backend | FastAPI |
| Extraction | Browser-Use + GPT-5.2 |
| Analyse | Claude Sonnet |
| Frontend | Jinja2 + CSS |

## Installation

```bash
# Cloner le repo
git clone https://github.com/YOUR_USERNAME/meta-ads-analyzer.git
cd meta-ads-analyzer

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Mac/Linux
# ou: venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Installer Playwright
playwright install chromium

# Configurer les clés API
cp .env.example .env
# Éditer .env avec vos clés
```

## Configuration

Créez un fichier `.env` avec :

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Utilisation

```bash
# Lancer le serveur
uvicorn app:app --reload

# Ouvrir http://localhost:8000
```

1. Entrez le nom d'une marque (ex: "Notion")
2. Cliquez "Analyser"
3. Attendez 30-60 secondes
4. Consultez le rapport généré

## Structure du Projet

```
meta-ads-analyzer/
├── app.py                 # FastAPI app
├── src/
│   ├── extractor.py       # Browser-Use extraction
│   ├── analyzer.py        # Claude analysis
│   ├── report.py          # HTML generation
│   └── prompts/
│       └── analysis.txt   # Analysis prompt
├── templates/             # HTML templates
├── static/                # CSS styles
├── data/reports/          # Generated reports
└── PLAN.md               # Detailed implementation plan
```

## Coût par Analyse

| Opération | Coût estimé |
|-----------|-------------|
| Extraction (GPT-5.2) | ~$0.10-0.25 |
| Analyse (Claude) | ~$0.30-0.50 |
| **Total** | **~$0.40-0.75** |

## Plan de Développement

Voir [PLAN.md](./PLAN.md) pour le plan d'implémentation détaillé en 7 phases.

## License

MIT
