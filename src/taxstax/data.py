"""
Data parsing/transform helpers shared by all TaxStax pages.
No Dash components live here — keep this module UI-free so it stays testable.
"""

import base64
import io
import json
from typing import Optional

import numpy as np
import pandas as pd

# color palettes

PALETTES: dict[str, list[str]] = {
    "Plotly (default)": [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
        "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
        "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
        "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
        "#AEC7E8", "#FFBB78", "#98DF8A", "#FF9896", "#C5B0D5",
    ],
    "Tableau (categorical)": [
        "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD",
        "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF",
        "#AEC7E8", "#FFBB78", "#98DF8A", "#FF9896", "#C5B0D5",
        "#C49C94", "#F7B6D2", "#C7C7C7", "#DBDB8D", "#9EDAE5",
    ],
    "Colorblind-safe (Okabe Ito)": [
        "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2",
        "#D55E00", "#CC79A7", "#000000", "#999999", "#44AA99",
        "#332288", "#117733", "#882255", "#AA4499", "#DDCC77",
        "#88CCEE", "#CC6677", "#AA4466", "#44AA99", "#999933",
        "#661100", "#6699CC", "#AA4466", "#888888", "#DDDDDD",
    ],
    "Rainbow": [
        "#E6194B", "#F58231", "#FFE119", "#BFef45", "#3CB44B",
        "#42D4F4", "#4363D8", "#911EB4", "#F032E6", "#FABED4",
        "#9A6324", "#FFFAC8", "#AAFFC3", "#469990", "#E6BEFF",
        "#800000", "#A9A9A9", "#000075", "#808000", "#BFEF45",
        "#DCBEFF", "#FDCFE3", "#AFFFCE", "#BEBADA", "#FB8072",
    ],
    "Earth tones": [
        "#6B4226", "#A0522D", "#CD853F", "#DEB887", "#D2B48C",
        "#BC8A5F", "#8B5E3C", "#704214", "#5C3317", "#3E2723",
        "#795548", "#9E7B65", "#BCAAA4", "#A1887F", "#8D6E63",
        "#6D4C41", "#4E342E", "#4CAF50", "#81C784", "#A5D6A7",
        "#388E3C", "#2E7D32", "#1B5E20", "#66BB6A", "#43A047",
    ],
    "Pink and purple": [
        "#4A148C", "#6A1B9A", "#8E24AA", "#AB47BC", "#CE93D8",
        "#F3E5F5", "#880E4F", "#AD1457", "#D81B60", "#EC407A",
        "#F48FB1", "#FCE4EC", "#311B92", "#4527A0", "#5E35B1",
        "#7E57C2", "#B39DDB", "#EDE7F6", "#C2185B", "#E91E63",
        "#F06292", "#F8BBD0", "#512DA8", "#9575CD", "#D1C4E9",
    ]
}

OTHER_COLOR = "#CCCCCC"

# Alpha diversity metric labels (used for dropdown options + y-axis defaults)
METRIC_LABELS: dict[str, str] = {
    "shannon": "Shannon diversity index (H')",
    "simpson": "Simpson's diversity index (1-D)",
    "observed": "Observed richness (# taxa)",
    "pielou": "Pielou's evenness (J')",
}

# Data helpers

def parse_tsv(contents: str) -> pd.DataFrame:
    """Decode a base64 upload and return a DataFrame."""
    _header, encoded = contents.split(",", 1)
    decoded = base64.b64decode(encoded)
    return pd.read_csv(io.StringIO(decoded.decode("utf-8")), sep="\t")


