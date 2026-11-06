"""Version 2 (copie de build_slides.py) : tableau par type et bruit au jalon 2. Génère soutenance/soutenance_v2.pptx : 10 diapos de corps (~12 min) + annexes pour les questions.
Lancer : uv run --with python-pptx python soutenance/build_slides.py
Chiffres : docs/jalon1.md, docs/jalon2.md, docs/jalon3.md, results/*.csv (voir le pied de chaque diapo)."""
from pathlib import Path
from lxml import etree
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

ROOT = Path(__file__).resolve().parent.parent
NAVY, BLUE, ORANGE = RGBColor(0x14,0x1E,0x3C), RGBColor(0x2A,0x78,0xD8), RGBColor(0xEE,0x6C,0x3B)
INK, MUTED, CARD, WHITE, GREY = RGBColor(0x1F,0x25,0x33), RGBColor(0x5B,0x64,0x75), RGBColor(0xEE,0xF2,0xF8), RGBColor(255,255,255), RGBColor(0x88,0x88,0x80)
PALE, PEACH = RGBColor(0xCA,0xDC,0xFC), RGBColor(0xFD,0xE8,0xDF)
FONT = "Calibri"

prs = Presentation(); prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
blank = prs.slide_layouts[6]

# ---------------------------------------------------------------- helpers
def text(s, x, y, w, h, runs, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, space=6):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = tb.text_frame
    tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    paras = runs if isinstance(runs, list) else [runs]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align; para.space_after = Pt(space)
        parts = p if isinstance(p, list) else [(p, {})]
        for t, o in parts:
            r = para.add_run(); r.text = t; f = r.font; f.name = FONT
            f.size = Pt(o.get("size", size)); f.bold = o.get("bold", bold); f.color.rgb = o.get("color", color)
    return tb

def box(s, x, y, w, h, fill=CARD, shape=MSO_SHAPE.ROUNDED_RECTANGLE, line=None):
    b = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    b.fill.solid(); b.fill.fore_color.rgb = fill
    if line: b.line.color.rgb = line; b.line.width = Pt(1.5)
    else: b.line.fill.background()
    b.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE: b.adjustments[0] = 0.08
    return b

def card(s, x, y, w, h, runs, fill=CARD, color=INK, size=16, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.LEFT, line=None, space=6):
    box(s, x, y, w, h, fill, line=line)
    text(s, x+0.2, y+0.12, w-0.4, h-0.24, runs, size=size, color=color, anchor=anchor, align=align, space=space)

def arrow(s, x1, y1, x2, y2, color=MUTED):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color; c.line.width = Pt(2.25)
    ln = c.line._get_or_add_ln()
    ln.append(etree.SubElement(ln, "{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd", type="triangle"))

def stat(s, x, y, w, big, label, color=BLUE, size=44):
    text(s, x, y, w, 0.8, big, size=size, bold=True, color=color)
    text(s, x, y+0.85, w, 0.6, label, size=14, color=MUTED)

def foot(s, txt, dark=False):
    text(s, 0.7, 7.02, 11.9, 0.3, txt, size=11, color=PALE if dark else GREY)

def slide(title, notes, dark=False, size=26):
    s = prs.slides.add_slide(blank)
    bg = s.background.fill; bg.solid(); bg.fore_color.rgb = NAVY if dark else WHITE
    if title: text(s, 0.7, 0.35, 11.9, 1.1, title, size=size, bold=True, color=WHITE if dark else NAVY, anchor=MSO_ANCHOR.MIDDLE)
    s.notes_slide.notes_text_frame.text = notes
    return s

def bars(s, x, y, w, items, gap=0.85, maxv=1.0):
    """Barres horizontales (0 à 1) : items = [(libellé, valeur, couleur, texte_valeur)]."""
    for i, (lab, v, col, vt) in enumerate(items):
        yy = y + i * gap
        text(s, x, yy, w, 0.3, lab, size=14, color=MUTED)
        box(s, x, yy + 0.33, w - 0.9, 0.34, RGBColor(0xE4,0xE8,0xF0), shape=MSO_SHAPE.RECTANGLE)
        box(s, x, yy + 0.33, max(0.05, (w - 0.9) * v / maxv), 0.34, col, shape=MSO_SHAPE.RECTANGLE)
        text(s, x + w - 0.8, yy + 0.27, 0.8, 0.45, vt, size=20, bold=True, color=col if col != GREY else MUTED)

def table(s, x, y, colw, rows, rowh=0.5, size=14, hl=(), hl_fill=PEACH, hl_color=ORANGE, align=None):
    """Tableau en cases de texte. rows[0] = en-tête. hl = indices de lignes à surligner."""
    total = sum(colw)
    for i, row in enumerate(rows):
        yy = y + i * rowh
        if i in hl: box(s, x - 0.08, yy - 0.06, total + 0.16, rowh - 0.04, hl_fill, shape=MSO_SHAPE.RECTANGLE)
        if i == 1: pass
        xx = x
        for j, (cell, w) in enumerate(zip(row, colw)):
            hdr = i == 0
            al = (align[j] if align else (PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER))
            text(s, xx, yy, w, rowh - 0.1, cell, size=size - 1 if hdr else size, bold=hdr or (i in hl and j > 0),
                 color=MUTED if hdr else (hl_color if i in hl and j > 0 else INK), align=al, anchor=MSO_ANCHOR.MIDDLE)
            xx += w
        if i == 0:
            ln = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x), Inches(yy + rowh - 0.06), Inches(x + total), Inches(yy + rowh - 0.06))
            ln.line.color.rgb = MUTED; ln.line.width = Pt(1)

def head(s, x, y, w, label, color=BLUE, size=18):
    text(s, x, y, w, 0.4, label, size=size, bold=True, color=color)

# ================================================================== CORPS
# 1 — Titre --------------------------------------------------------------
s = slide(None, "[~0,5 min — à répartir] Contexte en une phrase : apprendre un modèle de tri multicritère MR-Sort, d'abord de façon exacte (jalon 1), puis avec deux segments de clients (jalon 2), puis dans un échange A → B perturbé par un agent malveillant (jalon 3). Présenter l'équipe et annoncer le plan : contexte et objectif, vue d'ensemble des jalons, puis les trois jalons, puis conclusion. Des annexes sont prêtes pour les questions.", dark=True)
text(s, 0.9, 1.7, 11.5, 1.6, "Apprentissage de modèles MR-Sort", size=46, bold=True, color=WHITE)
text(s, 0.9, 3.2, 11.5, 1.0, "du MIP exact à un échange brouillé par un agent malveillant", size=26, color=PALE)
text(s, 0.9, 6.5, 11.5, 0.5, "Aurélien Delest · Robin Capelle · Thomas de la Grand'rive  —  Mention IA, soutenance du 06/11/2026", size=16, color=PALE)

# 2 — Contexte et objectif ---------------------------------------------------
s = slide("Contexte : retrouver la règle de décision qui explique des affectations observées",
 "[~1 min — à répartir] Le système de décision visé : un décideur (un comité d'admission, un supermarché qui classe ses produits) évalue des objets sur n critères et les affecte à l'une de p catégories ordonnées. La règle supposée est MR-Sort : chaque catégorie est délimitée par un profil ; un objet franchit un profil si les critères où il l'atteint réunissent un poids ≥ λ ; sa classe est le nombre de profils franchis. La décision à prendre ici est inverse : on observe des objets déjà classés (learning set) et on veut retrouver poids, λ et profils qui les reproduisent, pour un modèle interprétable. Objectif global : y arriver de façon fiable dans trois situations de plus en plus réalistes (les trois jalons) : données exactes mais petites, deux segments de clients inconnus, données brouillées par un agent malveillant. Détail lincs : seuil fixé à 1 avec des poids bruts W ; w = W/ΣW et λ = 1/ΣW.")
