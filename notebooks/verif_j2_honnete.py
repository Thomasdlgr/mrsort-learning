# Vérification de la précision « honnête » du jalon 2 (code du notebook 02_jalon2_final).
# À lancer depuis la racine du dépôt : python3 notebooks/verif_j2_honnete.py results/j2_mesure_honnete.csv
import re, time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
import matplotlib.pyplot as plt
import lincs, lincs.classification as C

DATA_DIR = Path("Datasets-Step2")

ITER_SECONDS   = 1.0     # temps lincs par apprentissage, pendant les itérations (pour 6 critères / 3 catégories)
POLISH_SECONDS = 4.0     # temps lincs de l'apprentissage final (polish), même référence
MAX_ITER       = 20      # nombre maximal d'itérations par départ
INITS          = ("errors", "random", "random", "random")   # départs : 1 guidé + 3 aléatoires
MIN_FRAC       = 0.10    # taille minimale d'un segment pour apprendre son modèle
print("lincs", lincs.__version__)

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
    csv_path = Path(csv_path)
    info = dict(type=csv_path.parent.parent.name, dossier=csv_path.parent.name, fichier=csv_path.stem)
    m = re.search(r"n(\d+)_rep(\d+)-(\d+)_noise(\d+)", csv_path.name)
    if m is None:                                     # nom hors convention : pas d'infos d'évaluation
        return dict(info, N=np.nan, rep="?", petit_attendu=np.nan, bruit=np.nan)
    return dict(info, N=int(m[1]), rep=f"{m[2]}-{m[3]}", petit_attendu=min(int(m[2]), int(m[3])) / 100,
                bruit=int(m[4]) / 100)

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

def show_model(model, title):
    df = pd.DataFrame(model["profiles"], index=[f"b{h + 1}" for h in range(len(model["profiles"]))],
                      columns=[f"c{i + 1}" for i in range(model["profiles"].shape[1])])
    df.loc["poids"] = model["weights"]
    print(f"--- {title}   lambda = {model['lmbda']:.3f}")
    display(df.round(3))

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

