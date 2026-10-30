import os
import pandas as pd
import plotly.graph_objects as go
import statsmodels.formula.api as smf
from scipy import stats

TABLES = "results/tables"
FIGURES = "analysis/figures"
COLORS = {"black": "#039be5", "white": "#f4511e"}

# figure styl
STYLE = {
    "layout.plot_bgcolor": "rgba(0, 0, 0, 0)",
    "layout.font.family": "Times New Roman",
    "layout.autosize": False,
    "layout.showlegend": True,
    "layout.margin": {"r": 5, "t": 5, "l": 5, "b": 5},
    "layout.xaxis.linecolor": "black",
    "layout.xaxis.ticks": "inside",
    "layout.xaxis.mirror": True,
    "layout.xaxis.showline": True,
    "layout.xaxis.tickfont.size": 16,
    "layout.xaxis.title.font.size": 20,
    "layout.yaxis.linecolor": "black",
    "layout.yaxis.ticks": "inside",
    "layout.yaxis.mirror": True,
    "layout.yaxis.showline": True,
    "layout.yaxis.tickfont.size": 16,
    "layout.yaxis.title.font.size": 20,
    "layout.legend.bgcolor": "rgba(0, 0, 0, 0)",
    "layout.legend.xanchor": "right",
    "layout.legend.x": 1,
    "layout.legend.font.family": "monospace",
}

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
    fig = go.Figure()
    for grp, sub in data.groupby("majority"):
        fig.add_trace(go.Scatter(x=list(range(len(sub))), y=sub.shortest_path, mode="markers",
                                 name=grp, legendgroup=grp, marker=dict(size=4, color=COLORS.get(grp))))
        fig.add_trace(go.Scatter(x=[0, len(sub) - 1], y=[sub.shortest_path.mean()] * 2, mode="lines",
                                 name=f"{grp} mean", legendgroup=grp, line_color=COLORS.get(grp)))

    fig.update(**STYLE)
    fig.update_layout(legend=dict(
        orientation="h",
        entrywidthmode="fraction",
        entrywidth=0.22,
        x=1, xanchor="right",
        y=1, yanchor="top",
    ))
    fig.update_layout(
        font=dict(size=20),
        legend_font_size=16,
        xaxis=dict(title_font_size=24, tickfont_size=24, title="Row number"),
        yaxis=dict(title_font_size=24, tickfont_size=24, title=f"Time to reach {label}"),
    )
    try:
        fig.write_image(f"{FIGURES}/{csv[:-4]}_time.pdf", scale=4)
    except Exception as e:
        print("could not write the image:", e)


def income_models():
    data = pd.read_csv(f"{TABLES}/weighted_refactored_income.csv").dropna()
    print("\n===== commuting pairs, income =====")
    # R's `income^2` collapses to `income`; the quadratic term is in the poly model
    print(smf.ols("shortest_path ~ income", data).fit().summary())
    print(smf.ols("n_cameras ~ shortest_path - 1", data).fit().summary())
    print(smf.ols("n_cameras ~ income + I(income**2)", data).fit().summary())


# commuting pairs (weighted.rmd)
analyse("weighted.csv", "commuting pairs")
income_models()