head(s, 0.7, 1.65, 6.4, "Le problème")
blocks = [("Système de décision visé", "Un décideur évalue des objets sur n critères et les range dans p catégories ordonnées (admission d'étudiants, produits d'un supermarché)."),
          ("Décision à prendre", "Retrouver, à partir d'objets déjà classés (le learning set), les paramètres du modèle : poids, seuil λ et profils."),
          ("Objectif global", "Un modèle interprétable, appris de façon fiable quand les données sont nombreuses, hétérogènes, puis brouillées.")]
for i, (a, b) in enumerate(blocks):
    y = 2.15 + i * 1.5
    box(s, 0.7, y, 6.4, 1.3, CARD)
    text(s, 0.95, y + 0.12, 5.9, 0.35, a, size=15, bold=True, color=BLUE)
    text(s, 0.95, y + 0.5, 5.9, 0.8, b, size=14, color=INK)
head(s, 7.6, 1.65, 5.2, "Rappel : la règle MR-Sort")
steps = [("Chaque critère vote", [("Le critère j vote pour le profil bʰ si l'objet l'atteint : ", {}), ("xⱼ ≥ bʰⱼ", {"bold": True})]),
         ("On additionne les poids des votes", [("σ(x, bʰ) = Σ wⱼ ", {"bold": True}), ("sur les critères qui votent pour", {})]),
         ("La majorité est-elle atteinte ?", [("σ ≥ λ ", {"bold": True}), ("→ x franchit bʰ. Sa classe est le nombre de profils franchis.", {})])]
for i, (a, b) in enumerate(steps):
    y = 2.15 + i * 1.05
    box(s, 7.6, y, 5.2, 0.92, CARD)
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(7.75), Inches(y + 0.22), Inches(0.48), Inches(0.48))
    o.fill.solid(); o.fill.fore_color.rgb = BLUE; o.line.fill.background(); o.shadow.inherit = False
    text(s, 7.75, y + 0.22, 0.48, 0.48, str(i + 1), size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space=0)
    text(s, 8.4, y + 0.08, 4.3, 0.3, a, size=14, bold=True, color=NAVY, space=0)
    text(s, 8.4, y + 0.4, 4.3, 0.5, [b], size=12, color=INK, space=0)
text(s, 7.6, 5.3, 5.2, 0.3, "Profils emboîtés b¹ ≤ b² ≤ … : une frontière par catégorie", size=12, bold=True, color=MUTED)
for i, (lab, fill, col) in enumerate([("C1", CARD, NAVY), ("C2", PALE, NAVY), ("C3", BLUE, WHITE)]):
    box(s, 7.6 + i * 1.75, 5.95, 1.7, 0.5, fill, shape=MSO_SHAPE.RECTANGLE)
    text(s, 7.6 + i * 1.75, 5.95, 1.7, 0.5, lab, size=14, bold=True, color=col, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, space=0)
    text(s, 7.6 + i * 1.75, 6.52, 1.7, 0.3, f"{i} profil{'s' if i > 1 else ''} franchi{'s' if i > 1 else ''}", size=12, color=MUTED, align=PP_ALIGN.CENTER, space=0)
for k, xx in enumerate((9.3, 11.05)):
    text(s, xx - 0.3, 5.62, 0.6, 0.3, f"b{'¹²'[k]}", size=13, bold=True, color=ORANGE, align=PP_ALIGN.CENTER, space=0)
foot(s, "Paramètres : poids wⱼ ≥ 0 (somme 1), seuil λ ∈ [0,5 ; 1[, profils bʰ · dans lincs : seuil fixé à 1, poids bruts W ; w = W/ΣW, λ = 1/ΣW")

# 3 — Vue d'ensemble des jalons ----------------------------------------------
s = slide("Vue d'ensemble : trois jalons, de plus en plus réalistes, qui se réutilisent",
 "[~1 min — à répartir] Fil rouge de la soutenance. Jalon 1 : le cas idéal, un seul décideur et des données exactes ; on apprend le MR-Sort de façon exacte par un MIP Gurobi ; ça marche (0,94 à 100 objets) mais le temps explose avec la taille. Jalon 2 : on passe à l'échelle et à l'hétérogénéité : deux segments de clients inconnus ; il faut partitionner ET apprendre deux MR-Sort ; heuristique lincs avec alternance. Jalon 3 : les données transmises de A à B sont brouillées par un agent malveillant ; B réutilise l'algorithme du jalon 2 pour apprendre deux modèles, puis choisit lequel est celui de A ; on étudie ensuite comment le malveillant peut mieux brouiller. Liens : J1 → J2 : même modèle et même protocole de test, mais le MIP ne passe pas à l'échelle, d'où lincs (le code du MIP n'est pas réutilisé). J2 → J3 : B réutilise l'alternance et la règle predict en numpy. Les trois jalons ne sont pas indépendants : chacun hérite du précédent.")
heads = [("Jalon 1", "Apprendre exactement", "un décideur, données exactes", BLUE),
         ("Jalon 2", "Deux segments", "deux décideurs inconnus", BLUE),
         ("Jalon 3", "Données brouillées", "A, malveillant, B", ORANGE)]
rows3 = [("Entrée", ["learning set classé par un seul MR-Sort", "learning set mélangeant 2 segments, partition inconnue", "mélange A + malveillant, source non étiquetée"]),
         ("Sortie", ["1 MR-Sort (poids, λ, profils)", "partition + 2 MR-Sort", "le modèle de A (choisi parmi 2)"]),
         ("Outil", ["MIP exact (Gurobi)", "lincs + alternance, multi-départ", "algorithme du J2 + critère « objets expliqués »"]),
         ("Résultat", ["0,94 en test (100 objets, 0,7 s) ; 14 à 16 s à 500 objets", "explique 95 % ; sans oracle 0,73 vs 0,71", "A identifié jusqu'au ratio 0,85 ; hasard à 1 ; B tombe à 0,44"])]
for j, (a, b, c, col) in enumerate(heads):
    x = 1.7 + j * 3.75
    card(s, x, 1.65, 3.2, 1.15, [[(a, {"bold": True, "size": 13, "color": PALE if False else WHITE})], [(b, {"bold": True, "size": 18})], [(c, {"size": 12})]], fill=col, color=WHITE, align=PP_ALIGN.CENTER, space=1)
for r, (lab, vals) in enumerate(rows3):
    y = 3.05 + r * 0.85
    text(s, 0.7, y + 0.1, 0.95, 0.6, lab, size=14, bold=True, color=MUTED, anchor=MSO_ANCHOR.MIDDLE)
    for j, v in enumerate(vals):
        box(s, 1.7 + j * 3.75, y, 3.2, 0.75, CARD)
        text(s, 1.85 + j * 3.75, y + 0.05, 2.9, 0.65, v, size=12, color=INK, anchor=MSO_ANCHOR.MIDDLE)
arrow(s, 4.95, 2.22, 5.45, 2.22, BLUE); arrow(s, 8.7, 2.22, 9.2, 2.22, BLUE)
card(s, 0.7, 6.42, 6.0, 0.55, "J1 → J2 : même modèle ; le MIP ne passe pas à l'échelle → lincs", size=12, fill=WHITE, line=CARD)
card(s, 6.8, 6.42, 6.0, 0.55, "J2 → J3 : B réutilise l'alternance et la règle predict du J2", size=12, fill=WHITE, line=CARD)
foot(s, "Le code du MIP n'est pas réutilisé au J2 : le lien J1 → J2 porte sur le modèle, le protocole de test et la motivation")

