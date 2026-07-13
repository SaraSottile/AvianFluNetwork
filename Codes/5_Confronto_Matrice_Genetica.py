# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 15:42:23 2026

@author: saras
"""
import pandas as pd
import numpy as np
from scipy.stats import spearmanr, mannwhitneyu, kruskal
import matplotlib.pyplot as plt

D_FILE = "mat_diff_basi.csv"

GAMMA_VALUES = [1/10, 1/5]
DMAX_VALUES = [1.5, 2.0]

for TARGET_GAMMA in GAMMA_VALUES:

    for TARGET_DMAX in DMAX_VALUES:
        
        LOG_FILE = (
            f"genetic_distance_statistics_"
            f"gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.txt"
        )
        
        log = open(LOG_FILE, "w", encoding="utf-8")
        
        def tee_print(*args):
            text = " ".join(str(a) for a in args)
            print(text)
            log.write(text + "\n")
            
        tee_print(
            f"\n===== gamma={TARGET_GAMMA:.3f} "
            f"dmax={TARGET_DMAX} ====="
        )

        P_FILE = (
            f"matrice_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        BEST_FILE = (
            f"best_infector_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )
        
    
        P_df_full = pd.read_excel(
            P_FILE,
            index_col=0
        )
        
        D_df = pd.read_csv(
            D_FILE,
            index_col=0
        )
        
        best_df = pd.read_excel(
            BEST_FILE
        )
        
        best_df["codice"] = (
            best_df["codice"].astype(str)
        )
        
        best_df["infettore"] = (
            best_df["infettore"].astype(str)
        )

        # -----------------------------
        # FATTORIE COMUNI
        # -----------------------------
        common = list(set(P_df_full.columns) & set(D_df.columns))
        print(f"Fattorie comuni: {len(common)}")
        
        # -----------------------------
        # MATRICE SENZA WILDLIFE (per coppie)
        # -----------------------------
        P_df = P_df_full.copy()
        if "WILDLIFE" in P_df.index:
            P_df = P_df.drop(index="WILDLIFE")
        
        P_sub = P_df.loc[common, common]
        D_sub = D_df.loc[common, common]
        
        # -----------------------------
        # COSTRUZIONE COPPIE
        # -----------------------------
        pairs_P = []
        pairs_D = []
        
        for j in common:
            for k in common:
        
                if k == j:
                    continue
        
                p = P_sub.loc[k, j]
                d = D_sub.loc[k, j]
        
                if pd.notna(p) and pd.notna(d):
                    pairs_P.append(p)
                    pairs_D.append(d)
        
        pairs_P = np.array(pairs_P)
        pairs_D = np.array(pairs_D)
        
        tee_print(f"Numero coppie analizzate: {len(pairs_P)}")
        
        # -----------------------------
        # CORRELAZIONE
        # -----------------------------
        corr, pval = spearmanr(pairs_P, pairs_D)
        
        tee_print("\n=== RISULTATI ===")
        tee_print(f"Spearman correlation: {corr:.4f}")
        tee_print(f"p-value: {pval:.4e}")
        
        # -----------------------------
        # INFETTORE PIÙ PROBABILE (DA FILE)
        # -----------------------------
        distances_best = []
        
        for _, row in best_df.iterrows():
        
            j = row["codice"]
            k = row["infettore"]
        
            if j not in common:
                continue
        
            if k == "WILDLIFE":
                continue
        
            if k in D_df.index and j in D_df.columns:
                if pd.notna(D_df.loc[k, j]):
                    distances_best.append(D_df.loc[k, j])
        
        distances_best = np.array(distances_best)
        
        tee_print("\n=== INFETTORE PIÙ PROBABILE ===")
        tee_print(f"Distanza media: {np.mean(distances_best):.3f}")
        tee_print(f"Distanza mediana: {np.median(distances_best):.3f}")
        tee_print(f"N usati: {len(distances_best)}")
        
        # -----------------------------
        # CLASSI DI PROBABILITÀ
        # -----------------------------
        bins = {"high": [], "medium": [], "low": []}
        
        for p, d in zip(pairs_P, pairs_D):
        
            if p > 0.5:
                bins["high"].append(d)
            elif p > 0.1:
                bins["medium"].append(d)
            else:
                bins["low"].append(d)
        
        tee_print("\n=== ANALISI PER CLASSI ===")
        
        for key in bins:
            vals = np.array(bins[key])
            tee_print(f"{key}: n={len(vals)}, mean={vals.mean():.3f}, median={np.median(vals):.3f}")
        
        # -----------------------------
        # TEST STATISTICI
        # -----------------------------
        pairs_high = pairs_D[pairs_P > 0.5]
        pairs_low  = pairs_D[pairs_P <= 0.5]
        
        stat, p = mannwhitneyu(pairs_high, pairs_low)
        tee_print("\nTest su due gruppi")
        tee_print(p)
        
        stat, p = kruskal(
            bins["high"],
            bins["medium"],
            bins["low"]
        )
        tee_print("Test su tre gruppi")
        tee_print(p)
        
        # -----------------------------
        # BOXPLOT FINALE
        # -----------------------------
        data = [
            bins["low"],
            bins["medium"],
            bins["high"],
            distances_best
        ]
        
        labels = [
            f"Low\n(n={len(bins['low'])})",
            f"Medium\n(n={len(bins['medium'])})",
            f"High\n(n={len(bins['high'])})",
            f"Most likely\ninfector\n(n={len(distances_best)})"
        ]
        
        plt.figure(figsize=(8,6))
        
        plt.boxplot(data, labels=labels, showfliers=False)
        
        # medie sopra
        for i, vals in enumerate(data, start=1):
            if len(vals) > 0:
                plt.text(i, np.mean(vals), f"{np.mean(vals):.1f}",
                         ha='center', va='bottom')
        
        plt.ylabel("Genetic distance")
        plt.xlabel("Transmission category")
        plt.title("Genetic distance vs transmission probability and inferred infector")
        
        plt.axhline(np.median(bins["low"]), linestyle='--', alpha=0.5)
        
        plt.grid(axis="y")
        plt.tight_layout()
        
        OUT_PLOT = (
            f"genetic_distance_probability_"
            f"gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.png"
        )
        
        plt.savefig(
            OUT_PLOT,
            dpi=600,
            bbox_inches="tight"
        )
        
        tee_print(f"Figura salvata: {OUT_PLOT}")
        
        plt.show()
        plt.close()
        
        tee_print(f"\nLog salvato in: {LOG_FILE}")

        log.close()