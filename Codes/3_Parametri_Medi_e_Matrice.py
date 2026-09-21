# -*- coding: utf-8 -*-
"""
Calcolo della matrice delle probabilità di trasmissione
a partire dai parametri medi del modello.
"""

import pandas as pd
import numpy as np
import glob

# -------------------------------------------------------
# INPUT
# -------------------------------------------------------

RESULTS_FILE = "risultati_completi.xlsx"
FATTORIE_FILE = "fattorie.xlsx"

L_CONST = 1e3

GAMMA_VALUES = [0, 1/5, 1/10]
DMAX_VALUES = [1.5, 2.0]


# -------------------------------------------------------
# LOOP PRINCIPALE
# -------------------------------------------------------

for TARGET_GAMMA in GAMMA_VALUES:

    for TARGET_DMAX in DMAX_VALUES:


        # -------------------------------------------------------
        # LOG
        # -------------------------------------------------------

        log_name = (
            f"log_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.txt"
        )

        log = open(log_name, "w", encoding="utf-8")

        def tee_print(*args):
            text = " ".join(str(a) for a in args)
            print(text)
            log.write(text + "\n")

        tee_print("=" * 60)
        tee_print(f"gamma = {TARGET_GAMMA}")
        tee_print(f"d_max = {TARGET_DMAX}")
        tee_print("=" * 60)


        # -------------------------------------------------------
        # LETTURA RISULTATI MODELLO
        # -------------------------------------------------------

        df_res = pd.read_excel(RESULTS_FILE)

        subset = df_res[
            (df_res["gamma"] == TARGET_GAMMA)
            &
            (df_res["d_max"] == TARGET_DMAX)
        ]

        if subset.empty:

            tee_print("Nessun risultato trovato.")
            log.close()
            continue


        # -------------------------------------------------------
        # PARAMETRI MEDI
        # -------------------------------------------------------

        params_mean = subset[
            ["beta_w", "beta_c", "beta_d", "alpha"]
        ].mean()

        params_median = subset[
            ["beta_w", "beta_c", "beta_d", "alpha"]
        ].median()

        params_std = subset[
            ["beta_w", "beta_c", "beta_d", "alpha"]
        ].std()

        beta_w = params_median["beta_w"]
        beta_c = params_median["beta_c"]
        beta_d = params_median["beta_d"]
        alpha = params_median["alpha"]

        tee_print("\nParametri mediana")
        tee_print(params_median)

        tee_print("\nParametri medi")
        tee_print(params_mean)

        tee_print("\nDeviazioni standard")
        tee_print(params_std)


        # -------------------------------------------------------
        # FILE DELLE E STIMATE
        # -------------------------------------------------------

        pattern = (
            f"E_results_seed*_"
            f"gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        files = sorted(glob.glob(pattern))

        if len(files) == 0:

            tee_print("Nessun file E trovato.")
            log.close()
            continue
        
        # -------------------------------------------------------
        # LETTURA DELLE E STIMATE
        # -------------------------------------------------------
    
        dfs = []
        
        for f in files:
        
            temp = pd.read_excel(f)[["codice", "E"]]
        
            temp["E"] = pd.to_datetime(
                temp["E"],
                errors="coerce"
            )
        
            # ricavo il seed dal nome del file
            seed = (
                f.split("seed")[1]
                 .split("_")[0]
            )
        
            temp = temp.rename(
                columns={"E": f"E_{seed}"}
            )
        
            dfs.append(temp)
        
    
    # -------------------------------------------------------
    # UNISCO TUTTI I FILE
    # -------------------------------------------------------
    
        df_E = dfs[0]
        
        for d in dfs[1:]:
        
            df_E = df_E.merge(
                d,
                on="codice",
                how="outer"
            )
        
        
    # -------------------------------------------------------
    # MEDIANA DELLE E
    # -------------------------------------------------------
    
        E_cols = [
            c
            for c in df_E.columns
            if c.startswith("E_")
        ]
        
        
        df_E["E"] = df_E[E_cols].apply(
        
            lambda row:
        
            pd.to_datetime(
        
                np.median(
        
                    [
                        x.value
                        for x in row
                        if pd.notna(x)
                    ]
        
                )
        
            )
        
            if row.notna().any()
        
            else pd.NaT,
        
            axis=1
        
        )
        
    
    # -------------------------------------------------------
    # DATASET ORIGINALE
    # -------------------------------------------------------
        
        df = pd.read_excel(FATTORIE_FILE)
        
        df["conferma"] = pd.to_datetime(
            df["conferma"],
            dayfirst=True,
            errors="coerce"
        )
        
        
        # aggiungo le E stimate
        df = df.merge(
            df_E[["codice", "E"]],
            on="codice",
            how="left"
        )
        
        
        # -------------------------------------------------------
        # SOLO FATTORIE INFETTE
        # -------------------------------------------------------
        
        df_inf = (
        
            df[
                (df["E"].notna())
                &
                (df["conferma"].notna())
            ]
        
            .copy()
        
            .reset_index(drop=True)
        
        )
        
        df_inf["D"] = df_inf["conferma"]
        
        n_inf = len(df_inf)
        
        
        tee_print(
            f"\nFattorie infette: {n_inf}"
        )
        
        if n_inf == 0:
        
            tee_print(
                "Nessuna fattoria infetta."
            )
        
            log.close()
        
            continue
        
        
        # -------------------------------------------------------
        # DELTA = D-E
        # -------------------------------------------------------
        
        df_inf["delta"] = (
            df_inf["D"] -
            df_inf["E"]
        ).dt.days
        
        
        tee_print("\nStatistiche delta")
        
        tee_print(
            f"Media: {df_inf['delta'].mean():.3f}"
        )
        
        tee_print(
            f"Mediana: {df_inf['delta'].median():.3f}"
        )
        
        tee_print(
            f"SD: {df_inf['delta'].std():.3f}"
            )
        
        tee_print(
            f"Min: {df_inf['delta'].min()}"
        )
        
        tee_print(
            f"Max: {df_inf['delta'].max()}"
        )
        
            # -------------------------------------------------------
        # TIMELINE
        # -------------------------------------------------------

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


        # -------------------------------------------------------
        # CODICI → INDICI LOCALI
        # -------------------------------------------------------

        codes = df_inf["codice"].tolist()

        code_to_idx = {
            code: idx
            for idx, code in enumerate(codes)
        }


        # -------------------------------------------------------
        # NETWORK SAME COMPANY
        # -------------------------------------------------------

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


        # -------------------------------------------------------
        # NETWORK DISTANCE
        # -------------------------------------------------------

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


        tee_print(
            f"\nArchi same company: {len(same_df)}"
        )

        tee_print(
            f"Archi neighborhood: {len(neighbors_df)}"
        )
        
        
            # -------------------------------------------------------
        # PHI MATRIX
        # -------------------------------------------------------

        def phi_cache_array(max_s, gamma):
            s = np.arange(max_s + 1)

            if gamma == 0:
                out = np.ones(max_s + 1)
            else:
                out = gamma * np.exp(-gamma * s)

            out[s <= 0] = 0.0
            return out



        max_s = int(D_arr.max() - E_arr.min()) + 5

        phi_cache = phi_cache_array(max_s, TARGET_GAMMA)

        phi_matrix = np.zeros((n_inf, n_days))


        for k in range(n_inf):

            for t in range(E_arr[k] + 1, D_arr[k] + 1):

                s = D_arr[k] - t

                if s >= 0:

                    phi_matrix[k, t] = phi_cache[s]
                
                
            # -------------------------------------------------------
        # LOOKUP DEI NETWORK
        # -------------------------------------------------------

        # same company
        same_lookup = set()

        for _, row in same_df.iterrows():

            same_lookup.add(
                (
                    int(row["from_id"]),
                    int(row["to_id"])
                )
            )

        # neighborhood
        dist_lookup = {}

        for _, row in neighbors_df.iterrows():

            dist_lookup[
                (
                    int(row["from_id"]),
                    int(row["to_id"])
                )
            ] = row["distance"]
            
            
            # -------------------------------------------------------
        # MATRICE DELLE PROBABILITÀ
        # -------------------------------------------------------

        P = np.zeros((n_inf + 1, n_inf))

        wildlife_vals = []
        same_vals = []
        dist_vals = []

        for j in range(n_inf):

            Ej = E_arr[j]

            same_sum = 0.0
            dist_sum = 0.0

            contrib = []

            for k in range(n_inf):

                if k == j:
                    continue

                # -------------------------
                # SAME COMPANY
                # -------------------------

                val_same = 0.0

                if (j, k) in same_lookup:

                    val_same = (
                        beta_c *
                        phi_matrix[k, Ej]
                    )

                # -------------------------
                # DISTANCE
                # -------------------------

                val_dist = 0.0

                if (j, k) in dist_lookup:

                    d = dist_lookup[(j, k)]

                    weight = 1.0 / (
                        1.0 +
                        L_CONST *
                        (d / TARGET_DMAX) ** alpha
                    )

                    val_dist = (
                        beta_d *
                        weight *
                        phi_matrix[k, Ej]
                    )

                value = val_same + val_dist

                same_sum += val_same
                dist_sum += val_dist

                contrib.append((k, value))

            wildlife = beta_w

            total = wildlife + same_sum + dist_sum

            if total > 0:

                wildlife_vals.append(
                    wildlife / total
                )

                same_vals.append(
                    same_sum / total
                )

                dist_vals.append(
                    dist_sum / total
                )

                P[n_inf, j] = wildlife / total

                for k, value in contrib:

                    P[k, j] = value / total

            else:

                P[n_inf, j] = 1.0

        np.fill_diagonal(P[:n_inf, :], np.nan)
        
        
            # -------------------------------------------------------
        # SALVA MATRICE
        # -------------------------------------------------------

        codes_inf = list(df_inf["codice"])
        codes_inf.append("WILDLIFE")

        P_df = pd.DataFrame(
            P,
            index=codes_inf,
            columns=df_inf["codice"]
        )

        outfile = (
            f"matrice_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        P_df.to_excel(outfile)

        tee_print(f"\nMatrice salvata: {outfile}")
        
        
            # -------------------------------------------------------
        # SALVA DATE
        # -------------------------------------------------------

        out_dates = df_inf[
            ["codice", "E", "D", "delta"]
        ]

        out_dates_file = (
            f"date_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        out_dates.to_excel(
            out_dates_file,
            index=False
        )

        tee_print(
            f"Date salvate in: {out_dates_file}"
        )
        
            # -------------------------------------------------------
        # ANALISI COMPONENTI
        # -------------------------------------------------------

        tee_print("\n=== ANALISI COMPONENTI ===")

        tee_print("\nWILDLIFE")
        tee_print(f"Media: {np.mean(wildlife_vals):.4f}")
        tee_print(f"Mediana: {np.median(wildlife_vals):.4f}")
        tee_print(f">50%: {(np.array(wildlife_vals) > 0.5).sum()}")

        tee_print("\nSAME COMPANY")
        tee_print(f"Media: {np.mean(same_vals):.4f}")
        tee_print(f"Mediana: {np.median(same_vals):.4f}")
        tee_print(f">50%: {(np.array(same_vals) > 0.5).sum()}")

        tee_print("\nDISTANCE")
        tee_print(f"Media: {np.mean(dist_vals):.4f}")
        tee_print(f"Mediana: {np.median(dist_vals):.4f}")
        tee_print(f">50%: {(np.array(dist_vals) > 0.5).sum()}")

        tee_print(f"\nLog salvato in: {log_name}")
       

        best_infector = P_df.idxmax()
        best_prob = P_df.max()

        df_best = pd.DataFrame({
            "codice": best_infector.index,
            "infettore": best_infector.values,
            "probabilità": best_prob.values
        })

        OUT_FILE = (
            f"best_infector_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        df_best.to_excel(OUT_FILE, index=False)

        tee_print(f"Best infector salvato: {OUT_FILE}")

        log.close()
        
print("\n✅ TUTTO COMPLETATO")

