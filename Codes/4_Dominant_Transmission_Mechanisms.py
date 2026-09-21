# -*- coding: utf-8 -*-
"""
Classification of the dominant transmission mechanism of infection.

For each infected farm j, possible source farms are first divided into:

    Only same company:
        farms belonging to the company network but not to the distance network

    Only distance:
        farms belonging to the distance network but not to the company network

    Distance and same company:
        farms belonging to both networks

    Wildlife:
        contribution from sources not explicitly represented in the farm
        networks

The contribution of a source belonging to both networks includes both
its company-mediated and distance-mediated contributions.

The dominant mechanism is the mechanism with the largest total contribution.

"""

import pandas as pd
import numpy as np


# =========================================================
# INPUT
# =========================================================

FARMS_FILE = "fattorie.xlsx"
RESULTS_FILE = "risultati_completi.xlsx"
SAME_FILE = "same_company.xlsx"

L_CONST = 1e3

GAMMAS = [0.100, 0.200]
DMAX_VALUES = [1.5, 2.0]

# Probability thresholds
HIGH_THRESHOLD = 0.50
LOW_THRESHOLD = 0.10


# =========================================================
# FUNCTION TO CLEAN FARM CODES
# =========================================================

def clean_code(x):

    if pd.isna(x):
        return None

    return str(x).strip()


# =========================================================
# LOOP OVER PARAMETER COMBINATIONS
# =========================================================

