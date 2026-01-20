# Makefile pour SupportTicketsAgent

# Variables
PYTHON := python
MODULE := scripts.load_data

# Commandes
.PHONY: load-data clean

# Lancer le script d'ingestion
load-data:
	@echo "🚀 Lancement du script load_data.py..."
	$(PYTHON) -m $(MODULE)

# Optionnel : nettoyer __pycache__ et fichiers temporaires
clean:
	@echo "🧹 Nettoyage des fichiers __pycache__..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
