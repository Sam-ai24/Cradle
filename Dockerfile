# Phase 11: local/cloud container packaging.
#
# NOT locally built or run: this machine has no Docker Desktop and no WSL2
# (confirmed directly - `docker`/`wsl` are absent, see docs/ROADMAP.md
# Phase 11), so this file is written but unverified by an actual build,
# unlike everything else in this phase. Lower-risk than it sounds: every
# compiled dependency Cradle needs (antimony, python-libsbml/-libsedml/
# -libcombine, h5py, basico) was confirmed via `pip download
# --platform manylinux2014_x86_64` to publish real Linux wheels for
# CPython 3.11 - so this image shouldn't need a compiler toolchain at all.
# Build/run it on a machine with Docker (or in CI) to actually confirm.
#
#   docker build -t cradle .
#   docker run --rm -it cradle pytest -q
FROM python:3.11-slim

WORKDIR /cradle

COPY pyproject.toml ./
COPY src ./src
COPY plugins ./plugins
COPY models ./models
COPY scripts ./scripts
COPY tests ./tests
COPY workflows ./workflows

# GPL-licensed engines (COBRApy, E-Cell4) run subprocess-isolated per
# NOTICE.md - installing them into the same image is fine; it's process
# isolation at run time that matters, not image separation.
RUN pip install --no-cache-dir -e ".[dev,demo,lab,pipelines]" \
    -e plugins/hello_data -e plugins/hello_sim -e plugins/hello_ai \
    -e plugins/tellurium_sim -e plugins/copasi_sim -e plugins/cobrapy_fba \
    -e plugins/uniprot_data -e plugins/pdb_data -e plugins/alphafold_data \
    -e plugins/reactome_data -e plugins/biomodels_data -e plugins/string_data \
    -e plugins/biogrid_data -e plugins/cellxgene_data -e plugins/kegg_data \
    -e plugins/chembl_data -e plugins/depmap_data -e plugins/scperturb_data \
    -e plugins/aging_expression_data -e plugins/collectri_data -e plugins/pubchem_data \
    -e plugins/openmm_md -e plugins/grn_inference -e plugins/boolean_qual_sim \
    -e plugins/ecell4_spatial -e plugins/perturbation_baselines \
    -e plugins/llm_orchestrator -e plugins/esmc_embedding

CMD ["pytest", "-q"]
