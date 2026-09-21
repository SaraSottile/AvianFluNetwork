# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 15:41:18 2026

@author: saras
"""

import pandas as pd
import numpy as np
from scipy.optimize import minimize
from scipy.sparse import csr_matrix
import time

# -----------------------------
# FILE INPUT
# -----------------------------
FATTORIE_FILE = "fattorie.xlsx"

# -----------------------------
# PARAMETRI GLOBALI
# -----------------------------

MAX_ITER = 500
RANGE_DAYS = 15
DAYS_INFECTIOUS = 2

SEEDS = list(range(100, 200))

GAMMA_VALUES = [0, 1/5, 1/10]   
DMAX_VALUES = [1.5, 2.0]

L_CONST = 1e3

# -----------------------------
# LOAD
# -----------------------------
df_base = pd.read_excel(FATTORIE_FILE)

df_base["D"] = pd.to_datetime(
    df_base["conferma"],
    format="%d/%m/%Y",
    errors="coerce"
)

farm_codes = df_base["codice"].values
n_farms = len(df_base)

# -----------------------------
# HELPER
# -----------------------------
def phi_cache_array(max_s, gamma):
    s = np.arange(max_s + 1)

    if gamma == 0:
        out = np.ones(max_s + 1)
    else:
        out = gamma * np.exp(-gamma * s)

    out[s <= 0] = 0.0
    return out

# -----------------------------
# MODELLO
# -----------------------------
def run_model(SEED, D_MAX, GAMMA):

    rng = np.random.default_rng(SEED)
    
    x0 = [
    rng.uniform(1e-4, 1e-2),
    rng.uniform(1e-4, 1e-2),
    rng.uniform(1e-4, 1e-2),
    rng.uniform(0.3,  2.0),
    ]
    
    log_name = f"output_log_seed{SEED}_gamma{GAMMA:.3f}_dmax{D_MAX}.txt"
    log = open(log_name, "w", encoding="utf-8")

    def tee_print(*args):
        text = " ".join(str(a) for a in args)
        print(text)
        log.write(text + "\n")

    start_time = time.time()

    tee_print(f"SEED={SEED}, gamma={GAMMA}, L={L_CONST}, D_MAX={D_MAX}")
    tee_print("x0 iniziale:", x0)
    # COPIE LOCALI
    df = df_base.copy()
    
    # -----------------------------
    # LETTURA NETWORK
    # -----------------------------
    same_df = pd.read_excel("same_company.xlsx")

    neighbors_df = pd.read_excel(
        f"neighbors_dmax{D_MAX}.xlsx"
    )

    same_company = (
        same_df
        .groupby("from_id")["to_id"]
        .apply(list)
        .to_dict()
    )

    for j in range(n_farms):
        same_company.setdefault(j, [])

    neighbors = (
        neighbors_df
        .groupby("from_id")[["to_id", "distance"]]
        .apply(lambda x: list(zip(x["to_id"], x["distance"])))
        .to_dict()
    )

    for j in range(n_farms):
        neighbors.setdefault(j, [])

    rows = same_df["from_id"].to_numpy()
    cols = same_df["to_id"].to_numpy()

    A_same = csr_matrix(
        (np.ones(len(rows)), (rows, cols)),
        shape=(n_farms, n_farms)
    )
   
    # -----------------------------
    # FATTORIE NELL'INTERSEZIONE
    # -----------------------------
    farms_overlap = []
    
    for j in range(n_farms):
        neigh_idx = {k for k, _ in neighbors[j]}
        if len(neigh_idx.intersection(same_company[j])) > 0:
            farms_overlap.append(j)
    
    tee_print(f"Numero di fattorie nell'intersezione: {len(farms_overlap)}")

    infected_arr = df["D"].notna().values
    
    # -----------------------------
    # FATTORIE INFETTE NELL'INTERSEZIONE
    # -----------------------------
    infected_overlap = [j for j in farms_overlap if infected_arr[j]]
    
    tee_print(f"Di queste, infette: {len(infected_overlap)}")
    
  

    # -----------------------------
    # TIME WINDOW
    # -----------------------------
    t_start = (df.loc[infected_arr, "D"] - pd.to_timedelta(RANGE_DAYS, unit="d")).min()
    t_end = df.loc[infected_arr, "D"].max()

    n_days = (t_end - t_start).days + 1
    t_grid = np.arange(n_days)

    # -----------------------------
    # TIMELINE
    # -----------------------------
    df["D_days"] = np.where(
        infected_arr,
        (df["D"] - t_start).dt.days.astype("Int64"),
        n_days - 1
    ).astype(int)

    df["E_days"] = 0
    df.loc[infected_arr, "E_days"] = ((df.loc[infected_arr, "D"] - pd.to_timedelta(RANGE_DAYS, unit="d") - t_start).dt.days.astype(int))

        
    # -----------------------------
    # PHI
    # -----------------------------
    E_arr = df["E_days"].values
    D_arr = df["D_days"].values

    max_s = int(D_arr[infected_arr].max() - E_arr[infected_arr].min()) + 5
    phi_cache = phi_cache_array(max_s, GAMMA)

    mask = (
        infected_arr[:, None]
        & (t_grid[None, :] > E_arr[:, None])
        & (t_grid[None, :] <= D_arr[:, None])
    )

    s_matrix = (D_arr[:, None] - t_grid[None, :]).astype(int)
    s_matrix = np.clip(s_matrix, 0, max_s)

    phi_matrix = np.zeros((n_farms, n_days))
    phi_matrix[mask] = phi_cache[s_matrix[mask]]

    dr = neighbors_df["from_id"].to_numpy()
    dc = neighbors_df["to_id"].to_numpy()
    dd = neighbors_df["distance"].to_numpy()

    # -----------------------------
    # LAMBDA
    # -----------------------------
    def compute_lambda(params):

        beta_w, beta_c, beta_d, alpha = params

        lambda_w = np.full((n_farms, n_days), beta_w)

        sum_N = A_same.dot(phi_matrix)

        lambda_c = beta_c * sum_N

        if len(dd) > 0:
            denom = 1 + L_CONST * (dd / D_MAX) ** alpha
            W = csr_matrix((1/denom, (dr, dc)), shape=(n_farms, n_farms))
            lambda_d = beta_d * W.dot(phi_matrix)
        else:
            lambda_d = 0

        return lambda_w + lambda_c + lambda_d

    # -----------------------------
    # LIKELIHOOD
    # -----------------------------
    def neg_logL(params):

        lam = compute_lambda(params)
        logL = 0

        for j in range(n_farms):

            if infected_arr[j]:
                Ej = int(df.loc[j, "E_days"])
                lamE = lam[j, Ej]

                Pj = max(1 - np.exp(-lamE), 1e-300)
                logL += np.log(Pj) - lam[j, :Ej].sum()

            else:
                logL -= lam[j].sum()

        return -logL

    bounds = [
        (1e-16, None),
        (1e-16, None),
        (1e-16, None),
        (1e-6, None),
    ]

    for _ in range(MAX_ITER):
        res = minimize(neg_logL, x0, method="L-BFGS-B", bounds=bounds)
        x0 = res.x
        
        # E-step
        lambda_matrix = compute_lambda(x0)

        for j in range(n_farms):

            if not infected_arr[j]:
                continue

            D_j = int(df.loc[j, "D_days"])

            # Limiti dell'intervallo E_j
            L = D_j - (RANGE_DAYS + 5)  # limite inferiore
            U = D_j - DAYS_INFECTIOUS    # limite superiore
            start_t = max(0, L)
            end_t = min(D_j, U)
    
            lam_row = lambda_matrix[j, 0:(D_j + 1)]
            cumsum = np.concatenate(([0.0], np.cumsum(lam_row)))
    
            best_prob = -1.0
            best_t = int(df.loc[j, "E_days"])

            for t in range(start_t, end_t + 1):

                Pj = 1 - np.exp(-lambda_matrix[j, t])
                Qj = np.exp(-cumsum[t])
                prob = Pj * Qj

                if prob > best_prob:
                    best_prob = prob
                    best_t = t

            df.at[j, "E_days"] = best_t

    # -----------------------------
    # OUTPUT
    # -----------------------------
    result = {
        "seed": SEED,
        "L": L_CONST,
        "gamma": GAMMA,
        "d_max": D_MAX,
        "beta_w": x0[0],
        "beta_c": x0[1],
        "beta_d": x0[2],
        "alpha": x0[3],
    }

    tee_print("RISULTATO:", result)
    tee_print("Tempo:", time.time() - start_time)

        # -----------------------------
    # CALCOLO LAMBDA FINALE 
    # -----------------------------
    lambda_matrix = compute_lambda(x0)

    # separo componenti (come nel tuo codice originale)
    beta_w, beta_c, beta_d, alpha = x0

    lambda_w_mat = np.full((n_farms, n_days), beta_w)

    sum_N = A_same.dot(phi_matrix)

    lambda_c_mat = beta_c * sum_N

    if len(dd) > 0:
        denom = 1 + L_CONST * (dd / D_MAX) ** alpha
        W = csr_matrix((1/denom, (dr, dc)), shape=(n_farms, n_farms))
        lambda_d_mat = beta_d * W.dot(phi_matrix)
    else:
        lambda_d_mat = np.zeros_like(lambda_w_mat)

    # -----------------------------
    # COSTRUZIONE DATE E delta_E
    # -----------------------------
    df["E"] = pd.NaT
    df.loc[infected_arr, "E"] = t_start + pd.to_timedelta(df.loc[infected_arr, "E_days"], unit="d")

    df["E_iniziale"] = pd.NaT
    df.loc[infected_arr, "E_iniziale"] = df.loc[infected_arr, "D"] - pd.to_timedelta(RANGE_DAYS, unit="d")

    df["delta_E"] = pd.NA
    df.loc[infected_arr, "delta_E"] = (
        df.loc[infected_arr, "E"] - df.loc[infected_arr, "E_iniziale"]
    ).dt.days

    # -----------------------------
    # STATISTICHE delta_E
    # -----------------------------
    delta = df.loc[infected_arr, "delta_E"].astype(float).values

    delta_min = float(np.min(delta)) if delta.size else np.nan
    delta_max = float(np.max(delta)) if delta.size else np.nan
    delta_mean = float(np.mean(delta)) if delta.size else np.nan
    delta_median = float(np.median(delta)) if delta.size else np.nan

    tee_print("\n--- STATISTICHE DELTA_E ---")
    tee_print(f"Min: {delta_min}")
    tee_print(f"Max: {delta_max}")
    tee_print(f"Mean: {delta_mean:.3f}" if np.isfinite(delta_mean) else "Mean: NaN")
    tee_print(f"Median: {delta_median}")

    # -----------------------------
    # INFLUENZA COMPONENTI
    # -----------------------------
    mean_w = float(lambda_w_mat.mean())
    mean_c = float(lambda_c_mat.mean())
    mean_d = float(lambda_d_mat.mean())

    tee_print("\n--- INFLUENZA COMPONENTI ---")
    tee_print(f"λ_w: {mean_w:.6f}")
    tee_print(f"λ_c: {mean_c:.6f}")
    tee_print(f"λ_d: {mean_d:.6f}")

    dominante = max(
        {"λ_w": mean_w, "λ_c": mean_c, "λ_d": mean_d},
        key=lambda k: {"λ_w": mean_w, "λ_c": mean_c, "λ_d": mean_d}[k]
    )

    tee_print(f"Dominante: {dominante}")

    # -----------------------------
    # SALVATAGGIO EXCEL
    # -----------------------------
    outfile = f"E_results_seed{SEED}_gamma{GAMMA:.3f}_dmax{D_MAX}.xlsx"

    df[["codice", "E_iniziale", "E", "delta_E"]].to_excel(outfile, index=False)

    tee_print(f"File salvato: {outfile}")

    log.close()

    return result

results = []

total = len(SEEDS) * len(GAMMA_VALUES) * len(DMAX_VALUES)
count = 0

for seed in SEEDS:
    for gamma in GAMMA_VALUES:
        for dmax in DMAX_VALUES:

            count += 1
            print(f"\n=== RUN {count}/{total} ===")

            try:
                res = run_model(seed, dmax, gamma)
                results.append(res)
            except Exception as e:
                print("Errore:", e)

# -----------------------------
# SALVATAGGIO
# -----------------------------
df_res = pd.DataFrame(results)
df_res.to_excel("risultati_completi.xlsx", index=False)