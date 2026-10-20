"""
Reconstruct activity curve for L=500, rho0=0.15 from the original campaign.
Outputs:
- activity_curve.csv : per-R mean and std (population and sample)
- survival_decomposition.csv : survival with Wilson CIs, conditional activity
- activity_curve_full.png : full-range validation figure
- activity_curve_crossover.png : crossover-focused figure (R=18 to 34)
"""

import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# CONFIGURATION
# ============================================================
_HERE = Path(__file__).resolve().parent
SUMMARY_FILE = _HERE / "gh_simulation_summary.csv"
OUTPUT_DIR = _HERE / "figures_final"
#OUTPUT_PREFIX = "L500_rho015"
OUTPUT_PREFIX = "L500_rho015_multiple"

# Target parameters
TARGET_L = 500
TARGET_RHO = 0.15

# Original campaign used for the figure
#TARGET_CAMPAIGN = "CSVs_GH_densidad_15"
TARGET_CAMPAIGN = "CSVs_GH_500_multiple"

# Column for activity fraction
ACTIVITY_COL = "late_mean_active_fraction"
SURVIVAL_COL = "survived_after_2000_updates"

# Crossover range for focused plot
CROSSOVER_R_MIN = 18
CROSSOVER_R_MAX = 34

# ============================================================
# WILSON CONFIDENCE INTERVAL
# ============================================================
def wilson_interval(n_success, n_total):
    """Wilson score interval for binomial proportion, clamped to [0,1]."""
    if n_total == 0:
        return np.nan, np.nan
    p = n_success / n_total
    z = 1.96  # 95% CI
    denominator = 1 + z**2 / n_total
    center = p + z**2 / (2 * n_total)
    half_width = z * math.sqrt(p * (1 - p) / n_total + z**2 / (4 * n_total**2))
    low = (center - half_width) / denominator
    high = (center + half_width) / denominator
    return max(0.0, low), min(1.0, high)

# ============================================================
# LOAD DATA
# ============================================================
if not SUMMARY_FILE.exists():
    raise FileNotFoundError(f"Summary file not found: {SUMMARY_FILE}")

rows_by_R = defaultdict(list)

