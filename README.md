<!-- TODO
- Option to remove samples
- Support for EMU combined files
- Option to add mapped counts file and display above bars
- Add demo data
- Add screenshots (images/) (main interface, legend editor, export)
-->


# Tax-Stax
Interactive Dash app for building customizable stacked barplots of relative abundance data, with sample ordering, color legend editing, grouping, and HTML/settings export.

---

## Features

- Upload one or more abundance TSVs
  - From GermGenie (long format: `sample`, `species`, `abundance`) or
  - From EMU (wide format: `species`, `genus`, `family`, `order`, `class`, `phylum`, `superkingdom`, samples)
- Optional samplesheet for renaming samples and defining groups
- Optional color legend TSV to fix species colors across plots
- Six built-in color palettes, including a colorblind-safe option
- Species filtering by Top N or minimum abundance %, with automatic "Other" grouping
- Drag-free reordering of samples (via ▲/▼ buttons), per group
- Live color editing per species via the legend editor
- Adjustable bar width, font size, figure size, legend position, axis rotation, titles
- Export the plot as a standalone interactive HTML file
- Save/load all plot settings as a JSON file for reproducibility
- Export and upload custom color legends as a TSV for reproducibility

---

## Screenshots
---

## Using TaxStax
To use the tool, there are 2 options. Either visit [atls-tools.org](https://www.atls-tools.org/taxastacks/) to start using it immediately, or clone the source code and run the app locally.

### Via atls-tools.org
Surf to https://www.atls-tools.org/taxastacks/ and start exploring!

### Local
Follow the steps below to install and run the app locally.
#### Installation

```bash
git clone https://github.com/<your-username>/tax-stax.git
cd tax-stax
pip install dash dash-bootstrap-components pandas plotly
```

#### Running the app

```bash
python tax_stax.py
```

By default the app runs on `http://0.0.0.0:8050/tax-stax/` (adjust the port/prefix in the script if needed for your server setup).

---

## Input file formats

**Abundance TSV** (required, one or more files), long format:

| sample | species | abundance |
|--------|---------|-----------|
| S1     | Species_A | 45.2 |
| S1     | Species_B | 30.1 |
| S2     | Species_A | 60.0 |

When supplied with multiple abundance TSVs, tax-stax will visualize all samples from all files in the same plot.

**Samplesheet TSV** (optional), renames samples and assigns groups:

| sample | samplename | group |
|--------|------------|-------|
| S1     | Control_1  | Control |
| S2     | Treated_1  | Treatment |

**Legend TSV** (optional), fixes colors for specific species:

| species | color |
|---------|-------|
| Species_A | #1F77B4 |
| Species_B | #FF7F0E |

**Settings JSON**  produced by "Save settings" in the app, can be re-loaded later to restore plot options.

---

## Testing the app with demo data

Demo files are provided in the [demo folder](https://github.com/Avans-ATLS/tax-stax/blob/main/demo/): [`demo_abundance.tsv`](https://github.com/Avans-ATLS/tax-stax/blob/main/demo/demo_abundance.tsv), [`demo_samplesheet.tsv`](https://github.com/Avans-ATLS/tax-stax/blob/main/demo/demo_samplesheet.tsv), and [`demo_legend.tsv`](https://github.com/Avans-ATLS/tax-stax/blob/main/demo/demo_legend.tsv).

1. Open the app in your browser.
2. Upload [`demo/demo_abundance.tsv`](https://github.com/Avans-ATLS/tax-stax/blob/main/demo/demo_abundance.tsv) under **Data upload → Abundance TSV(s)**. The plot should render immediately with default settings.
3. Upload [`demo/demo_samplesheet.tsv`](https://github.com/Avans-ATLS/tax-stax/blob/main/demo/demo_samplesheet.tsv) under **Samplesheet TSV**. Sample names in the plot should update, and the **Group** dropdown should now list the groups from the samplesheet.
4. Select a group from the **Group** dropdown and confirm the plot and sample order list update to show only that group's samples.
5. Use the ▲/▼ buttons under **Sample order** to reorder a couple of samples and confirm the plot x-axis follows the new order.
6. Switch **Species filter** from Top N to Min abundance (%) and back, adjusting the values, and confirm species are merged into "Other" as expected.
7. Upload [`demo/demo_legend.tsv`](https://github.com/Avans-ATLS/tax-stax/blob/main/demo/demo_legend.tsv) under **Color legend TSV** and confirm the specified species take on the fixed colors.
8. Change a color manually in the **Legend colors** editor on the right and confirm the plot updates live.
9. Try a different **Color palette** and confirm unassigned species get new colors while legend-fixed species keep theirs.
10. Adjust bar width, font size, figure size, legend position, x-axis rotation, y-axis title, and plot title, confirming each updates the plot.
11. Click **HTML** under **Export plot** and confirm a standalone `.html` file downloads and opens correctly in a browser.
12. Click **Save settings**, then reload the app (or change a few settings), and use **Load settings** to confirm your saved configuration is restored.
13. Click **Download legend TSV** and confirm the exported file matches the colors currently shown in the legend editor.

---

## License
[MIT license](https://github.com/Avans-ATLS/tax-stax/blob/main/LICENSE)

---

Developed by Birgit Rijvers-van Pruissen for the ATLS lectorate, Avans University of Applied Sciences.