for TARGET_GAMMA in GAMMAS:

    for TARGET_DMAX in DMAX_VALUES:

        print(f"\nRunning analysis with gamma = {TARGET_GAMMA} day^-1 and dmax = {TARGET_DMAX} km")
        # =================================================
        # FILE NAMES
        # =================================================

        DATES_FILE = (
            f"date_gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )

        NEIGHBOR_FILE = (
            f"neighbors_dmax{TARGET_DMAX}.xlsx"
        )


        # =================================================
        # LOAD DATA
        # =================================================

        farms = pd.read_excel(
            FARMS_FILE
        )

        dates = pd.read_excel(
            DATES_FILE
        )

        results_df = pd.read_excel(
            RESULTS_FILE
        )

        same_df = pd.read_excel(
            SAME_FILE
        )

        neighbors_df = pd.read_excel(
            NEIGHBOR_FILE
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
        # MERGE DATES
        # =================================================

        farms = farms.merge(
            dates[
                ["codice", "E", "D"]
            ],
            on="codice",
            how="left"
        )


        # =================================================
        # ONLY INFECTED FARMS
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

        if n_farms == 0:
            continue


        # =================================================
        # TIME
        # =================================================

        t_start = farms["E"].min()
        t_end = farms["D"].max()

        n_days = (
            t_end - t_start
        ).days + 1

        farms["E_days"] = (
            farms["E"] - t_start
        ).dt.days.astype(int)

        farms["D_days"] = (
            farms["D"] - t_start
        ).dt.days.astype(int)

        E_arr = farms["E_days"].values
        D_arr = farms["D_days"].values


        # =================================================
        # CODE -> INDEX
        # =================================================

        codes = farms["codice"].tolist()

        code_to_idx = {
            code: idx
            for idx, code in enumerate(codes)
        }

        infected_codes = set(codes)


        # =================================================
        # MODEL PARAMETERS
        # =================================================

        subset = results_df[
            (results_df["gamma"] == TARGET_GAMMA)
            &
            (results_df["d_max"] == TARGET_DMAX)
        ]

        if subset.empty:
            continue

        params = subset[
            [
                "beta_w",
                "beta_c",
                "beta_d",
                "alpha"
            ]
        ].median()

        beta_w = params["beta_w"]
        beta_c = params["beta_c"]
        beta_d = params["beta_d"]
        alpha = params["alpha"]


        # =================================================
        # SAME COMPANY NETWORK
        # =================================================
        #
        # from_code = target farm
        # to_code   = possible source farm
        # =================================================

        same_company = {
            j: []
            for j in range(n_farms)
        }

        for _, row in same_df.iterrows():

            target = row["from_code"]
            source = row["to_code"]

            if (
                target in infected_codes
                and
                source in infected_codes
            ):

                j = code_to_idx[target]
                k = code_to_idx[source]

                same_company[j].append(k)


        # =================================================
        # DISTANCE NETWORK
        # =================================================

        neighbors = {
            j: []
            for j in range(n_farms)
        }

        for _, row in neighbors_df.iterrows():

            target = row["from_code"]
            source = row["to_code"]
            distance = row["distance"]

            if (
                target in infected_codes
                and
                source in infected_codes
            ):

                j = code_to_idx[target]
                k = code_to_idx[source]

                neighbors[j].append(
                    (k, distance)
                )


        # =================================================
        # PHI
        # =================================================

        def phi_cache_array(max_s):

            s = np.arange(
                max_s + 1
            )

            out = (
                TARGET_GAMMA
                *
                np.exp(
                    -TARGET_GAMMA * s
                )
            )

            out[s <= 0] = 0

            return out


        max_s = (
            int(
                D_arr.max()
                -
                E_arr.min()
            )
            + 5
        )

        phi_cache = phi_cache_array(
            max_s
        )


        phi_matrix = np.zeros(
            (
                n_farms,
                n_days
            )
        )


        for k in range(n_farms):

            for t in range(
                E_arr[k] + 1,
                D_arr[k] + 1
            ):

                s = (
                    D_arr[k] - t
                )

                if s >= 0:

                    phi_matrix[
                        k,
                        t
                    ] = phi_cache[s]


        # =================================================
        # COMPUTE CONTRIBUTIONS
        # =================================================

        rows = []


        for j in range(n_farms):

            Ej = E_arr[j]


            # =================================================
            # 1. IDENTIFY NETWORK MEMBERSHIP FIRST
            # =================================================

            company_sources = set(
                same_company[j]
            )

            distance_sources = {
                k
                for k, d in neighbors[j]
            }


            # Sources belonging to each of the three
            # mutually exclusive network categories

            only_company_sources = (
                company_sources
                -
                distance_sources
            )

            only_distance_sources = (
                distance_sources
                -
                company_sources
            )

            both_sources = (
                company_sources
                &
                distance_sources
            )


            # Distance associated with each source
            distance_dict = {
                k: d
                for k, d in neighbors[j]
            }


            # =================================================
            # 2. ONLY COMPANY CONTRIBUTION
            # =================================================

            lambda_only_company = 0.0

            for k in only_company_sources:

                lambda_only_company += (
                    beta_c
                    *
                    phi_matrix[
                        k,
                        Ej
                    ]
                )


            # =================================================
            # 3. ONLY DISTANCE CONTRIBUTION
            # =================================================

            lambda_only_distance = 0.0

            for k in only_distance_sources:

                d = distance_dict[k]

                weight = (
                    1.0
                    /
                    (
                        1.0
                        +
                        L_CONST
                        *
                        (
                            d
                            /
                            TARGET_DMAX
                        ) ** alpha
                    )
                )

                lambda_only_distance += (
                    beta_d
                    *
                    weight
                    *
                    phi_matrix[
                        k,
                        Ej
                    ]
                )


            # =================================================
            # 4. BOTH COMPANY AND DISTANCE CONTRIBUTION
            # =================================================
            #
            # For a source in both networks, both components
            # contribute to the total force of infection.
            # =================================================

            lambda_both = 0.0

            for k in both_sources:

                # Company component
                company_contribution = (
                    beta_c
                    *
                    phi_matrix[
                        k,
                        Ej
                    ]
                )

                # Distance component
                d = distance_dict[k]

                weight = (
                    1.0
                    /
                    (
                        1.0
                        +
                        L_CONST
                        *
                        (
                            d
                            /
                            TARGET_DMAX
                        ) ** alpha
                    )
                )

                distance_contribution = (
                    beta_d
                    *
                    weight
                    *
                    phi_matrix[
                        k,
                        Ej
                    ]
                )

                lambda_both += (
                    company_contribution
                    +
                    distance_contribution
                )


            # =================================================
            # 5. WILDLIFE CONTRIBUTION
            # =================================================

            lambda_wildlife = beta_w


            # =================================================
            # 6. TOTAL FORCE OF INFECTION
            # =================================================

            total = (
                lambda_wildlife
                +
                lambda_only_company
                +
                lambda_only_distance
                +
                lambda_both
            )


            # =================================================
            # 7. PROBABILITIES
            # =================================================

            if total == 0:

                p_wildlife = 1.0
                p_only_company = 0.0
                p_only_distance = 0.0
                p_both = 0.0

            else:

                p_wildlife = (
                    lambda_wildlife
                    /
                    total
                )

                p_only_company = (
                    lambda_only_company
                    /
                    total
                )

                p_only_distance = (
                    lambda_only_distance
                    /
                    total
                )

                p_both = (
                    lambda_both
                    /
                    total
                )


            # Safety check
            probability_sum = (
                p_wildlife
                +
                p_only_company
                +
                p_only_distance
                +
                p_both
            )

            if not np.isclose(
                probability_sum,
                1.0
            ):
                raise ValueError(
                    "Probabilities do not sum to 1."
                )


            # =================================================
            # 8. DOMINANT MECHANISM
            # =================================================

            values = {

                "Wildlife":
                    p_wildlife,

                "Only same company":
                    p_only_company,

                "Only distance":
                    p_only_distance,

                "Distance and same company":
                    p_both
            }


            dominant = max(
                values,
                key=values.get
            )

            dominant_probability = (
                values[dominant]
            )


            # =================================================
            # 9. SECOND LARGEST PROBABILITY
            # =================================================

            sorted_probabilities = sorted(
                values.values(),
                reverse=True
            )

            second_probability = (
                sorted_probabilities[1]
            )


            # =================================================
            # 10. DOMINANCE MARGIN
            # =================================================

            dominance_margin = (
                dominant_probability
                -
                second_probability
            )


            # =================================================
            # 11. HIGH / MEDIUM / LOW
            # =================================================

            if dominant_probability > HIGH_THRESHOLD:

                probability_class = "High"

            elif dominant_probability > LOW_THRESHOLD:

                probability_class = "Medium"

            else:

                probability_class = "Low"


            # =================================================
            # 12. SAVE
            # =================================================

            rows.append({

                "codice":
                    farms.loc[
                        j,
                        "codice"
                    ],

                # Lambda contributions
                "lambda_Wildlife":
                    lambda_wildlife,

                "lambda_Only_company":
                    lambda_only_company,

                "lambda_Only_distance":
                    lambda_only_distance,

                "lambda_Both":
                    lambda_both,

                # Probabilities
                "p_Wildlife":
                    p_wildlife,

                "p_Only_company":
                    p_only_company,

                "p_Only_distance":
                    p_only_distance,

                "p_Both":
                    p_both,

                # Dominant mechanism
                "Dominant_mechanism":
                    dominant,

                "Dominant_probability":
                    dominant_probability,

                "Second_probability":
                    second_probability,

                "Dominance_margin":
                    dominance_margin,

                "Probability_class":
                    probability_class,

                # Network sizes
                "n_company_sources":
                    len(company_sources),

                "n_distance_sources":
                    len(distance_sources),

                "n_only_company_sources":
                    len(only_company_sources),

                "n_only_distance_sources":
                    len(only_distance_sources),

                "n_both_sources":
                    len(both_sources)
            })


        # =================================================
        # DATAFRAME
        # =================================================

        dominant_df = pd.DataFrame(
            rows
        )


        # =================================================
        # SUMMARY TABLE
        # =================================================

        category_order = [
            "Only same company",
            "Only distance",
            "Distance and same company",
            "Wildlife"
        ]

        summary_rows = []


        for category in category_order:

            subset_cat = dominant_df[
                dominant_df["Dominant_mechanism"]
                ==
                category
            ]

            n = len(subset_cat)

            high = (
                subset_cat[
                    "Dominant_probability"
                ]
                >
                HIGH_THRESHOLD
            ).sum()

            medium = (
                (
                    subset_cat[
                        "Dominant_probability"
                    ]
                    >
                    LOW_THRESHOLD
                )
                &
                (
                    subset_cat[
                        "Dominant_probability"
                    ]
                    <=
                    HIGH_THRESHOLD
                )
            ).sum()

            low = (
                subset_cat[
                    "Dominant_probability"
                ]
                <=
                LOW_THRESHOLD
            ).sum()

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

        print("\n" + "=" * 70)
        print(f"SUMMARY — gamma = {TARGET_GAMMA} day^-1, dmax = {TARGET_DMAX} km")
        print("=" * 70)
        print(summary_df.to_string(index=False))
        # =================================================
        # SAVE
        # =================================================

        OUT_FILE = (
            f"dominant_source_"
            f"classification_"
            f"gamma{TARGET_GAMMA:.3f}_"
            f"dmax{TARGET_DMAX}.xlsx"
        )


        with pd.ExcelWriter(
            OUT_FILE
        ) as writer:

            dominant_df.to_excel(
                writer,
                sheet_name="Classification",
                index=False
            )

            summary_df.to_excel(
                writer,
                sheet_name="Summary_4way",
                index=False
            )