# ---- gabarit des jalons : A = enjeu et approche, B = résultats ---------------------------------
def chip(s, j):
    parts = []
    for k in (1, 2, 3):
        parts.append((f"J{k} {'●' if k == j else '○'}", {"bold": k == j, "color": BLUE if k == j else GREY, "size": 12}))
        if k < 3: parts.append(("    ", {"size": 12}))
    text(s, 9.3, 0.1, 3.5, 0.3, [parts], size=12, align=PP_ALIGN.RIGHT)

def question(s, txt, y=1.55, h=0.8):
    card(s, 0.7, y, 12.1, h, [[("Question   ", {"bold": True, "color": BLUE}), (txt, {})]], size=15, fill=CARD)

def block(s, x, y, w, h, label, body, size=13, color=BLUE):
    box(s, x, y, w, h, CARD)
    text(s, x + 0.2, y + 0.1, w - 0.4, 0.3, label, size=13, bold=True, color=color)
    text(s, x + 0.2, y + 0.45, w - 0.4, h - 0.5, body, size=size, space=4)

def banner(s, txt, y=1.5, h=0.9):
    card(s, 0.7, y, 12.1, h, txt, size=16, fill=NAVY, color=WHITE)

def transition(s, txt, x=0.7, y=6.4, w=12.1, h=0.6):
    card(s, x, y, w, h, txt, size=12, fill=WHITE, line=CARD)

# 4 — Jalon 1 (une seule diapo : enjeu + résultat) -----------------------------------------------
s = slide("Jalon 1 : le MIP exact retrouve le modèle, mais ne passe pas à l'échelle",
 "[~1,25 min — à répartir] Question : peut-on apprendre exactement poids, λ et profils à partir d'un learning set classé ? Données : dataset0 (60 objets, 5 critères, 3 catégories) puis le protocole du sujet : 20 modèles tirés au hasard (poids Dirichlet, profils triés), 100 objets d'apprentissage, 10 000 objets de test. Méthode : MIP Gurobi ; variables : une binaire δ par objet, critère et profil (δ = 1 ⇔ xᵢ ≥ bᵢ), linéarisation wᵢ·δ, une binaire γ par objet ; objectif : maximiser le nombre d'objets restitués, donc toujours soluble même si le learning set n'est pas représentable. Piège numérique : le MIP ne sait pas écrire une inégalité stricte, on impose ε = 1e-3, on resserre la tolérance entière (1e-9) et on recentre les paramètres de −ε/2 pour que la règle sans tolérance redonne les mêmes classes. Résultat : dataset0 60/60 en 0,7 s ; 0,937 ± 0,028 en test avec 100 objets. Baseline : la taille du learning set : avec 500 objets 0,987 mais 14 à 16 s (max ~60 s). C'est la raison du passage à lincs. Attention : le rapport parle de 100 objets, pas de 500.")
chip(s, 1)
question(s, "Peut-on apprendre exactement les poids, λ et les profils d'un MR-Sort à partir d'un learning set classé ?")
block(s, 0.7, 2.5, 6.3, 1.2, "Données", ["dataset0 : 60 objets, 5 critères, 3 catégories", "Protocole du sujet : 20 modèles tirés au hasard, 100 objets d'apprentissage, 10 000 de test"], size=12)
block(s, 0.7, 3.8, 6.3, 1.6, "Méthode", ["MIP Gurobi : une binaire δ par objet, critère et profil (xᵢ ≥ bᵢ), une binaire γ par objet", "Objectif : maximiser les objets restitués, donc toujours soluble", [("M(δ − 1) ≤ xᵢ − bᵢ ≤ Mδ − ε", {"bold": True, "size": 14, "color": NAVY})]], size=12)
block(s, 0.7, 5.5, 6.3, 1.4, "Pourquoi ce choix", ["Exact et sans réglage : une référence de ce qu'on peut atteindre", "Inégalités strictes → ε = 10⁻³, tolérance entière 10⁻⁹, recentrage de −ε/2"], size=12)
card(s, 7.3, 2.5, 5.5, 1.0, [[("0,94 ", {"bold": True, "size": 28}), ("de fidélité en test (100 objets), en 0,7 s", {"size": 15})]], fill=NAVY, color=WHITE)
head(s, 7.3, 3.65, 5.5, "Baseline : la taille du learning set", MUTED, 14)
table(s, 7.3, 4.1, (1.9, 1.6, 2.0), [
  ("Learning set", "Qualité", "Temps moyen"),
  ("100 objets", "0,937", "0,7 s"),
  ("500 objets", "0,987", "14 à 16 s")], rowh=0.5, size=14, hl=(2,))
text(s, 7.3, 5.62, 5.5, 0.5, "Qualité = part des 10 000 objets de test classés comme le modèle d'origine · dataset0 : 60/60 objets restitués", size=12, color=MUTED)
transition(s, [[("→ Jalon 2 : ", {"bold": True}), ("5× plus de données coûtent ×20 en temps ; il faut une heuristique (lincs).", {})]], x=7.3, y=6.15, w=5.5, h=0.75)
foot(s, "20 ground truths (poids Dirichlet), 5 critères, 3 catégories, 10 000 objets de test · docs/jalon1.md")

# 5 — Jalon 2 A : enjeu et approche ---------------------------------------------------------------
s = slide("Jalon 2 : deux segments de clients inconnus, deux modèles à apprendre en même temps",
 "[~1,25 min — à répartir] Question : le supermarché a deux segments de comportement, inconnus ; il faut partitionner le learning set ET apprendre un MR-Sort par segment (inv-2-MR-Sort). Données : 72 fichiers (types A et B), 6 à 10 critères, 3 à 5 catégories, 300 à 1 200 objets, segments 50-50 ou 75-25, bruit 0 ou 10 % ; l'algorithme ignore les proportions et le bruit, qui ne servent qu'à évaluer. Méthode : alternance de type k-means (clusterwise regression, Späth 1979) : on apprend un MR-Sort par segment avec lincs (population de 9 candidats, poids par programmation linéaire, profils par heuristique, 4 pires réinitialisés), puis on réaffecte chaque objet au modèle qui l'explique mieux ; jusqu'à partition stable, puis polish. Pourquoi : (1) lincs car le MIP du jalon 1 explose avec la taille ; (2) multi-départ (1 guidé par les erreurs d'un modèle unique + 3 aléatoires) car l'alternance tombe dans des optima locaux ; (3) un objet ne bouge que s'il est STRICTEMENT mieux expliqué ailleurs : convergence, pas d'allers-retours ; (4) comparaison lexicographique : écart de catégorie, puis marge. Variantes abandonnées : partager ou exclure les objets ambigus (annexe A3).")
chip(s, 2)
question(s, "Comment partitionner le learning set ET apprendre un MR-Sort par segment, sans connaître les segments ?")
block(s, 0.7, 2.5, 3.9, 3.15, "Données", ["72 fichiers (types A et B)", "6 à 10 critères, 3 à 5 catégories", "300 à 1 200 objets", "Segments 50-50 ou 75-25", "Bruit 0 % ou 10 %", [("L'algorithme ignore proportions et bruit", {"color": MUTED, "size": 12})]], size=13)
box(s, 4.8, 2.5, 8.0, 3.15, CARD)
text(s, 5.0, 2.6, 7.6, 0.3, "Méthode : alternance de type k-means (Späth 1979)", size=13, bold=True, color=BLUE)
for i, lab in enumerate(["Partition initiale\n(1 guidée + 3 aléatoires)", "1 MR-Sort lincs\npar segment", "Réaffecter chaque objet\nau modèle qui l'explique\nstrictement mieux"]):
    card(s, 5.0 + i * 2.55, 3.05, 2.2, 1.2, lab, size=12, align=PP_ALIGN.CENTER, fill=WHITE)
    if i < 2: arrow(s, 7.2 + i * 2.55, 3.65, 7.55 + i * 2.55, 3.65)
