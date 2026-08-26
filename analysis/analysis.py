import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy import stats

TABLES = "results/tables"
FIGURES = "analysis/figures"
COLORS = {"black": "#00bfc4", "white": "#F8766D"}

os.makedirs(FIGURES, exist_ok=True)


# the demographic comparison shared by the transport hubs and the POI datasets
def analyse(csv, label, white_ref=False):
    data = pd.read_csv(f"{TABLES}/{csv}")
    black = data[data.majority == "black"]
    white = data[data.majority == "white"]

    print(f"\n===== {label} ({csv}) =====")
    print(f"mean time to reach -- black: {black.shortest_path.mean():.1f}, white: {white.shortest_path.mean():.1f}")

    tt = stats.ttest_ind(black.shortest_path, white.shortest_path, alternative="greater", equal_var=False)
    print(f"t-test time-to-reach (black > white): t={tt.statistic:.3f}, p={tt.pvalue:.4g}")

    # R used relevel(ref='white') for the hubs; default baseline (black) elsewhere
    majority = "C(majority, Treatment('white'))" if white_ref else "majority"
    print(smf.ols(f"n_cameras ~ {majority} + shortest_path", data).fit().summary())
    print(smf.ols(f"absolute_increase ~ {majority} + shortest_path", data).fit().summary())

    # time to reach by group, with group-mean lines
    plt.figure(figsize=(8, 5))
    for grp, sub in data.groupby("majority"):
        plt.scatter(range(len(sub)), sub.shortest_path, s=8, color=COLORS.get(grp), label=grp)
        plt.axhline(sub.shortest_path.mean(), color=COLORS.get(grp), linewidth=1)
    plt.xlabel("Row number"); plt.ylabel("Time to reach destination")
    plt.title(f"Time to reach {label} by group"); plt.legend(title="majority")
    plt.tight_layout(); plt.savefig(f"{FIGURES}/{csv[:-4]}_time.png", dpi=120); plt.close()


def income_models():
    data = pd.read_csv(f"{TABLES}/weighted_refactored_income.csv").dropna()
    print("\n===== commuting pairs, income =====")
    # R's `income^2` collapses to `income`; the quadratic term is in the poly model
    print(smf.ols("shortest_path ~ income", data).fit().summary())
    print(smf.ols("n_cameras ~ shortest_path - 1", data).fit().summary())
    print(smf.ols("n_cameras ~ income + I(income**2)", data).fit().summary())


# transport hubs (analysis.rmd) -- white baseline
for csv, label in [("CHI.csv", "Union Station"), ("ORD.csv", "O'Hare"), ("MDW.csv", "Midway")]:
    analyse(csv, label, white_ref=True)

# nearest POI (highschool-*.rmd, hospital-*.rmd)
for csv, label in [("high-school-1-closest.csv", "high school (nearest)"),
                   ("high-school-3-closest.csv", "high school (3 nearest)"),
                   ("hospital-1-closest.csv", "hospital (nearest)"),
                   ("hospital-3-closest.csv", "hospital (3 nearest)")]:
    analyse(csv, label)

# commuting pairs (weighted.rmd)
analyse("weighted.csv", "commuting pairs")
income_models()