with open(SUMMARY_FILE, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            L = int(row["grid_width"])
            rho = float(row["initial_density"])
            R = int(row["refractory_parameter"])
            if int(row["grid_height"]) != L:
                continue
        except (ValueError, TypeError):
            continue

        if L != TARGET_L or abs(rho - TARGET_RHO) > 1e-9:
            continue

        source = row.get("source_file", "").replace("\\", "/")
        campaign = source.split("/", 1)[0]
        if campaign != TARGET_CAMPAIGN:
            continue

        run_str = row.get("run", "")
        if run_str == "":
            continue

        act_str = row.get(ACTIVITY_COL, "")
        if act_str == "":
            continue
        try:
            activity = float(act_str)
        except ValueError:
            continue

        surv_str = row.get(SURVIVAL_COL, "")
        if surv_str == "":
            continue
        try:
            survived = int(surv_str)
        except ValueError:
            continue

        rows_by_R[R].append((activity, survived))

R_values = sorted(rows_by_R.keys())

print(f"Found {len(R_values)} R values for L={TARGET_L}, rho={TARGET_RHO}")
print(f"Campaign: {TARGET_CAMPAIGN}")

# ============================================================
# COMPUTE STATISTICS PER R
# ============================================================
output_rows = []
survival_rows = []

for R in R_values:
    acts = [a for a, s in rows_by_R[R]]
    survs = [s for a, s in rows_by_R[R]]
    n = len(acts)
    if n == 0:
        continue

    # --- Activity ---
    mean_act = np.mean(acts)
    population_sigma = np.std(acts, ddof=0)
    sample_sd = np.std(acts, ddof=1) if n > 1 else 0.0
    sem = sample_sd / math.sqrt(n) if n > 1 else 0.0

    # --- Survival ---
    n_surv = sum(survs)
    surv_prob = n_surv / n
    ci_low, ci_high = wilson_interval(n_surv, n)

    # --- Conditional activity ---
    cond_acts = [a for a, s in zip(acts, survs) if s == 1]
    if cond_acts:
        cond_mean = np.mean(cond_acts)
        if len(cond_acts) > 1:
            cond_sd = np.std(cond_acts, ddof=1)
            cond_sem = cond_sd / math.sqrt(len(cond_acts))
        else:
            cond_sd = np.nan
            cond_sem = np.nan
    else:
        cond_mean = np.nan
        cond_sd = np.nan
        cond_sem = np.nan

    # --- Candidate relation ---
    cand_val = 1.0 / (2 * (R // 2 + 1))

    # --- Decomposition ---
    if n_surv == 0:
        decomposed = 0.0
    else:
        decomposed = surv_prob * cond_mean
    residual = mean_act - decomposed

    output_rows.append({
        "R": R,
        "N_real": n,
        "mean_activity": mean_act,
        "population_sigma": population_sigma,
        "sample_sd": sample_sd,
        "sem": sem,
    })

    survival_rows.append({
        "R": R,
        "N_real": n,
        "N_surv": n_surv,
        "survival_probability": surv_prob,
        "survival_CI_low": ci_low,
        "survival_CI_high": ci_high,
        "cond_mean_activity": cond_mean,
        "cond_sd_activity": cond_sd,
        "cond_sem_activity": cond_sem,
        "candidate_relation": cand_val,
        "residual": residual,
    })

# ============================================================
# SAVE CSVs
# ============================================================
ACTIVITY_CSV = _HERE / f"{OUTPUT_PREFIX}_activity_curve.csv"
with open(ACTIVITY_CSV, "w", newline="", encoding="utf-8") as f:
    fieldnames = ["R", "N_real", "mean_activity", "population_sigma", "sample_sd", "sem"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in output_rows:
        writer.writerow({k: row[k] for k in fieldnames})
print(f"Activity curve saved to: {ACTIVITY_CSV}")

SURV_CSV = _HERE / f"{OUTPUT_PREFIX}_survival_decomposition.csv"
with open(SURV_CSV, "w", newline="", encoding="utf-8") as f:
    fieldnames = ["R", "N_real", "N_surv", "survival_probability",
                  "survival_CI_low", "survival_CI_high",
                  "cond_mean_activity", "cond_sd_activity", "cond_sem_activity",
                  "candidate_relation", "residual"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for row in survival_rows:
        writer.writerow({k: row[k] for k in fieldnames})
print(f"Survival decomposition saved to: {SURV_CSV}")

# ============================================================
# PLOTTING FUNCTION
# ============================================================
def make_plot(Rs, output_rows, survival_rows, title_suffix, xlim=None, filename_suffix="", show_candidate=False):
    # Subset data if xlim is provided
    if xlim is not None:
        keep = [i for i, r in enumerate(Rs) if xlim[0] <= r <= xlim[1]]
        if not keep:
            print(f"Warning: No data points in xlim {xlim}")
            return
        Rs = [Rs[i] for i in keep]
        output_rows = [output_rows[i] for i in keep]
        survival_rows = [survival_rows[i] for i in keep]

    fig, axes = plt.subplots(3, 1, figsize=(8, 12), sharex=True)

    means = [row["mean_activity"] for row in output_rows]
    sigmas = [row["population_sigma"] for row in output_rows]
    Rs_array = np.asarray(Rs)

    # Panel 1: Activity
    ax = axes[0]
    ax.errorbar(Rs, means, yerr=sigmas, fmt='o-', capsize=4, color='blue',
                label=r'$\langle \rho \rangle \pm \sigma$ (ddof=0)')
    ax.set_ylabel('Active fraction')
    ax.set_title(f'Activity vs R (L={TARGET_L}, ρ₀={TARGET_RHO}) {title_suffix}')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend()
    if xlim:
        ax.set_xlim(xlim)

    # Panel 2: Survival
    ax = axes[1]
    surv_probs = [row["survival_probability"] for row in survival_rows]
    ci_lows = [row["survival_CI_low"] for row in survival_rows]
    ci_highs = [row["survival_CI_high"] for row in survival_rows]

    ax.errorbar(Rs, surv_probs,
                yerr=[np.array(surv_probs)-np.array(ci_lows),
                      np.array(ci_highs)-np.array(surv_probs)],
                fmt='s-', capsize=4, color='red',
                label='Survival probability (Wilson 95% CI)')
    ax.set_ylabel(r'$P_{\rm surv}$')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend()
    if xlim:
        ax.set_xlim(xlim)
    ax.set_ylim(-0.05, 1.05)

    # Panel 3: Conditional activity
    ax = axes[2]
    cond_means = np.asarray([row["cond_mean_activity"] for row in survival_rows], dtype=float)
    cond_sds = np.asarray([row["cond_sd_activity"] for row in survival_rows], dtype=float)
    candidate_vals = np.asarray([row["candidate_relation"] for row in survival_rows], dtype=float)

    # Main line connecting conditional means
    ax.plot(Rs_array, cond_means, "d-", color="green", markersize=6,
            label=r"$\langle\rho\mid\mathrm{survival}\rangle$")

    # Error bars where SD is defined (N_surv > 1)
    has_sd = np.isfinite(cond_sds)
    if np.any(has_sd):
        ax.errorbar(Rs_array[has_sd], cond_means[has_sd],
                    yerr=cond_sds[has_sd], fmt="none", capsize=4, color="green",
                    label="Sample SD among survivors")

    # Candidate relation (only on crossover plot and where data support it)
    if show_candidate and xlim is not None:
        # Only show candidate relation up to R=34 where we have surviving realizations
        mask_candidate = Rs_array <= 34
        if np.any(mask_candidate):
            ax.plot(Rs_array[mask_candidate], candidate_vals[mask_candidate],
                    "k--", linewidth=1.5, alpha=0.6,
                    label=r'$[2(\lfloor R/2 \rfloor+1)]^{-1}$ (candidate diagnostic)')

    ax.set_xlabel('Refractory period R')
    ax.set_ylabel(r'$\langle \rho \mid {\rm survival} \rangle$')
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend()
    if xlim:
        ax.set_xlim(xlim)

    plt.tight_layout()
    plot_file = Path(f"{OUTPUT_PREFIX}_activity_curve{filename_suffix}.png")
    plt.savefig(plot_file, dpi=150)
    plt.close()
    print(f"Plot saved to: {plot_file}")

# ============================================================
# GENERATE PLOTS
# ============================================================
Rs_vals = [row["R"] for row in output_rows]

# Full-range plot (no candidate relation)
make_plot(Rs_vals, output_rows, survival_rows,
          title_suffix="(full range)", xlim=None,
          filename_suffix="_full", show_candidate=False)

# Crossover-focused plot (with candidate relation)
make_plot(Rs_vals, output_rows, survival_rows,
          title_suffix="(crossover focus)",
          xlim=(CROSSOVER_R_MIN, CROSSOVER_R_MAX),
          filename_suffix="_crossover", show_candidate=True)

# ============================================================
# DECOMPOSITION VERIFICATION
# ============================================================
print("\n=== DECOMPOSITION VERIFICATION ===")
residuals = [row["residual"] for row in survival_rows]
valid_residuals = [r for r in residuals if not np.isnan(r)]
if valid_residuals:
    max_residual = max(abs(r) for r in valid_residuals)
    print(f"Maximum residual: {max_residual:.6e}")
    if max_residual < 1e-9:
        print("✓ Decomposition verified: mean = surv_prob * cond_mean")
    else:
        print(f"⚠ Residual detected: {max_residual:.6e}")
else:
    print("No valid residuals to check.")

# ============================================================
# SUMMARY
# ============================================================
print(f"\n=== SUMMARY ===")
print(f"Campaign: {TARGET_CAMPAIGN}")
print(f"Total R values: {len(Rs_vals)}")
if Rs_vals:
    n_values = [row["N_real"] for row in output_rows]
    print(f"Realizations per R: {min(n_values)} to {max(n_values)}")
    print(f"R range: {min(Rs_vals)} to {max(Rs_vals)}")
print("\nDone!")