text(s, 5.0, 4.4, 7.6, 0.3, "↺ jusqu'à partition stable (≤ 20 itérations), puis « polish »", size=13, color=MUTED)
text(s, 5.0, 4.8, 7.6, 0.8, ["lincs apprend 1 MR-Sort : population de 9 modèles, poids par programmation linéaire (GLOP), profils par heuristique, 4 pires réinitialisés"], size=12, color=INK)
block(s, 0.7, 5.75, 12.1, 1.2, "Pourquoi ce choix", [
  "lincs plutôt que le MIP : il explose avec la taille · multi-départ (1 guidé + 3 aléatoires) : l'alternance tombe dans des optima locaux",
  "Un objet ne change de segment que s'il est strictement mieux expliqué ailleurs : convergence, pas d'allers-retours"], size=12)
foot(s, "Späth 1979 (clusterwise regression) · ≈ 7 min par fichier (4 départs × ≤ 20 itérations × 2 modèles) · docs/jalon2.md")

# 6 — Jalon 2 B : résultats -----------------------------------------------------------------------
s = slide("Jalon 2 : les deux modèles expliquent mieux le learning set, sans preuve de meilleure prédiction",
 "[~1,5 min — à répartir] Trois mesures, trois colonnes, avec les baselines dans chaque colonne. (1) Explication : on apprend et on mesure sur 100 % des objets (le sujet demande d'expliquer le learning set), 72 fichiers : détail par type et bruit : type A sans bruit 78,8 / 87,3 / 98,9 % (un modèle / partition aléatoire / segmentation), type A bruit 10 % 69,7 / 80,0 / 91,3, type B sans bruit 68,2 / 81,4 / 97,9, type B bruit 10 % 61,4 / 74,8 / 90,6 ; la segmentation ajoute 11 à 17 points par rapport à la partition aléatoire dans les quatre cas, et le bruit coûte environ 7 points (moyenne globale : 0,70 / 0,81 / 0,95). (2) Test : 10 % des objets écartés, 31 fichiers type A : 0,68, 0,79, 0,87. (3) Sans oracle : les deux premières colonnes comptent un objet comme bien classé si AU MOINS UN des deux modèles a raison, ce qui suppose de connaître la bonne catégorie. Un classifieur réel doit choisir un seul modèle : avec la règle des 5 plus proches voisins, 0,73 contre 0,71 pour un modèle seul, sur 4 fichiers et 60 objets de test. Chronologie à dire honnêtement : on a d'abord évalué en prédiction, puis réalisé que le jalon 2 relève de l'explicabilité (jalon2_explication.py), puis voulu tester ce que valent ces résultats (verif_j2_honnete.py). Donc : gain d'explication établi, gain de prédiction non.")
chip(s, 2)
banner(s, [[("La segmentation explique 91 à 99 % des objets (+11 à 17 points vs partition aléatoire) ; ", {}), ("en prédiction sans oracle, le gain n'est pas établi", {"color": RGBColor(0xFF,0xC4,0xA8)})]])
# gauche : explication, par type et bruit
head(s, 0.7, 2.5, 7.4, "Explication du learning set", BLUE, 18)
text(s, 0.7, 2.9, 7.4, 0.3, "Part des objets bien classés · 72 fichiers · bien classé = par au moins un des 2 modèles", size=12, color=MUTED, space=0)
box(s, 5.95, 3.4, 2.15, 3.0, PALE, shape=MSO_SHAPE.RECTANGLE)
table(s, 0.7, 3.45, (2.0, 1.6, 1.95, 1.85), [
    ("Type, bruit", "1 modèle", "Partition aléatoire", "Segmenté"),
    ("A, sans bruit", "78,8 %", "87,3 %", "98,9 %"),
    ("A, bruit 10 %", "69,7 %", "80,0 %", "91,3 %"),
    ("B, sans bruit", "68,2 %", "81,4 %", "97,9 %"),
    ("B, bruit 10 %", "61,4 %", "74,8 %", "90,6 %")], rowh=0.6, size=15, hl=(), align=[PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.CENTER, PP_ALIGN.CENTER])
# droite : prédiction
head(s, 8.6, 2.5, 4.2, "Et en prédiction ?", ORANGE, 18)
text(s, 8.6, 2.9, 4.2, 0.3, "Part des objets de test bien classés", size=12, color=MUTED, space=0)
box(s, 8.5, 3.4, 4.3, 3.0, CARD)
table(s, 8.65, 3.5, (1.9, 1.0, 1.0), [
    ("", "1 modèle", "2 modèles"),
    ("Test, avec oracle (31 fichiers)", "0,68", "0,87"),
    ("Sans oracle, 5-NN (4 fichiers)", "0,71", "0,73")], rowh=0.8, size=14, hl=(2,))
text(s, 8.7, 5.95, 3.9, 0.4, "« avec oracle » : au moins un des deux a raison", size=11, color=MUTED, space=0)
transition(s, [[("→ Jalon 3 : ", {"bold": True}), ("B réutilise cette alternance pour apprendre 2 modèles dans un mélange brouillé par un agent malveillant.", {})]])
foot(s, "Constat fait après coup : le jalon 2 relève de l'explicabilité → jalon2_explication.py, puis verif_j2_honnete.py pour tester ces résultats · 1 graine, pas de barres d'erreur")

# 7 — Jalon 3 A : le scénario ---------------------------------------------------------------------
s = slide("Jalon 3 : A transmet, un agent malveillant brouille, B doit retrouver le modèle de A",
 "[~1,25 min — à répartir] Question : A transmet un learning set à B ; un agent malveillant ajoute de faux objets (au plus un par objet de A) ; B peut-il retrouver le modèle de A, et comment le malveillant peut-il mieux le duper ? Un SCÉNARIO est un tirage complet : un MR-Sort pour A, un MR-Sort pour le malveillant (même générateur : B ne peut pas les distinguer à leur forme), les objets de A (300) et ceux du malveillant (au plus 300), le mélange dont les lignes sont mélangées, et 1 000 objets de test étiquetés par le modèle de A. Chaque graine donne un scénario différent. Exemple (graine 0) : A classe 58 / 16 / 26 % des objets dans les catégories 1 / 2 / 3, le malveillant 36 / 53 / 11 % : les deux règles sont très différentes. Le ratio est le nombre d'objets du malveillant divisé par celui de A. Plafond : si B n'apprenait que sur les objets de A (ce qu'il ne peut pas faire), il atteindrait 0,98. Méthode de B : réutiliser le jalon 2 pour apprendre deux modèles, puis garder celui qui classe correctement le plus d'objets reçus (critère « objets expliqués ») ; A en envoie plus, donc son modèle recolle à plus d'objets. Pourquoi ce critère : l'algorithme équilibre les segments, la taille d'un segment est trompeuse (261/189 trouvé pour 300/150 réels) ; 57 bons choix sur 60 avec « objets expliqués » contre 49 sur 60 avec la taille. Baseline : un modèle unique appris sur tout le mélange.")
