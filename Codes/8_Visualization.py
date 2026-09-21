import os
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as cx

from shapely.geometry import LineString
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.animation import FFMpegWriter


# ============================================================
# PARAMETRI
# ============================================================

FARMS_FILE = "fattorie.xlsx"
CULLING_FILE = "date_culling.csv"
SAME_FILE = "same_company.xlsx"

TARGET_GAMMAS = [0.100, 0.200]
DMAX_VALUES = [1.5, 2.0]


# ============================================================
# COLORI
# ============================================================

# Link
LINK_COLORS = {
    "company": "orange",
    "distance": "purple",
    "both": "teal",
}


# Nodi
NODE_COLOR_EXPOSED_NEW = "red"
NODE_COLOR_EXPOSED = "red"
NODE_COLOR_CULLED = "black"
NODE_COLOR_DETECTED = "green"
NODE_COLOR_SUSCEPTIBLE = "skyblue"


# ============================================================
# FUNZIONI DI SUPPORTO
# ============================================================

def normalize_code(x):
    """
    Normalizza i codici delle aziende/fattorie.
    """
    if pd.isna(x):
        return None

    return str(x).strip()


def parse_probability_series(series):
    """
    Converte una colonna di probabilità che può usare
    la virgola come separatore decimale.
    """
    return (
        series
        .astype(str)
        .str.strip()
        .str.replace(",", ".", regex=False)
        .replace({"": np.nan, "nan": np.nan})
        .astype(float)
    )


def load_best_infector(best_file):
    """
    Legge il file best_infector.

    Struttura attesa:

        codice | infettore | probabilità

    Restituisce un dizionario:

        target -> {
            "infector": ...,
            "probability": ...
        }
    """

    best_df = pd.read_excel(best_file)

    required_columns = {
        "codice",
        "infettore",
        "probabilità",
    }

    missing = required_columns - set(best_df.columns)

    if missing:
        raise ValueError(
            f"Nel file {best_file} mancano le colonne: {missing}"
        )

    best_df["codice"] = best_df["codice"].apply(normalize_code)
    best_df["infettore"] = best_df["infettore"].apply(normalize_code)

    best_df["probabilità"] = parse_probability_series(
        best_df["probabilità"]
    )

    best_lookup = {}

    for _, row in best_df.iterrows():

        target = row["codice"]

        if target is None:
            continue

        best_lookup[target] = {
            "infector": row["infettore"],
            "probability": row["probabilità"],
        }

    return best_lookup


def classify_link(source, target, same_lookup, distance_lookup):
    """
    Classifica automaticamente il link in:

        company
        distance
        both

    Se il link non appartiene a nessuna delle due reti,
    restituisce None.
    """

    pair = (source, target)

    if pair in same_lookup and pair in distance_lookup:
        return "both"

    if pair in same_lookup:
        return "company"

    if pair in distance_lookup:
        return "distance"

    return None


def get_linewidth(probability, is_best):
    """
    Spessore del link.

    Il best infector è sempre più spesso.

    Gli altri link hanno spessore proporzionale
    alla probabilità.
    """

    if is_best:
        return 5.0

    # Probabilità 0 -> 0.8
    # Probabilità 1 -> 4.0
    return 0.8 + 3.2 * probability


# ============================================================
# CICLO PRINCIPALE
# ============================================================

