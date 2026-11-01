# Jalon 3 — Choix de conception

Journal des décisions prises pendant l'implémentation du jalon 3 (`notebooks/03_jalon3_agent_malicieux.ipynb`). Une section par sous-tâche, mise à jour à chaque nouvelle implémentation.

## Découpage

| | Sous-tâche | État |
|---|---|---|
| T1 | Génération du scénario (A, malveillant, mélange) | fait |
| T2 | Algorithme de B (adaptation de l'inv-2-MR-Sort, vitesse) | fait |
| T3 | Identification du modèle de A | à cadrer |
| T4 | Évaluation contre la vérité terrain | à cadrer |
| T5 | Exemple de démonstration | à cadrer |
| T6 | Modélisation du jeu (partie 2) | à cadrer |
| T7 | Stratégies de brouillage | à cadrer |
| T8 | Évaluation de l'impact | à cadrer |
| T9 | Livrables et soutenance | à cadrer |

---

## T1. Génération du scénario

### Choix et raisons

| Choix | Raison |
|---|---|
| **Paramètres par défaut : 6 critères, 3 catégories, 300 objets pour A**, tous configurables (`ScenarioConfig`) | Format le plus rapide pour lincs (comme `cr06_ca03` au jalon 2) et 300 objets de A donnent 600 objets au total, taille où les résultats du jalon 2 sont corrects. Rien n'est figé : on peut faire varier `n`, `p` et `n_A` pour tester la robustesse. |
| **Le malveillant envoie autant d'objets que A** (`ratio_malveillant = 1`) | C'est l'énoncé : une donnée supplémentaire par donnée de A. B reçoit donc un mélange 50/50. Le ratio reste un paramètre pour les variantes. |
| **Modèle du malveillant tiré avec le même générateur que celui de A** | Cas le plus neutre : les deux modèles sont indiscernables *a priori*, B ne peut pas reconnaître le malveillant à la forme de son modèle. Un générateur différent reste possible plus tard. |
| **Performances `x` uniformes sur [0,1]ⁿ pour A et le malveillant** (`loi_x`, `loi_x_malveillant`) | Même loi que les datasets du jalon 2 et le test du jalon 1. Les `x` ne portent aucune information sur la source : le malveillant « basique » ne triche que sur les étiquettes. La loi est un paramètre, car la partie 2 pourra faire placer au malveillant ses objets ailleurs (c'est un levier de stratégie). |
| **Poids : Dirichlet(1,…,1)** | Tirage uniforme sur le simplexe : positifs, somme 1, sans préférence pour des poids égaux ou déséquilibrés. |
| **λ uniforme dans [0,5 ; 1[** | Pour λ ≤ 0,5, deux coalitions disjointes pourraient franchir la même frontière, ce qui n'a pas de sens pour une « majorité ». λ = 1 est exclu : il exigerait tous les critères. |
| **Profils : p−1 valeurs par critère tirées dans [0,1] puis triées** | Impose b¹ ≤ b² ≤ … sur chaque critère, condition d'un MR-Sort valide. |
| **Rejet des modèles dégénérés** : on retire le modèle si sa plus petite catégorie contient moins de 10 % des objets d'un tirage de contrôle de 10 000 points (`min_part_categorie`, 1000 essais maximum, erreur explicite ensuite) | Une catégorie quasi vide rend le problème trivial (prédire une constante suffit) ou inapprenable (3 exemples sur 300), et les deux sources se contredisent à peine. 10 % laisse environ 30 exemples par catégorie sur 300. Le contrôle se fait sur la loi des objets du scénario. |
| **Même filtre pour A et le malveillant** | Le rejet biaise légèrement la loi des modèles, mais les deux sources restent symétriques, ce qui préserve l'hypothèse « même générateur ». |
| **Règle `predict` en numpy reprise du jalon 2** (float32, poids bruts, seuil 1) | Déjà validée à 100 % contre lincs. Les modèles tirés ont `raw_weights = weights / lmbda`, donc le seuil vaut 1 et le code est réutilisé tel quel. |
| **Sources aléatoires indépendantes** (`SeedSequence.spawn`) pour chaque modèle, chaque lot de `x`, le mélange et le test | Changer une option ne décale pas les autres tirages : deux scénarios qui diffèrent d'un seul paramètre restent comparables. |
| **Lignes mélangées** | B ne doit pas deviner la source par la position (A d'abord, malveillant ensuite). |
| **Le scénario conserve la vérité terrain** (`source`, `model_A`, `model_M`) à côté de ce que voit B (`X`, `y`) | Nécessaire pour l'évaluation (T4). Au jalon 2, l'absence de vérité terrain empêchait de mesurer la qualité réelle. |
| **Jeu de test de 1000 objets, de même loi que A, étiqueté par le modèle de A** | Référence de la qualité de B : proportion d'objets classés comme le modèle de A, définition du jalon 1. |
| **Notebook autonome : `predict` est recopié du jalon 2** | Pas de module Python partagé dans le dépôt. Évite un refactor pour l'instant. À reconsidérer si le code dupliqué grossit. |

### Tests (tous passés sur 30 scénarios)

1. Reproductibilité : même graine, mêmes données ; graines différentes, données différentes.
2. Étiquettes cohérentes avec le modèle de la source ; jeu de test cohérent avec le modèle de A.
3. Modèles valides : poids ≥ 0 de somme 1, λ ∈ [0,5 ; 1[, profils croissants dans [0,1].
4. Aucune catégorie sous le seuil ; en moyenne 3,6 essais de rejet par modèle (20 au maximum).
5. Tailles des sources correctes et lignes mélangées (part de A dans la première moitié : 0,499).
6. Indiscernabilité : test de Kolmogorov-Smirnov A contre malveillant par critère, 6,1 % de p-valeurs < 0,05 (attendu 5 %). Les `x` ne trahissent pas la source.
7. Accord de 100 % entre `predict` (numpy) et lincs sur un modèle tiré.
8. Un seuil impossible lève une erreur claire.

### Observation

Sur le scénario d'exemple (graine 0), A et le malveillant ont des répartitions de catégories très différentes (A : 58 / 16 / 26 %, malveillant : 36 / 53 / 11 %). C'est une différence naturelle entre deux modèles aléatoires. Elle pourra aider B à séparer les sources, mais c'est un indice et non une garantie.

---

## T2. Algorithme de B

`learn_B(X, y, p)` sépare le mélange reçu en deux segments et apprend un MR-Sort par segment. C'est l'inv-2-MR-Sort du jalon 2, rendu plus rapide. Il ne décide pas lequel des deux modèles est celui de A (T3).

### Choix et raisons

| Choix | Raison |
|---|---|
| **B reste aveugle** : l'algorithme ne connaît ni la proportion des sources ni le niveau de bruit | Plus général : B reste correct si le malveillant envoie plus ou moins que A. Les erreurs de proportion du jalon 2 (0,09 à 0,12) sont jugées acceptables. Exploiter le 50/50 pourra être testé plus tard. |
| **Algorithme du jalon 2 conservé** : alternance apprentissage lincs par segment / réaffectation lexicographique (écart de catégorie, puis marge), déplacement seulement si strictement mieux expliqué | Déjà justifié et validé au jalon 2. T2 n'y touche que pour la vitesse. |
| **4 départs (1 guidé + 3 aléatoires), exécutés en parallèle avec `joblib` (backend `loky`)** | Les départs sont indépendants. Au jalon 2, le départ guidé gagne 13 fois sur 31 et les aléatoires 18 fois : aucun ne domine. En parallèle, 4 départs coûtent le même temps que 2. `loky` sérialise les fonctions du notebook avec cloudpickle, ce que `multiprocessing` ne fait pas sous macOS. |
| **Parallélisme sur les départs seulement** | Simple, sans parallélisme imbriqué. Les deux segments d'une itération dépendent de la réaffectation précédente. |
| **Arrêt quand moins de 1 % des objets changent de segment** (`TOL_CHANGES`), ou après `MAX_ITER` | Au jalon 2, l'arrêt strict était presque toujours épuisé par `MAX_ITER` (20 itérations sur 4 fichiers). Les dernières itérations ne déplacent que quelques objets. `TOL_CHANGES = 0` retrouve l'arrêt strict. |
| **`MAX_ITER = 10`** | Choix empirique, voir la validation. |
| **`ITER_SECONDS = 1,0` et `POLISH_SECONDS = 4,0` inchangés** | Le polish final fixe la qualité du résultat et n'a pas été retenu pour les tests. |
| **`share_ambiguous` abandonné** | La phase 1 du jalon 2 conclut qu'il ne fait pas mieux et coûte 23 % de temps. Le code est plus simple. |
| **Les modèles renvoyés sont purement numpy** (`profiles`, `raw_weights`, `weights`, `lmbda`), sans objets lincs | Les objets lincs ne se sérialisent pas entre processus, et T3 et T4 n'utilisent que `predict` en numpy. |
| **Mêmes graines `seed * 100 + r` qu'au jalon 2** | Comparaison équitable avec la version séquentielle. |
| **`n_jobs=1` désactive le parallélisme** | Référence séquentielle pour la validation et le débogage. |
| **Dépendance ajoutée : `joblib`** (`uv add joblib`, version 1.6.0, avec `cloudpickle`) | Reproductible pour toute l'équipe via `pyproject.toml` et `uv.lock`. |

### Constat sur lincs

lincs est multithread (OpenMP) : un apprentissage seul utilise environ 5 cœurs (temps CPU / temps mur ≈ 5). Quatre départs parallèles se partagent donc les 8 cœurs et chaque apprentissage, limité à 1 s, fait moins de travail : précision d'apprentissage de 0,75 seul, contre 0,71 à 4 en parallèle (et 0,71 seul avec un thread). Le parallélisme des départs n'apporte donc pas un gain de 4. Le gain de temps vient surtout de la réduction des itérations et de l'arrêt à 1 %.

### Validation sur les fichiers du jalon 2

**Protocole** : 4 fichiers `n0600_rep50-50_noise00` (`type_a` et `type_b`, dossiers `cr06_ca03` et `cr08_ca04`), graine 0, 10 % de test, comme au jalon 2. Résultats dans `results/t2_validation.csv`.

| Variante | `deux_test` | écart vs jalon 2 | `erreur_proportion` | itérations | temps moyen (min–max) |
|---|---|---|---|---|---|
| jalon 2 (séquentiel, 20 it., arrêt strict) | 0,967 ± 0,030 | — | 0,033 | 20 | 418 s (122–1081) |
| parallèle, 4 départs, 8 it. | 0,917 ± 0,053 | −0,050 | 0,056 | 8 | 145 s (25–486) |
| **parallèle, 4 départs, 10 it. (retenu)** | **0,954 ± 0,028** | **−0,012** | 0,071 | 9,5 | **41 s (29–53)** |
| parallèle, 4 départs, 20 it. | 0,929 ± 0,037 | −0,037 | 0,076 | 19,5 | 67 s (46–89) |
| parallèle, 2 départs, 10 it. | 0,913 ± 0,042 | −0,054 | 0,041 | 9 | 39 s (27–52) |

(± : écart-type entre les 4 fichiers. L'écart-type de l'écart apparié à la référence est de 3,2 points pour la variante retenue.)

**Configuration retenue** : 4 départs en parallèle, `MAX_ITER = 10`, `TOL_CHANGES = 0,01`. C'est la seule variante rapide qui reste dans les 1 à 2 points du jalon 2 (−1,2 point), et elle tient l'objectif de moins de 60 s (environ 10 fois plus rapide que le jalon 2).

### Limites

- **Peu de données** : 4 fichiers, une graine, 60 objets de test (1,7 point par objet). Les écarts de 3 à 5 points entre variantes sont du même ordre que le bruit. L'ordre 8 < 20 < 10 itérations n'est pas monotone, donc on ne peut pas affirmer que 10 est strictement meilleur que 8 ou 20 : seulement que 10 ne dégrade pas nettement le jalon 2. Le nombre de graines et de fichiers pourra être augmenté si T4 révèle un problème.
- **La proportion est moins bien retrouvée** : `erreur_proportion` de 0,071 contre 0,033. Le petit segment est moins bien dimensionné, ce qui pèse sur T3.
- **Surapprentissage accru ou ajustement moindre** : `deux_train` baisse de 0,996 à 0,974 avec moins d'itérations.
- **Pureté de la partition** : sur le scénario de démonstration T1 (graine 0), l'accord entre segments trouvés et sources réelles est de 0,78 (0,76 avec 20 itérations). Les modèles expliquent 99 % des objets, mais ne séparent pas les sources proprement. Un seul scénario, mais c'est le point à regarder en T3 et T4.
- **Une anomalie de temps** : un essai à 8 itérations a pris 486 s sur un fichier (contre 46 à 50 s pour les autres variantes sur ce même fichier), sans cause identifiée.
- **Exécution du notebook** : les mesures ont été faites avec des scripts lancés dans le `.venv` du projet. Le notebook a été généré mais n'a pas été exécuté par `nbconvert` (le noyau `python3` disponible n'est pas celui du `.venv`), donc il est livré sans sorties enregistrées.
