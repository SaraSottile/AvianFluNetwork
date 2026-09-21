# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 17:20:31 2026

@author: saras
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

GAMMA_VALUES = [1/10, 1/5]
DMAX_VALUES = [1.5, 2.0]

for TARGET_GAMMA in GAMMA_VALUES:

    for TARGET_DMAX in DMAX_VALUES:
        
        LOG_FILE = (
            f"gap_statistics_"
            f"gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.txt"
        )
        
        log = open(
            LOG_FILE,
            "w",
            encoding="utf-8"
        )
        
        def tee_print(*args):
            text = " ".join(str(a) for a in args)
            print(text)
            log.write(text + "\n")

        print(
            f"\n===== gamma={TARGET_GAMMA:.3f} "
            f"dmax={TARGET_DMAX} ====="
        )

        P_FILE = (
            f"matrice_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        P_df = pd.read_excel(
            P_FILE,
            index_col=0
        )
        
        
        results = []
      
        for j in P_df.columns:
      
            probs = (
                P_df[j]
                .dropna()
                .sort_values(ascending=False)
            )
      
            probs = probs.drop(
                "WILDLIFE",
                errors="ignore"
            )
      
            if len(probs) < 2:
                continue
      
            P1 = probs.iloc[0]
            P2 = probs.iloc[1]
      
            gap = P1 - P2
      
            ratio = (
                P1 / P2
                if P2 > 0
                else np.nan
            )
      
            results.append({
      
                "codice": j,
      
                "P1": P1,
      
                "P2": P2,
      
                "gap": gap,
      
                "ratio": ratio
      
            })
      
        df_gap = pd.DataFrame(results)

        tee_print("\n=== CERTEZZA INFETTORE ===")

        tee_print(
            f"Gap medio: {df_gap['gap'].mean():.3f}"
        )

        tee_print(
            f"Gap mediano: {df_gap['gap'].median():.3f}"
        )

        tee_print("\nPercentuali:")

        tee_print(
            f"P1 > 0.5: {(df_gap['P1'] > 0.5).mean():.3f}"
        )

        tee_print(
            f"Gap > 0.2: {(df_gap['gap'] > 0.2).mean():.3f}"
        )

        tee_print(
            f"Ratio > 2: {(df_gap['ratio'] > 2).mean():.3f}"
        )
    
        plt.figure(figsize=(7,5))

        plt.hist(
            df_gap["gap"],
            bins=30
        )
        
        plt.xlabel("P1 - P2")
        plt.ylabel("Frequency")
        plt.title("Uncertainty in infector attribution")
        
        OUT_PLOT = (
            f"gap_distribution_"
            f"gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.png"
        )
        
        plt.tight_layout()
        
        plt.savefig(
            OUT_PLOT,
            dpi=600
        )
        
        tee_print(
            f"\nFigura salvata: {OUT_PLOT}"
        )
        
        plt.show()
        plt.close()
        
        tee_print(
            f"Log salvato in: {LOG_FILE}"
        )

        log.close()

print("\nTUTTO COMPLETATO")