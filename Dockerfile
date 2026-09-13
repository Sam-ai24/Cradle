# Phase 11: local/cloud container packaging.
#
# Originally written on Windows without Docker (Phase 11). First actual
# build attempted 2026-09-13 on macOS with Docker 29. See also
# Dockerfile.flagship — a thinner image that only needs what the E. coli
# essentiality flagship uses, verified if the full plugin set fails to
# build (Geneformer/ESM-C weights are not required for pytest of core).
#
#   docker build -t cradle .
#   docker run --rm -it cradle pytest -q
# antimony>=3.1 has no linux/arm64 wheel (confirmed 2026-09-13).
FROM --platform=linux/amd64 python:3.11-slim

# python-libsbml / libcombine wheels need libexpat at runtime
# (confirmed 2026-09-13: ImportError: libexpat.so.1 on python:3.11-slim).
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

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
    -e plugins/llm_orchestrator -e plugins/esmc_embedding -e plugins/geneformer_embedding

CMD ["pytest", "-q"]
