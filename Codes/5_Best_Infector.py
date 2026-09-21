# -*- coding: utf-8 -*-
"""
Check classification of the best infector

Per ciascuna delle 297 fattorie infette:

1. leggiamo il best infector dal file

2. se infettore == WILDLIFE:
       -> Wildlife

3. altrimenti controlliamo il best infector nei due network:
       - same_company
       - distance

4. classificazione mutuamente esclusiva:

       Only same company
       Only distance
       Distance and same company
       Wildlife
       Unmatched  (solo controllo)

DEFINIZIONI
-----------
Only same company:
    best infector presente in same_company
    ma NON presente in neighbors.

Only distance:
    best infector presente in neighbors
    ma NON presente in same_company.

Distance and same company:
    best infector presente in entrambi.

Wildlife:
    la colonna "infettore" del file best_infector
    contiene "WILDLIFE".


"""

import pandas as pd


# =========================================================
# INPUT
# =========================================================

FARMS_FILE = "fattorie.xlsx"
SAME_FILE = "same_company.xlsx"

GAMMAS = [0.100, 0.200]
DMAX_VALUES = [1.5, 2.0]


# =========================================================
# CLEAN CODE
# =========================================================

def clean_code(x):

    if pd.isna(x):
        return None

    return str(x).strip()


# =========================================================
# LOOP
# =========================================================

