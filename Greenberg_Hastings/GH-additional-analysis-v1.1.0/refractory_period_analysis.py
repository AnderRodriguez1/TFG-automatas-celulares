"""
Generate final figures for the article:
- Figure 1: Full-range activity with descriptive phenomenological fit (M0)
- Figure 1_supp: Three-model comparison (optional, supplementary)
- Figure 2: Dynamical decomposition:
    (a) Survival probability P_surv across crossover
    (b) Effective cycle length T_eff = 1/<rho|survival> over full active range
"""

import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
from scipy.optimize import curve_fit

# ============================================================
# CONFIGURATION
# ============================================================
_HERE = Path(__file__).resolve().parent
SUMMARY_FILE = _HERE / "gh_simulation_summary.csv"
OUTPUT_DIR = _HERE / "figures_final"
OUTPUT_DIR.mkdir(exist_ok=True)

# Target parameters
TARGET_L = 500
TARGET_RHO = 0.15

# Original campaign (single dataset, no "Original"/"Replica" labels)
TARGET_CAMPAIGN = "CSVs_GH_densidad_15"

# Columns
ACTIVITY_COL = "late_mean_active_fraction"
SURVIVAL_COL = "survived_after_2000_updates"

# Crossover range
CROSSOVER_R_MIN = 16
CROSSOVER_R_MAX = 36

# Historical parameters for descriptive fit
R_FIT_HIST = 34.8
TAU_HIST = 0.62
BETA_HIST = 0.79
C_HIST = 0.00838  # Not used in reduced model, but kept for reference

# ============================================================
# WILSON CONFIDENCE INTERVAL
# ============================================================
def wilson_interval(n_success, n_total):
    if n_total == 0:
        return np.nan, np.nan
    p = n_success / n_total
    z = 1.96
    denominator = 1 + z**2 / n_total
    center = p + z**2 / (2 * n_total)
    half_width = z * math.sqrt(p * (1 - p) / n_total + z**2 / (4 * n_total**2))
    low = (center - half_width) / denominator
    high = (center + half_width) / denominator
    return max(0.0, low), min(1.0, high)

# ============================================================
# LOAD DATA
# ============================================================
def load_campaign_data(campaign_folder):
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
            if campaign != campaign_folder:
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
    return rows_by_R

# ============================================================
# COMPUTE STATISTICS
# ============================================================
def compute_statistics(rows_by_R):
    results = []
    for R in sorted(rows_by_R.keys()):
        acts = [a for a, s in rows_by_R[R]]
        survs = [s for a, s in rows_by_R[R]]
        n = len(acts)
        if n == 0:
            continue
        mean_act = np.mean(acts)
        sd_across_runs = np.std(acts, ddof=0)
        n_surv = sum(survs)
        surv_prob = n_surv / n
        ci_low, ci_high = wilson_interval(n_surv, n)
        cond_acts = [a for a, s in zip(acts, survs) if s == 1]
        if cond_acts:
            cond_mean = np.mean(cond_acts)
            if len(cond_acts) > 1:
                cond_sd = np.std(cond_acts, ddof=1)
            else:
                cond_sd = np.nan
        else:
            cond_mean = np.nan
            cond_sd = np.nan
        results.append({
            "R": R,
            "N_real": n,
            "N_surv": n_surv,
            "mean_activity": mean_act,
            "sd_across_runs": sd_across_runs,
            "survival_probability": surv_prob,
            "survival_CI_low": ci_low,
            "survival_CI_high": ci_high,
            "cond_mean_activity": cond_mean,
            "cond_sd_activity": cond_sd,
        })
    return results

# ============================================================
# MODEL FUNCTIONS
# ============================================================
def model_reduced(R, A, R_fit, tau, beta):
    result = np.zeros_like(R, dtype=float)
    mask = R < R_fit
    if np.any(mask):
        result[mask] = A * R[mask]**(-tau) * (R_fit - R[mask])**beta
    return result

# ============================================================
# MAIN
# ============================================================
print("Loading data...")
rows_by_R = load_campaign_data(TARGET_CAMPAIGN)
results = compute_statistics(rows_by_R)

