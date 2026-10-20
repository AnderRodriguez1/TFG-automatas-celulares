# Greenberg–Hastings: activity, survival and bootstrap analysis

These scripts analyse the original Greenberg–Hastings simulation CSVs. They do not run new cellular-automaton simulations and do not require a GPU. They support the activity, survival, conditional-activity and model-comparison analyses in the manuscript.

This README documents the additional analysis scripts. The repository's existing simulation and plotting instructions remain applicable to the other studies.

## 1. Requirements

Use a Python 3 environment with NumPy, SciPy, Matplotlib and PySide6. Alternatively, activate the environment.yml for easier use:

```bash
python -m pip install numpy scipy matplotlib PySide6
```

`gh_summarize_csv.py` uses the Python standard library and PySide6. The other scripts additionally require NumPy and Matplotlib; the final-figure and bootstrap scripts also require SciPy. Record the Python and package versions used for the release, since numerical optimization can depend on the software environment. The commands above install dependencies but do not specify a historically validated environment.

## 2. Files and inputs

Keep these four scripts together in an analysis directory. Use the filename `gh_summarize_csv.py` (remove any download suffix such as `(1)`).

| Script | Purpose | Input |
| --- | --- | --- |
| `gh_summarize_csv.py` | Summarize each simulation and record integrity diagnostics. | Original simulation CSVs. |
| `refractory_period_analysis.py` | Generate the final activity and survival/conditional-activity figures. | `gh_simulation_summary.csv`. |
| `bootstrap_analysis.py` | Compare reduced and exponential activity models; profile the fitted endpoint. | `gh_simulation_summary.csv`. |
| `reconstruct_activity_curve.py` | Generate additional diagnostic tables and plots, including the survival-product residual. | `gh_simulation_summary.csv`. |

The raw files must contain the columns:

```text
Step, Active_cells, Refractory_cells, Resting_cells
```

Simulation parameters and realization identifiers are read from filenames such as:

```text
GH_size500x500_density15_refr29_run2.csv
```

The final-figure and bootstrap analyses select the campaign directory `CSVs_GH_densidad_15`, with a 500 × 500 lattice and initial excited-site probability 0.15. Preserve the campaign directory names and the original filenames.

**The data root passed to the summarizer must be the parent directory containing the campaign folders**, rather than `CSVs_GH_densidad_15` itself. The downstream scripts identify the campaign using the first component of the relative `source_file` path.

For the commands below, assume the scripts are in an analysis directory and its sibling directory `data` contains `CSVs_GH_densidad_15` and any other campaigns to be analysed. Replace `../data` with the actual data-root path if necessary. Quote paths containing spaces. Keep generated analysis CSVs outside the raw-data root: the summarizer recursively scans CSV files under that root.

## 3. Generate the simulation summary

Run all commands from the directory containing the analysis scripts:

```bash
python gh_summarize_csv.py "../data" --output gh_simulation_summary.csv --late-window 100 --checkpoints 1000 2000
```

The summary contains one row per successfully processed simulation, including:

- Activity averaged over the final 100 recorded rows, expressed as an excited-site fraction.
- Survival at the requested observation checkpoints and at the end of the file.
- Extinction time, when observed, and whether the final averaging window contains only zeros.
- Checks for discontinuous step labels, inconsistent cell totals and reactivation after zero activity.

The script interprets `Step = 0` as the first post-update state, so 2000 completed updates correspond to `Step = 1999`. This convention must match the simulation exporter. Missing checkpoints are left blank; shorter records are not extrapolated. The late-time average always uses the end of each file, so records used for a stated observation time must end at that time.

Check the processed-file count and any reported errors. The summary itself records integrity diagnostics that must also be inspected; successfully reading a CSV does not guarantee that all its checks passed.

## 4. Generate the manuscript figures

```bash
python refractory_period_analysis.py
```

The script selects `CSVs_GH_densidad_15` and uses survival after 2000 updates. Outputs are written to `figures_final/`:

- `activity_with_fit.png` and `.pdf`
- `survival_and_cycle_length.png` and `.pdf`

Activity error bars use the standard deviation across realizations with `ddof=0`. Survival intervals are 95% Wilson intervals. Conditional activity is the mean late-time activity among realizations surviving at 2000 updates; it is undefined when no realization survives. The effective timescale is the reciprocal of this conditional mean, and the plotted deviation is measured relative to `R + 1`.

For the displayed descriptive activity curve, the script fixes `R_fit = 34.8`, `tau = 0.62` and `beta = 0.79`, and refits only the amplitude `A` using sampled values with `R < 34.8`. The fitted amplitude is printed to the terminal. This is not a new four-parameter fit.