chip(s, 3)
question(s, "B peut-il retrouver le modèle de A dans un mélange brouillé, et comment le malveillant peut-il mieux le duper ?")
block(s, 0.7, 2.5, 3.9, 3.15, "Données : un scénario = un tirage", [
  "Un MR-Sort pour A, un autre pour le malveillant (même générateur)",
  "A : 300 objets · malveillant : ≤ 300 (ratio)",
  "Mélange sans la source des objets",
  "Test : 1 000 objets étiquetés par A",
  [("Exemple (graine 0) : A classe 58/16/26 % des objets dans C1/C2/C3, le malveillant 36/53/11 %", {"color": MUTED, "size": 11})]], size=12)
box(s, 4.8, 2.5, 8.0, 3.15, CARD)
text(s, 5.0, 2.6, 7.6, 0.3, "Méthode", size=13, bold=True, color=BLUE)
card(s, 5.0, 3.0, 1.9, 0.8, [[("A", {"bold": True, "size": 16}), ("  300 objets", {"size": 12})]], fill=BLUE, color=WHITE, align=PP_ALIGN.CENTER)
card(s, 5.0, 4.15, 1.9, 0.8, [[("Malveillant", {"bold": True, "size": 15})], [("≤ 300 objets", {"size": 12})]], fill=ORANGE, color=WHITE, align=PP_ALIGN.CENTER, space=0)
arrow(s, 6.9, 3.4, 7.4, 3.9); arrow(s, 6.9, 4.55, 7.4, 4.1)
card(s, 7.5, 3.4, 1.5, 1.1, [[("B", {"bold": True, "size": 16})], [("sans la source", {"size": 11})]], fill=NAVY, color=WHITE, align=PP_ALIGN.CENTER, space=0)
text(s, 9.3, 2.95, 3.4, 1.0, "B apprend 2 modèles (jalon 2) et garde celui qui explique le plus d'objets reçus", size=12, bold=True, color=INK)
text(s, 9.3, 4.0, 3.4, 1.5, [[("Baseline : ", {"bold": True}), ("1 modèle unique appris sur tout le mélange", {})], [("Plafond : ", {"bold": True}), ("0,98, si B n'apprenait que sur A", {})]], size=12)
text(s, 5.0, 5.15, 4.2, 0.45, "Mesure : précision de B sur les 1 000 objets de test", size=12, color=MUTED)
block(s, 0.7, 5.75, 12.1, 1.2, "Pourquoi ce choix", [
  "Le jalon 2 sépare les deux sources ; « objets expliqués » car la taille d'un segment est trompeuse (261/189 trouvé pour 300/150 réels)",
  "57 bons choix sur 60 avec « objets expliqués » (ratio < 1), contre 49 sur 60 avec la taille du segment"], size=12)
foot(s, "6 critères, 3 catégories · ratio = objets du malveillant / objets de A · exemple de la graine 0 : docs/jalon3.md (T1)")

# 8 — Jalon 3 B : le cas de base, ratio 1 ------------------------------------------------------------
s = slide("Malveillant basique : B identifie A jusqu'au ratio 0,85, puis choisit au hasard à quota égal",
 "[~1,5 min — à répartir] Le cas de base : le malveillant tire un MR-Sort au hasard et envoie des objets ; la variable est le ratio, nombre d'objets du malveillant divisé par celui de A. 80 scénarios, 20 par ratio. Lire la figure : bleu = pipeline à 2 modèles (méthode de B), orange = modèle unique (baseline), gris pointillé haut = oracle (le meilleur des deux modèles appris), gris bas = hasard. Tant que le ratio ≤ 0,85, B désigne la bonne règle 18/20 à 20/20 ; à 0,925 (20 scénarios de plus) 16/20 ; à ratio 1 (même quota) 9/20, pile ou face. Le meilleur des deux modèles atteint encore 0,85 : la séparation marche, c'est le CHOIX qui échoue. À ratio 1 le dommage est d'environ 0,28 (plafond 0,98, modèle unique 0,70) : c'est la référence à laquelle les stratégies suivantes se comparent. Point d'honnêteté : le modèle unique fait aussi bien (0,91 / 0,84 / 0,83 / 0,70) en 4 s au lieu de 27 à 31 s ; on a essayé de combler l'écart au plafond (même budget de calcul, retrait des objets mal classés, réapprentissage) sur 100 scénarios : aucune variante ne fait mieux que +0,3 point (annexe A5).")
chip(s, 3)
banner(s, [[("Quota égal (ratio 1) : B ne retrouve plus A — ", {}), ("9 bonnes règles sur 20 et 0,68 de précision, contre un plafond de 0,98", {"color": RGBColor(0xFF,0xC4,0xA8)})]])
s.shapes.add_picture(str(ROOT/"results/t4_final.png"), Inches(0.7), Inches(2.5), width=Inches(6.2))
head(s, 7.3, 2.5, 5.5, "Cas de base : ratio 1, 20 scénarios", BLUE, 16)
text(s, 7.3, 2.85, 5.5, 0.45, "Précision = part des 1 000 objets de test classés comme le ferait le modèle de A", size=12, bold=True, color=INK, space=0)
bars(s, 7.3, 3.35, 5.5, [("plafond : B n'apprend que sur A", 0.98, GREY, "0,98"), ("modèle unique (baseline)", 0.70, ORANGE, "0,70"),
                         ("choix de B (pipeline à 2 modèles)", 0.68, BLUE, "0,68"), ("meilleur des 2 modèles (oracle)", 0.85, GREY, "0,85")], gap=0.68)
card(s, 7.3, 6.12, 5.5, 0.8, [[("Bonne règle choisie : ", {"bold": True}), ("ratio 0,5 → 20/20 · 0,7 → 19/20 · 0,85 → 18/20 · 0,925 → 16/20 · ", {}), ("1 → 9/20", {"bold": True, "color": ORANGE})]], size=12)
foot(s, "80 scénarios (20 par ratio, graines 300 à 379) + 20 à ratio 0,925 · plafond : 100 scénarios de confirmation · barres ± 1,96 erreur-type · results/t4_final.csv")

# 9 — Jalon 3 C : stratégies de brouillage ------------------------------------------------------------
s = slide("Trois stratégies de brouillage : une règle simple et cohérente met B en échec",
 "[~1,5 min — à répartir] Le malveillant n'a pas accès au modèle de A ; il utilise tout son quota (ratio 1) et ne change que les étiquettes de ses objets. Quatre façons de les fabriquer : MR-SORT AU HASARD (le cas de base de la diapo précédente) ; MODÈLE EXTRÊME (un seul critère porte le poids, seuils hauts : presque tous ses objets tombent dans la catégorie la plus basse) ; CLASSE FIXE (tous ses objets dans la catégorie la plus basse, sans modèle) ; DEUX MR-SORT (deux modèles, moitié-moitié). 10 scénarios (graines 1100 à 1109) ; les objets de A sont identiques pour les quatre stratégies d'une même graine. Résultats : classe fixe et modèle extrême font tomber B à 0,44 et 0,45, sous le hasard (0,58 à 0,61) : B garde la règle du malveillant (bonne règle 2/10) ; le modèle unique tombe à 0,57 et 0,63. Deux MR-Sort gêne peu (0,81, 10/10) : les objets de A restent les plus cohérents. Mécanisme : une règle simple et très cohérente « explique » plus d'objets que le vrai modèle de A, donc le critère « objets expliqués » de B se retourne contre lui. Honnêteté : sur un seul scénario (graine de démonstration) les chiffres sont très variables, d'où les 10 scénarios ; les barres d'erreur restent larges.")