R_values = [r["R"] for r in results]
mean_activity = [r["mean_activity"] for r in results]
sd_across_runs = [r["sd_across_runs"] for r in results]
survival_prob = [r["survival_probability"] for r in results]
survival_CI_low = [r["survival_CI_low"] for r in results]
survival_CI_high = [r["survival_CI_high"] for r in results]
cond_mean = [r["cond_mean_activity"] for r in results]
cond_sd = [r["cond_sd_activity"] for r in results]

print(f"Loaded {len(results)} R values (1..100) with 10 realizations each.")

# ============================================================
# FIT REDUCED MODEL (descriptive, historical parameters fixed)
# ============================================================
Rs_orig = np.array(R_values)
means_orig = np.array(mean_activity)

# Fit only amplitude A with historical parameters fixed
fit_mask = Rs_orig < R_FIT_HIST
R_fit_data = Rs_orig[fit_mask]
rho_fit_data = means_orig[fit_mask]

def historical_form(R, A):
    return model_reduced(R, A, R_FIT_HIST, TAU_HIST, BETA_HIST)

popt, _ = curve_fit(historical_form, R_fit_data, rho_fit_data, p0=[0.1])
A_est = popt[0]
print(f"Descriptive fit: A = {A_est:.4f} (R_fit={R_FIT_HIST}, tau={TAU_HIST}, beta={BETA_HIST})")

# Smooth curve for plotting
R_smooth = np.linspace(1, R_FIT_HIST - 0.1, 500)
rho_smooth = historical_form(R_smooth, A_est)

# ============================================================
# FIGURE 1: FULL-RANGE ACTIVITY WITH DESCRIPTIVE FIT
# ============================================================
print("\nGenerating Figure 1...")
fig1, ax1 = plt.subplots(figsize=(15.360, 7.590))

# Data
ax1.errorbar(Rs_orig, means_orig, yerr=sd_across_runs, fmt='o', capsize=5,
             color='blue', label='Data ($\\langle\\rho\\rangle \\pm$ SD across 10 runs)',
             markersize=6, linestyle='none')
#ax1.plot(Rs_orig, means_orig, 'b-', alpha=0.3, linewidth=1)

# Descriptive fit
ax1.plot(R_smooth, rho_smooth, 'r--', linewidth=2,
         label='Descriptive fit (reduced model)')

# Vertical line at R_fit
ax1.axvline(x=R_FIT_HIST, color='darkgreen', linestyle='--', alpha=0.5, linewidth=2,
            label=f'$R_{{\\rm fit}}={R_FIT_HIST}$ (fitted endpoint)')

# ---- LEYENDA A LA IZQUIERDA ----
ax1.legend(bbox_to_anchor=(0.02, 0.98), loc='upper left', fontsize=14, framealpha=0.9)

# ---- INSET MÁS GRANDE (aprovechando el espacio de la derecha) ----
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset

axins = inset_axes(ax1, width="50%", height="50%", loc='center',
                   bbox_to_anchor=(0.20, 0.20, 0.9, 0.9),
                   bbox_transform=ax1.transAxes,
                   borderpad=0.5)

mask_inset = (Rs_orig >= CROSSOVER_R_MIN) & (Rs_orig <= CROSSOVER_R_MAX)
R_inset = Rs_orig[mask_inset]
rho_inset = means_orig[mask_inset]
sd_inset = np.array(sd_across_runs)[mask_inset]

axins.errorbar(R_inset, rho_inset, yerr=sd_inset, fmt='o-', capsize=3,
               color='blue', markersize=6, linewidth=1.5)
R_smooth_inset = np.linspace(CROSSOVER_R_MIN, CROSSOVER_R_MAX, 100)
rho_smooth_inset = historical_form(R_smooth_inset, A_est)
axins.plot(R_smooth_inset, rho_smooth_inset, 'r--', linewidth=2)
axins.set_xlim(CROSSOVER_R_MIN, CROSSOVER_R_MAX)
axins.set_ylim(-0.01, 0.07)
axins.grid(True, linestyle='--', alpha=0.3, linewidth=0.5)
axins.tick_params(axis='both', which='major', labelsize=12)  # Ticks del inset
#axins.text(0.05, 0.9, 'Crossover', transform=axins.transAxes, fontsize=10, fontweight='bold')
mark_inset(ax1, axins, loc1=2, loc2=4, fc="none", ec="gray", linestyle=':', alpha=0.9)

