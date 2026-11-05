# Jalon 2 — inv-2-MR-Sort : explication de 100 % des objets (pas de test, pas de validation).
# Même algorithme que notebooks/02_jalon2_final.ipynb (cellules 1, 3, 5, 8), SHARE_AMBIGUOUS = False.
# À lancer depuis la racine du dépôt :
#   python3 notebooks/jalon2_explication.py --types type_a --seeds 0
# Le CSV de sortie est écrit ligne par ligne ; les (fichier, graine) déjà présents sont sautés.
# Les sections "# %%" sont reprises telles quelles dans notebooks/04_jalon2_explication.ipynb.

# %% config
import argparse, re, time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
import lincs, lincs.classification as C

ROOT = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path("..").resolve()
DATA_DIR = ROOT / "Datasets-Step2"
OUT_CSV  = ROOT / "results" / "jalon2_explication.csv"

ITER_SECONDS    = 1.0     # temps lincs par apprentissage, pendant les itérations (pour 6 critères / 3 catégories)
POLISH_SECONDS  = 4.0     # temps lincs de l'apprentissage final (polish), même référence
MAX_ITER        = 20      # nombre maximal d'itérations par départ
INITS           = ("errors", "random", "random", "random")   # départs : 1 guidé + 3 aléatoires
MIN_FRAC        = 0.10    # taille minimale d'un segment pour apprendre son modèle
SHARE_AMBIGUOUS = False   # chaque objet appartient à un seul segment (choix du jalon 2)

# %% chargement
def load_dataset(csv_path):
    csv_path = Path(csv_path)
    pb = yaml.safe_load((csv_path.parent / "problem.yml").read_text())
    assert all(c.get("preference_direction", "increasing") == "increasing" for c in pb["criteria"])
    criteria = [str(c["name"]) for c in pb["criteria"]]
    categories = [str(c["name"]) for c in pb["ordered_categories"]]
    df = pd.read_csv(csv_path)
    y = df["category"].astype(str).map({c: h for h, c in enumerate(categories)})
    assert not y.isna().any(), "catégorie inconnue"
    return df[criteria].to_numpy(float), y.to_numpy(int), len(categories)

def file_info(csv_path):
    # rep et bruit servent UNIQUEMENT à l'évaluation après coup : l'algorithme ne les voit pas
    csv_path = Path(csv_path)
    info = dict(type=csv_path.parent.parent.name, dossier=csv_path.parent.name, fichier=csv_path.stem)
    m = re.search(r"n(\d+)_rep(\d+)-(\d+)_noise(\d+)", csv_path.name)
    if m is None:
        return dict(info, N=np.nan, rep="?", petit_attendu=np.nan, bruit=np.nan)
    return dict(info, N=int(m[1]), rep=f"{m[2]}-{m[3]}", petit_attendu=min(int(m[2]), int(m[3])) / 100,
                bruit=int(m[4]) / 100)

# %% mrsort
def n_params(n, p):
    return n * (p - 1) + n + 1

def budget(base_seconds, n, p):
    return base_seconds * n_params(n, p) / n_params(6, 3)

def make_problem(n, p):
    crits = [C.Criterion(f"c{i + 1}", C.Criterion.RealValues(C.Criterion.PreferenceDirection.increasing, 0., 1.))
             for i in range(n)]
    return C.Problem(crits, [C.Category(f"cat{h}") for h in range(p)])

def to_alts(problem, X, y=None):
    return C.Alternatives(problem, [
        C.Alternative(f"a{k}", [C.Performance(C.Performance.Real(float(v))) for v in X[k]],
                      None if y is None else int(y[k])) for k in range(len(X))])