The shaded interval in the conditional-activity panel is `R = 11–15`. Figure dimensions, colours and typography can be changed without changing the numerical analysis. Some console messages retain older figure names; the output filenames listed above are the actual save targets.

## 5. Bootstrap comparison

### AICc correction for the release

The corrected version of `bootstrap_analysis.py` must count the estimated residual variance in addition to the fitted curve parameters. Inside `run_bootstrap`, use:

```python
k_m0 = len(popt_m0) + 1  # 4 curve parameters + residual variance
k_m1 = len(popt_m1) + 1  # 5 curve parameters + residual variance
```

The `compute_aicc` function is unchanged. Preserve the earlier calculation in version history; outputs made with the original counts of 4 and 5 are not the corrected AICc results.

### Execution and settings

```bash
python bootstrap_analysis.py
```

The script requires exactly ten realizations at each integer `R` from 1 to 40 in `CSVs_GH_densidad_15`. It resamples the ten realization-level late-time activities with replacement independently within each `R`, calculates the resampled mean curve, and fits both models by unweighted nonlinear least squares with multiple starting points.

- Reduced model: `A * R**(-tau) * (R_fit - R)**beta` for `R < R_fit`, zero otherwise.
- Extended model: the same positive branch multiplied by `exp(-c * R)`.
- Bounds: `0 <= A <= 10`, `15 <= R_fit <= 40`, `0 <= tau, beta <= 2`, and `0 <= c <= 0.1`.
- Validation batch: 200 resamples, random seed `20260827`.
- Final batch: 200 separate resamples, random seed `20260828`.
- Reported comparison: `Delta AICc = AICc_extended - AICc_reduced`, using 40 mean-activity observations and parameter counts 6 and 5, respectively.

The comment about increasing the final batch to 2000 is historical: the supplied configuration uses **200 final resamples**, not 2000. The validation and final batches must not be combined when reporting the final 200-replicate results.

The extended-model fit includes a starting point derived from the reduced fit with `c = 0`. Fit failures and violations of the expected nested-model RSS ordering are recorded. The script also evaluates RSS profiles at fixed endpoint values. It writes the following files in `bootstrap_analysis/`:

- `bootstrap_results_validation.csv` and `bootstrap_results_final.csv`
- `bootstrap_failures_validation.csv` and `bootstrap_failures_final.csv`
- `bootstrap_delta_aicc.png`
- `R_fit_profile.csv` and `R_fit_profile.png`

An empty failure file means no failures were logged. Inspect the reported number of successful replicates. Running the script again overwrites these outputs, so retain historical outputs separately if needed.

This is a provisional sensitivity comparison. The RSS-based criterion uses a working Gaussian, common-variance error model, whereas the uncertainty of the ensemble means varies across `R`. Bootstrap comparison frequencies are not probabilities that either model is true.

## 6. Optional reconstruction and final-window diagnostic

`reconstruct_activity_curve.py` is independent of the final-figure and bootstrap scripts. In the supplied historical copy it selects:

```python
TARGET_CAMPAIGN = "CSVs_GH_500_multiple"
OUTPUT_PREFIX = "L500_rho015_multiple"
```

These settings reproduce the alternative-campaign diagnostic. To analyse the manuscript campaign instead, select:

```python
TARGET_CAMPAIGN = "CSVs_GH_densidad_15"
OUTPUT_PREFIX = "L500_rho015"
```

Then run:

```bash
python reconstruct_activity_curve.py
```

The script saves activity and survival-decomposition CSVs plus full-range and crossover diagnostic plots using the selected prefix. Its `residual` column is:

```text
mean_activity - survival_probability * conditional_mean_activity
```

Here activity is averaged over the last 100 recorded updates, while survival is evaluated at update 2000. A realization that becomes extinct during that window can still contribute positive average activity. The residual measures this extinct-realization contribution; the product identity alone is applicable only when that contribution vanishes, up to numerical precision. The script prints the maximum absolute residual and compares it with `1e-9`.

Changing the diagnostic campaign does not change the campaign selected by `refractory_period_analysis.py` or `bootstrap_analysis.py`. Ensure that the summary contains the requested campaign, that survival checkpoints are present, and that the record endpoints match the intended observation time.

## 7. Release contents

Include these scripts, this README and the original input data (or their documented location). Intermediate summaries, numerical outputs and figures can be regenerated; they need not be duplicated in the release when the complete input data and workflow are available. Record any numerical changes made to other analysis scripts, including the existing `graphs.py`, if those changes are needed to reproduce the manuscript's reported results.

After incorporating the corrected analysis code, identify the release tag and corresponding commit in the manuscript's data-and-code availability statement.
