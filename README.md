# Transmission Network Reconstruction for HPAI Outbreaks

This repository contains the Python implementation of the transmission model presented in *[paper title]*.

Because the original epidemiological and genetic data are subject to confidentiality restrictions, they are **not included** in this repository. Instead, synthetic datasets reproducing the structure of the original files are provided, allowing the complete workflow to be executed without access to the real data.

The repository reproduces the full analysis pipeline, from network construction and parameter estimation to transmission attribution, genetic validation, and epidemic visualization.

---

# Synthetic datasets

Three synthetic input files are included.

| File | Description |
|------|-------------|
| `fattorie.xlsx` | Synthetic farm-level dataset containing farm identifiers, geographic coordinates, company membership, and confirmation dates. |
| `date_culling.csv` | Synthetic culling dates for infected farms. |
| `mat_diff_basi.csv` | Synthetic pairwise genetic distance matrix between infected farms. |

These datasets preserve the same structure, variable names, and formats as the original data but contain no real epidemiological information.

---

# Workflow

The complete workflow consists of seven scripts that should be executed sequentially.

---

# 1. Create transmission networks

**Script**

`1_Create_Networks.py`

### Purpose

Constructs the static transmission networks used throughout the analysis.

Two possible transmission mechanisms are represented:

- Same company
- Spatial neighborhood

### Input

- `fattorie.xlsx`

### Parameters

```python
DMAX_VALUES = [1.5, 2.0]
```

where `DMAX_VALUES` defines the maximum neighborhood distance (km).

### Output

- `same_company.xlsx`
- `neighbors_dmax1.5.xlsx`
- `neighbors_dmax2.0.xlsx`

---

# 2. Parameter estimation

**Script**

`2_Codice_Stima.py`

### Purpose

Estimates the transmission model parameters by maximum likelihood while jointly reconstructing latent exposure dates using an iterative EM-like algorithm.

The estimation is repeated using multiple random initializations.

### Input

- `fattorie.xlsx`
- `same_company.xlsx`
- `neighbors_dmaxX.xlsx`

### Main parameters

```python
GAMMA_VALUES = [1/5, 1/10]
DMAX_VALUES = [1.5, 2.0]
SEEDS = range(100,200)
```

Additional configurable parameters include

- `MAX_ITER`
- `RANGE_DAYS`
- `DAYS_INFECTIOUS`
- `L_CONST`

### Output

For each parameter combination:

- estimated exposure dates
- optimization log
- estimated model parameters

Final summary:

- `risultati_completi.xlsx`

---

# 3. Transmission probability matrix

**Script**

`3_Parametri_Medi_e_Matrice.py`

### Purpose

Computes the transmission probability matrix using the median estimated model parameters and identifies the most likely infector for each infected farm.

### Input

- `risultati_completi.xlsx`
- `fattorie.xlsx`
- `same_company.xlsx`
- `neighbors_dmaxX.xlsx`
- all `E_results_...xlsx`

### Parameters

```python
GAMMA_VALUES
DMAX_VALUES
L_CONST
```

### Output

For each parameter combination:

- transmission probability matrix
- estimated exposure dates
- most likely infector table
- summary statistics

Main files:

- `matrice_gamma...xlsx`
- `date_gamma...xlsx`
- `best_infector_gamma...xlsx`

---

# 4. Dominant transmission mechanisms

**Script**

`4_Dominant_Transmission_Mechanisms.py`

### Purpose

Computes the relative contribution of each transmission mechanism (wildlife, same company, neighborhood) for every infected farm and identifies the dominant mechanism.

### Input

- `fattorie.xlsx`
- `risultati_completi.xlsx`
- `date_gamma...xlsx`
- `best_infector_gamma...xlsx`
- network files

### Parameters

```python
GAMMA_VALUES
DMAX_VALUES
```

### Output

- dominant transmission classification
- summary tables
- stacked bar plots

---

# 5. Genetic validation

**Script**

`5_Confronto_Matrice_Genetica.py`

### Purpose

Compares inferred transmission probabilities with pairwise genetic distances to evaluate whether genetically similar farms are associated with higher transmission probabilities.

The script also computes summary statistics for inferred infectors and performs non-parametric statistical tests.

### Input

- `mat_diff_basi.csv`
- `matrice_gamma...xlsx`
- `best_infector_gamma...xlsx`

### Parameters

```python
GAMMA_VALUES
DMAX_VALUES
```

### Output

- statistical summaries
- boxplots
- hypothesis test results

---

# 6. Source attribution uncertainty

**Script**

`6_Gap_Best_Infector.py`

### Purpose

Quantifies uncertainty in source attribution by comparing the highest and second-highest transmission probabilities assigned to each farm.

### Input

- `matrice_gamma...xlsx`

### Parameters

```python
GAMMA_VALUES
DMAX_VALUES
```

### Output

- uncertainty statistics
- gap distributions
- histograms

---

# 7. Epidemic visualization

**Script**

`7_Visualization.py`

### Purpose

Produces an animated reconstruction of the epidemic.

Each newly infected farm is connected only to its most likely inferred transmission source.

### Input

- `fattorie.xlsx`
- `date_culling.csv`
- `date_gamma...xlsx`
- `best_infector_gamma...xlsx`
- `same_company.xlsx`
- `neighbors_dmaxX.xlsx`

### Parameters

```python
TARGET_GAMMA
DMAX_VALUES
```

### Output

For each spatial scenario:

- animation frames
- MP4 video

---

# Running the pipeline

The scripts should be executed in the following order:

1. `1_Create_Networks.py`
2. `2_Codice_Stima.py`
3. `3_Parametri_Medi_e_Matrice.py`
4. `4_Dominant_Transmission_Mechanisms.py`
5. `5_Confronto_Matrice_Genetica.py`
6. `6_Gap_Best_Infector.py`
7. `7_Visualization.py`

---

# Configurable model parameters

The analyses can be repeated under different epidemiological assumptions by modifying:

- `GAMMA_VALUES` (infectiousness decay parameter)
- `DMAX_VALUES` (maximum neighborhood distance)
- `SEEDS` (random initializations)
- `L_CONST`
- `RANGE_DAYS`
- `DAYS_INFECTIOUS`

Different combinations automatically generate independent sets of output files.