def learn_2_mrsort(X, y, p, init="errors", seed=0, share_ambiguous=False,
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

def split(N, seed, test_frac=0.10):
    rng = np.random.default_rng(10_000 + seed)
    test = np.zeros(N, bool)
    test[rng.choice(N, round(test_frac * N), replace=False)] = True
    return test

def two_models_accuracy(models, X, y):
    return np.stack([predict(m, X) == y for m in models]).any(axis=0).mean()

def bench_file(csv, seed, variants=(False, True), keep=None):
    X, y, p = load_dataset(csv)
    test = split(len(X), seed)
    Xtr, ytr, Xte, yte = X[~test], y[~test], X[test], y[test]
    rng = np.random.default_rng(seed)
    t_ref = budget(POLISH_SECONDS, X.shape[1], p)

    single = learn_mrsort(Xtr, ytr, p, seed=seed, seconds=t_ref)                       # référence 1
    halves_seg = rng.integers(0, 2, len(Xtr))                                           # référence 2
    halves = [learn_mrsort(Xtr[halves_seg == k], ytr[halves_seg == k], p, seed=seed + k, seconds=t_ref)
              for k in (0, 1)]
    refs = dict(unique_train=(predict(single, Xtr) == ytr).mean(), unique_test=(predict(single, Xte) == yte).mean(),
                moities_test=two_models_accuracy(halves, Xte, yte))

    rows = []
    for share in variants:
        t = time.time()
        best, _ = learn_2_mrsort_multistart(Xtr, ytr, p, seed=seed, share_ambiguous=share)
        sizes = np.bincount(best["seg"], minlength=2)
        rows.append(dict(**file_info(csv), graine=seed, partage_ambigus=share, **refs,
                         deux_train=best["score"], deux_test=two_models_accuracy(best["models"], Xte, yte),
                         petit_segment=sizes.min() / sizes.sum(),
                         ambigus=(best["E"] == 0).all(axis=1).mean(),
                         depart=best["init"], temps=time.time() - t))
        if keep is not None:                                     # pour afficher les modèles ensuite
            keep.append(dict(fichier=csv, graine=seed, partage_ambigus=share, best=best))
    return rows

def run_bench(files, seeds, variants, out_csv=None, keep=None):
    rows = []
    for f in files:
        for s in seeds:
            rows += bench_file(f, s, variants, keep)
            if out_csv:
                pd.DataFrame(rows).to_csv(out_csv, index=False)  # sauvegarde au fil de l'eau
            r = rows[-1]
            print(f"{r['type']}/{r['dossier']}/{r['fichier']} graine={s} : "
                  + " | ".join(f"partage={x['partage_ambigus']} test={x['deux_test']:.3f}" for x in rows[-len(variants):]),
                  flush=True)
    return pd.DataFrame(rows)

SUMMARY_COLS = ["deux_train", "deux_test", "ecart", "unique_test", "moities_test",
                "gain_vs_unique", "gain_vs_moities", "erreur_proportion", "temps"]

def add_measures(df):
    return df.assign(ecart=df.deux_train - df.deux_test,
                     gain_vs_unique=df.deux_test - df.unique_test,
                     gain_vs_moities=df.deux_test - df.moities_test,
                     erreur_proportion=(df.petit_segment - df.petit_attendu).abs())

def summary(df, by, with_means=False):
    agg = add_measures(df).groupby(by)[SUMMARY_COLS].agg(["mean", "std"])
    fmt = lambda m, s: f"{m:.3f}" if np.isnan(s) else f"{m:.3f} ± {s:.3f}"
    table = pd.DataFrame({c: [fmt(m, s) for m, s in zip(agg[c]["mean"], agg[c]["std"])]
                          for c in SUMMARY_COLS}, index=agg.index)
    return (table, agg.xs("mean", axis=1, level=1)) if with_means else table

def display(x): print(x)
import sys
files=[DATA_DIR/"type_a/cr06_ca03"/f for f in ["n0600_rep50-50_noise00.csv","n0600_rep75-25_noise00.csv","n0600_rep50-50_noise10.csv","n0600_rep75-25_noise10.csv"]]
out=[]
for f in files:
    seed=2
    X,y,p=load_dataset(f); test=split(len(X),seed)
    Xtr,ytr,Xte,yte=X[~test],y[~test],X[test],y[test]
    rng=np.random.default_rng(seed); t_ref=budget(POLISH_SECONDS,X.shape[1],p)
    single=learn_mrsort(Xtr,ytr,p,seed=seed,seconds=t_ref)
    best,_=learn_2_mrsort_multistart(Xtr,ytr,p,seed=seed)
    P=np.stack([predict(m,Xte) for m in best["models"]])
    ok=P==yte
    # regle sans oracle : segment du plus proche voisin (5-NN) dans l'apprentissage
    d=((Xte[:,None,:]-Xtr[None,:,:])**2).sum(-1); nn=np.argsort(d,axis=1)[:,:5]
    segp=(best["seg"][nn].mean(1)>0.5).astype(int)
    knn=(P[segp,np.arange(len(yte))]==yte).mean()
    # vrai ensemble de test plus grand : tous les objets ? non -> test seulement
    c=np.bincount(ytr,minlength=p); top=np.argsort(-c)[:2]
    r=dict(fichier=f.stem,ntest=len(yte),unique=(predict(single,Xte)==yte).mean(),
      modele0=ok[0].mean(),modele1=ok[1].mean(),hasard=ok.mean(),knn5=knn,
      union=ok.any(0).mean(),constantes_union=np.isin(yte,top).mean(),
      tailles=np.bincount(best["seg"]).tolist(),
      accord_seg0=(P[0]==P[1]).mean())
    print(r,flush=True); out.append(r)
pd.DataFrame(out).to_csv(sys.argv[1] if len(sys.argv)>1 else "verif.csv",index=False)
