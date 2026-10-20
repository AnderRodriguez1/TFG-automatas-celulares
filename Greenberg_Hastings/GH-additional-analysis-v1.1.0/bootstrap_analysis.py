"""
Bootstrap and profile analysis for model comparison (M0 vs M1).
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

# ============================================================
# CONFIGURATION
# ============================================================
_HERE = Path(__file__).resolve().parent
SUMMARY_FILE = _HERE / "gh_simulation_summary.csv"
OUTPUT_DIR = _HERE / "figures_final"
OUTPUT_DIR.mkdir(exist_ok=True)

TARGET_L = 500
TARGET_RHO = 0.15
TARGET_CAMPAIGN = "CSVs_GH_densidad_15"

ACTIVITY_COL = "late_mean_active_fraction"

COMPARISON_R_MIN = 1
COMPARISON_R_MAX = 40

# R_fit range for fitting (ampliado para evitar fronteras artificiales)
R_FIT_MIN = 15
R_FIT_MAX = 40

# Bootstrap replicates
N_BOOTSTRAP_VALIDATION = 200
N_BOOTSTRAP_FINAL = 200  # inicialmente igual a la validación; luego se aumenta a 2000

SEED = 20260827

# ============================================================
# MODEL FUNCTIONS
# ============================================================
def model_reduced(R, A, R_fit, tau, beta):
    result = np.zeros_like(R, dtype=float)
    mask = R < R_fit
    if np.any(mask):
        result[mask] = A * R[mask]**(-tau) * (R_fit - R[mask])**beta
    return result

def model_exponential(R, A, R_fit, tau, beta, c):
    result = np.zeros_like(R, dtype=float)
    mask = R < R_fit
    if np.any(mask):
        result[mask] = A * R[mask]**(-tau) * np.exp(-c * R[mask]) * (R_fit - R[mask])**beta
    return result

# ============================================================
# LOAD RAW DATA
# ============================================================
def load_raw_data():
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
            rows_by_R[R].append(activity)
    return rows_by_R

# ============================================================
# FIT FUNCTIONS
# ============================================================
def fit_m0(R_data, rho_data):
    """Fit reduced model with multiple starts across R_fit."""
    R_fit_starts = np.arange(R_FIT_MIN + 0.1, R_FIT_MAX, 1.0)
    p0_list = [
        [0.03, rf, 0.62, 0.79]
        for rf in R_fit_starts
    ]
    bounds = ([0, R_FIT_MIN, 0, 0], [10, R_FIT_MAX, 2, 2])
    
    best_popt = None
    best_rss = np.inf
    best_pcov = None
    
    for p0 in p0_list:
        try:
            popt, pcov = curve_fit(model_reduced, R_data, rho_data, p0=p0, bounds=bounds, maxfev=100000)
            rho_pred = model_reduced(R_data, *popt)
            rss = np.sum((rho_data - rho_pred)**2)
            if rss < best_rss:
                best_rss = rss
                best_popt = popt
                best_pcov = pcov
        except Exception:
            continue
    
    if best_popt is None:
        return None, None, None
    return best_popt, best_pcov, best_rss

def fit_m1(R_data, rho_data, m0_solution=None):
    """Fit exponential model, initialized from M0 if provided."""
    p0_list = []
    if m0_solution is not None:
        A0, Rf0, tau0, beta0 = m0_solution
        p0_list.append([A0, Rf0, tau0, beta0, 0.0])
    # Additional starts across R_fit range
    R_fit_starts = np.arange(R_FIT_MIN + 0.1, R_FIT_MAX, 1.0)
    for rf in R_fit_starts:
        p0_list.append([0.03, rf, 0.62, 0.79, 0.00838])
    bounds = ([0, R_FIT_MIN, 0, 0, 0], [10, R_FIT_MAX, 2, 2, 0.1])
    
    best_popt = None
    best_rss = np.inf
    best_pcov = None
    
    for p0 in p0_list:
        try:
            popt, pcov = curve_fit(model_exponential, R_data, rho_data, p0=p0, bounds=bounds, maxfev=100000)
            rho_pred = model_exponential(R_data, *popt)
            rss = np.sum((rho_data - rho_pred)**2)
            if rss < best_rss:
                best_rss = rss
                best_popt = popt
                best_pcov = pcov
        except Exception:
            continue
    
    if best_popt is None:
        return None, None, None
    return best_popt, best_pcov, best_rss

# ============================================================
# AICc
# ============================================================
def compute_aicc(rss, n_data, k):
    aic = n_data * np.log(rss / n_data) + 2 * k
    if n_data > k + 1:
        aicc = aic + (2 * k * (k + 1)) / (n_data - k - 1)
    else:
        aicc = np.nan
    return aicc

# ============================================================
# BOOTSTRAP
# ============================================================
def run_bootstrap(raw_data, R_values, n_bootstrap, rng):
    """Run bootstrap replicates."""
    results = []
    failures = []
    
    for rep in range(n_bootstrap):
        if (rep + 1) % 50 == 0:
            print(f"  Replicate {rep+1}/{n_bootstrap}")
        
        # Resample independently for each R
        rho_boot = []
        R_boot = []
        for R in R_values:
            acts = raw_data[R]
            if len(acts) < 10:
                failures.append({"replicate": rep, "R": R, "reason": "not_enough_realizations"})
                continue
            resampled = rng.choice(acts, size=len(acts), replace=True)
            rho_boot.append(np.mean(resampled))
            R_boot.append(R)
        
        if len(R_boot) == 0:
            failures.append({"replicate": rep, "R": None, "reason": "no_data"})
            continue
        
        R_boot = np.array(R_boot)
        rho_boot = np.array(rho_boot)
        
        # Fit M0
        popt_m0, pcov_m0, rss_m0 = fit_m0(R_boot, rho_boot)
        if popt_m0 is None:
            failures.append({"replicate": rep, "R": None, "reason": "M0_fit_failed"})
            continue
        k_m0 = len(popt_m0) + 1
        aicc_m0 = compute_aicc(rss_m0, len(R_boot), k_m0)
        
        # Fit M1 initialized from M0
        popt_m1, pcov_m1, rss_m1 = fit_m1(R_boot, rho_boot, m0_solution=popt_m0)
        if popt_m1 is None:
            failures.append({"replicate": rep, "R": None, "reason": "M1_fit_failed"})
            continue
        k_m1 = len(popt_m1) + 1
        aicc_m1 = compute_aicc(rss_m1, len(R_boot), k_m1)
        
        # Sanity check: M1 RSS should be <= M0 RSS
        if rss_m1 > rss_m0 + 1e-12:
            failures.append({"replicate": rep, "R": None, "reason": "RSS_M1 > RSS_M0 (optimizer failed)"})
            continue
        
        delta_aicc = aicc_m1 - aicc_m0  # can be negative
        
        results.append({
            "replicate": rep,
            "delta_aicc": delta_aicc,
            "R_fit_M0": popt_m0[1],
            "tau_M0": popt_m0[2],
            "beta_M0": popt_m0[3],
            "R_fit_M1": popt_m1[1],
            "tau_M1": popt_m1[2],
            "beta_M1": popt_m1[3],
            "c_M1": popt_m1[4],
            "rss_M0": rss_m0,
            "rss_M1": rss_m1,
            "aicc_M0": aicc_m0,
            "aicc_M1": aicc_m1,
        })
    
    return results, failures

# ============================================================
# PROFILE OVER R_fit
# ============================================================
def profile_R_fit(raw_data, R_values):
    """Profile RSS over fixed R_fit with fine grid."""
    # Build grid: fine spacing + points near integers
    integers = np.arange(R_FIT_MIN, R_FIT_MAX + 1)
    grid_fine = np.arange(R_FIT_MIN, R_FIT_MAX + 0.001, 0.05)
    grid_near_int = np.concatenate([integers - 1e-3, integers + 1e-3])
    R_fit_grid = np.sort(np.unique(np.concatenate([grid_fine, grid_near_int])))
    # Recortar al rango declarado
    R_fit_grid = R_fit_grid[(R_fit_grid >= R_FIT_MIN) & (R_fit_grid <= R_FIT_MAX)]
    
    R_data = np.array(R_values)
    rho_data = np.array([np.mean(raw_data[R]) for R in R_values])
    
    profile = []
    for Rf in R_fit_grid:
        # M0 with fixed R_fit
        def m0_fixed(R, A, tau, beta):
            return model_reduced(R, A, Rf, tau, beta)
        popt_m0 = None
        try:
            popt_m0, _ = curve_fit(m0_fixed, R_data, rho_data, p0=[0.03, 0.62, 0.79],
                                   bounds=([0, 0, 0], [10, 2, 2]), maxfev=100000)
            rho_pred_m0 = m0_fixed(R_data, *popt_m0)
            rss_m0 = np.sum((rho_data - rho_pred_m0)**2)
        except Exception:
            rss_m0 = np.nan
        
        if popt_m0 is None:
            profile.append({"R_fit": Rf, "rss_M0": np.nan, "rss_M1": np.nan})
            continue
        
        # M1 with fixed R_fit, try multiple starting points
        def m1_fixed(R, A, tau, beta, c):
            return model_exponential(R, A, Rf, tau, beta, c)
        A0, tau0, beta0 = popt_m0
        best_rss_m1 = np.inf
        for c_start in [0.0, 0.00838, 0.02]:
            try:
                popt_m1, _ = curve_fit(m1_fixed, R_data, rho_data,
                                       p0=[A0, tau0, beta0, c_start],
                                       bounds=([0, 0, 0, 0], [10, 2, 2, 0.1]),
                                       maxfev=100000)
                rho_pred_m1 = m1_fixed(R_data, *popt_m1)
                rss_m1 = np.sum((rho_data - rho_pred_m1)**2)
                if rss_m1 < best_rss_m1:
                    best_rss_m1 = rss_m1
            except Exception:
                continue
        if best_rss_m1 == np.inf:
            best_rss_m1 = np.nan
        
        profile.append({"R_fit": Rf, "rss_M0": rss_m0, "rss_M1": best_rss_m1})
    
    return profile

# ============================================================
# MAIN
# ============================================================
if not SUMMARY_FILE.exists():
    raise FileNotFoundError(f"Summary file not found: {SUMMARY_FILE}")

print("Loading raw data...")
raw_data = load_raw_data()

# Validar R=1..40 (ignorando R>40 que existen legítimamente)
found_R = {R for R in raw_data if COMPARISON_R_MIN <= R <= COMPARISON_R_MAX}
expected_R = set(range(COMPARISON_R_MIN, COMPARISON_R_MAX + 1))
missing = expected_R - found_R
extra = found_R - expected_R
if missing or extra:
    raise ValueError(
        f"R values mismatch: missing {sorted(missing)}, extra {sorted(extra)}"
    )
for R in expected_R:
    if len(raw_data[R]) != 10:
        raise ValueError(f"R={R}: expected 10 realizations, got {len(raw_data[R])}")

R_values = sorted(expected_R)
print(f"Found {len(R_values)} R values (1..40) with 10 realizations each.")
print(f"R_fit fitting range: {R_FIT_MIN} to {R_FIT_MAX}")

# ============================================================
# Bootstrap - Generadores separados
# ============================================================
rng_validation = np.random.default_rng(SEED)
rng_final = np.random.default_rng(SEED + 1)

print(f"\nRunning bootstrap validation (N={N_BOOTSTRAP_VALIDATION})...")
results_val, failures_val = run_bootstrap(raw_data, R_values, N_BOOTSTRAP_VALIDATION, rng_validation)

print(f"Converged: {len(results_val)}/{N_BOOTSTRAP_VALIDATION}")
if failures_val:
    print(f"Failures: {len(failures_val)}")

# Save validation results
val_file = OUTPUT_DIR / "bootstrap_results_validation.csv"
with open(val_file, "w", newline="", encoding="utf-8") as f:
    if results_val:
        writer = csv.DictWriter(f, fieldnames=results_val[0].keys())
        writer.writeheader()
        writer.writerows(results_val)
print(f"Validation results saved to: {val_file}")

# Save failures
fail_file_val = OUTPUT_DIR / "bootstrap_failures_validation.csv"
with open(fail_file_val, "w", newline="", encoding="utf-8") as f:
    if failures_val:
        writer = csv.DictWriter(f, fieldnames=["replicate", "R", "reason"])
        writer.writeheader()
        writer.writerows(failures_val)
print(f"Validation failures saved to: {fail_file_val}")

if len(results_val) < N_BOOTSTRAP_VALIDATION * 0.9:
    print("Warning: convergence rate < 90%. Check failures before proceeding.")
    sys.exit(1)

# ============================================================
# Run final bootstrap
# ============================================================
print(f"\nRunning final bootstrap (N={N_BOOTSTRAP_FINAL})...")
results_final, failures_final = run_bootstrap(raw_data, R_values, N_BOOTSTRAP_FINAL, rng_final)

final_file = OUTPUT_DIR / "bootstrap_results_final.csv"
with open(final_file, "w", newline="", encoding="utf-8") as f:
    if results_final:
        writer = csv.DictWriter(f, fieldnames=results_final[0].keys())
        writer.writeheader()
        writer.writerows(results_final)
print(f"Final results saved to: {final_file}")

fail_file_final = OUTPUT_DIR / "bootstrap_failures_final.csv"
with open(fail_file_final, "w", newline="", encoding="utf-8") as f:
    if failures_final:
        writer = csv.DictWriter(f, fieldnames=["replicate", "R", "reason"])
        writer.writeheader()
        writer.writerows(failures_final)
print(f"Final failures saved to: {fail_file_final}")

# ============================================================
# STATISTICS
# ============================================================
if results_final:
    delta_aiccs = [r["delta_aicc"] for r in results_final]
    c_vals = [r["c_M1"] for r in results_final]
    Rf_m0 = [r["R_fit_M0"] for r in results_final]
    Rf_m1 = [r["R_fit_M1"] for r in results_final]
    
    # Quantiles
    quantiles = {
        "delta_aicc": np.percentile(delta_aiccs, [2.5, 50, 97.5]),
        "c_M1": np.percentile(c_vals, [2.5, 50, 97.5]),
        "R_fit_M0": np.percentile(Rf_m0, [2.5, 50, 97.5]),
        "R_fit_M1": np.percentile(Rf_m1, [2.5, 50, 97.5]),
    }
    
    # Categories
    frac_gt_2 = np.mean(np.array(delta_aiccs) > 2)
    frac_mid = np.mean(np.abs(np.array(delta_aiccs)) <= 2)
    frac_lt_minus_2 = np.mean(np.array(delta_aiccs) < -2)
    
    # Bound diagnostics
    frac_c_zero = np.mean(np.array(c_vals) < 1e-6)
    frac_Rf_m0_low = np.mean(np.array(Rf_m0) < R_FIT_MIN + 0.05)
    frac_Rf_m1_low = np.mean(np.array(Rf_m1) < R_FIT_MIN + 0.05)
    
    print("\n=== Bootstrap Results ===")
    print(f"Converged: {len(results_final)}/{N_BOOTSTRAP_FINAL}")
    print(f"Fraction ΔAICc > 2 (M0 favored): {frac_gt_2:.3f}")
    print(f"Fraction |ΔAICc| ≤ 2 (indistinguishable): {frac_mid:.3f}")
    print(f"Fraction ΔAICc < -2 (M1 favored): {frac_lt_minus_2:.3f}")
    print(f"\nQuantiles (2.5%, 50%, 97.5%):")
    print(f"  ΔAICc: {quantiles['delta_aicc'][0]:.2f}, {quantiles['delta_aicc'][1]:.2f}, {quantiles['delta_aicc'][2]:.2f}")
    print(f"  c_M1:  {quantiles['c_M1'][0]:.4f}, {quantiles['c_M1'][1]:.4f}, {quantiles['c_M1'][2]:.4f}")
    print(f"  R_fit_M0: {quantiles['R_fit_M0'][0]:.2f}, {quantiles['R_fit_M0'][1]:.2f}, {quantiles['R_fit_M0'][2]:.2f}")
    print(f"  R_fit_M1: {quantiles['R_fit_M1'][0]:.2f}, {quantiles['R_fit_M1'][1]:.2f}, {quantiles['R_fit_M1'][2]:.2f}")
    print(f"\nBound diagnostics:")
    print(f"  Fraction c ≈ 0: {frac_c_zero:.3f}")
    print(f"  Fraction R_fit_M0 near lower bound: {frac_Rf_m0_low:.3f}")
    print(f"  Fraction R_fit_M1 near lower bound: {frac_Rf_m1_low:.3f}")

# ============================================================
# PROFILE
# ============================================================
print("\nRunning R_fit profile...")
profile = profile_R_fit(raw_data, R_values)
prof_file = OUTPUT_DIR / "R_fit_profile.csv"
with open(prof_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["R_fit", "rss_M0", "rss_M1"])
    writer.writeheader()
    writer.writerows(profile)
print(f"Profile saved to: {prof_file}")

# ============================================================
# PLOTS
# ============================================================
if results_final:
    fig1, ax1 = plt.subplots(figsize=(8, 5))
    ax1.hist(delta_aiccs, bins=30, edgecolor='black', alpha=0.7, color='blue')
    ax1.axvline(x=2, color='red', linestyle='--', label='ΔAICc = 2 (threshold)')
    ax1.axvline(x=-2, color='red', linestyle='--', alpha=0.5)
    ax1.axvline(x=np.median(delta_aiccs), color='black', linestyle='-', label=f'Median = {np.median(delta_aiccs):.2f}')
    ax1.set_xlabel(r'$\Delta$AICc = AICc$_{M1}$ - AICc$_{M0}$')
    ax1.set_ylabel('Frequency')
    ax1.set_title(f'Bootstrap distribution of ΔAICc (N={len(results_final)} replicates)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    fig1.savefig(OUTPUT_DIR / "bootstrap_delta_aicc.png", dpi=300)
    plt.close(fig1)
    print("  Bootstrap histogram saved.")

# Profile plot
fig2, ax2 = plt.subplots(figsize=(8, 5))
profile_data = [p for p in profile if not np.isnan(p["rss_M0"])]
if profile_data:
    Rf_vals = [p["R_fit"] for p in profile_data]
    rss_m0 = [p["rss_M0"] for p in profile_data]
    rss_m1 = [p["rss_M1"] for p in profile_data]

    ax2.plot(Rf_vals, rss_m0, 'o-', color='blue', label='M0 (reduced)', markersize=4)
    ax2.plot(Rf_vals, rss_m1, 's-', color='red', label='M1 (exponential)', markersize=4)
    ax2.axvline(x=34.8, color='gray', linestyle=':', label='Historical R_fit = 34.8')
    ax2.set_xlabel(r'Fixed $R_{\rm fit}$')
    ax2.set_ylabel('RSS')
    ax2.set_title(f'RSS vs fixed $R_{{\\rm fit}}$ (R={COMPARISON_R_MIN}..{COMPARISON_R_MAX})')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    fig2.savefig(OUTPUT_DIR / "R_fit_profile.png", dpi=300)
    plt.close(fig2)
    print("  R_fit profile plot saved.")

print(f"\nAll results saved in: {OUTPUT_DIR}")