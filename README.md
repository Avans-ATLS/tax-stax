<!-- TODO
- Support for EMU combined files
- Add screenshots (images/) (main interface, legend editor, export)
-->
# Tax-Stax
Interactive Dash app for building customizable stacked barplots of relative abundance data, with sample ordering, color legend editing, grouping, and HTML/settings export.

## Features

- Upload one or more abundance TSVs
  - From GermGenie (long format: `sample`, `species`, `abundance`) or
  - From EMU (wide format: `species`, `genus`, `family`, `order`, `class`, `phylum`, `superkingdom`, samples)
- Optional samplesheet for renaming samples and defining groups
- Optional color legend TSV to fix species colors across plots
- Six built-in color palettes, including a colorblind-safe option
- Species filtering by Top N or minimum abundance %, with automatic "Other" grouping
- Drag-free reordering of samples (via ▲/▼ buttons), per group
- Option to annotate samples with total input reads and/or % mapped reads
- Live color editing per species via the legend editor
- Adjustable bar width, font size, figure size, legend position, axis rotation, titles
- Export the plot as a standalone interactive HTML file
- Save/load all plot settings as a JSON file for reproducibility
- Export and upload custom color legends as a TSV for reproducibility

# Screenshots

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

# Input file formats
## Abundance file(s)
TaxStax supports multiple abundance input formats, so the tool is usable on GermGenie runs, EMU runs or combined EMU runs.
### GermGenie `abundance.tsv` file(s)

**Abundance TSV** (one or more files), long format:

| sample | species | abundance |
|--------|---------|-----------|
| S1     | Species_A | 45.0 |
| S1     | Species_B | 55.0 |
| S2     | Species_A | 100.0 |
| S3     | Species_B | 80.0 |
| S3     | Species_C | 20.0 |

When supplied with multiple abundance TSVs, TaxStax will visualize all samples from all files in the same plot.

### EMU file(s)
[EMU](https://github.com/treangenlab/emu) outputs one abundance file per sample, but these files can not be loaded into TaxStax. Use the `emu combine-outputs` command from EMU to combine multiple samples into one file.

See the GitHub of EMU for instructions: https://github.com/treangenlab/emu#combine-outputs

TaxStax supports outputs from `emu combine-outputs` with or without the `--counts` flag. 

## Samplesheet
A samplesheet is optional, but is very useful for reproducibility, visualizing subsets of your samples and adding metadata.

If you do not upload a samplesheet, all samples will be included in the plot using the value from `sample` in the abundance file. By default samples are sorted alphabetically, but you can change the order manually.
### Basic, renaming only
The most basic form of a samplesheet that TaxStax can use looks like:

Renames samples:

| sample | samplename |
|--------|------------|
| S1     | Control_1  |
| S2     | Treated_1  |
| S3     | Treated_2  |

The samples in `sample` should correspond with the values of `sample` in the uploaded abundance file. If a sample is included in the abundance file but not in the samplesheet, it will not be included in any of the visualizations.
All samples will be renamed to their corresponding `samplename` value. If you do not want to rename samples, just use the same value for both the `sample` and `samplename` columns.

### With groups
To categorize samples in groups, add an extra column to your samplesheet called `group`. You can assign 1 or multiple custom groups to each sample in this column. When adding multiple groups, use commas ("," without spaces) to separate them. TaxStax will always to offer the option to visualize all samples, so no need to create a separate group for that.

The example below will give the "Group" options "All" (S1,S2,S3), "Control" (S1), "Treatment" (S2, S3) and "Fig1" (S1, S3)

| sample | samplename | group |
|--------|------------|-------|
| S1     | Control_1  | Control,Fig1 |
| S2     | Treated_1  | Treatment |
| S3     | Treated_2  | Treatment,Fig1 |

### With mapping stats
If you want to show mapping statistics above the bars for your samples, you can also add this as extra headers to your samplesheet! If you supply a samplesheet like the example below, each sample bar will be annotated with the total amount of input reads (mapped + unclassified_mapped + unmapped) and the percentage of mapped reads ((mapped/total reads)*100).

| sample | samplename | group | mapped | unclassified_mapped | unmapped |
|--------|------------|-------|-------|-------|-------|
| S1     | Control_1  | Control,Fig1 | 34892 | 16 | 2|
| S2     | Treated_1  | Treatment | 45632 | 10 | 5 | 
| S3     | Treated_2  | Treatment,Fig1 | 2777 | 2 | 1 |

You can also supply a samplesheet that does not contain the `group` column, but does contain the columns needed for the mapping stats.

## Legend TSV (optional)
A legend TSV can be used to fix colors for specific species. You can create it manually like the example below, or use the build-in color picker from TaxStax to assign colors to species and export the legend via the "Download legend TSV" button.

| species | color |
|---------|-------|
| Species_A | #1F77B4 |
| Species_B | #FF7F0E |
| Species_C | #64D19E |

If you have uploaded a legend TSV that does not contain all species in your current samples, the new species will get an automatically assigned color from the currently selected color palette. Do not forget to save the legend TSV with your new species added to use it in your next visualizations.

## Settings JSON  
Produced by "Save settings" in the app, can be re-loaded later to restore all custom plot options.

# Testing the app with demo data

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
11. Switch off the display of the total input reads with "Show % mapped reads"
12. Click **HTML** under **Export plot** and confirm a standalone `.html` file downloads and opens correctly in a browser.
13. Click **Save settings**, then reload the app (or change a few settings), and use **Load settings** to confirm your saved configuration is restored.
14. Click **Download legend TSV** and confirm the exported file matches the colors currently shown in the legend editor.

# License
[MIT license](https://github.com/Avans-ATLS/tax-stax/blob/main/LICENSE)
---
Developed by Birgit Rijvers-van Pruissen for the ATLS lectorate, Avans University of Applied Sciences.