# ---- TÍTULO ----
#ax1.set_title('Mean proportion of active automata ($\\rho_0 = 0.15$)')

# ---- ETIQUETAS ----
ax1.set_xlabel('Refractory period $R$', fontsize=18)
ax1.set_ylabel(r'Mean active fraction $\langle \rho \rangle$', fontsize=18)
ax1.grid(True, linestyle='--', alpha=0.3)
ax1.set_xlim(0.5, 100.5)
ax1.set_ylim(-0.01, 0.55)
ax1.tick_params(axis='both', which='major', labelsize=14)  # Ticks del panel principal

#plt.tight_layout()
fig1.subplots_adjust(left=0.06, right=0.98, bottom=0.1, top=0.97)
fig1.savefig(OUTPUT_DIR / "activity_with_fit.png", dpi=300)
fig1.savefig(OUTPUT_DIR / "activity_with_fit.pdf")
plt.close(fig1)
print("  Figure 1 saved.")

# ============================================================
# FIGURE 2: DYNAMICAL DECOMPOSITION (custom size for PR-E)
# ============================================================
print("\nGenerating Figure 2 (custom size for PR-E)...")

# Dimensiones deseadas para cada subplot (en pulgadas)
subplot_width = 15.360
subplot_height = 7.590


# Márgenes y espaciado (fracciones de la figura)
left = 0.05
right = 0.98
bottom = 0.04
top = 0.97
hspace = 0.18  # Un poco más de espacio entre (a) y (b)


# Calcular el tamaño total de la figura
fig_width = subplot_width / (right - left)
fig_height = (subplot_height * 2 + hspace * subplot_height) / (top - bottom)

fig = plt.figure(figsize=(fig_width, fig_height))
gs = GridSpec(2, 1, left=left, right=right, bottom=bottom, top=top, hspace=hspace)

ax_a = fig.add_subplot(gs[0])
ax_b = fig.add_subplot(gs[1])

# --- Panel (a): Survival probability ---
mask_cross = (Rs_orig >= CROSSOVER_R_MIN) & (Rs_orig <= CROSSOVER_R_MAX)
Rs_cross = Rs_orig[mask_cross]
surv_cross = np.array(survival_prob)[mask_cross]
ci_low_cross = np.array(survival_CI_low)[mask_cross]
ci_high_cross = np.array(survival_CI_high)[mask_cross]

ax_a.errorbar(Rs_cross, surv_cross,
              yerr=[surv_cross - ci_low_cross, ci_high_cross - surv_cross],
              fmt='s', capsize=5, color='blue', markersize=10,
              label='Survival probability (Wilson 95% CI)')
ax_a.set_ylabel(r'$P_{\rm surv}$', fontsize=18)
ax_a.set_title('(a)', fontsize=20, fontweight='bold')
ax_a.grid(True, linestyle='--', alpha=0.5)
ax_a.set_ylim(-0.05, 1.05)
ax_a.set_xlim(CROSSOVER_R_MIN - 1, CROSSOVER_R_MAX + 1)
ax_a.tick_params(axis='both', which='major', labelsize=14)
# Forzamos a que se vean las etiquetas del eje X en el panel (a)
ax_a.tick_params(axis='x', labelbottom=True)
ax_a.set_xlabel('Refractory period $R$', fontsize=18)

# --- Panel (b): Deviation from minimal cycle ---
R_min_full = 1
R_max_full = 34

cond_mean_array = np.array(cond_mean)
mask_active = (Rs_orig >= R_min_full) & (Rs_orig <= R_max_full) & np.isfinite(cond_mean_array)
Rs_active = Rs_orig[mask_active]
cond_mean_active = cond_mean_array[mask_active]