def load_abundance(contents_list: list[str]) -> pd.DataFrame:
    """Concatenate one or more uploaded abundance TSVs."""
    frames = [parse_tsv(c) for c in contents_list]
    df = pd.concat(frames, ignore_index=True)
    df.columns = df.columns.str.strip()
    required = {"sample", "species", "abundance"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    df["abundance"] = pd.to_numeric(df["abundance"], errors="coerce").fillna(0)
    return df


def df_from_store(json_str: Optional[str]) -> Optional[pd.DataFrame]:
    """Safely read a DataFrame from a JSON store, avoiding the literal-string FutureWarning."""
    if not json_str:
        return None
    return pd.read_json(io.StringIO(json_str), orient="split")


def apply_samplesheet(df: pd.DataFrame, ss: Optional[pd.DataFrame]) -> tuple[pd.DataFrame, list[str], dict, dict]:
    """Rename samples, build group mapping, and read total-reads if supplied."""
    if ss is None:
        samples = list(df["sample"].unique())
        return df, samples, {"All": samples}, {}

    ss = ss.copy()
    ss.columns = ss.columns.str.strip()
    rename_map = dict(zip(ss["sample"], ss["samplename"]))
    df = df.copy()
    df["sample"] = df["sample"].map(rename_map).fillna(df["sample"])

    present = set(df["sample"].unique())
    ordered = [rename_map.get(s, s) for s in ss["samplename"] if rename_map.get(s, s) in present]

    groups: dict[str, list[str]] = {"All": ordered}
    group_names: dict[str, str] = {}
    if "group" in ss.columns:
        for _, row in ss.iterrows():
            sname = rename_map.get(row["sample"], row["sample"])
            if sname not in present:
                continue
            grp_raw = str(row.get("group", "")).strip()
            if grp_raw and grp_raw != "nan":
                for group_value in (g.strip() for g in grp_raw.split(",")):
                    if group_value:
                        group_key = group_value.casefold()
                        group_name = group_names.setdefault(group_key, group_value)
                        groups.setdefault(group_name, [])
                        if sname not in groups[group_name]:
                            groups[group_name].append(sname)

    read_totals: dict[str, dict[str, float]] = {}
    read_cols = {"mapped", "unclassified_mapped", "unmapped"}
    if read_cols.issubset(ss.columns):
        for _, row in ss.iterrows():
            sname = rename_map.get(row["sample"], row["sample"])
            if sname not in present:
                continue
            mapped = pd.to_numeric(row["mapped"], errors="coerce")
            mapped = 0.0 if pd.isna(mapped) else float(mapped)
            total = mapped
            for c in read_cols - {"mapped"}:
                val = pd.to_numeric(row[c], errors="coerce")
                total += 0.0 if pd.isna(val) else float(val)
            read_totals[sname] = {"total": total, "mapped": mapped}

    return df, ordered, groups, read_totals


def filter_species(df: pd.DataFrame, mode: str, top_n: int, min_pct: float) -> pd.DataFrame:
    """Merge low-abundance species into 'Other'."""
    totals = df.groupby("species")["abundance"].sum()
    keep = totals.nlargest(top_n).index.tolist() if mode == "topn" else totals[totals >= min_pct].index.tolist()
    df = df.copy()
    df["species"] = df["species"].where(df["species"].isin(keep), other="Other")
    return df.groupby(["sample", "species"], as_index=False)["abundance"].sum()


def build_color_map(
    species_order: list[str],
    palette_name: str,
    legend_df: Optional[pd.DataFrame],
) -> dict[str, str]:
    """
    Assign a color to every species.
    Legend file takes priority; unlisted species get palette colors.
    Returns the FULL mapping including newly assigned colors.
    """
    palette = PALETTES[palette_name]
    color_map: dict[str, str] = {"Other": OTHER_COLOR}

    if legend_df is not None:
        legend_df = legend_df.copy()
        legend_df.columns = legend_df.columns.str.strip()
        if {"species", "color"}.issubset(legend_df.columns):
            color_map.update(dict(zip(legend_df["species"], legend_df["color"])))

    # assign palette colors only to species not covered by legend
    palette_idx = 0
    for sp in species_order:
        if sp not in color_map:
            color_map[sp] = palette[palette_idx % len(palette)]
            palette_idx += 1

    return color_map


def species_order_by_abundance(df: pd.DataFrame) -> list[str]:
    """Species sorted by total abundance descending; 'Other' always last."""
    totals = (
        df[df["species"] != "Other"]
        .groupby("species")["abundance"]
        .sum()
        .sort_values(ascending=False)
    )
    order = totals.index.tolist()
    if "Other" in df["species"].values:
        order.append("Other")
    return order


def compute_alpha_diversity(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """
    Compute one alpha diversity value per sample from long-format abundance
    data (columns: sample, species, abundance). Rows with zero or negative
    abundance are dropped before computing proportions, per sample.

    metric: one of "shannon", "simpson", "observed", "pielou".
    Returns a DataFrame with columns: sample, value.
    """
    if metric not in METRIC_LABELS:
        raise ValueError(f"Unknown alpha diversity metric: {metric}")

    rows = []
    for sample, sub in df.groupby("sample"):
        counts = sub.loc[sub["abundance"] > 0, "abundance"].to_numpy(dtype=float)

        if counts.size == 0:
            rows.append({"sample": sample, "value": 0.0})
            continue

        props = counts / counts.sum()

        if metric == "shannon":
            value = float(-np.sum(props * np.log(props)))
        elif metric == "simpson":
            value = float(1.0 - np.sum(props ** 2))
        elif metric == "observed":
            value = float(counts.size)
        else:  # pielou
            richness = counts.size
            if richness > 1:
                shannon = -np.sum(props * np.log(props))
                value = float(shannon / np.log(richness))
            else:
                value = 0.0

        rows.append({"sample": sample, "value": value})

    return pd.DataFrame(rows)


# Beta diversity: Bray-Curtis dissimilarity + PCoA / PCA ordination.
# Implemented with numpy only 

ORDINATION_METHODS: dict[str, str] = {
    "pcoa": "PCoA (Bray\u2013Curtis dissimilarity)",
    "pca": "PCA (relative abundance)",
}


def bray_curtis_dissimilarity(matrix: np.ndarray) -> np.ndarray:
    """Pairwise Bray-Curtis dissimilarity for a samples x species matrix."""
    n = matrix.shape[0]
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            denom = np.sum(matrix[i] + matrix[j])
            d = float(np.sum(np.abs(matrix[i] - matrix[j])) / denom) if denom > 0 else 0.0
            dist[i, j] = d
            dist[j, i] = d
    return dist


def classical_mds(dist: np.ndarray, n_axes: int = 2) -> tuple[np.ndarray, list[float]]:
    """
    Classical multidimensional scaling (= PCoA) on a distance matrix.
    Returns (coordinates [n_samples x n_axes], percent variance explained per axis).
    """
    n = dist.shape[0]
    d2 = dist ** 2
    centering = np.eye(n) - np.ones((n, n)) / n
    b = -0.5 * centering @ d2 @ centering

    eigvals, eigvecs = np.linalg.eigh(b)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]

    total_positive = eigvals[eigvals > 0].sum()
    coords = np.zeros((n, n_axes))
    variance_explained = []
    for i in range(n_axes):
        ev = eigvals[i] if i < len(eigvals) else 0.0
        if ev > 0:
            coords[:, i] = eigvecs[:, i] * np.sqrt(ev)
            variance_explained.append(float(ev / total_positive * 100) if total_positive > 0 else 0.0)
        else:
            variance_explained.append(0.0)
    return coords, variance_explained


def pca_svd(matrix: np.ndarray, n_axes: int = 2) -> tuple[np.ndarray, list[float]]:
    """Simple PCA via SVD on a mean-centered samples x features matrix."""
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    u, s, _vt = np.linalg.svd(centered, full_matrices=False)
    total_var = np.sum(s ** 2)
    coords = u[:, :n_axes] * s[:n_axes]
    variance_explained = [
        float((s[i] ** 2) / total_var * 100) if total_var > 0 and i < len(s) else 0.0
        for i in range(n_axes)
    ]
    return coords, variance_explained


def compute_beta_ordination(
    df: pd.DataFrame, method: str = "pcoa", n_axes: int = 2
) -> tuple[pd.DataFrame, list[float], str]:
    """
    Build a samples x species abundance matrix and run the requested ordination.

    method: "pcoa" runs classical MDS on a Bray-Curtis dissimilarity matrix;
    "pca" runs PCA on per-sample relative abundances (row-normalized).

    Returns (DataFrame with columns [sample, axis1, axis2, ...], percent
    variance explained per axis, axis label prefix e.g. "PCo" or "PC").
    """
    if method not in ORDINATION_METHODS:
        raise ValueError(f"Unknown ordination method: {method}")

    pivot = df.pivot_table(index="sample", columns="species", values="abundance",
                            aggfunc="sum", fill_value=0.0)
    samples = pivot.index.tolist()
    matrix = pivot.to_numpy(dtype=float)

    if method == "pca":
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        rel_matrix = matrix / row_sums
        coords, variance_explained = pca_svd(rel_matrix, n_axes=n_axes)
        axis_prefix = "PC"
    else:
        dist = bray_curtis_dissimilarity(matrix)
        coords, variance_explained = classical_mds(dist, n_axes=n_axes)
        axis_prefix = "PCo"

    result = pd.DataFrame(coords, columns=[f"axis{i + 1}" for i in range(n_axes)])
    result.insert(0, "sample", samples)
    return result, variance_explained, axis_prefix


def settings_to_json(**kwargs) -> str:
    return json.dumps(kwargs, indent=2)
