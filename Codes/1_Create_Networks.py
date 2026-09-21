# -*- coding: utf-8 -*-
"""
Created on Tue Jul  7 16:00:08 2026

Costruzione dei network

Produce:
- same_company.xlsx
- neighbors_dmaxX.xlsx

@author: saras
"""

# -*- coding: utf-8 -*-
"""

"""

import pandas as pd
import numpy as np

# -----------------------------
# INPUT
# -----------------------------
FATTORIE_FILE = "fattorie.xlsx"

DMAX_VALUES = [1.5, 2.0]

# -----------------------------
# LETTURA
# -----------------------------
df = pd.read_excel(FATTORIE_FILE)

n_farms = len(df)

farm_codes = df["codice"].values
company_vals = df["azienda"].values

# -----------------------------
# MATRICE DISTANZE
# -----------------------------
lat = np.radians(df["latitudine"].values)
lon = np.radians(df["longitudine"].values)

dlat = lat[:, None] - lat[None, :]
dlon = lon[:, None] - lon[None, :]

x = dlon * np.cos((lat[:, None] + lat[None, :]) / 2)
y = dlat

dist_matrix = 6371 * np.sqrt(x**2 + y**2)

# -----------------------------
# SAME COMPANY
# -----------------------------
groups = {}

for i, c in enumerate(company_vals):
    groups.setdefault(c, []).append(i)

rows = []

for j in range(n_farms):

    for k in groups[company_vals[j]]:

        if k != j:

            rows.append({
                "from_id": j,
                "to_id": k,
                "from_code": farm_codes[j],
                "to_code": farm_codes[k]
            })

same_df = pd.DataFrame(rows)

same_df.to_excel("same_company.xlsx", index=False)

print("Salvato same_company.xlsx")

# -----------------------------
# NEIGHBORS
# -----------------------------
for D_MAX in DMAX_VALUES:

    rows = []

    for j in range(n_farms):

        idxs = np.where(
            (dist_matrix[j] <= D_MAX) &
            (dist_matrix[j] > 0)
        )[0]

        for k in idxs:

            rows.append({
                "from_id": j,
                "to_id": k,
                "from_code": farm_codes[j],
                "to_code": farm_codes[k],
                "distance": dist_matrix[j, k]
            })

    neigh_df = pd.DataFrame(rows)

    outfile = f"neighbors_dmax{D_MAX}.xlsx"

    neigh_df.to_excel(outfile, index=False)

    print(f"Salvato {outfile}")