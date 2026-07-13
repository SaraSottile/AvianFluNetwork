# -*- coding: utf-8 -*-
"""
Created on Fri Jun 26 16:06:16 2026

@author: saras
"""

# -*- coding: utf-8 -*-
"""
Dominant transmission mechanism
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# --------------------------------------------------
# INPUT
# --------------------------------------------------

FATTORIE_FILE = "fattorie.xlsx"
RESULTS_FILE = "risultati_completi.xlsx"

L_CONST = 1e3

GAMMA_VALUES = [1/5, 1/10]
DMAX_VALUES = [1.5, 2.0]


# --------------------------------------------------
# LOOP
# --------------------------------------------------

for TARGET_GAMMA in GAMMA_VALUES:

    for TARGET_DMAX in DMAX_VALUES:

        print(
            f"\n===== gamma={TARGET_GAMMA:.3f}   "
            f"d_max={TARGET_DMAX} ====="
        )

        DATES_FILE = (
            f"date_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        BEST_INFECTOR_FILE = (
            f"best_infector_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        # --------------------------------------------------
        # LOAD DATA
        # --------------------------------------------------

        df = pd.read_excel(FATTORIE_FILE)

        df["conferma"] = pd.to_datetime(
            df["conferma"],
            dayfirst=True,
            errors="coerce"
        )

        dates = pd.read_excel(DATES_FILE)

        dates["E"] = pd.to_datetime(dates["E"])
        dates["D"] = pd.to_datetime(dates["D"])

        df = df.merge(
            dates[["codice", "E", "D"]],
            on="codice",
            how="left"
        )

        df_inf = (

            df[
                df["E"].notna()
                &
                df["D"].notna()
            ]

            .copy()

            .reset_index(drop=True)

        )

        n_inf = len(df_inf)

        print(f"Numero fattorie infette: {n_inf}")
        
        
                # --------------------------------------------------
        # LETTURA RISULTATI MODELLO
        # --------------------------------------------------
        
        df_res = pd.read_excel(RESULTS_FILE)
    # --------------------------------------------------
    # PARAMETRI MEDI
    # --------------------------------------------------
        subset = df_res[

            (df_res["gamma"] == TARGET_GAMMA)

            &

            (df_res["d_max"] == TARGET_DMAX)

        ]

        params = subset[
            ["beta_w", "beta_c", "beta_d", "alpha"]
        ].median()

        beta_w = params["beta_w"]
        beta_c = params["beta_c"]
        beta_d = params["beta_d"]
        alpha = params["alpha"]


        print("\nParametri - mediana")
        
        print(f"beta_w = {beta_w:.8f}")
        print(f"beta_c = {beta_c:.8f}")
        print(f"beta_d = {beta_d:.8f}")
        print(f"alpha  = {alpha:.4f}")


        # --------------------------------------------------
        # TIME
        # --------------------------------------------------

        t_start = df_inf["E"].min()
        t_end = df_inf["D"].max()

        n_days = (t_end - t_start).days + 1

        df_inf["E_days"] = (
            df_inf["E"] - t_start
        ).dt.days.astype(int)

        df_inf["D_days"] = (
            df_inf["D"] - t_start
        ).dt.days.astype(int)

        E_arr = df_inf["E_days"].values
        D_arr = df_inf["D_days"].values

        # --------------------------------------------------
        # CODICI → INDICI LOCALI
        # --------------------------------------------------

        codes = df_inf["codice"].tolist()

        code_to_idx = {
            code: idx
            for idx, code in enumerate(codes)
        }


        # --------------------------------------------------
        # NETWORK SAME COMPANY
        # --------------------------------------------------

        same_df = pd.read_excel("same_company.xlsx")

        same_df = same_df[
            same_df["from_code"].isin(codes)
            &
            same_df["to_code"].isin(codes)
        ].copy()

        same_df["from_id"] = (
            same_df["from_code"]
            .map(code_to_idx)
        )

        same_df["to_id"] = (
            same_df["to_code"]
            .map(code_to_idx)
        )


        # --------------------------------------------------
        # NETWORK DISTANCE
        # --------------------------------------------------

        neighbors_df = pd.read_excel(
            f"neighbors_dmax{TARGET_DMAX}.xlsx"
        )

        neighbors_df = neighbors_df[
            neighbors_df["from_code"].isin(codes)
            &
            neighbors_df["to_code"].isin(codes)
        ].copy()

        neighbors_df["from_id"] = (
            neighbors_df["from_code"]
            .map(code_to_idx)
        )

        neighbors_df["to_id"] = (
            neighbors_df["to_code"]
            .map(code_to_idx)
        )


                # --------------------------------------------------
        # SAME COMPANY
        # --------------------------------------------------
        
        same_company = {j: [] for j in range(n_inf)}
        
        for _, row in same_df.iterrows():
        
            j = int(row["from_id"])
            k = int(row["to_id"])
        
            same_company[j].append(k)
        
        
        # --------------------------------------------------
        # NEIGHBORS
        # --------------------------------------------------
        
        neighbors = {j: [] for j in range(n_inf)}
        
        for _, row in neighbors_df.iterrows():
        
            j = int(row["from_id"])
            k = int(row["to_id"])
            d = row["distance"]
        
            neighbors[j].append((k, d))
        
        # --------------------------------------------------
        # PHI(t)
        # --------------------------------------------------
        
        def phi_cache_array(max_s):

            s = np.arange(max_s + 1)
        
            out = TARGET_GAMMA * np.exp(-TARGET_GAMMA * s)
        
            out[s <= 0] = 0
        
            return out


        max_s = int(D_arr.max() - E_arr.min()) + 5

        phi_cache = phi_cache_array(max_s)

        phi_matrix = np.zeros((n_inf, n_days))

        for k in range(n_inf):

            for t in range(E_arr[k] + 1, D_arr[k] + 1):

                s = D_arr[k] - t

                if s >= 0:

                    phi_matrix[k, t] = phi_cache[s]

        # --------------------------------------------------
        # COMPUTE DOMINANT MECHANISM
        # --------------------------------------------------
        
        rows = []
        
        for j in range(n_inf):
        
            Ej = E_arr[j]
        
            same_sum = 0.0
            for k in same_company[j]:
            
                same_sum += beta_c * phi_matrix[k, Ej]
        
            dist_sum = 0.0
            for k, d in neighbors[j]:
        
                weight = 1.0 / (
                    1.0 +
                    L_CONST * (d / TARGET_DMAX) ** alpha
                )
            
                dist_sum += (
                    beta_d *
                    weight *
                    phi_matrix[k, Ej]
                )
        
            # -----------------------------
            # WILDLIFE
            # -----------------------------
            wildlife = beta_w
        
            total = wildlife + same_sum + dist_sum
        
            if total == 0:
        
                p_wildlife = 1.0
                p_company = 0.0
                p_distance = 0.0
        
            else:
        
                p_wildlife = wildlife / total
                p_company = same_sum / total
                p_distance = dist_sum / total
        
            # -----------------------------
            # DOMINANT MECHANISM
            # -----------------------------
        
            values = {
                "Wildlife": p_wildlife,
                "Company": p_company,
                "Distance": p_distance
            }
        
            mechanism = max(values, key=values.get)
        
            probability = values[mechanism]
        
            # -----------------------------
            # PROBABILITY CLASS
            # -----------------------------
        
            if probability > 0.5:
        
                prob_class = "High"
        
            elif probability > 0.1:
        
                prob_class = "Medium"
        
            else:
        
                prob_class = "Low"
        
            rows.append({
        
                "codice": df_inf.loc[j, "codice"],
        
                "Wildlife": p_wildlife,
        
                "Company": p_company,
        
                "Distance": p_distance,
        
                "Dominant_mechanism": mechanism,
        
                "Dominant_probability": probability,
        
                "Probability_class": prob_class
        
            })

# --------------------------------------------------
# DATAFRAME
# --------------------------------------------------
        dominant_df = pd.DataFrame(rows)

        print("\nPrime righe:")
        print(dominant_df.head())
        
        print("\nDominant mechanisms:")
        print(dominant_df["Dominant_mechanism"].value_counts())
        
        OUT_CLASS = (
            f"dominant_mechanism_classification_"
            f"gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )
        
        dominant_df.to_excel(
            OUT_CLASS,
            index=False
        )
        
        print(f"{OUT_CLASS} salvato.")

        
        # --------------------------------------------------
        # BEST INFECTOR
        # --------------------------------------------------
        
        best_df = pd.read_excel(BEST_INFECTOR_FILE)
        
        
        print("\nDistribuzione probabilità best infector")
        print(best_df["probabilità"].describe())
        
        print("\nQuantili")
        print(best_df["probabilità"].quantile([0,0.1,0.25,0.5,0.75,0.9,1]))

        merged = dominant_df.merge(
            best_df[["codice", "probabilità"]],
            on="codice"
        )
        
        
        def classify(p):
        
            if p > 0.5:
                return "High"
        
            elif p > 0.1:
                return "Medium"
        
            else:
                return "Low"
        
        
        merged["BestInfectorClass"] = (
            merged["probabilità"]
            .apply(classify)
        )
        

        # --------------------------------------------------
        # SUMMARY TABLES
        # --------------------------------------------------
        
        counts = pd.crosstab(
            merged["Dominant_mechanism"],
            merged["BestInfectorClass"]
        )
        
        counts = counts.reindex(
            index=["Wildlife", "Company", "Distance"],
            columns=["High", "Medium", "Low"],
            fill_value=0
        )
        
        counts["Total"] = counts.sum(axis=1)
        
        percentages = (
            counts[["High", "Medium", "Low"]]
            .div(counts["Total"], axis=0)
            * 100
        )
        
        OUT_SUMMARY = (
            f"dominant_mechanism_summary_"
            f"gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )
        
        with pd.ExcelWriter(OUT_SUMMARY) as writer:
        
            counts.to_excel(
                writer,
                sheet_name="Counts"
            )
        
            percentages.to_excel(
                writer,
                sheet_name="Percentages"
            )
        
        print(counts)
        print(percentages)
        
        print(f"{OUT_SUMMARY} salvato.")
        
        # --------------------------------------------------
        # PLOT
        # --------------------------------------------------
   
        
        order = ["Wildlife", "Company", "Distance"]
        
        plot_df = percentages.loc[order]
        totals = counts.loc[order, "Total"]
        
        colors = {
            "High":   "#0B5AA5",
            "Medium": "#69A9E9",
            "Low":    "#D9E8F7"
        }
        
        legend_labels = {
            "High": "> 0.5",
            "Medium": "0.1–0.5",
            "Low": "≤ 0.1"
        }
        
        fig, ax = plt.subplots(figsize=(7.5,5.5))
        
        bottom = np.zeros(len(order))
        
        # High in basso, poi Medium, poi Low
        for cls in ["High", "Medium", "Low"]:
        
            vals = plot_df[cls].values
        
            bars = ax.bar(
                np.arange(len(order)),
                vals,
                bottom=bottom,
                color=colors[cls],
                edgecolor="black",
                linewidth=1.2
            )
        
            for i, (bar, val) in enumerate(zip(bars, vals)):
        
                if val > 2:
        
                    txt_color = "white" if cls == "High" else "black"
        
                    ax.text(
                        bar.get_x() + bar.get_width()/2,
                        bottom[i] + val/2,
                        f"{val:.2f}%",
                        ha="center",
                        va="center",
                        fontsize=8.5,
                        color=txt_color,
                        fontweight="semibold"
                    )
        
            bottom += vals
        
        
        ax.set_xticks(np.arange(len(order)))
        
        ax.set_xticklabels([
            f"Wildlife\n(n={totals['Wildlife']})",
            f"Company\n(n={totals['Company']})",
            f"Distance\n(n={totals['Distance']})"
        ], fontsize=12)
        
        ax.set_ylim(0,100)
        
        ax.set_ylabel("Percentage of farms (%)", fontsize=13)
        
        ax.set_yticks(np.arange(0,101,20))
        
        # togli bordo superiore e destro
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        
        ax.tick_params(axis='both', labelsize=11)
        
        # legenda personalizzata
        handles = [
            Patch(facecolor=colors["Low"], edgecolor="black",
                  label="≤ 0.1"),
            Patch(facecolor=colors["Medium"], edgecolor="black",
                  label="0.1–0.5"),
            Patch(facecolor=colors["High"], edgecolor="black",
                  label="> 0.5"),
        ]
        
        ax.legend(
            handles=handles,
            title="Best infector\nprobability",
            frameon=True,
            loc="upper left",
            bbox_to_anchor=(1.02,1.0),
            fontsize=11,
            title_fontsize=12
        )
        
        plt.tight_layout()
        
        OUT_PLOT = (
            f"dominant_mechanism_probability_"
            f"gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.png"
        )

        plt.savefig(
            OUT_PLOT,
            dpi=600,
            bbox_inches="tight"
        )
        
        print(f"{OUT_PLOT} salvato.")
        
        plt.show()
        plt.close()