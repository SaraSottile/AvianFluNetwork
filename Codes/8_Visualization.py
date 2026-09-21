import os
import shutil
import subprocess

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as cx

from shapely.geometry import LineString
from matplotlib.lines import Line2D

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
        .replace({
            "": np.nan,
            "nan": np.nan
        })
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

    best_df = pd.read_excel(
        best_file
    )

    required_columns = {
        "codice",
        "infettore",
        "probabilità",
    }

    missing = (
        required_columns
        - set(best_df.columns)
    )

    if missing:

        raise ValueError(
            f"Nel file {best_file} "
            f"mancano le colonne: {missing}"
        )

    best_df["codice"] = (
        best_df["codice"]
        .apply(normalize_code)
    )

    best_df["infettore"] = (
        best_df["infettore"]
        .apply(normalize_code)
    )

    best_df["probabilità"] = (
        parse_probability_series(
            best_df["probabilità"]
        )
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


def classify_link(
    source,
    target,
    same_lookup,
    distance_lookup
):
    """
    Classifica automaticamente il link in:

        company
        distance
        both

    Se il link non appartiene a nessuna delle due reti,
    restituisce None.
    """

    pair = (
        source,
        target
    )

    if (
        pair in same_lookup
        and pair in distance_lookup
    ):
        return "both"

    if pair in same_lookup:
        return "company"

    if pair in distance_lookup:
        return "distance"

    return None


def get_linewidth(probability):
    """
    Spessore del link proporzionale
    alla probabilità.

    Probabilità 0 -> 0.8
    Probabilità 1 -> 4.0
    """

    return 0.8 + 3.2 * probability


# ============================================================
# CICLO PRINCIPALE
# ============================================================

for TARGET_GAMMA in TARGET_GAMMAS:

    for TARGET_DMAX in DMAX_VALUES:

        print()
        print("=" * 70)

        print(
            f"gamma = {TARGET_GAMMA:.3f} | "
            f"dmax = {TARGET_DMAX}"
        )

        print("=" * 70)


        # ====================================================
        # NOMI FILE
        # ====================================================

        DATES_FILE = (
            f"date_gamma"
            f"{TARGET_GAMMA:.3f}"
            f"_dmax"
            f"{TARGET_DMAX}.xlsx"
        )

        MATRIX_FILE = (
            f"matrice_gamma"
            f"{TARGET_GAMMA:.3f}"
            f"_dmax"
            f"{TARGET_DMAX}.xlsx"
        )

        NEIGHBORS_FILE = (
            f"neighbors_dmax"
            f"{TARGET_DMAX}.xlsx"
        )

        BEST_FILE = (
            f"best_infector_gamma"
            f"{TARGET_GAMMA:.3f}"
            f"_dmax"
            f"{TARGET_DMAX}.xlsx"
        )

        FRAME_DIR = (
            f"frames_gamma"
            f"{TARGET_GAMMA:.3f}"
            f"_dmax"
            f"{TARGET_DMAX}"
        )

        VIDEO_NAME = (
            f"epidemic_map_gamma"
            f"{TARGET_GAMMA:.3f}"
            f"_dmax"
            f"{TARGET_DMAX}.mp4"
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

        os.makedirs(
            FRAME_DIR,
            exist_ok=True
        )


        # ====================================================
        # LETTURA FATTORIE
        # ====================================================

        print(
            "Lettura fattorie..."
        )

        df = pd.read_excel(
            FARMS_FILE
        )

        df["codice"] = (
            df["codice"]
            .apply(normalize_code)
        )

        for col in [
            "latitudine",
            "longitudine"
        ]:

            df[col] = (
                df[col]
                .astype(str)
                .str.replace(
                    ",",
                    ".",
                    regex=False
                )
                .astype(float)
            )


        # ====================================================
        # DATE DI ESPOSIZIONE / DETEZIONE
        # ====================================================

        print(
            "Lettura date..."
        )

        dates_df = pd.read_excel(
            DATES_FILE
        )

        dates_df["codice"] = (
            dates_df["codice"]
            .apply(normalize_code)
        )

        df = df.merge(
            dates_df[
                [
                    "codice",
                    "E",
                    "D"
                ]
            ],
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

        print(
            "Lettura date di culling..."
        )

        culling_df = pd.read_csv(
            CULLING_FILE,
            sep=";"
        )

        culling_df["codice"] = (
            culling_df["codice"]
            .apply(normalize_code)
        )

        culling_df["estinzione"] = (
            pd.to_datetime(
                culling_df["estinzione"],
                dayfirst=True,
                errors="coerce"
            )
        )

        df = df.merge(
            culling_df[
                [
                    "codice",
                    "estinzione"
                ]
            ],
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

        gdf_merc = gdf.to_crs(
            epsg=3857
        )


        # ====================================================
        # COORDINATE DI OGNI FATTORIA
        # ====================================================

        coords = {

            row["codice"]: row.geometry

            for _, row
            in gdf_merc.iterrows()

            if row["codice"] is not None

            and row.geometry is not None

        }


        # ====================================================
        # RETE SAME COMPANY
        # ====================================================

        print(
            "Lettura rete same company..."
        )

        same_df = pd.read_excel(
            SAME_FILE
        )

        same_df["from_code"] = (
            same_df["from_code"]
            .apply(normalize_code)
        )

        same_df["to_code"] = (
            same_df["to_code"]
            .apply(normalize_code)
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

        print(
            "Lettura rete distance..."
        )

        neighbors_df = pd.read_excel(
            NEIGHBORS_FILE
        )

        neighbors_df["from_code"] = (
            neighbors_df["from_code"]
            .apply(normalize_code)
        )

        neighbors_df["to_code"] = (
            neighbors_df["to_code"]
            .apply(normalize_code)
        )

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
            same_lookup
            - distance_lookup
        )

        distance_only = (
            distance_lookup
            - same_lookup
        )

        both_lookup = (
            same_lookup
            & distance_lookup
        )

        print(
            f"Company only:      "
            f"{len(company_only)}"
        )

        print(
            f"Distance only:     "
            f"{len(distance_only)}"
        )

        print(
            f"Company + distance: "
            f"{len(both_lookup)}"
        )


        # ====================================================
        # LETTURA BEST INFECTOR
        # ====================================================

        print(
            f"Lettura best infector: "
            f"{BEST_FILE}"
        )

        best_lookup = (
            load_best_infector(
                BEST_FILE
            )
        )


        # ====================================================
        # LETTURA MATRICE DELLE PROBABILITÀ
        # ====================================================

        print(
            "Lettura matrice delle probabilità..."
        )

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
            lambda col:
                parse_probability_series(col)
        )


        # ====================================================
        # COSTRUZIONE DEI LINK
        # ====================================================

        print(
            "Costruzione rete di trasmissione..."
        )

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

                p = matrix.loc[
                    source,
                    target
                ]

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
                    pd.Timestamp(
                        exposure_date
                    )
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

                if edge_type is None:

                    skipped_network += 1

                    continue


                # -------------------------------------------
                # BEST INFECTOR DEL TARGET
                # -------------------------------------------

                best_info = (
                    best_lookup.get(
                        target
                    )
                )

                best_infector = None

                if best_info is not None:

                    best_infector = (
                        best_info["infector"]
                    )


                # -------------------------------------------
                # WILDLIFE COME BEST INFECTOR
                # -------------------------------------------

                if (
                    best_infector is not None
                    and
                    best_infector.upper()
                    == "WILDLIFE"
                ):

                    skipped_wildlife += 1

                    continue


                # -------------------------------------------
                # È IL BEST INFECTOR?
                # -------------------------------------------

                is_best = (
                    best_infector is not None
                    and
                    source == best_infector
                )


                # -------------------------------------------
                # SPESSORE
                # -------------------------------------------

                linewidth = get_linewidth(p)


                # -------------------------------------------
                # GEOMETRIA
                # -------------------------------------------

                line = LineString(
                    [
                        coords[source],
                        coords[target]
                    ]
                )


                # -------------------------------------------
                # SALVATAGGIO
                # -------------------------------------------

                links_by_date.setdefault(
                    exposure_ts,
                    []
                ).append(
                    {
                        "source": source,

                        "target": target,

                        "probability": p,

                        "is_best": is_best,

                        "best_infector":
                            best_infector,

                        "geometry": line,

                        "type": edge_type,

                        "linewidth": linewidth,
                    }
                )


        print(
            f"Numero di giorni con link: "
            f"{len(links_by_date)}"
        )

        print(
            f"Link ignorati perché "
            f"wildlife è best: "
            f"{skipped_wildlife}"
        )

        print(
            f"Codici senza coordinate: "
            f"{skipped_unknown}"
        )

        print(
            f"Link non appartenenti "
            f"alle due reti: "
            f"{skipped_network}"
        )


        # ====================================================
        # INTERVALLO TEMPORALE DEL VIDEO
        # ====================================================

        all_dates = []

        all_dates.extend(
            df["E"]
            .dropna()
            .tolist()
        )

        all_dates.extend(
            df["D"]
            .dropna()
            .tolist()
        )

        all_dates.extend(
            df["estinzione"]
            .dropna()
            .tolist()
        )


        if not all_dates:

            print(
                "Nessuna data disponibile. "
                "Salto questo caso."
            )

            continue


        min_date = (
            pd.Timestamp(
                min(all_dates)
            )
            .normalize()
        )

        max_date = (
            pd.Timestamp(
                max(all_dates)
            )
            .normalize()
        )


        video_dates = pd.date_range(
            start=min_date,
            end=max_date,
            freq="D"
        )


        print(
            f"Periodo video: "
            f"{min_date.date()} -> "
            f"{max_date.date()}"
        )

        print(
            f"Numero frame: "
            f"{len(video_dates)}"
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

                            newly_exposed.add(
                                code
                            )


                # -------------------------------------------
                # DETECTED
                # -------------------------------------------

                if pd.notna(D):

                    D_ts = (
                        pd.Timestamp(D)
                        .normalize()
                    )

                    if D_ts <= current_ts:

                        detected.add(
                            code
                        )


                # -------------------------------------------
                # CULLED
                # -------------------------------------------

                if pd.notna(C):

                    C_ts = (
                        pd.Timestamp(C)
                        .normalize()
                    )

                    if C_ts <= current_ts:

                        culled.add(
                            code
                        )


            return (
                newly_exposed,
                exposed,
                detected,
                culled
            )


        # ====================================================
        # CREAZIONE FRAME
        # ====================================================

        print()
        print(
            f"Creazione frame per il video: "
            f"{VIDEO_NAME}"
        )

        print(
            f"Cartella frame: "
            f"{FRAME_DIR}"
        )


        # ====================================================
        # FIGURA
        # ====================================================

        fig = plt.figure(
            figsize=(16, 9)
        )


        # ====================================================
        # CICLO DEI FRAME
        # ====================================================

        for frame_number, current_ts in enumerate(
            video_dates
        ):

            print(
                f"Frame "
                f"{frame_number + 1}/"
                f"{len(video_dates)}: "
                f"{current_ts.date()}"
            )


            # -----------------------------------------------
            # PULIZIA FIGURA
            # -----------------------------------------------

            fig.clear()

            ax = fig.add_subplot(
                111
            )


            # -----------------------------------------------
            # STATO NODI
            # -----------------------------------------------

            (
                newly_exposed,
                exposed,
                detected,
                culled
            ) = get_node_states(
                current_ts
            )


            # -----------------------------------------------
            # LINK DEL GIORNO CORRENTE
            # -----------------------------------------------

            day_links = (
                links_by_date.get(
                    current_ts,
                    []
                )
            )


            # -----------------------------------------------
            # LINK NON-BEST
            # -----------------------------------------------

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
                    linestyle="--",
                    alpha=0.90,
                    solid_capstyle="round",
                    zorder=3
                )


            # -----------------------------------------------
            # BEST INFECTOR
            # -----------------------------------------------

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
                    zorder=4
                )


            # -----------------------------------------------
            # NODI SUSCETTIBILI
            # -----------------------------------------------

            susceptible_mask = (
                ~gdf["codice"].isin(
                    exposed
                )
                &
                ~gdf["codice"].isin(
                    culled
                )
            )

            if susceptible_mask.any():

                gdf_merc.loc[
                    susceptible_mask
                ].plot(
                    ax=ax,
                    color=NODE_COLOR_SUSCEPTIBLE,
                    markersize=6,
                    zorder=2
                )


            # -----------------------------------------------
            # ESPOSTE MA NON NUOVE
            # -----------------------------------------------

            exposed_mask = (
                gdf["codice"].isin(
                    exposed
                )
                &
                ~gdf["codice"].isin(
                    newly_exposed
                )
                &
                ~gdf["codice"].isin(
                    culled
                )
            )

            if exposed_mask.any():

                gdf_merc.loc[
                    exposed_mask
                ].plot(
                    ax=ax,
                    color=NODE_COLOR_EXPOSED,
                    markersize=8,
                    zorder=2
                )


            # -----------------------------------------------
            # DETECTED
            # -----------------------------------------------

            detected_mask = (
                gdf["codice"].isin(
                    detected
                )
                &
                ~gdf["codice"].isin(
                    culled
                )
                &
                ~gdf["codice"].isin(
                    newly_exposed
                )
            )

            if detected_mask.any():

                gdf_merc.loc[
                    detected_mask
                ].plot(
                    ax=ax,
                    color=NODE_COLOR_DETECTED,
                    markersize=8,
                    zorder=2
                )


            # -----------------------------------------------
            # NUOVE ESPOSTE
            # -----------------------------------------------

            new_mask = (
                gdf["codice"].isin(
                    newly_exposed
                )
                &
                ~gdf["codice"].isin(
                    culled
                )
            )

            if new_mask.any():

                gdf_merc.loc[
                    new_mask
                ].plot(
                    ax=ax,
                    color=NODE_COLOR_EXPOSED_NEW,
                    markersize=40,
                    zorder=2
                )


            # -----------------------------------------------
            # CULLED
            # -----------------------------------------------

            culled_mask = (
                gdf["codice"].isin(
                    culled
                )
            )

            if culled_mask.any():

                gdf_merc.loc[
                    culled_mask
                ].plot(
                    ax=ax,
                    color=NODE_COLOR_CULLED,
                    markersize=8,
                    zorder=2
                )


            # -----------------------------------------------
            # BASEMAP
            # -----------------------------------------------

            cx.add_basemap(
                ax,
                source=(
                    cx.providers
                    .OpenStreetMap.HOT
                ),
                crs=gdf_merc.crs
            )


            # -----------------------------------------------
            # LIMITI MAPPA
            # -----------------------------------------------

            (
                xmin,
                ymin,
                xmax,
                ymax
            ) = gdf_merc.total_bounds


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


            # -----------------------------------------------
            # TITOLO
            # -----------------------------------------------

            ax.set_title(
                (
                    "Epidemic transmission network\n"
                    f"{current_ts.strftime('%d/%m/%Y')}"
                ),
                fontsize=18,
                pad=12
            )


            # -----------------------------------------------
            # LEGENDA LINK
            # -----------------------------------------------

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


            # -----------------------------------------------
            # LEGENDA NODI
            # -----------------------------------------------

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


            # -----------------------------------------------
            # LEGENDA
            # -----------------------------------------------

            ax.legend(
                handles=(
                    link_legend
                    +
                    node_legend
                ),
                loc="upper right",
                fontsize=9,
                frameon=True
            )


            # -----------------------------------------------
            # ASSI
            # -----------------------------------------------

            ax.set_axis_off()


            # -----------------------------------------------
            # SALVATAGGIO FRAME PNG
            # -----------------------------------------------

            frame_path = os.path.join(
                FRAME_DIR,
                f"frame_{frame_number:04d}.png"
            )

            fig.savefig(
                frame_path,
                dpi=120,
                bbox_inches=None
            )


        # ====================================================
        # CHIUSURA FIGURA
        # ====================================================

        plt.close(
            fig
        )


        print()
        print(
            "Tutti i frame sono stati creati."
        )


        # ====================================================
        # CREAZIONE VIDEO DA PNG
        # ====================================================
        
        print()
        print("=" * 70)
        print("CREAZIONE VIDEO MP4")
        print("=" * 70)
        
        # ----------------------------------------------------
        # PATTERN DEI FRAME
        # ----------------------------------------------------
        
        input_pattern = os.path.join(
            FRAME_DIR,
            "frame_%04d.png"
        )
        
        print(
            f"Frame di input: {input_pattern}"
        )
        
        # ----------------------------------------------------
        # COMANDO FFMPEG
        # ----------------------------------------------------
        
        ffmpeg_command = [
            shutil.which("ffmpeg"),
        
            "-y",
        
            # 2 frame al secondo
            "-framerate",
            "2",
        
            # PNG
            "-i",
            input_pattern,
        
            # Codec H.264
            "-c:v",
            "libx264",
        
            # Qualità
            "-crf",
            "18",
        
            # Preset
            "-preset",
            "medium",
        
            # Formato colore compatibile
            "-pix_fmt",
            "yuv420p",
        
            # File di output
            VIDEO_NAME
        ]
        
        print()
        print("Comando FFmpeg:")
        print()
        
        print(
            " ".join(
                (
                    f'"{x}"'
                    if " " in str(x)
                    else str(x)
                )
                for x in ffmpeg_command
            )
        )
        
        print()
        print("Avvio FFmpeg...")
        print()
        
        # ----------------------------------------------------
        # ESECUZIONE
        # ----------------------------------------------------
        
        result = subprocess.run(
            ffmpeg_command,
            capture_output=True,
            text=True
        )
        
        # ----------------------------------------------------
        # OUTPUT FFmpeg
        # ----------------------------------------------------
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print(result.stderr)
        
        # ----------------------------------------------------
        # CONTROLLO
        # ----------------------------------------------------
        
        if result.returncode != 0:
        
            print()
            print("=" * 70)
            print("ERRORE FFmpeg")
            print("=" * 70)
        
            print(
                f"Codice di uscita: {result.returncode}"
            )
        
            print()
            print("Messaggio FFmpeg:")
            print(result.stderr)
        
            raise RuntimeError(
                "FFmpeg non è riuscito "
                "a creare il video."
            )
        
        # ----------------------------------------------------
        # CONTROLLO FILE
        # ----------------------------------------------------
        
        if not os.path.exists(VIDEO_NAME):
        
            raise RuntimeError(
                "FFmpeg ha terminato senza errori, "
                "ma il file MP4 non è stato trovato."
            )
        
        # ----------------------------------------------------
        # RISULTATO
        # ----------------------------------------------------
        
        print()
        print("=" * 70)
        print("VIDEO COMPLETATO")
        print("=" * 70)
        
        print(
            f"File video: {VIDEO_NAME}"
        )
        
        print(
            f"Cartella frame: {FRAME_DIR}"
        )
        
        print("=" * 70)