T_eff = 1.0 / cond_mean_active
diff = T_eff - (Rs_active + 1)

# Línea horizontal
ax_b.axhline(y=0, color='red', linestyle='--', linewidth=2, alpha=0.8,
             label='Minimal-cycle prediction: $\\Delta T = 0$')

# Datos
ax_b.plot(Rs_active, diff, 'o', color='blue', markersize=10,
          markeredgewidth=1.5,
          label='$\\Delta T = T_{\\rm eff} - (R+1)$ (data)')

# Predicción de paridad
R_ref = np.arange(R_min_full, R_max_full + 1)
diff_parity = 2 * (R_ref // 2 + 1) - (R_ref + 1)
ax_b.plot(R_ref, diff_parity, 'g-.', linewidth=2, alpha=0.8,
          label='Bipartite parity prediction')

# Banda sombreada (de 11 a 15, como pediste)
ax_b.fill_betweenx([0.0, 1.0], 11, 15, color='blue', alpha=0.15,
                   label='Crossover region')

ax_b.set_xlabel('Refractory period $R$', fontsize=18)
ax_b.set_ylabel(r'$\Delta T$ (updates)', fontsize=18)
ax_b.set_title('(b)', fontsize=20, fontweight='bold')
ax_b.grid(True, linestyle='--', alpha=0.5)
ax_b.legend(loc='upper left', fontsize=14, framealpha=0.9)
ax_b.set_xlim(R_min_full - 1, R_max_full + 1)
ax_b.set_ylim(-0.1, 1.4)
ax_b.tick_params(axis='both', which='major', labelsize=14)

# Guardar
#plt.savefig(OUTPUT_DIR / "survival_and_cycle_length.png", dpi=300, bbox_inches='tight', pad_inches=0)
plt.savefig(OUTPUT_DIR / "survival_and_cycle_length.png", dpi=300)
plt.savefig(OUTPUT_DIR / "survival_and_cycle_length.pdf", bbox_inches='tight', pad_inches=0)
plt.close(fig)
print("  Figure 2 saved (custom size).")
"""
# ============================================================
# OPTIONAL SUPPLEMENTARY: THREE-MODEL COMPARISON
# ============================================================
print("\nGenerating Figure 1 supplementary (three-model comparison)...")
fig_supp, ax_supp = plt.subplots(figsize=(8, 6))

# Data
ax_supp.errorbar(Rs_orig, means_orig, yerr=sd_across_runs, fmt='o', capsize=3,
                 color='blue', label='Data', markersize=4, linestyle='none')

# Reduced model (descriptive)
ax_supp.plot(R_smooth, rho_smooth, 'r--', linewidth=2,
             label='Reduced model (descriptive)')

# For completeness, also show exponential model (historical) if needed
# But we won't include it here to avoid clutter

ax_supp.set_xlabel('Refractory period $R$')
ax_supp.set_ylabel(r'Active fraction $\langle \rho \rangle$')
ax_supp.set_title('Three-model comparison (supplementary)')
ax_supp.grid(True, linestyle='--', alpha=0.3)
ax_supp.legend(loc='upper right', fontsize=8)
ax_supp.set_xlim(0, 105)
ax_supp.set_ylim(bottom=-0.01)

plt.tight_layout()
fig_supp.savefig(OUTPUT_DIR / "Figure1_supp_three_model_comparison.png", dpi=300)
fig_supp.savefig(OUTPUT_DIR / "Figure1_supp_three_model_comparison.pdf")
plt.close(fig_supp)
print("  Figure 1 supplementary saved.")
"""
# ============================================================
# SUMMARY
# ============================================================
print("\n" + "="*50)
print("DONE")
print("="*50)
print(f"Output figures saved in: {OUTPUT_DIR}")
print("  - Figure1_activity_with_fit.png / .pdf")
print("  - Figure2_survival_and_cycle_length.png / .pdf")
print("  - Figure1_supp_three_model_comparison.png / .pdf (optional)")
print(f"\nDescriptive fit: A = {A_est:.4f}")
print("✓ Ready for manuscript figures.")