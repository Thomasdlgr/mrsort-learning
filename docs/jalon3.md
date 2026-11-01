# Jalon 3 — Choix de conception

Journal des décisions prises pendant l'implémentation du jalon 3 (`notebooks/03_jalon3_agent_malicieux.ipynb`). Une section par sous-tâche, mise à jour à chaque nouvelle implémentation.

## Découpage

| | Sous-tâche | État |
|---|---|---|
| T1 | Génération du scénario (A, malveillant, mélange) | fait |
| T2 | Algorithme de B (adaptation de l'inv-2-MR-Sort, vitesse) | fait |
| T3 | Identification du modèle de A | fait |
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
| **Paramètres par défaut : 6 critères, 3 catégories, 300 objets pour A**, tous configurables (`ScenarioConfig`) | Format le plus rapide pour lincs (comme `cr06_ca03` au jalon 2) et 300 objets de A donnent 450 objets au total à ratio 0,5 (600 à ratio 1), taille où les résultats du jalon 2 sont corrects. Rien n'est figé : on peut faire varier `n`, `p` et `n_A` pour tester la robustesse. |
| **Le malveillant envoie la moitié des objets de A par défaut** (`ratio_malveillant = 0,5`) | *Modifié en T3* (T1 avait posé 1,0). L'énoncé dit que le malveillant « peut » envoyer une donnée additionnelle par donnée de A : il envoie *au plus* autant que A. À ratio 1 les deux sources sont symétriques et le modèle de A est inidentifiable (T3). 0,5 est le cas où l'identification par la taille fonctionne (A fait 67 % de ce que reçoit B), donc celui de l'exemple de la partie 1. Le ratio est la variable de T4 : balayage sur {1,0 ; 0,85 ; 0,7 ; 0,5}. |
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
5. Tailles des sources correctes et lignes mélangées (part de A dans la première moitié des lignes : 0,665 pour 0,667 attendu à ratio 0,5 ; l'assertion compare à `n_A / (n_A + n_M)`, et non plus à 0,5).
6. Indiscernabilité : test de Kolmogorov-Smirnov A contre malveillant par critère, 3,3 % de p-valeurs < 0,05 à ratio 0,5 (6,1 % à ratio 1 ; attendu 5 %). Les `x` ne trahissent pas la source.
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

---

## T3. Identification du modèle de A

`identify_A(result_B, seuil)` décide lequel des deux modèles appris par `learn_B` est celui de A. `evaluate_identification(scenario, result_B, decision)` compare ce résultat à la vérité terrain.

### Le problème

Avec les choix de T1 (même générateur de modèles, même loi des `x`) et un ratio de 1, les deux sources sont **symétriques** : choisir A est un pile ou face, même avec une séparation parfaite. L'information n'est pas dans les données. T3 consiste donc à choisir l'asymétrie que l'on accorde à B.

### Choix et raisons

| Choix | Raison |
|---|---|
| **Asymétrie : ratio du malveillant < 1, le plus grand segment est supposé celui de A** | L'énoncé dit que le malveillant « peut » envoyer une donnée additionnelle par donnée de A, donc *au plus* autant. C'est la seule asymétrie garantie par le sujet, contrairement à un échantillon sûr de A (non prévu) ou à une régularité du modèle de A (hypothèse extérieure). |
| **Ratio par défaut 0,5, balayage {1,0 ; 0,85 ; 0,7 ; 0,5} en T4** | À 0,5, A fait 67 % de ce que reçoit B : l'identification a une chance de fonctionner, l'exemple est lisible. Le balayage montre où elle s'effondre. Le ratio 1 est le meilleur choix du malveillant, donc un levier de la partie 2. |
| **Confiance = écart relatif de taille `(n_grand − n_petit) / N`, taille seulement** | Rien ne rend le modèle de A mieux ajusté que celui du malveillant. Ajouter la qualité d'ajustement créerait un signal artificiel. |
| **Abstention sous un seuil de confiance : B renvoie alors les deux modèles** | Quand les tailles sont proches, B annoncerait une certitude qu'il n'a pas. Confiance ≥ seuil donne un choix (donc seuil 0 : B choisit toujours, même à égalité, en prenant le segment 0). |
| **Seuil `SEUIL_CONFIANCE = 0,10`, provisoire** | Posé a priori d'après l'erreur de proportion du jalon 2 (environ 10 points). **Il sera calibré en T4** sur des scénarios de calibration distincts de ceux du rapport final. Les essais ci-dessous montrent qu'il est probablement trop bas. |
| **Sortie `Decision`** (dataclass) : `abstention`, `confiance`, `indice_segment_A`, `modele_A`, `modeles`, `tailles`, `seuil` | `modele_A` n'est renseigné que s'il y a un choix, `modeles` (les deux) que s'il y a abstention. |
| **Deux métriques** : `oracle` = précision du meilleur des deux modèles appris sur le jeu de test (séparation), `identifie` = précision du modèle choisi (identification) | Quand un résultat est mauvais, on sait si l'échec vient de T2 ou de T3. |
| **`identifie` vaut NaN en cas d'abstention** (et `bon_segment` aussi) | L'abstention est comptée à part (taux en T4) et la précision des cas où B se prononce se calcule avec `nanmean`. Remplacer NaN par `oracle` masquerait le coût de l'abstention. |
| **Indicateurs supplémentaires** : `bon_segment` (le segment choisi contient majoritairement des objets de A), `grand_segment_est_A` (idem pour le plus grand segment, abstention ou non), `accord` (pureté de la partition à une permutation près) | `grand_segment_est_A` mesure l'hypothèse elle-même, indépendamment du seuil : il servira à calibrer le seuil. |

### Tests

**Sans lincs, déterministes** (résultats de B synthétiques construits à partir de la vérité terrain d'un scénario T1) : tous passés.
1. Ratio 0,5, partition parfaite : B choisit le segment de A, `oracle` = `identifie` = 1, confiance = 1/3.
2. Numéros de segments permutés : même identification.
3. Ratio 1, partition parfaite : tailles égales, abstention, `identifie` = NaN, `oracle` = 1.
4. Seuil 0 : B choisit toujours, même à égalité.
5. Frontière : confiance exactement égale au seuil donne un choix, juste au-dessus une abstention.
6. Limite : si le malveillant envoie plus que A (ratio 2), l'hypothèse est fausse : B choisit le modèle du malveillant, `bon_segment` = 0, `identifie` < `oracle` = 1.
7. Partition aléatoire : `accord` entre 0,45 et 0,62.

**Essai réel** (chaîne `make_scenario` → `learn_B` → `identify_A` → `evaluate_identification`, résultats dans `results/t3_essais.csv`, environ 28 s par scénario) :

| Graine | Ratio | Segments trouvés | Segments réels | Confiance | Décision | `oracle` | `identifie` | `bon_segment` | `accord` |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0,5 | 285 / 165 | 300 / 150 | 0,27 | choix | 0,880 | 0,880 | oui | 0,75 |
| 2 | 0,5 | 261 / 189 | 300 / 150 | 0,16 | choix | 0,860 | 0,860 | oui | 0,63 |
| 3 | 0,5 | 305 / 145 | 300 / 150 | 0,36 | choix | 0,879 | 0,879 | oui | 0,73 |
| 1 | 1,0 | 365 / 235 | 300 / 300 | 0,22 | **choix (faux)** | 0,884 | 0,439 | **non** | 0,72 |
| 0 (exemple de la cellule T2) | 0,5 | 230 / 220 | 300 / 150 | 0,02 | abstention | non mesuré | — | — | 0,73 |

(Le dernier scénario n'est pas dans le CSV : il vient de la cellule d'essai de T2, qui utilise désormais le ratio 0,5 par défaut. Seuls ses segments et son accord ont été relevés, pas `oracle` : ne pas le comparer aux autres lignes sur ce point.)

### Ce que montrent ces essais

- **À ratio 0,5, l'hypothèse « le plus grand segment est A » est juste 3 fois sur 3**, avec des tailles trouvées proches des vraies (285/165, 261/189, 305/145 contre 300/150).
- **Mais le scénario de la graine 0 donne 230/220** : l'algorithme a rapproché les segments de 50/50. Avec le seuil provisoire, B s'abstient, ce qui est honnête mais montre que l'identification par la taille ne marche pas à tout coup, même à ratio 0,5. Sur 4 scénarios à ratio 0,5, 3 permettent un choix correct, 1 donne une abstention.
- **À ratio 1, B ne s'abstient pas et se trompe.** Les segments trouvés sont 365/235 alors que les vrais sont 300/300, soit une confiance de 0,22, au-dessus du seuil de 0,10. B choisit le modèle du malveillant (`identifie` = 0,44 pour un `oracle` de 0,88). Sans signal, les tailles trouvées s'écartent de 50/50 de plusieurs dizaines d'objets : une confiance de 0,22 ne prouve rien. **Le seuil provisoire de 0,10 est donc trop bas**, et le cas qui devait montrer l'abstention attendue montre le contraire. Ce résultat n'est pas une anomalie de code : les tests synthétiques 3 et 6 passent, c'est la partition de `learn_B` qui est déséquilibrée.
- **La séparation est moyenne** : `oracle` ≈ 0,86 à 0,88, soit 12 à 14 % des objets de test classés autrement que par le modèle de A, même en prenant le meilleur modèle. C'est la limite de T2 (accord segments / sources de 0,63 à 0,75, comme sur le scénario de T2 qui donnait 0,73 à 0,78), pas de T3.

### Limites

- **Le seuil n'est pas calibré.** `SEUIL_CONFIANCE = 0,10` est provisoire. Quatre essais ne suffisent pas à le fixer : T4 doit le calibrer sur des scénarios à ratio 1 (où il faut s'abstenir) et à ratio < 1 (où il faut choisir), distincts de ceux du rapport final.
- **L'algorithme tend à équilibrer les segments** (confirmé : 261/189 et 230/220 pour 300/150). L'écart de taille vu par B est donc plus petit que l'écart réel, et il est bruité de plusieurs dizaines d'objets. Le risque est que l'indicateur « taille » ne discrimine pas assez aux ratios intermédiaires (0,7 et 0,85).
- **L'hypothèse est exploitable par le malveillant** : il lui suffit d'envoyer autant d'objets que A. C'est le point de départ de la partie 2.
- **Peu de données** : 4 scénarios (5 avec l'exemple), tous mesurés avec une seule graine par ratio. Aucune moyenne ni écart-type n'est donnée, car ils n'auraient pas de sens à cette taille.
- **`n_A` = 300 est la seule taille testée.** Le comportement pour d'autres tailles reste à mesurer.
- **Le jeu de test suit la loi de A** (uniforme par défaut) : `oracle` et `identifie` mesurent la fidélité au modèle de A sur cette loi.
