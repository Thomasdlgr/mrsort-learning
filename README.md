# mrsort-learning

Projet SDP 2026-27 : apprentissage de modèles de tri multicritère **MR-Sort**
(programme linéaire en nombres entiers avec Gurobi, heuristique avec lincs) et
de mélanges de deux modèles (**inv-2-MR-Sort**).

## Installation

```bash
uv sync                  # crée .venv avec les dépendances de pyproject.toml
uv run jupyter lab       # ou ouvrir les notebooks dans VS Code (noyau .venv)
```

Gurobi nécessite une licence (la licence restreinte suffit pour les petits exemples).

## Organisation

| Dossier | Contenu |
|---|---|
| `docs/` | Sujet du projet et article de référence (Leroy, Mousseau, Pirlot 2011) |
| `data/` | `dataset0.txt` (jalon 1). `Datasets-Step2/` (jalon 2) n'est pas versionné : à déposer ici |
| `notebooks/` | Notebooks numérotés, à exécuter depuis ce dossier (chemins relatifs `../data`, `../results`) |
| `notebooks/archive/` | Notebooks d'exploration ou non exécutables, conservés pour mémoire |
| `results/` | CSV de résultats des benchmarks. `logs/` et `benchmark_results/` ne sont pas versionnés |

## Notebooks

0. `00_tp_gurobi` : TP de prise en main de Gurobi (programmes linéaires)
1. `01_jalon1_mrsort` : modèle MR-Sort en MIP, validation sur `dataset0`
2. `02_jalon2_final` : algorithme inv-2-MR-Sort (lincs) et benchmark sur `Datasets-Step2`

`notebooks/archive/` contient les variantes d'exploration (`jalon2_2mrsort`, `jalon2_ambigus`)
et `benchmark.ipynb`, qui dépend de scripts (`benchmark_run.py`, `benchmark_core.py`) présents
uniquement sur la branche `benchmark` : il ne s'exécute pas sur `main`.
