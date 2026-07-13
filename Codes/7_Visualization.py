# -*- coding: utf-8 -*-

import os
import imageio.v2 as imageio
import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from shapely.geometry import LineString
from tqdm import tqdm

TARGET_GAMMA = 0.100

DMAX_VALUES = [1.5, 2.0]

FARMS_FILE = "fattorie.xlsx"
CULLING_FILE = "date_culling.csv"

for TARGET_DMAX in DMAX_VALUES:

    print(
        f"\n===== gamma={TARGET_GAMMA:.3f} "
        f"dmax={TARGET_DMAX} ====="
    )

    DATES_FILE = (
        f"date_gamma{TARGET_GAMMA:.3f}_"
        f"dmax{TARGET_DMAX}.xlsx"
    )

    BEST_FILE = (
        f"best_infector_gamma{TARGET_GAMMA:.3f}_"
        f"dmax{TARGET_DMAX}.xlsx"
    )

    NEIGHBORS_FILE = (
        f"neighbors_dmax{TARGET_DMAX}.xlsx"
    )

    FRAME_DIR = (
        f"frames_dmax{TARGET_DMAX}"
    )

    VIDEO_NAME = (
        f"epidemic_map_gamma{TARGET_GAMMA:.3f}_"
        f"dmax{TARGET_DMAX}.mp4"
    )
    
    df = pd.read_excel(FARMS_FILE)
    
    # coordinate
    for col in ["latitudine", "longitudine"]:

        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", ".")
            .astype(float)
        )
        
    dates_df = pd.read_excel(DATES_FILE)
    
    best_df = pd.read_excel(BEST_FILE)
    
    same_df = pd.read_excel("same_company.xlsx")
    
    neighbors_df = pd.read_excel(NEIGHBORS_FILE)
    
    culling_df = pd.read_csv(
        CULLING_FILE,
        sep=";"
    )
    
    dates_df["E"] = pd.to_datetime(dates_df["E"])

    dates_df["D"] = pd.to_datetime(dates_df["D"])
    
    culling_df["estinzione"] = pd.to_datetime(
        culling_df["estinzione"],
        dayfirst=True
    )
    
    for x in [df, dates_df, best_df, culling_df]:

        x["codice"] = x["codice"].astype(str)
        
    best_df["infettore"] = (
        best_df["infettore"]
        .astype(str)
    )
    
    # ---------------------------------------------------
    # MERGE
    # ---------------------------------------------------
    
    df = df.merge(
        dates_df[["codice", "E", "D"]],
        on="codice",
        how="left"
    )
    
    df = df.merge(
        culling_df[["codice", "estinzione"]],
        on="codice",
        how="left"
    )
    
    df = (
        df[
            df["codice"].notna() &
            (df["codice"].str.strip() != "")
        ]
        .reset_index(drop=True)
    )
    
    # ---------------------------------------------------
    # GEODATAFRAME
    # ---------------------------------------------------
    
    geometry = gpd.points_from_xy(
        df["longitudine"],
        df["latitudine"]
    )
    
    gdf = gpd.GeoDataFrame(
        df,
        geometry=geometry,
        crs="EPSG:4326"
    )
    gdf_merc = gdf.to_crs(3857)
    
    
    # ---------------------------------------------------
    # LOOKUP NETWORK
    # ---------------------------------------------------
    
    same_lookup = set(
        zip(
            same_df["from_code"].astype(str),
            same_df["to_code"].astype(str)
        )
    )
    
    distance_lookup = set(
        zip(
            neighbors_df["from_code"].astype(str),
            neighbors_df["to_code"].astype(str)
        )
    )
    
        # ---------------------------------------------------
    # CODICI
    # ---------------------------------------------------
    
    code_to_idx = {
        code: idx
        for idx, code in enumerate(df["codice"])
    }
    
    # ---------------------------------------------------
    # COSTRUZIONE LINK BEST INFECTOR
    # ---------------------------------------------------
    
    best_edges = []
    
    edge_info = {}
    
    for _, row in best_df.iterrows():
    
        target_code = row["codice"]
        source_code = row["infettore"]
    
        if (
            pd.isna(source_code)
            or source_code.lower() == "wildlife"
        ):
            continue
    
        if (
            target_code not in code_to_idx
            or source_code not in code_to_idx
        ):
            continue
    
        source_idx = code_to_idx[source_code]
        target_idx = code_to_idx[target_code]
    
        if (source_code, target_code) in same_lookup:
    
            edge_type = "company"
    
        elif (source_code, target_code) in distance_lookup:
    
            edge_type = "distance"
    
        else:
    
            edge_type = "other"
    
        line = LineString([
            gdf_merc.geometry.iloc[source_idx],
            gdf_merc.geometry.iloc[target_idx]
        ])
    
        best_edges.append(line)
    
        edge_info[line.wkt] = {
            "source": source_idx,
            "target": target_idx,
            "type": edge_type
        }
        
            # ---------------------------------------------------
    # RANGE TEMPORALE
    # ---------------------------------------------------
    
    min_date = df["E"].min().date()
    
    max_date = max(
        df["D"].max(),
        df["estinzione"].max()
    ).date()
    
    # ---------------------------------------------------
    # NUOVI ESPOSTI
    # ---------------------------------------------------
    
    new_exposed = (
        df
        .groupby(df["E"].dt.date)
        .apply(lambda x: x.index.tolist())
        .to_dict()
    )
    
    # ---------------------------------------------------
    # OUTPUT
    # ---------------------------------------------------
    
    os.makedirs(
        FRAME_DIR,
        exist_ok=True
    )
    
    # ---------------------------------------------------
    # LOOP TEMPORALE
    # ---------------------------------------------------
    
    for frame_idx, current_date in enumerate(
    
        tqdm(
            pd.date_range(min_date, max_date),
            desc="Generazione frame"
        )
    
    ):
    
        current_ts = pd.Timestamp(current_date)
    
        nuovi_esposti = new_exposed.get(
            current_date.date(),
            []
        )
        
    # ---------------------------------------------------
    # COLORI NODI
    # ---------------------------------------------------
    
        colors = []
        sizes = []
        
        for idx, row in df.iterrows():
        
            E = row["E"]
            D = row["D"]
            R = row["estinzione"]
        
            # nuovo esposto
            if idx in nuovi_esposti:
        
                colors.append("red")
                sizes.append(40)
        
            # culling
            elif pd.notna(R) and current_ts >= R:
        
                colors.append("black")
                sizes.append(8)
        
            # rilevato
            elif pd.notna(D) and current_ts >= D:
        
                colors.append("green")
                sizes.append(8)
        
            # esposto
            elif pd.notna(E) and current_ts >= E:
        
                colors.append("red")
                sizes.append(8)
        
            # suscettibile
            else:
        
                colors.append("skyblue")
                sizes.append(6)
                
            # ---------------------------------------------------
        # FIGURA
        # ---------------------------------------------------
        
        fig, ax = plt.subplots(figsize=(16,9))
        
        gdf_merc.plot(
        ax=ax,
        color=colors,
        markersize=sizes,
        zorder=6
        )
    
        cx.add_basemap(
            ax,
        crs=gdf_merc.crs,
        source=cx.providers.OpenStreetMap.Mapnik
        )
        
        # ---------------------------------------------------
        # LINK BEST INFECTOR
        # ---------------------------------------------------
        
        for geom in best_edges:
        
            info = edge_info[geom.wkt]
        
            source_idx = info["source"]
            target_idx = info["target"]
            edge_type = info["type"]
        
            # mostra solo i nuovi esposti
            if target_idx not in nuovi_esposti:
                continue
        
            source_row = df.loc[source_idx]
        
            # il source deve essere infettivo
            if not (
                pd.notna(source_row["E"])
                and pd.notna(source_row["D"])
                and source_row["E"] <= current_ts < source_row["D"]
            ):
                continue
        
            if edge_type == "company":
        
                edge_color = "orange"
        
            elif edge_type == "distance":
        
                edge_color = "purple"
        
            else:
        
                edge_color = "gray"
        
            gpd.GeoSeries(
                [geom],
                crs=gdf_merc.crs
            ).plot(
                ax=ax,
                color=edge_color,
                linewidth=2.5,
                alpha=0.9,
                zorder=7
            )
                
                
                # ---------------------------------------------------
        # TITOLO
        # ---------------------------------------------------
        
        ax.set_title(
            current_date.strftime("%d/%m/%Y"),
            fontsize=18
        )
        
        ax.axis("off")
        
        # ---------------------------------------------------
        # SAVE FRAME
        # ---------------------------------------------------
        
        plt.savefig(
            os.path.join(
                FRAME_DIR,
                f"frame_{frame_idx+1:04d}.png"
            ),
            dpi=150,
            bbox_inches="tight"
        )
        
        plt.close()
        
    # ---------------------------------------------------
    # VIDEO
    # ---------------------------------------------------
    
    frame_files = sorted(
        os.listdir(FRAME_DIR)
    )
    
    images = [
        imageio.imread(
            os.path.join(FRAME_DIR, file)
        )
        for file in frame_files
    ]
    
    imageio.mimsave(
        VIDEO_NAME,
        images,
        fps=1,
        format="ffmpeg"
    )
    
    print(
        f"\nVideo salvato: {VIDEO_NAME}"
    )