def learn_mrsort(X, y, p, seed=0, seconds=2.0, models=9, patience=30):
    problem = make_problem(X.shape[1], p)
    pre = C.PreprocessedLearningSet(problem, to_alts(problem, X, y))
    mbl = C.LearnMrsortByWeightsProfilesBreed.ModelsBeingLearned(pre, models, int(seed))
    init = C.InitializeProfilesForProbabilisticMaximalDiscriminationPowerPerCriterion(pre, mbl)
    weights = C.OptimizeWeightsUsingGlop(pre, mbl)
    profiles = C.ImproveProfilesWithAccuracyHeuristicOnCpu(pre, mbl)
    breed = C.ReinitializeLeastAccurate(mbl, init, weights, count=models // 2)
    term = C.TerminateWhenAny([C.TerminateAtAccuracy(mbl, len(X)), C.TerminateAfterSeconds(seconds),
                               C.TerminateAfterIterationsWithoutProgress(mbl, patience)])
    m = C.LearnMrsortByWeightsProfilesBreed(pre, mbl, init, weights, profiles, breed, term).perform()
    B = np.array([[np.inf if av.real_thresholds.thresholds[h] is None else av.real_thresholds.thresholds[h]
                   for av in m.accepted_values] for h in range(p - 1)])          # (p-1, n)
    W = np.array(m.sufficient_coalitions[0].weights.criterion_weights)           # seuil de majorité = 1 (lincs)
    return {"profiles": B, "raw_weights": W, "weights": W / W.sum(), "lmbda": 1. / W.sum(),
            "_lincs": m, "_problem": problem}

def concordance(model, X):
    # C[k, h] = somme des poids (bruts) des critères où x_k >= b^h, en float32 comme lincs
    X32 = np.asarray(X, dtype=np.float32)
    W32 = np.asarray(model["raw_weights"], dtype=np.float32)
    return np.stack([(X32 >= b.astype(np.float32)).astype(np.float32) @ W32 for b in model["profiles"]],
                    axis=1).astype(float)

def predict(model, X):
    return np.cumprod(concordance(model, X) >= 1., axis=1).sum(axis=1)       # nb de frontières franchies

def margins(model, X, y):
    Cn = (concordance(model, X) - 1.) / model["raw_weights"].sum()          # C(x, b^h) - lambda, poids normalisés
    m = np.full(len(X), np.inf)
    low = y >= 1                                                             # doit franchir b^{h-1}
    m[low] = np.minimum(m[low], Cn[low, y[low] - 1] + 1e-12)
    up = np.where(y <= Cn.shape[1] - 1)[0]                                   # ne doit pas franchir b^h
    m[up] = np.minimum(m[up], -Cn[up, y[up]] - 1e-12)
    m[np.isinf(m)] = 1.
    return m

# %% algorithme
def scores(models, X, y):
    E = np.stack([np.abs(predict(m, X) - y) for m in models], axis=1)     # (N, 2) écart de catégorie
    M = np.stack([margins(m, X, y) for m in models], axis=1)              # (N, 2) marge
    return E, M

def reassign(models, X, y, seg):
    E, M = scores(models, X, y)
    key = E - 1e-3 * np.clip(M, -1, 1)               # lexicographique : l'écart domine, la marge départage
    best = key.argmin(axis=1)
    rows = np.arange(len(X))
    move = key[rows, best] < key[rows, seg] - 1e-12  # strictement mieux expliqué ailleurs
    return np.where(move, best, seg), E

def fit_segments(X, y, p, seg, shared, rng, seconds):
    models = []
    for k in (0, 1):
        idx = np.where((seg == k) | shared)[0]
        size_min = int(max(10, MIN_FRAC * len(X)))
        if len(idx) < size_min:                       # segment trop petit : tirage aléatoire
            idx = rng.choice(len(X), size=size_min, replace=False)
        models.append(learn_mrsort(X[idx], y[idx], p, seed=int(rng.integers(1e9)), seconds=seconds))
    return models

def init_partition(X, y, p, how, rng, seconds):
    if how == "random":
        return rng.integers(0, 2, len(X))
    single = learn_mrsort(X, y, p, seed=int(rng.integers(1e9)), seconds=seconds)
    return (predict(single, X) != y).astype(int)      # "errors" : erreurs du modèle unique -> segment 1

def learn_2_mrsort(X, y, p, init="errors", seed=0, share_ambiguous=SHARE_AMBIGUOUS,
                   max_iter=MAX_ITER, iter_seconds=ITER_SECONDS, polish_seconds=POLISH_SECONDS):
    rng = np.random.default_rng(seed)
    n = X.shape[1]
    t_iter, t_polish = budget(iter_seconds, n, p), budget(polish_seconds, n, p)
    seg = init_partition(X, y, p, init, rng, t_iter)
    shared = np.zeros(len(X), bool)
    best, history = None, []

    for it in range(max_iter):
        models = fit_segments(X, y, p, seg, shared, rng, t_iter)          # apprentissage
        new_seg, E = reassign(models, X, y, seg)                           # réaffectation
        score = (E.min(axis=1) == 0).mean()                                # expliqués par au moins un modèle
        sizes = np.bincount(new_seg, minlength=2)
        history.append(dict(iteration=it + 1, expliques=score, petit_segment=sizes.min() / sizes.sum(),
                            ambigus=(E == 0).all(axis=1).mean(), changements=(new_seg != seg).mean()))
        if best is None or score > best["score"]:
            best = dict(score=score, models=models, seg=new_seg.copy(), E=E)
        if (new_seg == seg).all():                                         # arrêt : partition stable
            break
        seg = new_seg
        if share_ambiguous:
            shared = (E == 0).all(axis=1)

    # polish : apprentissage plus long sur la partition retenue
    seg = best["seg"]
    shared = (best["E"] == 0).all(axis=1) if share_ambiguous else np.zeros(len(X), bool)
    polished = []
    for k in (0, 1):
        idx = np.where((seg == k) | shared)[0]
        old = best["models"][k]
        if len(idx) < 10:
            polished.append(old)
            continue
        new = learn_mrsort(X[idx], y[idx], p, seed=int(rng.integers(1e9)), seconds=t_polish)
        better = (predict(new, X[idx]) == y[idx]).mean() >= (predict(old, X[idx]) == y[idx]).mean()
        polished.append(new if better else old)
    new_seg, E = reassign(polished, X, y, seg)
    score = (E.min(axis=1) == 0).mean()
    if score >= best["score"]:
        best.update(score=score, models=polished, seg=new_seg, E=E)

    best["history"] = pd.DataFrame(history)
    best["init"] = init
    return best

def learn_2_mrsort_multistart(X, y, p, inits=INITS, seed=0, **kwargs):
    runs = [learn_2_mrsort(X, y, p, init=how, seed=seed * 100 + r, **kwargs) for r, how in enumerate(inits)]
    return max(runs, key=lambda r: r["score"]), runs

# %% mesures
def explained(models, X, y):
    # (N, nb modèles) : True si le modèle classe bien l'objet
    return np.stack([predict(m, X) == y for m in models], axis=1)

def explain_file(csv, seed):
    """Une ligne de mesures pour (fichier, graine), sur 100 % des objets."""
    X, y, p = load_dataset(csv)
    rng = np.random.default_rng(seed)
    t_ref = budget(POLISH_SECONDS, X.shape[1], p)

    # référence 1 : un seul MR-Sort sur tout le fichier
    single = learn_mrsort(X, y, p, seed=seed, seconds=t_ref)
    # référence 2 : deux MR-Sort sur une partition aléatoire 50/50, sans réaffectation
    halves = rng.permutation(len(X)) % 2
    rand_models = [learn_mrsort(X[halves == k], y[halves == k], p, seed=seed + 1 + k, seconds=t_ref)
                   for k in (0, 1)]
    ok_rand = explained(rand_models, X, y)

    t = time.time()
    best, _ = learn_2_mrsort_multistart(X, y, p, seed=seed)
    temps = time.time() - t
    ok = explained(best["models"], X, y)
    sizes = np.bincount(best["seg"], minlength=2)
    info = file_info(csv)
    petit = sizes.min() / sizes.sum()
    return dict(**info, graine=seed,
                unique_expl=explained([single], X, y)[:, 0].mean(),
                aleatoire_expl=ok_rand.any(axis=1).mean(),
                deux_expl=ok.any(axis=1).mean(),
                ambigus=ok.all(axis=1).mean(),
                petit_segment=petit,
                erreur_proportion=abs(petit - info["petit_attendu"]),
                depart=best["init"], temps=temps)

# %% main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", nargs="+", default=["type_a"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    ap.add_argument("--files", nargs="*", default=None, help="sous-chaînes du chemin à garder (filtre)")
    ap.add_argument("--out", default=str(OUT_CSV))
    args = ap.parse_args()

    out = Path(args.out)
    done = set()
    if out.exists():
        old = pd.read_csv(out)
        done = set(zip(old.type, old.dossier, old.fichier, old.graine))
    files = [f for t in args.types for f in sorted((DATA_DIR / t).glob("cr*_ca*/*.csv"))]
    if args.files:
        files = [f for f in files if any(s in str(f) for s in args.files)]
    print(f"lincs {lincs.__version__} | {len(files)} fichiers x {len(args.seeds)} graines | sortie {out}", flush=True)

    for f in files:
        for s in args.seeds:
            i = file_info(f)
            if (i["type"], i["dossier"], i["fichier"], s) in done:
                continue
            t = time.time()
            row = explain_file(f, s)
            pd.DataFrame([row]).to_csv(out, mode="a", header=not out.exists(), index=False)
            print(f"{i['type']}/{i['dossier']}/{i['fichier']} graine={s} : unique={row['unique_expl']:.3f} "
                  f"aleatoire={row['aleatoire_expl']:.3f} deux={row['deux_expl']:.3f} ambigus={row['ambigus']:.3f} "
                  f"petit={row['petit_segment']:.3f} ({time.time() - t:.0f} s)", flush=True)

if __name__ == "__main__":
    main()