chip(s, 3)
banner(s, [[("Classe fixe et modèle extrême font tomber B à 0,44–0,45, sous le hasard : ", {}), ("une règle simple « explique » plus d'objets que le vrai modèle", {"color": RGBColor(0xFF,0xC4,0xA8)})]])
strat = [("MR-Sort au hasard", "cas de base : un MR-Sort tiré comme celui de A", "0,73", "5/10", BLUE),
         ("Modèle extrême", "un seul critère porte le poids, seuils hauts : presque tout en catégorie la plus basse", "0,45", "2/10", ORANGE),
         ("Classe fixe", "tous ses objets dans la catégorie la plus basse, sans modèle", "0,44", "2/10", ORANGE),
         ("Deux MR-Sort", "deux modèles, la moitié des objets chacun", "0,81", "10/10", BLUE)]
text(s, 3.6, 2.5, 3.0, 0.3, "précision de B · bonne règle", size=12, bold=True, color=MUTED, align=PP_ALIGN.RIGHT)
for i, (a, b, v, r, c) in enumerate(strat):
    y = 2.85 + i * 0.9
    box(s, 0.7, y, 5.9, 0.8, PEACH if c == ORANGE else CARD)
    text(s, 0.9, y + 0.07, 3.9, 0.28, a, size=14, bold=True, color=NAVY, space=0)
    text(s, 0.9, y + 0.37, 3.9, 0.42, b, size=11, color=INK, space=0)
    text(s, 4.85, y + 0.1, 1.65, 0.35, v, size=20, bold=True, color=c, align=PP_ALIGN.RIGHT, space=0)
    text(s, 4.85, y + 0.48, 1.65, 0.28, r, size=12, color=MUTED, align=PP_ALIGN.RIGHT, space=0)
text(s, 0.7, 6.42, 5.9, 0.55, "Précision = part des 1 000 objets de test classés comme le ferait A ; bonne règle = B garde le modèle de A (sur 10 scénarios, ratio 1).", size=12, color=MUTED)
s.shapes.add_picture(str(ROOT/"results/strategies_multi.png"), Inches(6.85), Inches(2.5), width=Inches(5.95))
text(s, 6.85, 6.7, 5.95, 0.3, "Baselines : modèle unique (orange), hasard (gris) · barres ± 1,96 erreur-type", size=11, color=INK)
foot(s, "10 scénarios par stratégie · B = choix du pipeline à 2 modèles · results/strategies_multi.csv")

# 10 — Conclusion ------------------------------------------------------------
s = slide("Ce qu'il faut retenir : un message par jalon",
 "[~1,25 min — à répartir] Trois messages, un par jalon, puis les limites et l'ouverture. (1) Le MIP est exact mais ne passe pas à l'échelle (0,94 à 100 objets en 0,7 s ; 0,99 à 500 objets en 15 s). (2) L'alternance + multi-départ explique 95 % du learning set avec deux modèles (+14 points vs partition aléatoire) ; en test 0,87 ; mais sans oracle le gain de prédiction n'est pas établi (0,73 vs 0,71). (3) Jeu A / B / malveillant : B identifie A tant que le malveillant envoie moins (≤ 0,85) ; à quota égal le choix est aléatoire (9/20) ; une règle simple et extrême est plus nuisible qu'un modèle réaliste (0,44). Le modèle unique fait aussi bien que le pipeline en précision. Limites à assumer : un seul format (6 critères, 3 catégories), 10 scénarios pour les stratégies, jalon 2 sur 1 graine, malveillant sans connaissance du modèle de A. Pistes : B pourrait détecter les sources « trop simples » (classe constante, un seul critère) ; le malveillant pourrait placer ses objets ailleurs que uniformément. Remercier, ouvrir aux questions.")
cols = [("Jalon 1", "MIP exact", "Retrouve le modèle (0,94 en test, 0,7 s à 100 objets) mais 14 à 16 s à 500 objets : ne passe pas à l'échelle.", BLUE),
        ("Jalon 2", "Segmentation", "Deux modèles expliquent 95 % du learning set (+14 pts vs partition aléatoire). Sans oracle : 0,73 vs 0,71, gain de prédiction non établi.", BLUE),
        ("Jalon 3", "Brouillage", "B identifie A jusqu'au ratio 0,85 ; à quota égal, pile ou face (9/20). Classe fixe / modèle extrême : B tombe à 0,44.", ORANGE)]
for i, (a, b, c, col) in enumerate(cols):
    x = 0.7 + i * 4.15
    box(s, x, 1.65, 3.9, 3.35, CARD)
    text(s, x+0.3, 1.85, 3.3, 0.4, a, size=16, bold=True, color=col)
    text(s, x+0.3, 2.3, 3.3, 0.6, b, size=26, bold=True, color=NAVY)
    text(s, x+0.3, 3.1, 3.3, 1.85, c, size=15, color=INK)
head(s, 0.7, 5.25, 5.8, "Limites", ORANGE)
text(s, 0.7, 5.7, 5.9, 1.3, ["Un seul format testé : 6 critères, 3 catégories", "Jalon 2 : 1 graine ; jalon 3 : 10 scénarios par stratégie", "Le modèle unique fait aussi bien que le pipeline de B"], size=14, space=5)
head(s, 7.0, 5.25, 5.8, "Pistes", BLUE)
text(s, 7.0, 5.7, 5.8, 1.3, ["B détecte les sources « trop simples » (classe constante, un critère)", "Le malveillant choisit où placer ses objets", "Apprentissage robuste pour combler l'écart au plafond 0,98"], size=14, space=5)

# ================================================================== ANNEXES
s = slide(None, "Annexes : à n'ouvrir que si une question le demande. A1 MIP ; A2 learn_mrsort ; A3 variantes abandonnées au jalon 2 ; A4 vérification honnête du jalon 2 ; A5 jalon 3 : identification et améliorations de B ; A6 limites.", dark=True)
text(s, 0.9, 2.6, 11.5, 1.2, "Annexes", size=46, bold=True, color=WHITE)
text(s, 0.9, 3.8, 11.5, 2.5, ["A1  MIP du jalon 1 en détail", "A2  Comment lincs apprend un MR-Sort", "A3  Jalon 2 : décisions et variantes abandonnées", "A4  Jalon 2 : vérification sans oracle", "A5  Jalon 3 : identification de A et améliorations de B", "A6  Limites"], size=18, color=PALE, space=6)

# A1 ------------------------------------------------------------------------
s = slide("A1 · MIP du jalon 1 : variables, contraintes et réglages numériques",
 "Variables : wᵢ, λ, bʰᵢ continues ; δʰᵢ(x) binaires (une par objet, critère et profil utile) ; wʰᵢ(x) = wᵢ·δʰᵢ(x) continues (linéarisation) ; γ(x) binaire. Pour un objet de classe h, seuls les profils bʰ⁻¹ et bʰ interviennent, ce qui limite les binaires. Big-M = plage + 1 pour garder la relaxation serrée ; M = 2 pour les contraintes de classe (sommes de poids dans [0,1]). ε = 1e-3 : assez grand pour dépasser la tolérance du solveur. IntFeasTol = 1e-9 : par défaut Gurobi accepte δ = 1e-6 comme 0, ce qui permettrait de tricher sur une inégalité stricte. Recentrage −ε/2 pour que la règle sans tolérance redonne les mêmes classes. Validation indépendante : predict numpy contre ObjVal Gurobi ; dataset0 60/60, contrôle 1,000 ; exemple d'admission du sujet 4/4.")
