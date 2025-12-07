# PDF Document Analysis API

Outil d'analyse structurelle de documents PDF avec extraction automatique d'éléments (titres, sections, tableaux, images) et calcul de statistiques détaillées.

## 📋 Fonctionnalités

- **Extraction d'éléments** : Titres, sous-titres, sections, paragraphes, listes, tableaux, images
- **Base de données relationnelle** : Stockage SQLite avec schéma optimisé
- **API REST complète** : Endpoints pour ingestion, consultation et export
- **Statistiques avancées** : Métriques par document et globales
- **Export de données** : CSV pour tableaux, JSON pour métadonnées

## 🚀 Installation et Exécution

### Prérequis
- Python 3.8+
- pip ou conda

### Installation des dépendances avec pip
```bash
pip install -r requirements.txt
```

### Lancement de l'API
```bash
python main.py
```

L'API sera disponible sur : `http://localhost:8000`

Documentation interactive : `http://localhost:8000/docs`

## 📖 Utilisation

### 1. Télécharger un document PDF
```bash
curl -X POST "http://localhost:8000/documents/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@example.pdf"
```

**Réponse :**
```json
{
  "message": "Document processed successfully",
  "document_uuid": "0317cd01-b194-...",
  "filename": "example.pdf",
  "elements_count": 151,
  "statistics": {
    "title_count": 2,
    "section_count": 1,
    "table_count": 2,
    "image_count": 13,
    "avg_text_density_per_page": 1488.66,
    "avg_hierarchical_depth": 1.88,
    "avg_paragraph_length": 19.62,
    "section_distribution": {
      "1": 1
    }
  }
}
```

### 2. Lister les documents analysés
```bash
curl -X GET "http://localhost:8000/documents"
```

### 3. Obtenir les éléments d'un document
```bash
# Tous les éléments
curl -X GET "http://localhost:8000/documents/{uuid}/elements"

# Filtrer par type
curl -X GET "http://localhost:8000/documents/{uuid}/elements?element_type=table"

# Filtrer par page
curl -X GET "http://localhost:8000/documents/{uuid}/elements?page_number=2"
```

### 4. Consulter les statistiques
```bash
# Statistiques d'un document
curl -X GET "http://localhost:8000/documents/{uuid}/statistics"

# Statistiques globales
curl -X GET "http://localhost:8000/statistics/global"
```

### 5. Exporter les données
```bash
# Export des tableaux en CSV
curl -X GET "http://localhost:8000/documents/{uuid}/export/tables" \
     --output tables.csv

# Export des métadonnées (doc info et statistiques) en JSON
curl -X GET "http://localhost:8000/documents/{uuid}/export/json" \
     --output metadata.json
```

## 🏗️ Architecture

```
├── main.py              # Point d'entrée FastAPI
├── file_parser.py       # Extraction et classification d'éléments
├── doc_storage.py       # Gestion base de données SQLite
├── requirements.txt     # Dépendances Python
└── README.md           # Ce fichier
```

### Composants principaux

- **`PDFExtractor`** : Analyse structurelle des PDF avec PyMuPDF
- **`DocumentStorage`** : Couche d'abstraction base de données
- **API REST** : Endpoints FastAPI pour toutes les opérations

## 📊 Types d'éléments détectés

| Type | Critères de détection |
|------|----------------------|
| **Title** | Police ≥16pt + gras |
| **Subtitle** | Police ≥14pt + gras |
| **Section** | Police ≥12pt + gras OU ≥13pt + ≤20 mots |
| **Paragraph** | Texte standard |
| **List Item** | Patterns : •, 1., a), -, etc. |
| **Table** | Détection automatique PyMuPDF |
| **Image** | Extraction d'images intégrées |

## 📈 Statistiques calculées

### Par document
- Nombre de titres, sections, tableaux, images
- Profondeur hiérarchique moyenne
- Densité de texte par page
- Longueur moyenne des paragraphes
- Distribution des sections par page

### Globales
- Résumé par type d'élément
- Moyennes sur tous les documents
- Statistiques comparatives

## 🔧 Configuration

### Base de données
Par défaut : `pdf_documents.sqlite` dans le répertoire courant.

Pour modifier :
```python
doc_storage = DocumentStorage(db_path="custom/path/documents.sqlite")
```

### Logging
Les logs sont configurés au niveau INFO. Pour plus de détails :
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🧪 Tests rapides

### Vérification de l'installation
```bash
curl -X GET "http://localhost:8000/health"
```

### Test complet
1. Télécharger un PDF de test
2. Vérifier les statistiques générées
3. Tester les exports CSV/JSON
4. Consulter les statistiques globales

## 🐛 Dépannage

### Erreurs communes

**"Only PDF files are allowed"**
- Vérifiez l'extension du fichier (.pdf)

**"Document not found"**
- Vérifiez l'UUID retourné lors de l'upload

**"Error processing document"**
- Vérifiez que le PDF n'est pas corrompu ou protégé

### Logs
Consultez les logs de l'application pour plus de détails sur les erreurs.

## 📝 Notes techniques

- **PyMuPDF** pour l'extraction PDF haute performance
- **SQLite** avec index optimisés pour les requêtes
- **FastAPI** avec validation automatique des données
- **Classification basée sur les polices** pour l'identification des éléments

## 🚀 Améliorations possibles
- Export json et csv pour tout type de données.
- Téléchargement possible pour les figures et images.
- Traitement du contenu texte.
