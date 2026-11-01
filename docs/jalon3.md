# Jalon 3 — Choix de conception

Journal des décisions prises pendant l'implémentation du jalon 3 (`notebooks/03_jalon3_agent_malicieux.ipynb`). Une section par sous-tâche, mise à jour à chaque nouvelle implémentation.

## Découpage

| | Sous-tâche | État |
|---|---|---|
| T1 | Génération du scénario (A, malveillant, mélange) | fait |
| T2 | Algorithme de B (adaptation de l'inv-2-MR-Sort, vitesse) | fait |
| T3 | Identification du modèle de A | fait |
| T4 | Évaluation contre la vérité terrain | fait |
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

`identify_A(result_B, X, y, seuil)` décide lequel des deux modèles appris par `learn_B` est celui de A, avec le critère des **objets expliqués**. `evaluate_identification(scenario, result_B, decision)` compare ce résultat à la vérité terrain. L'ancien critère par la taille des segments est conservé sous le nom `identify_A_taille` (méthode M2 des comparaisons). `run_B` enchaîne `learn_B` et `identify_A` : c'est la méthode de B (M3).

*Historique.* La première version de T3 choisissait le plus grand segment. Les essais puis le diagnostic ont montré que ce critère est fragile ; il a été remplacé par les objets expliqués (voir « Diagnostic T3 » plus bas). Cette section décrit l'état actuel et garde l'essai réel fait avec l'ancien critère, pour la trace.

### Le problème

Avec les choix de T1 (même générateur de modèles, même loi des `x`) et un ratio de 1, les deux sources sont **symétriques** : choisir A est un pile ou face, même avec une séparation parfaite. L'information n'est pas dans les données. T3 consiste donc à choisir l'asymétrie que l'on accorde à B.

### Choix et raisons

| Choix | Raison |
|---|---|
| **Asymétrie : ratio du malveillant < 1, A est majoritaire dans ce que reçoit B** | L'énoncé dit que le malveillant « peut » envoyer une donnée additionnelle par donnée de A, donc *au plus* autant. C'est la seule asymétrie garantie par le sujet, contrairement à un échantillon sûr de A (non prévu) ou à une régularité du modèle de A (hypothèse extérieure). |
| **Ratio par défaut 0,5, balayage {1,0 ; 0,85 ; 0,7 ; 0,5} en T4** | À 0,5, A fait 67 % de ce que reçoit B : l'identification a une chance de fonctionner, l'exemple est lisible. Le balayage montre où elle s'effondre. Le ratio 1 est le meilleur choix du malveillant, donc un levier de la partie 2. |
| **Critère : objets expliqués.** Chaque modèle appris explique `n_k` objets du mélange entier (il les classe dans la catégorie reçue) ; le plus grand `n_k` désigne le modèle de A. Confiance = `\|n_0 − n_1\| / N` | `learn_B` **équilibre** les segments : il trouve 261/189 pour 300/150 réels, 365/235 pour 300/300. La taille d'un segment est donc un mauvais indicateur de l'effectif réel. Le nombre d'objets expliqués ne dépend que des deux modèles et des données reçues, pas du rangement. Le diagnostic a donné 18 bons choix sur 18 à ratio < 1, contre 14 sur 18 pour la taille. |
| **Pas de qualité d'ajustement dans le critère** | Rien ne rend le modèle de A mieux ajusté que celui du malveillant : cela créerait un signal artificiel. Le critère compte les objets des deux sources, et n'avantage A que par son effectif. |
| **Abstention sous un seuil de confiance : B renvoie alors les deux modèles** | Quand les comptes sont proches, B annoncerait une certitude qu'il n'a pas. Confiance ≥ seuil donne un choix (donc seuil 0 : B choisit toujours, même à égalité, en prenant le segment 0). |
| **Seuil `SEUIL_CONFIANCE = 0`, provisoire** (pas d'abstention) | Aucune donnée ne permet encore de le fixer : il est calibré en T4 (`SEUIL_CALIBRE`) sur des scénarios distincts de ceux du rapport final. L'ancien critère a gardé son seuil a priori `SEUIL_TAILLE = 0,10`. |
| **Sortie `Decision`** (dataclass) : `abstention`, `confiance`, `indice_segment_A`, `modele_A`, `modeles`, `tailles`, `seuil`, `expliques` | `modele_A` n'est renseigné que s'il y a un choix, `modeles` (les deux) que s'il y a abstention. `expliques` donne `(n_0, n_1)` (None pour le critère « taille »). |
| **Deux métriques** : `oracle` = précision du meilleur des deux modèles appris sur le jeu de test (séparation), `identifie` = précision du modèle choisi (identification) | Quand un résultat est mauvais, on sait si l'échec vient de T2 ou de T3. |
| **`identifie` vaut NaN en cas d'abstention** (et `bon_choix`, `bon_segment` aussi) | L'abstention est comptée à part (taux en T4) et la précision des cas où B se prononce se calcule avec `nanmean`. Remplacer NaN par `oracle` masquerait le coût de l'abstention. |
| **Indicateurs supplémentaires** : `bon_choix` (le modèle choisi est le plus précis des deux en test), `bon_segment` (le segment choisi contient majoritairement des objets de A), `grand_segment_est_A`, `accord` (pureté de la partition à une permutation près) | `bon_choix` est la définition a posteriori du bon choix pour le diagnostic et T4. `grand_segment_est_A` mesure l'hypothèse de l'ancien critère. |
| **M1 (`learn_single`) conservé comme méthode de référence** | Répondre à « pourquoi pas un seul modèle ? » : T4 compare B à un modèle unique appris sur tout le mélange. |

### Tests

**Sans lincs, déterministes** (résultats de B synthétiques construits à partir de la vérité terrain d'un scénario T1) : 8 groupes, tous passés.
1. Ratio 0,5, partition parfaite : B choisit le modèle de A (qui explique au moins 300 objets, le modèle du malveillant au moins 150), `oracle` = `identifie` = 1.
2. Numéros de segments permutés : même identification.
3. Deux modèles identiques : comptes égaux, confiance 0, abstention dès que le seuil est strictement positif ; à seuil 0, B choisit le segment 0.
4. Seuil au-dessus de toute confiance : abstention, `identifie` = NaN, `oracle` = 1.
5. Frontière : confiance exactement égale au seuil donne un choix, juste au-dessus une abstention.
6. Limite : si le malveillant envoie plus que A (ratio 2), l'hypothèse est fausse : B choisit le modèle du malveillant, `bon_choix` = 0, `identifie` < `oracle` = 1.
7. Le choix ne dépend pas de la partition : avec un rangement aléatoire des objets (`accord` entre 0,45 et 0,62), B choisit encore le modèle de A.
8. Ancien critère `identify_A_taille` : choix, permutation, abstention à ratio 1 au seuil de 0,10, seuil 0, frontière.

**Essai réel, fait avec l'ancien critère « taille » et son seuil a priori de 0,10** (chaîne `make_scenario` → `learn_B` → `identify_A_taille` → `evaluate_identification`, résultats dans `results/t3_essais.csv`, environ 28 s par scénario) :

| Graine | Ratio | Segments trouvés | Segments réels | Confiance | Décision | `oracle` | `identifie` | `bon_segment` | `accord` |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0,5 | 285 / 165 | 300 / 150 | 0,27 | choix | 0,880 | 0,880 | oui | 0,75 |
| 2 | 0,5 | 261 / 189 | 300 / 150 | 0,16 | choix | 0,860 | 0,860 | oui | 0,63 |
| 3 | 0,5 | 305 / 145 | 300 / 150 | 0,36 | choix | 0,879 | 0,879 | oui | 0,73 |
| 1 | 1,0 | 365 / 235 | 300 / 300 | 0,22 | **choix (faux)** | 0,884 | 0,439 | **non** | 0,72 |
| 0 (exemple de la cellule T2) | 0,5 | 230 / 220 | 300 / 150 | 0,02 | abstention | non mesuré | — | — | 0,73 |

(Le dernier scénario n'est pas dans le CSV : il vient de la cellule d'essai de T2, qui utilise désormais le ratio 0,5 par défaut. Seuls ses segments et son accord ont été relevés, pas `oracle` : ne pas le comparer aux autres lignes sur ce point.)

### Ce que montrent ces essais (critère « taille »)

- **À ratio 0,5, l'hypothèse « le plus grand segment est A » est juste 3 fois sur 3**, avec des tailles trouvées proches des vraies (285/165, 261/189, 305/145 contre 300/150).
- **Mais le scénario de la graine 0 donne 230/220** : l'algorithme a rapproché les segments de 50/50. Avec le seuil provisoire, B s'abstient, ce qui est honnête mais montre que l'identification par la taille ne marche pas à tout coup, même à ratio 0,5. Sur 4 scénarios à ratio 0,5, 3 permettent un choix correct, 1 donne une abstention.
- **À ratio 1, B ne s'abstient pas et se trompe.** Les segments trouvés sont 365/235 alors que les vrais sont 300/300, soit une confiance de 0,22, au-dessus du seuil de 0,10. B choisit le modèle du malveillant (`identifie` = 0,44 pour un `oracle` de 0,88). Sans signal, les tailles trouvées s'écartent de 50/50 de plusieurs dizaines d'objets : une confiance de 0,22 ne prouve rien. **Le seuil provisoire de 0,10 est donc trop bas**, et le cas qui devait montrer l'abstention attendue montre le contraire. Ce résultat n'est pas une anomalie de code : les tests synthétiques 3 et 6 passent, c'est la partition de `learn_B` qui est déséquilibrée.
- **La séparation est moyenne** : `oracle` ≈ 0,86 à 0,88, soit 12 à 14 % des objets de test classés autrement que par le modèle de A, même en prenant le meilleur modèle. C'est la limite de T2 (accord segments / sources de 0,63 à 0,75, comme sur le scénario de T2 qui donnait 0,73 à 0,78), pas de T3.

### Limites

- **Le seuil n'est pas calibré dans T3.** `SEUIL_CONFIANCE = 0` (pas d'abstention) est provisoire ; la calibration est faite en T4 (voir cette section).
- **L'algorithme tend à équilibrer les segments** (confirmé : 261/189 et 230/220 pour 300/150). C'est ce qui a fait abandonner le critère « taille » : l'écart de taille vu par B est plus petit que l'écart réel, et bruité de plusieurs dizaines d'objets.
- **Le critère « objets expliqués » repose sur l'hypothèse que A est majoritaire.** À ratio 1 il ne peut rien (comptes égaux en moyenne) ; si le malveillant envoie plus que A, il désigne le modèle du malveillant (test 6).
- **L'hypothèse est exploitable par le malveillant** : il lui suffit d'envoyer autant d'objets que A. C'est le point de départ de la partie 2.
- **Peu de données dans l'essai T3** : 4 scénarios (5 avec l'exemple), une seule graine par ratio, avec l'ancien critère. Le diagnostic (6 par ratio) puis T4 (20 par ratio) donnent des statistiques.
- **`n_A` = 300 est la seule taille testée.** Le comportement pour d'autres tailles reste à mesurer.
- **Le jeu de test suit la loi de A** (uniforme par défaut) : `oracle` et `identifie` mesurent la fidélité au modèle de A sur cette loi.


---

## Diagnostic T3 : le pipeline à deux modèles est-il utile ?

*Ajouté après les essais de T3, qui montraient une identification par la taille fragile. Code : fin du notebook (`learn_single`, `diag_scenario` ; le critère « objets expliqués » s'appelait `identify_A_expliques` à l'époque, il est maintenant `identify_A`) ; données : `results/t3_diagnostic.csv`.*

### Question et méthodes

Deux doutes : (1) un **seul** modèle appris sur tout le mélange suffit-il quand A est majoritaire ? (2) la **taille des segments** est-elle un bon indicateur, alors que `learn_B` tend à équilibrer les segments ? On compare, sur les mêmes scénarios et par la précision sur le jeu de test (étiqueté par le modèle de A) :

| | Méthode |
|---|---|
| **M1** | un seul modèle lincs sur tout le mélange : 4 apprentissages en parallèle (graines différentes, `POLISH_SECONDS`), on garde le meilleur **sur le mélange reçu** (pas de vérité terrain) |
| **M2** | `learn_B` puis choix du modèle du plus grand segment, sans abstention |
| **M3** | `learn_B` puis choix du modèle qui **explique le plus d'objets du mélange entier** (qui classe dans la catégorie reçue), sans abstention. Confiance = écart relatif des deux comptes. Ne dépend pas de la partition. |
| oracle | meilleur des deux modèles de `learn_B` (qualité de la séparation) |
| hasard | moyenne des deux modèles de `learn_B` |

Scénarios : ratios {1,0 ; 0,85 ; 0,7 ; 0,5}, 6 graines par ratio (**graines 100 à 105**, distinctes de celles de l'essai T3 ; ce sont des scénarios de diagnostic, à ne pas réutiliser pour le rapport final). Le « bon choix » est défini a posteriori : le modèle choisi est celui des deux qui a la meilleure précision en test.

### Résultats (moyenne ± écart-type sur 6 scénarios)

| Ratio | M1 modèle unique | M2 pipeline + taille | M3 pipeline + expliqués | oracle | hasard |
|---|---|---|---|---|---|
| 1,0 | 0,632 ± 0,065 | 0,516 ± 0,275 | 0,724 ± 0,261 | 0,880 ± 0,052 | 0,605 ± 0,059 |
| 0,85 | 0,740 ± 0,094 | 0,671 ± 0,227 | 0,853 ± 0,111 | 0,853 ± 0,111 | 0,600 ± 0,073 |
| 0,7 | 0,798 ± 0,100 | 0,803 ± 0,189 | 0,847 ± 0,105 | 0,847 ± 0,105 | 0,605 ± 0,046 |
| 0,5 | 0,878 ± 0,050 | 0,826 ± 0,175 | 0,893 ± 0,046 | 0,893 ± 0,046 | 0,653 ± 0,070 |

Différences appariées (moyenne, et nombre de scénarios sur 6 où la première méthode gagne strictement) :

| Ratio | M1 − M2 | M3 − M2 | M1 − M3 | M1 − oracle |
|---|---|---|---|---|
| 1,0 | +0,115 (4/6) | +0,208 (2/6) | −0,092 (2/6) | −0,248 |
| 0,85 | +0,069 (4/6) | +0,182 (2/6) | −0,113 (2/6) | −0,113 |
| 0,7 | −0,004 (3/6) | +0,044 (1/6) | −0,048 (3/6) | −0,048 |
| 0,5 | +0,052 (2/6) | +0,067 (1/6) | −0,014 (1/6) | −0,014 |

(Dans M3 − M2, M3 est toujours au moins aussi bon que M2 : quand les deux choix diffèrent, M3 a raison. Les « 1/6 » et « 2/6 » comptent les scénarios où M3 gagne strictement.)

Choix du modèle de A, partitions et temps :

| Ratio | Bon choix M2 | Bon choix M3 | Plus grand segment = A | Taille trouvée (grand / petit) | Taille réelle (A / malveillant) | Accord segments / sources | Temps M1 | Temps pipeline |
|---|---|---|---|---|---|---|---|---|
| 1,0 | 2/6 | 4/6 | 2/6 | 358 / 242 | 300 / 300 | environ 0,7 | 4,2 s | 27 s |
| 0,85 | 4/6 | 6/6 | 4/6 | 346 / 210 | 300 / 255 | environ 0,7 | 4,2 s | 27 s |
| 0,7 | 5/6 | 6/6 | 6/6 | 301 / 209 | 300 / 210 | environ 0,7 | 4,2 s | 28 s |
| 0,5 | 5/6 | 6/6 | 6/6 | 276 / 174 | 300 / 150 | environ 0,7 | 4,2 s | 27 s |

### Observations

1. **M3 est le seul critère d'identification sans erreur à ratio < 1** : 18/18 contre 14/18 pour M2. Les 4 erreurs de M2 viennent de partitions où le plus grand segment trouvé n'est pas celui de A (graines 101 à ratio 0,85, 104 à 0,85 et 0,5, 105 à 0,7) ; M3 y choisit juste, parce qu'il compte les objets expliqués sur le mélange entier au lieu de se fier au rangement fait par l'algorithme. Cela confirme l'hypothèse qui motivait le diagnostic.
2. **La séparation fonctionne, l'identification est le goulot.** `oracle` est supérieur à M1 à tous les ratios (de +1,4 point à 0,5 à +24,8 points à 1,0). À ratio 1,0, `oracle` vaut 0,88 : B retrouve bien le modèle de A *parmi les deux* qu'il apprend, mais ne peut pas dire lequel (aucune méthode ne le peut par la taille ou les objets expliqués : M3 y fait 4/6, soit 0,34 de probabilité sous le hasard).
3. **M1 n'est pas ridicule, surtout à ratio 0,5** : 0,878 contre 0,893 pour M3 (écart −1,4 ± 2,9 points, indistinct de zéro), en 4 s au lieu de 27 s. L'avantage de M3 augmente quand A est moins majoritaire (−4,8 points à 0,7, −11,3 à 0,85).
4. **M2 n'apporte rien sur M1** : M1 − M2 va de −0,4 à +11,5 points selon le ratio, avec 16 à 28 points d'écart-type. Il garde le défaut de l'écart de taille qui s'écrase vers 50/50 (276/174 au lieu de 300/150 à ratio 0,5).
5. **Les segments trouvés restent impurs** (accord d'environ 0,7), sans lien visible avec le ratio.

### Ce qui est établi, indicatif, non conclu

- **Établi (dans cette configuration)** : M3 choisit le bon modèle 18 fois sur 18 à ratio < 1 (borne basse à 95 % de Wilson : environ 82 %) ; M2 fait 4 erreurs sur 18 ; M1 est environ 6 fois plus rapide que le pipeline.
- **Indicatif (n = 6)** : M3 meilleur que M1 en moyenne à chaque ratio (de 1 à 11 points) ; M2 pas meilleur que M1 en moyenne.
- **Non conclu** : un seuil d'abstention pour M3 (aucun mauvais choix à ratio < 1 pour fixer la frontière ; confiance des bons choix de 0,006 à 0,465, dont 9 sur 18 sous 0,10) ; le comportement à ratio 1,0 (M3 à 4/6, cohérent avec le hasard) ; toute généralisation à d'autres tailles de problème ; la supériorité de M3 sur M1 à ratio 0,5.

### Recommandation

*Appliquée ensuite : M3 est la méthode de B, `identify_A` utilise le critère des objets expliqués (`identify_A_taille` conserve l'ancien), M1 reste la référence, et T4 a été mené selon les points 2 à 4 ci-dessous.*

1. **Retenir le pipeline à deux modèles avec le critère « objets expliqués » (M3) comme méthode de B.** C'est la seule méthode qui, ici, apprend en plus la structure à deux sources et identifie A sans erreur quand A est majoritaire. Son coût de calcul supplémentaire (27 s contre 4 s) est justifié surtout aux ratios 0,7 à 0,85, où le gain sur M1 est de 5 à 11 points, mais cet ordre de grandeur reste indicatif. Si seul le ratio 0,5 compte et que le temps est la contrainte, M1 est une alternative proche.
2. **Garder M1 comme référence en T4**, pour pouvoir répondre en soutenance à « pourquoi pas un seul modèle ? ».
3. **Pour T3** : `identify_A` actuel (taille) devrait céder la place à `identify_A_expliques` comme critère par défaut ; la décision est laissée à l'auteur du cadrage car elle change le comportement de T3. La confiance devient l'écart relatif des objets expliqués.
4. **Pour T4** : calibrer le seuil d'abstention sur la confiance de M3, avec des scénarios de calibration distincts de ceux du diagnostic (graines 100 à 105) et du rapport final ; passer à une vingtaine de scénarios par ratio (n = 6 ne permet de conclure que sur des écarts importants) ; rapporter M1, M2, M3, oracle et hasard côte à côte.
5. **Pour la partie 2** : le ratio 1,0 est bien le levier du malveillant : l'identification n'y est plus possible, alors que la séparation (`oracle` = 0,88) reste bonne.

### Limites

- **n = 6 scénarios par ratio**, une seule configuration (6 critères, 3 catégories, 300 objets de A, loi uniforme).
- **« Bon choix » défini a posteriori** par la précision en test, donc par la vérité terrain ; B n'y a pas accès.
- **lincs s'arrête sur un temps** : les résultats ne sont pas reproductibles à l'octet près d'une exécution à l'autre.
- **Les temps de M1** sont mesurés avec 4 apprentissages concurrents sur la machine ; ils ne valent que pour cette machine.
- **Le notebook n'a pas été exécuté par Jupyter** (le noyau disponible n'est pas celui du `.venv`) : il est livré sans sorties, et les tableaux ont été vérifiés en exécutant le code des cellules comme un script.


---

## T4. Évaluation de B contre la vérité terrain

*Code : fin du notebook (`graine_t4`, `run_t4`, `courbe_seuil`, `choisir_seuil`). Données : `results/t4_calibration.csv`, `results/t4_final.csv`, figure `results/t4_final.png`.*

### Question

Sur beaucoup de scénarios, dans quelle mesure B retrouve-t-il le modèle de A, et à partir de quel ratio du malveillant cela cesse-t-il d'être possible ?

### Protocole

| Élément | Décision | Raison |
|---|---|---|
| Ratios du malveillant | {1,0 ; 0,85 ; 0,7 ; 0,5} | Montre où l'identification s'effondre quand le malveillant se rapproche de l'envoi maximal (ratio 1), qui est son meilleur choix. |
| Configuration | 6 critères, 3 catégories, 300 objets de A, loi uniforme ; **aucune autre variation** | Concentrer le temps de calcul sur la courbe selon le ratio. Limite : on ne sait pas si les conclusions tiennent à d'autres tailles. |
| Lot final | 20 scénarios par ratio (80), graines `300 + 20·i_ratio + k`, soit 300 à 379 | Comme le jalon 1 (une vingtaine de répétitions) : moyenne et écart-type exploitables. |
| Lot de calibration | 10 scénarios par ratio (40), graines `200 + 10·i_ratio + k`, soit 200 à 239 | Le seuil d'abstention ne doit pas être réglé sur les scénarios qui servent à annoncer le résultat. |
| Graines déjà prises | 0 à 9 (développement), 100 à 105 (diagnostic) | Un test vérifie que les quatre plages sont disjointes et que chaque lot couvre exactement la sienne. |
| Méthodes, mêmes scénarios | M1 modèle unique (`learn_single`, référence), M2 `learn_B` + taille, M3 `learn_B` + objets expliqués (méthode de B), oracle, hasard | Voir « Diagnostic T3 » pour leur définition. |
| Mesure | précision sur le jeu de test de 1000 objets étiqueté par le modèle de A | Définition du jalon 1. |
| Enregistrement | chaque scénario est évalué **sans abstention**, le seuil s'applique ensuite sur la confiance enregistrée | Changer de seuil ne demande pas de relancer lincs. |

### Règle de calibration du seuil (écrite avant de lancer la calibration, donc avant le lot final)

Grille de seuils 0 ; 0,01 ; … ; 0,50. À un seuil donné, B s'abstient quand la confiance de M3 est inférieure au seuil. L'**erreur** est la part de mauvais choix (`bon_choix` = 0, défini a posteriori) **parmi les scénarios où B ne s'abstient pas**.

1. **Règle principale** : seuil retenu = le plus petit seuil dont l'erreur, sur le lot de calibration tous ratios réunis, est ≤ 10 %.
2. **Repli** : si aucun seuil de la grille ne convient (probable, car à ratio 1,0 le choix est un pile ou face), on retient le seuil qui minimise l'erreur agrégée sous la contrainte que l'abstention aux ratios < 1 reste ≤ 30 % (à erreur égale, le plus petit seuil). On dit alors explicitement que le repli a servi.
3. La courbe erreur / abstention (agrégée et par ratio) est documentée, puis le seuil est figé (`SEUIL_CALIBRE`). Le lot final n'est lancé qu'après ce gel et n'a servi à aucun choix.

### Comptabilité de l'abstention (lot final)

Quand B s'abstient, il renvoie les deux modèles sans en désigner un. Deux façons d'attribuer une précision à B pour le comparer à M1 et à M3 sans abstention :
- **« abstention = réponse au hasard »** (**mesure principale**) : précision = `hasard` du scénario (moyenne des deux modèles), comme si B répondait l'un des deux au hasard. Lecture neutre, comparable aux autres méthodes ;
- **« abstention = échec »** (borne pessimiste) : précision = 0 quand B s'abstient.

On rapporte aussi la précision de M3 sur les seuls scénarios où il se prononce, et le taux d'abstention.

### Calibration (lot de calibration : 40 scénarios, graines 200 à 239, 10 par ratio)

Courbe erreur / abstention de M3 (extraits de la grille ; données : `results/t4_calibration.csv`). « Erreur » : part de mauvais choix parmi les scénarios où B se prononce.

| Seuil | Abstention (tous ratios) | Erreur (tous ratios) | Choix faits | Abstention (ratios < 1) | Erreur (ratios < 1) | Abstention à ratio 1,0 |
|---|---|---|---|---|---|---|
| 0 | 0 % | 20,0 % | 40 | 0 % | 6,7 % | 0 % |
| 0,03 | 12,5 % | 14,3 % | 35 | 3,3 % | 6,9 % | 40 % |
| 0,05 | 32,5 % | 11,1 % | 27 | 23,3 % | 8,7 % | 60 % |
| **0,06** | **37,5 %** | **4,0 %** | **25** | **26,7 %** | **4,5 %** | **70 %** |
| 0,08 | 50,0 % | 5,0 % | 20 | 36,7 % | 5,3 % | 90 % |
| 0,10 | 52,5 % | 5,3 % | 19 | 40,0 % | 5,6 % | 90 % |
| 0,12 | 60,0 % | 0 % | 16 | 50,0 % | 0 % | 90 % |
| 0,20 | 77,5 % | 0 % | 9 | 70,0 % | 0 % | 100 % |

**Seuil retenu : `SEUIL_CALIBRE = 0,06` par la règle principale** (le repli n'a pas servi).

- **Fragile** : un seul scénario sépare 0,05 (erreur 11,1 %, règle non satisfaite) de 0,06 (4,0 %). Avec 10 scénarios par ratio, la calibration est approximative.
- **L'erreur agrégée tient en partie à l'abstention à ratio 1,0** : à 0,06, B s'abstient 7 fois sur 10 à ratio 1,0 et ne choisit que 3 fois (3 bons choix, sans doute par chance, car sans abstention il se trompe 6 fois sur 10 à ce ratio).
- **Aux ratios < 1** : 26,7 % d'abstention, 1 erreur sur 22 choix (4,5 %), à ratio 0,85 (1 choix sur 4 faux).
- **Sans abstention, M3 se trompe 2 fois sur 30 aux ratios < 1** (une à 0,85, une à 0,7), contre 0 sur 18 dans le diagnostic : les « 18 sur 18 » du diagnostic n'étaient pas une garantie.
- **M1 n'est pas dominé sur le lot de calibration** : précision moyenne de M1 / M3 par ratio : 0,5 : 0,916 / 0,917 ; 0,7 : 0,860 / 0,829 ; 0,85 : 0,822 / 0,904 ; 1,0 : 0,548 / 0,554 (oracle : 0,917 / 0,838 / 0,906 / 0,892). Ces chiffres n'ont servi qu'à régler le seuil ; c'est le lot final qui les mesure.

Le seuil est figé ici, avant de lancer le lot final.

### Résultats du lot final (80 scénarios, 20 par ratio, graines 300 à 379, seuil figé à 0,06)

Précision sur le jeu de test (modèle de A), moyenne ± écart-type sur 20 scénarios (erreur-type = écart-type / √20) :

| Ratio | M1 modèle unique | M2 taille | M3 expliqués (sans abstention) | B avec abstention (= hasard) | B avec abstention (= échec) | oracle | hasard |
|---|---|---|---|---|---|---|---|
| 1,0 | 0,703 ± 0,144 | 0,733 ± 0,219 | 0,675 ± 0,251 | 0,653 ± 0,121 | 0,270 ± 0,358 | 0,853 ± 0,109 | 0,644 ± 0,052 |
| 0,85 | 0,830 ± 0,094 | 0,785 ± 0,203 | 0,862 ± 0,180 | 0,771 ± 0,147 | 0,439 ± 0,459 | 0,900 ± 0,101 | 0,659 ± 0,056 |
| 0,7 | 0,844 ± 0,072 | 0,819 ± 0,162 | 0,872 ± 0,097 | 0,839 ± 0,129 | 0,743 ± 0,334 | 0,880 ± 0,074 | 0,654 ± 0,046 |
| 0,5 | 0,910 ± 0,041 | 0,809 ± 0,179 | 0,867 ± 0,107 | 0,860 ± 0,117 | 0,797 ± 0,286 | 0,867 ± 0,107 | 0,649 ± 0,055 |

Figure : `results/t4_final.png` (M1 et M3 avec barres d'erreur à ± 1,96 erreur-type, oracle et hasard en repères).

Différences appariées de précision (même scénario), moyenne [intervalle bootstrap à 95 %, 1000 tirages] :

| Ratio | M3 − M1 | M3 gagne / égal / perd | M3 − M2 | B (abstention = hasard) − M1 |
|---|---|---|---|---|
| 1,0 | −0,028 [−0,123 ; +0,096] | 8 / 0 / 12 | −0,058 [−0,186 ; +0,074] | −0,050 [−0,100 ; +0,005] |
| 0,85 | +0,032 [−0,047 ; +0,102] | 14 / 0 / 6 | +0,077 [−0,033 ; +0,189] | −0,059 [−0,113 ; −0,001] |
| 0,7 | +0,028 [−0,019 ; +0,074] | 12 / 0 / 8 | +0,053 [+0,000 ; +0,134] | −0,005 [−0,064 ; +0,053] |
| 0,5 | **−0,043 [−0,091 ; −0,003]** | 9 / 0 / 11 | +0,058 [+0,000 ; +0,129] | −0,050 [−0,102 ; −0,004] |
| < 1 réunis | +0,006 [−0,029 ; +0,036] | 35 / 0 / 25 | +0,062 [+0,015 ; +0,111] | −0,038 [−0,067 ; −0,004] |

Identification (bon choix défini a posteriori, sans abstention ; intervalle de Wilson à 95 %), partitions, abstention, temps :

| Ratio | Bon choix M3 | Bon choix M2 | Abstention de B | M3 quand B se prononce | Taille trouvée (grand / petit) | Taille réelle (A / malveillant) | Accord segments / sources | Temps M1 | Temps pipeline |
|---|---|---|---|---|---|---|---|---|---|
| 1,0 | 9/20 = 0,45 [0,26 ; 0,66] | 12/20 = 0,60 | 60 % | 0,674 (3 bons choix sur 8) | 343 / 257 | 300 / 300 | 0,72 | 4,2 s | 30,0 s |
| 0,85 | 18/20 = 0,90 [0,70 ; 0,97] | 15/20 = 0,75 | 50 % | 0,878 (10 sur 10) | 324 / 231 | 300 / 255 | 0,74 | 4,2 s | 31,3 s |
| 0,7 | 19/20 = 0,95 [0,76 ; 0,99] | 17/20 = 0,85 | 15 % | 0,874 (16 sur 17) | 311 / 199 | 300 / 210 | 0,71 | 4,2 s | 27,1 s |
| 0,5 | 20/20 = 1,00 [0,84 ; 1,00] | 17/20 = 0,85 | 10 % | 0,886 (18 sur 18) | 267 / 183 | 300 / 150 | 0,71 | 4,2 s | 26,8 s |
| < 1 réunis | 57/60 = 0,95 [0,86 ; 0,98] | 49/60 = 0,82 [0,70 ; 0,89] | 25 % | | 301 / 204 | 300 / 205 | 0,72 | 4,2 s | 28,4 s |

### Lecture

**Établi (20 scénarios par ratio, cette configuration)**
- **L'identification de A par les objets expliqués marche quand A est majoritaire** : 57 bons choix sur 60 aux ratios < 1 (0,95 [0,86 ; 0,98]), contre 49 sur 60 pour la taille de segment (0,82 [0,70 ; 0,89]). À ratio 1,0 : 9 sur 20 (0,45 [0,26 ; 0,66]), compatible avec le hasard, comme prévu.
- **La séparation en deux modèles fonctionne à tous les ratios** : `oracle` de 0,85 à 0,90, y compris à ratio 1,0.
- **L'identification tient jusqu'à 0,85 au moins** (18 sur 20) ; aucun ratio n'est testé entre 0,85 et 1,0, on ne sait donc pas où elle cesse.

**Ce que le lot final nuance ou contredit par rapport au diagnostic**
- **M3 ne bat pas M1 en précision.** M3 − M1 vaut +0,006 [−0,029 ; +0,036] aux ratios < 1 (indiscernable de zéro), et à ratio 0,5 **M1 est meilleur** de 4,3 points ([−9,1 ; −0,3]). Le diagnostic (6 scénarios par ratio) avait indiqué +5 à +11 points à 0,7 et 0,85 : c'était dans le bruit. M1 est environ 7 fois plus rapide (4,2 s contre 27 à 31 s).
- **Le gain possible n'est pas réalisé.** À 0,85 et 0,7, `oracle` dépasse M1 de 7,0 et 3,7 points, mais B n'atteint pas l'`oracle` (mauvais choix et segments impurs sont les explications probables, non isolées). À ratio 0,5, `oracle` est **sous** M1 (de 4,3 points) : apprendre sur un segment impur (accord d'environ 0,72) coûte peut-être plus que ce que la séparation apporte (explication probable, non testée).
- **Les « 18 sur 18 » du diagnostic n'étaient pas une garantie** : 3 erreurs sur 60 ici (et 2 sur 30 en calibration).
- M2 (taille) est moins bon que M3 pour le choix (82 % contre 95 %) et en précision (M3 − M2 = +6,2 points [+1,5 ; +11,1] aux ratios < 1).

**L'abstention (seuil figé 0,06)**
- B s'abstient dans 10 %, 15 %, 50 % et 60 % des scénarios aux ratios 0,5 ; 0,7 ; 0,85 ; 1,0.
- **Elle ne fait pas gagner de précision.** Avec la mesure principale (abstention = réponse au hasard), B est en dessous de M3 sans abstention de 0,7 à 9,1 points. À ratio 0,85, elle écarte 8 choix corrects sur 10 abstentions. Elle sert de signal d'incertitude, pas d'amélioration. La borne pessimiste (abstention = échec) donne 0,27 à 0,80 selon le ratio.
- **L'objectif de calibration n'est pas tenu sur le lot final** : l'erreur parmi les scénarios où B se prononce vaut 6/53 = 11,3 % [5,3 ; 22,6] pour une cible de 10 %. Elle est de 1/45 (2,2 %) aux ratios < 1 et de **5 sur 8 à ratio 1,0**. La confiance moyenne de M3 vaut 0,046 à ratio 1,0 et 0,07 à 0,85, contre 0,15 à 0,7 et 0,16 à 0,5 : elle sépare mal le cas indécidable du cas difficile.

### Conclusion sur l'approche (pipeline M3 contre modèle unique M1)

Ce lot **n'établit pas** que le pipeline à deux modèles apporte un gain de précision sur le modèle unique dans cette configuration. Ce qu'il apporte est structurel : il identifie A (95 % de bons choix quand A est majoritaire), apprend aussi le modèle du malveillant, et peut signaler une incertitude, ce que M1 ne fait pas. Si seule la précision sur le modèle de A compte, M1 suffit et coûte 7 fois moins. À ratio 1,0, ni l'une ni l'autre ne retrouve A : M1 atteint 0,70 parce qu'il apprend un modèle de compromis (non mesuré par rapport au modèle du malveillant), pas parce qu'il identifie A.

Conséquence pour la partie 2 : le ratio 1,0 désarme l'identification (45 % de bons choix) mais pas la séparation (`oracle` 0,85) ; un malveillant plus subtil cherchera à dégrader la séparation ou à rendre trompeuse la confiance de B.

### Limites

- **Une seule configuration** : 6 critères, 3 catégories, 300 objets de A, loi uniforme. Rien ne dit que les conclusions tiennent pour d'autres tailles.
- **« Bon choix » défini a posteriori**, avec la vérité terrain (le modèle choisi est le plus précis des deux en test) ; B n'y a pas accès.
- **lincs s'arrête sur un temps** : résultats non reproductibles à l'octet près (le lot a été exécuté une fois).
- **Calibration sur 40 scénarios seulement** : le seuil est fragile (un scénario sépare 0,05 de 0,06) et la cible de 10 % d'erreur n'est pas tenue sur le lot final (11,3 %).
- **M1 est évalué seulement par rapport au modèle de A.**
- **Pas de correction pour les comparaisons multiples** ; intervalles bootstrap sur 20 scénarios par ratio.
- **Aucun ratio entre 0,85 et 1,0.**
- **Le notebook n'a pas été exécuté par Jupyter** (le noyau disponible n'est pas celui du `.venv`) : il est livré sans sorties, et les tableaux ont été vérifiés en exécutant le code des cellules comme un script.