for TARGET_GAMMA in GAMMAS:

    for TARGET_DMAX in DMAX_VALUES:

        print("\n")
        print("=" * 80)
        print(
            f"gamma={TARGET_GAMMA:.3f}   "
            f"dmax={TARGET_DMAX}"
        )
        print("=" * 80)


        # =================================================
        # FILE NAMES
        # =================================================

        DATES_FILE = (
            f"date_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        BEST_FILE = (
            f"best_infector_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        NEIGHBOR_FILE = (
            f"neighbors_dmax{TARGET_DMAX}.xlsx"
        )


        # =================================================
        # LOAD
        # =================================================

        farms = pd.read_excel(
            FARMS_FILE
        )

        dates = pd.read_excel(
            DATES_FILE
        )

        same_df = pd.read_excel(
            SAME_FILE
        )

        neighbors_df = pd.read_excel(
            NEIGHBOR_FILE
        )

        best_df = pd.read_excel(
            BEST_FILE
        )


        # =================================================
        # CLEAN CODES
        # =================================================

        farms["codice"] = (
            farms["codice"]
            .apply(clean_code)
        )

        dates["codice"] = (
            dates["codice"]
            .apply(clean_code)
        )

        same_df["from_code"] = (
            same_df["from_code"]
            .apply(clean_code)
        )

        same_df["to_code"] = (
            same_df["to_code"]
            .apply(clean_code)
        )

        neighbors_df["from_code"] = (
            neighbors_df["from_code"]
            .apply(clean_code)
        )

        neighbors_df["to_code"] = (
            neighbors_df["to_code"]
            .apply(clean_code)
        )

        best_df["codice"] = (
            best_df["codice"]
            .apply(clean_code)
        )

        best_df["infettore"] = (
            best_df["infettore"]
            .apply(clean_code)
        )


        # =================================================
        # DATES
        # =================================================

        dates["E"] = pd.to_datetime(
            dates["E"],
            errors="coerce"
        )

        dates["D"] = pd.to_datetime(
            dates["D"],
            errors="coerce"
        )


        # =================================================
        # MERGE
        # =================================================

        farms = farms.merge(
            dates[
                ["codice", "E", "D"]
            ],
            on="codice",
            how="left"
        )


        # =================================================
        # INFECTED FARMS
        # =================================================
        # E notna AND D notna
        #
        # =================================================

        farms = farms[
            farms["E"].notna()
            &
            farms["D"].notna()
        ].copy()

        farms.reset_index(
            drop=True,
            inplace=True
        )


        n_farms = len(farms)

        print(
            f"\nNumero fattorie infette: {n_farms}"
        )


        if n_farms == 0:
            continue


        # =================================================
        # INFECTED CODES
        # =================================================

        infected_codes = set(
            farms["codice"]
        )


        # =================================================
        # CODE -> LOCAL INDEX
        # =================================================

        code_to_idx = {
            code: idx
            for idx, code in enumerate(
                farms["codice"]
            )
        }


        # =================================================
        # SAME COMPANY NETWORK
        # =================================================

        same_company = {
            j: set()
            for j in range(n_farms)
        }


        for _, row in same_df.iterrows():

            target_code = row["from_code"]
            infector_code = row["to_code"]


            if (
                target_code in infected_codes
                and
                infector_code in infected_codes
            ):

                j = code_to_idx[
                    target_code
                ]

                k = code_to_idx[
                    infector_code
                ]

                same_company[j].add(k)


        # =================================================
        # DISTANCE NETWORK
        # =================================================
        #
        # Anche qui:
        #
        # from_code = target
        # to_code   = infector
        #
        # Manteniamo anche la distanza per il debug.
        #
        # =================================================

        neighbors = {
            j: {}
            for j in range(n_farms)
        }


        for _, row in neighbors_df.iterrows():

            target_code = row["from_code"]
            infector_code = row["to_code"]

            if (
                target_code in infected_codes
                and
                infector_code in infected_codes
            ):

                j = code_to_idx[
                    target_code
                ]

                k = code_to_idx[
                    infector_code
                ]

                distance = row["distance"]

                neighbors[j][k] = distance


        # =================================================
        # BEST INFECTOR PROBABILITY
        # =================================================

        best_df["probabilità"] = (
            best_df["probabilità"]
            .astype(str)
            .str.replace(
                ",",
                ".",
                regex=False
            )
        )

        best_df["probabilità"] = pd.to_numeric(
            best_df["probabilità"],
            errors="coerce"
        )


        # =================================================
        # ONLY INFECTED TARGETS
        # =================================================

        best_df = best_df[
            best_df["codice"].isin(
                infected_codes
            )
            &
            best_df["probabilità"].notna()
        ].copy()


        # =================================================
        # ONE ROW PER TARGET
        # =================================================

        best_df = (
            best_df
            .sort_values(
                [
                    "codice",
                    "probabilità"
                ],
                ascending=[
                    True,
                    False
                ]
            )
            .drop_duplicates(
                subset="codice",
                keep="first"
            )
            .copy()
        )


        # =================================================
        # CLASSIFY BEST INFECTOR
        # =================================================

        rows = []


        for _, row in best_df.iterrows():

            target_code = row["codice"]
            infector = row["infettore"]
            probability = row["probabilità"]


            if target_code not in code_to_idx:
                continue


            target_idx = code_to_idx[
                target_code
            ]


            # -------------------------------------------------
            # WILDLIFE
            # -------------------------------------------------

            if (
                infector is not None
                and
                infector.upper() == "WILDLIFE"
            ):

                in_same = False
                in_distance = False
                distance = None
                category = "Wildlife"


            else:

                # ---------------------------------------------
                # FIND INFECTOR INDEX
                # ---------------------------------------------

                infector_idx = code_to_idx.get(
                    infector
                )


                if infector_idx is None:

                    in_same = False
                    in_distance = False
                    distance = None
                    category = "Unmatched"


                else:

                    # -----------------------------------------
                    # SAME COMPANY?
                    # -----------------------------------------

                    in_same = (
                        infector_idx
                        in same_company[target_idx]
                    )


                    # -----------------------------------------
                    # DISTANCE?
                    # -----------------------------------------

                    in_distance = (
                        infector_idx
                        in neighbors[target_idx]
                    )


                    if in_distance:

                        distance = neighbors[
                            target_idx
                        ][infector_idx]

                    else:

                        distance = None


                    # -----------------------------------------
                    # CLASSIFICATION
                    # -----------------------------------------

                    if (
                        in_same
                        and
                        in_distance
                    ):

                        category = (
                            "Distance and same company"
                        )

                    elif (
                        in_same
                        and
                        not in_distance
                    ):

                        category = (
                            "Only same company"
                        )

                    elif (
                        not in_same
                        and
                        in_distance
                    ):

                        category = (
                            "Only distance"
                        )

                    else:

                        category = (
                            "Unmatched"
                        )


            # -------------------------------------------------
            # SAVE
            # -------------------------------------------------

            rows.append({

                "codice":
                    target_code,

                "infettore":
                    infector,

                "probabilità":
                    probability,

                "in_same_company":
                    in_same,

                "in_distance":
                    in_distance,

                "distance":
                    distance,

                "Category":
                    category
            })


        # =================================================
        # FINAL DATAFRAME
        # =================================================

        classification_df = pd.DataFrame(
            rows
        )


        # =================================================
        # SUMMARY
        # =================================================

        order = [
            "Only same company",
            "Only distance",
            "Distance and same company",
            "Wildlife",
            "Unmatched"
        ]


        counts = (
            classification_df[
                "Category"
            ]
            .value_counts()
            .reindex(
                order,
                fill_value=0
            )
        )


        # =================================================
        # PRINT CLASSIFICATION
        # =================================================

        print("\n")
        print("=" * 80)
        print(
            "BEST INFECTOR CLASSIFICATION"
        )
        print("=" * 80)


        for category in order:

            print(
                f"{category}: "
                f"{counts[category]}"
            )


        print(
            "\nTotale:"
        )

        print(
            counts.sum()
        )


        # =================================================
        # PROBABILITY CLASSES
        # =================================================

        print("\n")
        print("=" * 80)
        print(
            "BEST INFECTOR PROBABILITY"
        )
        print("=" * 80)


        summary_rows = []


        main_order = [
            "Only same company",
            "Only distance",
            "Distance and same company",
            "Wildlife"
        ]


        for category in main_order:

            subset = classification_df[
                classification_df["Category"]
                ==
                category
            ]


            n = len(subset)


            high = (
                subset["probabilità"]
                > 0.5
            ).sum()


            medium = (
                (
                    subset["probabilità"]
                    > 0.1
                )
                &
                (
                    subset["probabilità"]
                    <= 0.5
                )
            ).sum()


            low = (
                subset["probabilità"]
                <= 0.1
            ).sum()


            print(
                f"\n{category}"
            )

            print(
                f"n = {n}"
            )


            if n > 0:

                print(
                    f"High   (>0.5): "
                    f"{high} "
                    f"({100 * high / n:.1f}%)"
                )

                print(
                    f"Medium (0.1-0.5): "
                    f"{medium} "
                    f"({100 * medium / n:.1f}%)"
                )

                print(
                    f"Low    (<=0.1): "
                    f"{low} "
                    f"({100 * low / n:.1f}%)"
                )


            summary_rows.append({

                "Dominant mechanism":
                    category,

                "High":
                    high,

                "Medium":
                    medium,

                "Low":
                    low,

                "Total":
                    n
            })


        summary_df = pd.DataFrame(
            summary_rows
        )


        # =================================================
        # DEBUG 1
        # BEST INFECTOR IN SAME COMPANY
        # =================================================

        debug_same_df = (
            classification_df[
                classification_df["in_same_company"]
            ]
            .copy()
        )


        print("\n")
        print("=" * 80)
        print(
            "DEBUG 1: BEST INFECTOR IN SAME COMPANY"
        )
        print("=" * 80)


        print(
            f"Numero best infector in same company: "
            f"{len(debug_same_df)}"
        )


        if len(debug_same_df) > 0:

            print(
                "\nDi questi, quanti sono anche distance?"
            )

            print(
                debug_same_df[
                    "in_distance"
                ]
                .value_counts()
                .to_string()
            )


            print(
                "\nPrime 20:"
            )

            print(
                debug_same_df[
                    [
                        "codice",
                        "infettore",
                        "probabilità",
                        "in_same_company",
                        "in_distance",
                        "distance",
                        "Category"
                    ]
                ]
                .head(20)
                .to_string(
                    index=False
                )
            )


        # =================================================
        # DEBUG 2
        # COMPANY BUT NOT DISTANCE PAIRS
        # =================================================

        company_not_distance = []


        for target_idx in range(n_farms):

            same_set = (
                same_company[target_idx]
            )

            distance_set = set(
                neighbors[target_idx].keys()
            )


            only_company_sources = (
                same_set - distance_set
            )


            for source_idx in only_company_sources:

                company_not_distance.append({

                    "target":
                        farms.loc[
                            target_idx,
                            "codice"
                        ],

                    "source":
                        farms.loc[
                            source_idx,
                            "codice"
                        ]
                })


        company_not_distance_df = pd.DataFrame(
            company_not_distance
        )


        print("\n")
        print("=" * 80)
        print(
            "DEBUG 2: SAME COMPANY BUT NOT DISTANCE"
        )
        print("=" * 80)


        print(
            f"Numero coppie: "
            f"{len(company_not_distance_df)}"
        )


        if len(company_not_distance_df) > 0:

            print(
                "\nPrime 20 coppie:"
            )

            print(
                company_not_distance_df
                .head(20)
                .to_string(
                    index=False
                )
            )


        # =================================================
        # DEBUG 3
        # BEST INFECTOR UNMATCHED
        # =================================================

        unmatched_df = classification_df[
            classification_df["Category"]
            ==
            "Unmatched"
        ].copy()


        print("\n")
        print("=" * 80)
        print(
            "DEBUG 3: UNMATCHED"
        )
        print("=" * 80)


        print(
            f"Numero Unmatched: "
            f"{len(unmatched_df)}"
        )


        if len(unmatched_df) > 0:

            print(
                unmatched_df[
                    [
                        "codice",
                        "infettore",
                        "probabilità"
                    ]
                ]
                .head(50)
                .to_string(
                    index=False
                )
            )


        # =================================================
        # SAVE RESULTS
        # =================================================

        OUT_FILE = (
            f"best_infector_network_"
            f"classification_"
            f"gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        with pd.ExcelWriter(
            OUT_FILE
        ) as writer:

            classification_df.to_excel(
                writer,
                sheet_name="Classification",
                index=False
            )

            summary_df.to_excel(
                writer,
                sheet_name="Summary",
                index=False
            )
