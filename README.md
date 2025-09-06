# UFS Workflow Metrics

This repository provides a scalable, automated pipeline for tracking performance metrics across UFS regression tests. It extracts core hour and memory usage from test logs, flags anomalies, and generates visual summaries for all applications defined in `by_app/` YAML configs.

## 🔍 Features

- Parses all test definitions in `ufs-wm-metrics/tests-yamls/configs/by_app/*.yaml`
- Clones and analyzes `ufs-weather-model` across the last 50 commits
- Extracts:
  - 🕒 Core hour usage (second time in brackets)
  - 💾 Max memory usage (value in parentheses)
- Flags anomalies using rolling median and standard deviation
- Generates:
  - CSVs and high-res plots per test case
  - Markdown summaries per application

## 🖥️ Machines Covered

- `orion`, `hera`, `gaeac6`, `hercules`, `derecho`, `ursa`, `wcoss2`, `acorn`

## 📁 Output Structure

results/by_app/ 
├── walltime/<app>/<test>.csv + .png 
├── memsize/<app>/<test>_memory.csv + .png 
├── summary/<app>_summary.md


## 🚀 How to Run Locally

```bash
git clone https://github.com/ufs-community/ufs-weather-model.git
git clone https://github.com/ufs-community/ufs-wm-metrics.git
cd ufs-wm-metrics
pip install matplotlib pyyaml
python dump_all_apps_core_mem.py