head(s, 0.7, 1.65, 6.0, "Variables")
text(s, 0.7, 2.1, 5.9, 2.3, ["wᵢ, λ, bʰᵢ continues", "δʰᵢ(x) ∈ {0,1} : xᵢ ≥ bʰᵢ, par objet, critère et profil utile", "wʰᵢ(x) = wᵢ·δʰᵢ(x) : produit linéarisé", "γ(x) ∈ {0,1} : l'objet x est bien restitué"], size=15, space=6)
head(s, 0.7, 4.4, 6.0, "Contraintes")
text(s, 0.7, 4.85, 5.9, 2.1, ["Σᵢ wᵢ = 1 ; profils croissants", "M(δ − 1) ≤ xᵢ − bᵢ ≤ Mδ − ε", "wʰ ≤ w ;  wʰ ≤ δ ;  wʰ ≥ δ + w − 1", "classe h ≥ 1 : Σ wʰ⁻¹(x) ≥ λ − 2(1 − γ)", "classe h ≤ p−2 : Σ wʰ(x) + ε ≤ λ + 2(1 − γ)"], size=15, space=6)
head(s, 7.1, 1.65, 5.7, "Réglages et raisons", ORANGE)
table(s, 7.1, 2.15, (2.2, 3.5), [
  ("Choix", "Raison"),
  ("Big-M = plage + 1", "relaxation continue la plus serrée"),
  ("ε = 10⁻³", "dépasse la tolérance du solveur"),
  ("IntFeasTol = 10⁻⁹", "empêche δ = 10⁻⁶ de « tricher »"),
  ("Recentrage −ε/2", "règle sans tolérance = mêmes classes"),
  ("Objectif Σγ", "toujours soluble si bruit"),
  ("Validation numpy", "détecte une erreur de signe ou de M")], rowh=0.62, size=13, align=[PP_ALIGN.LEFT, PP_ALIGN.LEFT])
foot(s, "docs/jalon1.md · notebooks/01_jalon1_mrsort.ipynb")

# A2 ------------------------------------------------------------------------
s = slide("A2 · Comment lincs apprend un MR-Sort (brique 1, `learn_mrsort`)",
 "lincs est utilisé comme boîte noire avec ses composants assemblés à la main. Population de 9 modèles : plusieurs candidats limitent le risque de rester dans un optimum local. À chaque itération : initialisation des profils par pouvoir discriminant maximal probabiliste ; poids optimisés par programmation linéaire (GLOP), profils fixés ; profils améliorés par une heuristique de précision, poids fixés ; les 4 moins bons modèles réinitialisés. Arrêt : 100 % de précision, temps écoulé, ou 30 itérations sans progrès. Normalisation : lincs fixe le seuil à 1 avec des poids bruts ; on stocke raw_weights, weights = W/ΣW et lmbda = 1/ΣW. Au jalon 2, chaque tour de l'alternance appelle cette brique deux fois ; au jalon 3, 4 départs en parallèle.")
head(s, 0.7, 1.65, 6.0, "Une itération")
for i, (a, b) in enumerate([("Initialiser", "profils par pouvoir discriminant maximal probabiliste"), ("Poids", "programmation linéaire (GLOP), profils fixés"), ("Profils", "heuristique de précision, poids fixés"), ("Réinitialiser", "les 4 moins bons modèles sur 9")]):
    card(s, 0.7, 2.15+i*1.1, 6.0, 0.95, [[(a + " : ", {"bold": True, "color": BLUE}), (b, {})]], size=15)
head(s, 7.2, 1.65, 5.6, "Arrêt et sortie", ORANGE)
text(s, 7.2, 2.15, 5.6, 2.2, [
  [("Arrêt dès que : ", {"bold": True}), ("100 % de précision, ou temps écoulé, ou 30 itérations sans progrès", {})],
  [("Sortie : ", {"bold": True}), ("le meilleur des 9 modèles", {})],
], size=15, space=10)
card(s, 7.2, 4.4, 5.6, 1.5, [[("Normalisation : ", {"bold": True}), ("lincs fixe le seuil à 1 avec des poids bruts W", {})], [("w = W / ΣW   et   λ = 1 / ΣW", {"bold": True, "size": 18})]], size=15, align=PP_ALIGN.CENTER)
text(s, 7.2, 6.1, 5.6, 0.8, "Au jalon 2 : 2 appels par tour de l'alternance. Au jalon 3 : 4 départs en parallèle.", size=14, color=MUTED)
foot(s, "docs/jalon2.md (brique 1) · Sobrie, thèse (heuristique weights-profiles-breed)")

# A3 ------------------------------------------------------------------------
s = slide("A3 · Jalon 2 : décisions de conception et variantes abandonnées",
 "Décisions : réaffectation strictement mieux expliqué (Späth / ACC Brisimi 2018) car les égalités de marge sont fréquentes ; comparaison lexicographique parce qu'une erreur d'une catégorie vaut mieux que deux ; plancher de 10 % pour un segment (modèles dégénérés sinon) ; arrêt : le seuil fixe 0,97 n'était jamais atteint avec 10 % de bruit, l'arrêt sur validation coûtait des données sans gain net, retenu : partition stable + meilleure itération ; polish de 4 s au lieu de 1 s ; budget proportionnel au nombre de paramètres. Variantes : partage des ambigus : test 0,958 sans partage contre 0,933 avec, +23 % de temps ; exclusion des ambigus : 0,80 à 0,83 contre 0,77 mais 60 objets de test, non reproductible. À dire honnêtement : l'effet de l'exclusion n'est ni établi ni réfuté.")
table(s, 0.7, 1.65, (2.9, 4.2, 4.9), [
  ("Question", "Décision", "Raison"),
  ("Qui change de segment ?", "seulement si strictement mieux expliqué", "convergence ; égalités de marge fréquentes"),
  ("Comparer deux modèles", "écart de catégorie, puis marge", "se tromper d'1 catégorie < de 2"),
  ("Quand s'arrêter ?", "partition stable + meilleure itération", "seuil 0,97 jamais atteint avec 10 % de bruit"),
  ("Segment minuscule", "plancher de 10 % des objets", "évite les modèles dégénérés"),
  ("Apprentissages courts", "polish de 4 s au lieu de 1 s", "améliore les modèles livrés"),
  ("Départ", "1 guidé + 3 aléatoires", "optima locaux")], rowh=0.55, size=13, align=[PP_ALIGN.LEFT]*3)
head(s, 0.7, 5.6, 6.0, "Variantes abandonnées", ORANGE)
text(s, 0.7, 6.05, 12.1, 0.9, [
  [("Partager les ambigus : ", {"bold": True}), ("test 0,958 sans partage vs 0,933 avec, +23 % de temps.   ", {}),
   ("Exclure les ambigus : ", {"bold": True}), ("0,80 à 0,83 vs 0,77, mais 60 objets de test et non reproductible : effet ni établi ni réfuté.", {})]], size=14)
foot(s, "docs/jalon2.md")