for TARGET_GAMMA in TARGET_GAMMAS:

    for TARGET_DMAX in DMAX_VALUES:

        print("\n" + "=" * 70)
        print(
            f"gamma = {TARGET_GAMMA:.3f} | "
            f"dmax = {TARGET_DMAX}"
        )
        print("=" * 70)


        # ====================================================
        # NOMI FILE
        # ====================================================

        DATES_FILE = (
            f"date_gamma{TARGET_GAMMA:.3f}_dmax{TARGET_DMAX}.xlsx"
        )

        MATRIX_FILE = (
            f"matrice_gamma{TARGET_GAMMA:.3f}_dmax{TARGET_DMAX}.xlsx"
        )

        NEIGHBORS_FILE = (
            f"neighbors_dmax{TARGET_DMAX}.xlsx"
        )

        BEST_FILE = (
            f"best_infector_gamma{TARGET_GAMMA:.3f}_dmax{TARGET_DMAX}.xlsx"
        )


        FRAME_DIR = (
            f"frames_v2_gamma{TARGET_GAMMA:.3f}_dmax{TARGET_DMAX}"
        )

        VIDEO_NAME = (
            f"epidemic_map_v2_gamma"
            f"{TARGET_GAMMA:.3f}_dmax{TARGET_DMAX}.mp4"
        )


        # ====================================================
        # CONTROLLO FILE
        # ====================================================

        required_files = [
            FARMS_FILE,
            CULLING_FILE,
            SAME_FILE,
            DATES_FILE,
            MATRIX_FILE,
            NEIGHBORS_FILE,
            BEST_FILE,
        ]

        for file in required_files:

            if not os.path.exists(file):
                raise FileNotFoundError(
                    f"File non trovato: {file}"
                )


        # ====================================================
        # CARTELLA FRAME
        # ====================================================

        os.makedirs(FRAME_DIR, exist_ok=True)


        # ====================================================
        # LETTURA FATTORIE
        # ====================================================

        print("Lettura fattorie...")

        df = pd.read_excel(FARMS_FILE)

        df["codice"] = df["codice"].apply(normalize_code)

        for col in ["latitudine", "longitudine"]:

            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .astype(float)
            )


        # ====================================================
        # DATE DI ESPOSIZIONE / DETEZIONE
        # ====================================================

        print("Lettura date...")

        dates_df = pd.read_excel(DATES_FILE)

        dates_df["codice"] = dates_df["codice"].apply(
            normalize_code
        )

        df = df.merge(
            dates_df[["codice", "E", "D"]],
            on="codice",
            how="left"
        )

        df["E"] = pd.to_datetime(
            df["E"],
            errors="coerce"
        )

        df["D"] = pd.to_datetime(
            df["D"],
            errors="coerce"
        )


        # ====================================================
        # DATA DI CULLING
        # ====================================================

        print("Lettura date di culling...")

        culling_df = pd.read_csv(
            CULLING_FILE,
            sep=";"
        )

        culling_df["codice"] = culling_df["codice"].apply(
            normalize_code
        )

        culling_df["estinzione"] = pd.to_datetime(
            culling_df["estinzione"],
            dayfirst=True,
            errors="coerce"
        )

        df = df.merge(
            culling_df[["codice", "estinzione"]],
            on="codice",
            how="left"
        )


        # ====================================================
        # GEODATAFRAME
        # ====================================================

        geometry = gpd.points_from_xy(
            df["longitudine"],
            df["latitudine"]
        )

        gdf = gpd.GeoDataFrame(
            df,
            geometry=geometry,
            crs="EPSG:4326"
        )

        gdf_merc = gdf.to_crs(epsg=3857)


        # ====================================================
        # COORDINATE DI OGNI FATTORIA
        # ====================================================

        coords = {
            row["codice"]: row.geometry
            for _, row in gdf_merc.iterrows()
            if row["codice"] is not None
            and row.geometry is not None
        }


        # ====================================================
        # RETE SAME COMPANY
        # ====================================================

        print("Lettura rete same company...")

        same_df = pd.read_excel(SAME_FILE)

        same_df["from_code"] = same_df["from_code"].apply(
            normalize_code
        )

        same_df["to_code"] = same_df["to_code"].apply(
            normalize_code
        )

        same_lookup = set(
            zip(
                same_df["from_code"],
                same_df["to_code"]
            )
        )


        # ====================================================
        # RETE DISTANZA
        # ====================================================

        print("Lettura rete distance...")

        neighbors_df = pd.read_excel(
            NEIGHBORS_FILE
        )

        neighbors_df["from_code"] = neighbors_df[
            "from_code"
        ].apply(normalize_code)

        neighbors_df["to_code"] = neighbors_df[
            "to_code"
        ].apply(normalize_code)

        distance_lookup = set(
            zip(
                neighbors_df["from_code"],
                neighbors_df["to_code"]
            )
        )


        # ====================================================
        # CLASSIFICAZIONE AUTOMATICA DELLE RETI
        # ====================================================

        company_only = (
            same_lookup - distance_lookup
        )

        distance_only = (
            distance_lookup - same_lookup
        )

        both_lookup = (
            same_lookup & distance_lookup
        )


        print(
            f"Company only:      {len(company_only)}"
        )

        print(
            f"Distance only:     {len(distance_only)}"
        )

        print(
            f"Company + distance: {len(both_lookup)}"
        )


        # ====================================================
        # LETTURA BEST INFECTOR
        # ====================================================

        print(
            f"Lettura best infector: {BEST_FILE}"
        )

        best_lookup = load_best_infector(
            BEST_FILE
        )


        # ====================================================
        # LETTURA MATRICE DELLE PROBABILITÀ
        #
        # Riga = SOURCE
        # Colonna = TARGET
        # ====================================================

        print("Lettura matrice delle probabilità...")

        matrix = pd.read_excel(
            MATRIX_FILE,
            index_col=0
        )


        # Normalizzazione codici
        matrix.index = [
            normalize_code(x)
            for x in matrix.index
        ]

        matrix.columns = [
            normalize_code(x)
            for x in matrix.columns
        ]


        # Conversione valori a numerico
        matrix = matrix.apply(
            lambda col: parse_probability_series(col)
        )


        # ====================================================
        # COSTRUZIONE DEI LINK
        # ====================================================

        print("Costruzione rete di trasmissione...")

        links_by_date = {}

        skipped_wildlife = 0
        skipped_unknown = 0
        skipped_network = 0


        for source in matrix.index:

            # -----------------------------------------------
            # WILDLIFE NON HA COORDINATE
            # -----------------------------------------------

            if source is None:
                continue

            if source.upper() == "WILDLIFE":
                continue

            if source not in coords:
                skipped_unknown += 1
                continue


            # -----------------------------------------------
            # TUTTI I TARGET
            # -----------------------------------------------

            for target in matrix.columns:

                if target is None:
                    continue

                if target.upper() == "WILDLIFE":
                    continue

                if target not in coords:
                    skipped_unknown += 1
                    continue

                if source == target:
                    continue


                # -------------------------------------------
                # PROBABILITÀ
                # -------------------------------------------

                p = matrix.loc[source, target]

                if pd.isna(p):
                    continue

                if p <= 0:
                    continue

                p = float(p)


                # -------------------------------------------
                # DATA DI ESPOSIZIONE DEL TARGET
                # -------------------------------------------

                target_rows = df[
                    df["codice"] == target
                ]

                if target_rows.empty:
                    continue

                exposure_date = (
                    target_rows.iloc[0]["E"]
                )

                if pd.isna(exposure_date):
                    continue

                exposure_ts = (
                    pd.Timestamp(exposure_date)
                    .normalize()
                )


                # -------------------------------------------
                # TIPO DI LINK
                # -------------------------------------------

                edge_type = classify_link(
                    source,
                    target,
                    same_lookup,
                    distance_lookup
                )

                # Non mostriamo link che non appartengono
                # né alla rete company né alla rete distance.
                if edge_type is None:
                    skipped_network += 1
                    continue


                # -------------------------------------------
                # BEST INFECTOR DEL TARGET
                # -------------------------------------------

                best_info = best_lookup.get(
                    target
                )

                best_infector = None

                if best_info is not None:
                    best_infector = (
                        best_info["infector"]
                    )


                # -------------------------------------------
                # WILDLIFE COME BEST INFECTOR
                #
                # Se wildlife è il best infector,
                # non viene mostrato nessun link
                # farm-to-farm per questo target.
                # -------------------------------------------

                if (
                    best_infector is not None
                    and best_infector.upper() == "WILDLIFE"
                ):
                    skipped_wildlife += 1
                    continue


                # -------------------------------------------
                # È IL BEST INFECTOR?
                # -------------------------------------------

                is_best = (
                    best_infector is not None
                    and source == best_infector
                )


                # -------------------------------------------
                # SPESSORE
                # -------------------------------------------

                linewidth = get_linewidth(
                    p,
                    is_best
                )


                # -------------------------------------------
                # GEOMETRIA
                # -------------------------------------------

                line = LineString([
                    coords[source],
                    coords[target]
                ])


                # -------------------------------------------
                # SALVATAGGIO
                # -------------------------------------------

                links_by_date.setdefault(
                    exposure_ts,
                    []
                ).append({

                    "source": source,

                    "target": target,

                    "probability": p,

                    "is_best": is_best,

                    "best_infector": best_infector,

                    "geometry": line,

                    "type": edge_type,

                    "linewidth": linewidth,
                })


        print(
            f"Numero di giorni con link: "
            f"{len(links_by_date)}"
        )

        print(
            f"Link ignorati perché wildlife è best: "
            f"{skipped_wildlife}"
        )

        print(
            f"Codici senza coordinate: "
            f"{skipped_unknown}"
        )

        print(
            f"Link non appartenenti alle due reti: "
            f"{skipped_network}"
        )


        # ====================================================
        # INTERVALLO TEMPORALE DEL VIDEO
        # ====================================================

        all_dates = []

        all_dates.extend(
            df["E"].dropna().tolist()
        )

        all_dates.extend(
            df["D"].dropna().tolist()
        )

        all_dates.extend(
            df["estinzione"].dropna().tolist()
        )


        if not all_dates:
            print(
                "Nessuna data disponibile. "
                "Salto questo caso."
            )
            continue


        min_date = (
            pd.Timestamp(min(all_dates))
            .normalize()
        )

        max_date = (
            pd.Timestamp(max(all_dates))
            .normalize()
        )


        video_dates = pd.date_range(
            start=min_date,
            end=max_date,
            freq="D"
        )


        print(
            f"Periodo video: "
            f"{min_date.date()} -> {max_date.date()}"
        )

        print(
            f"Numero frame: {len(video_dates)}"
        )


        # ====================================================
        # FUNZIONE PER LO STATO DEI NODI
        # ====================================================

        def get_node_states(current_ts):

            newly_exposed = set()
            exposed = set()
            detected = set()
            culled = set()

            for _, row in gdf.iterrows():

                code = row["codice"]

                E = row["E"]
                D = row["D"]
                C = row["estinzione"]


                # -------------------------------------------
                # ESPOSTA
                # -------------------------------------------

                if pd.notna(E):

                    E_ts = (
                        pd.Timestamp(E)
                        .normalize()
                    )

                    if E_ts <= current_ts:

                        exposed.add(code)

                        if E_ts == current_ts:
                            newly_exposed.add(code)


                # -------------------------------------------
                # DETECTED
                # -------------------------------------------

                if pd.notna(D):

                    D_ts = (
                        pd.Timestamp(D)
                        .normalize()
                    )

                    if D_ts <= current_ts:
                        detected.add(code)


                # -------------------------------------------
                # CULLED
                # -------------------------------------------

                if pd.notna(C):

                    C_ts = (
                        pd.Timestamp(C)
                        .normalize()
                    )

                    if C_ts <= current_ts:
                        culled.add(code)


            return (
                newly_exposed,
                exposed,
                detected,
                culled
            )


        # ====================================================
        # PREPARAZIONE VIDEO
        # ====================================================

        print(
            f"Creazione video: {VIDEO_NAME}"
        )


        writer = FFMpegWriter(
            fps=2,
            metadata={
                "title": (
                    f"Epidemic transmission network "
                    f"gamma={TARGET_GAMMA:.3f}, "
                    f"dmax={TARGET_DMAX}"
                )
            }
        )


        # ====================================================
        # CREAZIONE FRAME + VIDEO
        # ====================================================

        with writer.saving(
            plt.figure(figsize=(16, 9)),
            VIDEO_NAME,
            dpi=120
        ):

            for frame_number, current_ts in enumerate(
                video_dates
            ):

                print(
                    f"Frame {frame_number + 1}/"
                    f"{len(video_dates)}: "
                    f"{current_ts.date()}"
                )


                # -------------------------------------------
                # FIGURA FULL HD
                # -------------------------------------------

                fig, ax = plt.subplots(
                    figsize=(16, 9)
                )


                # -------------------------------------------
                # STATO NODI
                # -------------------------------------------

                (
                    newly_exposed,
                    exposed,
                    detected,
                    culled
                ) = get_node_states(
                    current_ts
                )


                # -------------------------------------------
                # LINK DEL GIORNO CORRENTE
                #
                # Prima i link normali.
                # Poi il best infector sopra.
                # -------------------------------------------

                day_links = (
                    links_by_date.get(
                        current_ts,
                        []
                    )
                )


                # -------------------------------------------
                # LINK NON-BEST
                # -------------------------------------------

                for link in day_links:

                    if link["is_best"]:
                        continue

                    line = link["geometry"]

                    x, y = line.xy

                    ax.plot(
                        x,
                        y,
                        color=LINK_COLORS[
                            link["type"]
                        ],
                        linewidth=link["linewidth"],
                        alpha=0.90,
                        solid_capstyle="round",
                        zorder=8
                    )


                # -------------------------------------------
                # BEST INFECTOR
                # -------------------------------------------

                for link in day_links:

                    if not link["is_best"]:
                        continue

                    line = link["geometry"]

                    x, y = line.xy

                    ax.plot(
                        x,
                        y,
                        color=LINK_COLORS[
                            link["type"]
                        ],
                        linewidth=link["linewidth"],
                        alpha=1.0,
                        solid_capstyle="round",
                        zorder=9
                    )


                # -------------------------------------------
                # NODI
                # -------------------------------------------

                # Suscettibili
                susceptible_mask = (
                    ~gdf["codice"].isin(exposed)
                    & ~gdf["codice"].isin(culled)
                )

                if susceptible_mask.any():

                    gdf_merc.loc[
                        susceptible_mask
                    ].plot(
                        ax=ax,
                        color=NODE_COLOR_SUSCEPTIBLE,
                        markersize=6,
                        zorder=10
                    )


                # Esposte ma non nuove
                exposed_mask = (
                    gdf["codice"].isin(exposed)
                    & ~gdf["codice"].isin(newly_exposed)
                    & ~gdf["codice"].isin(culled)
                )

                if exposed_mask.any():

                    gdf_merc.loc[
                        exposed_mask
                    ].plot(
                        ax=ax,
                        color=NODE_COLOR_EXPOSED,
                        markersize=8,
                        zorder=11
                    )


                # Detected
                detected_mask = (
                    gdf["codice"].isin(detected)
                    & ~gdf["codice"].isin(culled)
                    & ~gdf["codice"].isin(newly_exposed)
                )

                if detected_mask.any():

                    gdf_merc.loc[
                        detected_mask
                    ].plot(
                        ax=ax,
                        color=NODE_COLOR_DETECTED,
                        markersize=8,
                        zorder=12
                    )


                # Nuove esposte
                new_mask = (
                    gdf["codice"].isin(
                        newly_exposed
                    )
                    & ~gdf["codice"].isin(culled)
                )

                if new_mask.any():

                    gdf_merc.loc[
                        new_mask
                    ].plot(
                        ax=ax,
                        color=NODE_COLOR_EXPOSED_NEW,
                        markersize=40,
                        zorder=14
                    )


                # Culled
                culled_mask = (
                    gdf["codice"].isin(culled)
                )

                if culled_mask.any():

                    gdf_merc.loc[
                        culled_mask
                    ].plot(
                        ax=ax,
                        color=NODE_COLOR_CULLED,
                        markersize=8,
                        zorder=15
                    )


                # -------------------------------------------
                # BASEMAP
                # -------------------------------------------

                cx.add_basemap(
                    ax,
                    source=cx.providers.OpenStreetMap.HOT,
                    crs=gdf_merc.crs
                )


                # -------------------------------------------
                # LIMITI MAPPA
                # -------------------------------------------

                xmin, ymin, xmax, ymax = (
                    gdf_merc.total_bounds
                )

                margin_x = (
                    xmax - xmin
                ) * 0.05

                margin_y = (
                    ymax - ymin
                ) * 0.05

                ax.set_xlim(
                    xmin - margin_x,
                    xmax + margin_x
                )

                ax.set_ylim(
                    ymin - margin_y,
                    ymax + margin_y
                )


                # -------------------------------------------
                # TITOLO
                # -------------------------------------------

                ax.set_title(
                    (
                        f"Epidemic transmission network\n"
                        f"{current_ts.strftime('%d/%m/%Y')}  |  "
                        f"γ = {TARGET_GAMMA:.3f}  |  "
                        f"dmax = {TARGET_DMAX}"
                    ),
                    fontsize=18,
                    pad=12
                )


                # -------------------------------------------
                # LEGENDA LINK
                # -------------------------------------------

                link_legend = [

                    Line2D(
                        [0],
                        [0],
                        color="orange",
                        linewidth=3,
                        label="Company only"
                    ),

                    Line2D(
                        [0],
                        [0],
                        color="purple",
                        linewidth=3,
                        label="Distance only"
                    ),

                    Line2D(
                        [0],
                        [0],
                        color="teal",
                        linewidth=3,
                        label="Company + distance"
                    ),

                ]


                # -------------------------------------------
                # LEGENDA NODI
                # -------------------------------------------

                node_legend = [

                    Line2D(
                        [0],
                        [0],
                        marker="o",
                        color="none",
                        markerfacecolor="skyblue",
                        markersize=5,
                        label="Susceptible"
                    ),

                    Line2D(
                        [0],
                        [0],
                        marker="o",
                        color="none",
                        markerfacecolor="red",
                        markersize=6,
                        label="Exposed"
                    ),

                    Line2D(
                        [0],
                        [0],
                        marker="o",
                        color="none",
                        markerfacecolor="red",
                        markersize=10,
                        label="Newly exposed"
                    ),

                    Line2D(
                        [0],
                        [0],
                        marker="o",
                        color="none",
                        markerfacecolor="green",
                        markersize=6,
                        label="Detected"
                    ),

                    Line2D(
                        [0],
                        [0],
                        marker="o",
                        color="none",
                        markerfacecolor="black",
                        markersize=6,
                        label="Culled"
                    ),

                ]


                # -------------------------------------------
                # LEGENDA
                # -------------------------------------------

                ax.legend(
                    handles=(
                        link_legend
                        + node_legend
                    ),
                    loc="upper right",
                    fontsize=9,
                    frameon=True
                )


                # -------------------------------------------
                # ASSI
                # -------------------------------------------

                ax.set_axis_off()


                # -------------------------------------------
                # SALVATAGGIO FRAME
                # -------------------------------------------

                frame_path = os.path.join(
                    FRAME_DIR,
                    f"frame_{frame_number:04d}.png"
                )

                plt.savefig(
                    frame_path,
                    dpi=120,
                    bbox_inches=None
                )


                # -------------------------------------------
                # AGGIUNTA AL VIDEO
                # -------------------------------------------

                writer.grab_frame()


                plt.close(fig)


        print("\nVideo completato:")
        print(VIDEO_NAME)

        print(
            f"Frame salvati in: {FRAME_DIR}"
        )

        print("=" * 70)