# A4 ------------------------------------------------------------------------
s = slide("A4 · Jalon 2 : que reste-t-il de la précision sans oracle ?",
 "Script verif_j2_honnete.py : 4 fichiers type_a/cr06_ca03, n = 600, graine 2, 10 % de test (60 objets) jamais utilisés pour apprendre. Colonnes : unique = un seul MR-Sort ; hasard = choisir un des deux modèles au hasard ; 5-NN = règle sans oracle : segment majoritaire des 5 plus proches voisins de l'apprentissage, puis on applique le modèle de ce segment ; union = au moins un des deux a raison (avec oracle) ; constante = un prédicteur trivial qui répond toujours l'une des deux catégories les plus fréquentes, avec le même oracle. Moyennes : 0,71 / 0,62 / 0,73 / 0,90 / 0,85. Lecture : sans oracle, 0,73 contre 0,71, soit un objet sur 60. L'union est en grande partie un artefact : le prédicteur trivial atteint 0,85 avec le même oracle. Portée : quatre fichiers, une graine, un objet = 1,7 point : contrôle de cohérence, pas benchmark. Ça ne prouve pas que la segmentation est inutile : le gain d'explication est réel, le gain de prédiction n'est pas démontré.")
table(s, 0.7, 1.65, (3.4, 1.4, 1.4, 1.4, 1.4, 1.5), [
  ("Fichier (n = 600)", "Un seul", "Hasard", "5-NN", "Union", "Constante"),
  ("50-50, sans bruit", "0,60", "0,62", "0,68", "0,88", "0,88"),
  ("75-25, sans bruit", "0,87", "0,72", "0,78", "0,95", "0,93"),
  ("50-50, bruit 10 %", "0,63", "0,48", "0,70", "0,92", "0,87"),
  ("75-25, bruit 10 %", "0,75", "0,64", "0,73", "0,87", "0,70"),
  ("Moyenne", "0,71", "0,62", "0,73", "0,90", "0,85")], rowh=0.6, size=15, hl=(5,), hl_fill=CARD, hl_color=NAVY)
text(s, 0.7, 5.25, 12.1, 0.32, "Valeurs = précision de test (part des 60 objets de test bien classés).", size=12, color=MUTED)
card(s, 0.7, 5.6, 5.9, 1.3, [[("Sans oracle : ", {"bold": True}), ("0,73 contre 0,71 pour un seul modèle, soit 1 objet sur 60.", {})]], size=15)
card(s, 6.9, 5.6, 5.9, 1.3, [[("Avec oracle : ", {"bold": True}), ("l'« union » 0,90 est surtout un artefact, un prédicteur trivial fait 0,85.", {})]], size=15, fill=PEACH)
foot(s, "results/j2_mesure_honnete.csv · 4 fichiers, graine 2, 60 objets de test (1 objet = 1,7 point)")

# A5 ------------------------------------------------------------------------
s = slide("A5 · Jalon 3 : le pipeline identifie A, mais le modèle unique fait aussi bien",
 "Critère d'identification retenu : objets expliqués (le modèle qui classe correctement le plus d'objets du mélange est celui de A), car learn_B tend à équilibrer les segments : la taille d'un segment est un mauvais indicateur (261/189 trouvé pour 300/150 réels). Aux ratios < 1 : 57 bons choix sur 60 contre 49 sur 60 pour la taille. Mais en précision, M3 ne bat pas M1 (M3 − M1 = +0,006 [−0,029 ; +0,036]) et M1 est 7 fois plus rapide (4,2 s vs 27 à 31 s). Plafond : lincs appris sur les seuls objets de A donne 0,98 à tous les ratios : toute la perte vient de la contamination. Améliorations testées sur 100 scénarios : plus de calcul pour M1 (M1_eq) +0,003 ; réapprentissage après choix +0,002 à +0,003 par rapport à M1 ; aucune n'est mesurable. L'abstention (seuil 0,06) ne fait pas gagner de précision et la confiance sépare mal le cas indécidable du cas difficile.")
table(s, 0.7, 1.65, (1.7, 1.4, 1.4, 1.4, 1.4), [
  ("Ratio", "M1 (unique)", "M3 (pipeline)", "Oracle", "Bon choix M3"),
  ("0,5", "0,910", "0,867", "0,867", "20/20"),
  ("0,7", "0,844", "0,872", "0,880", "19/20"),
  ("0,85", "0,830", "0,862", "0,900", "18/20"),
  ("1,0", "0,703", "0,675", "0,853", "9/20")], rowh=0.6, size=15, hl=(4,))
text(s, 0.7, 4.75, 7.3, 0.4, "Précision sur le test (modèle de A), 20 scénarios par ratio, lot final.", size=13, color=MUTED)
head(s, 8.4, 1.65, 4.4, "Plafond et améliorations", ORANGE)
text(s, 8.4, 2.15, 4.4, 3.3, [
  [("Plafond 0,98 ", {"bold": True}), ("(lincs sur les seuls objets de A) : toute la perte vient de la contamination", {})],
  [("M1 avec 7× plus de calcul : ", {"bold": True}), ("+0,003", {})],
  [("Réapprentissage après choix : ", {"bold": True}), ("+0,002 vs M1", {})],
  [("Abstention (seuil 0,06) : ", {"bold": True}), ("aucun gain de précision", {})],
], size=14, space=8)
card(s, 0.7, 5.3, 12.1, 1.5, [[("Pourquoi le critère « objets expliqués » ? ", {"bold": True}), ("La taille d'un segment est trompeuse (261/189 trouvé pour 300/150 réels) : 57 bons choix sur 60 avec les objets expliqués, contre 49 sur 60 avec la taille. ", {}),
                              ("Mais M3 − M1 = +0,006 [−0,029 ; +0,036] : pas de gain de précision.", {"bold": True})]], size=15)
foot(s, "results/t4_final.csv, results/b_confirm.csv (100 scénarios, graines 600 à 699) · docs/jalon3.md")

# A6 ------------------------------------------------------------------------
s = slide("A6 · Limites à connaître",
 "À dire honnêtement si on est interrogé. Jalon 1 : NP-difficile, ×20 en temps entre 100 et 500 objets ; la qualité mesure la fidélité au modèle d'origine. Jalon 2 : benchmark sur 31 fichiers type A, une graine, test de 60 objets ; 72 fichiers pour l'explication ; la précision « au moins un des deux » suppose un oracle ; proportions de segments retrouvées à 9 points près ; coût élevé du multi-départ. Jalon 3 : une seule configuration ; 10 scénarios par stratégie ; bon choix défini a posteriori avec la vérité terrain ; lincs s'arrête sur un temps, donc non reproductible à l'octet près ; l'abstention n'est pas calibrée de façon fiable.")
cols = [("Jalon 1", ["Passage à l'échelle : ×20 en temps de 100 à 500 objets", "ε et M sont des constantes à réadapter à d'autres échelles", "La qualité mesure la fidélité au modèle d'origine"]),
        ("Jalon 2", ["Explication : 72 fichiers, 1 graine. Test : 31 fichiers type A", "« Au moins un des deux » suppose un oracle", "Proportions des segments à 9 points près ; ≈ 7 min par fichier", "Gain de prédiction sans oracle non démontré"]),
        ("Jalon 3", ["Une seule configuration (6 critères, 3 catégories, 300 objets)", "10 scénarios par stratégie, barres d'erreur larges", "« Bon choix » défini avec la vérité terrain", "lincs s'arrête sur un temps : non reproductible à l'octet près"])]
for i, (t, items) in enumerate(cols):
    x = 0.7 + i * 4.15
    box(s, x, 1.65, 3.9, 5.1, CARD)
    text(s, x+0.3, 1.85, 3.3, 0.4, t, size=18, bold=True, color=ORANGE if i == 2 else BLUE)
    text(s, x+0.3, 2.4, 3.3, 4.2, ["• " + it for it in items], size=14, space=10)

out = ROOT / "soutenance" / "soutenance_v2.pptx"; prs.save(out); print(out, len(prs.slides._sldIdLst), "diapos")
