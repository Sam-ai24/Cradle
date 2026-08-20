"""Phase 4: build, validate, and publish Cradle's first fully curated model.

Run once, from the repo root, with the Phase 1/2 dependencies installed
(`pip install -e ".[dev,demo]" -e plugins/tellurium_sim -e plugins/copasi_sim`):

    python scripts/curate_repressilator.py

Writes models/repressilator/repressilator.omex and curation.json. This
script is not part of the installed `cradle` package — it's the one-time
act of publishing an artifact, not a runtime capability.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cradle.analysis import amplitude_range, count_local_maxima  # noqa: E402
from cradle.curation import promote_to_curated, write_curation_record  # noqa: E402
from cradle.substrate import archive, experiment, model  # noqa: E402
from cradle.substrate.examples.repressilator import (  # noqa: E402
    SPECIES_IDS,
    build_annotated_document,
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "models" / "repressilator"
OUTPUT_END_TIME = 1000.0
NUMBER_OF_STEPS = 500
MIN_EXPECTED_PEAKS = 3  # published behavior is "sustained oscillations"; well below the ~9 observed


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sbml_path = str(OUTPUT_DIR / "repressilator.xml")
    sedml_path = str(OUTPUT_DIR / "experiment.xml")
    archive_path = str(OUTPUT_DIR / "repressilator.omex")

    print("Downloading and annotating the real curated SBML from BioModels...")
    document = build_annotated_document()
    model.write_sbml(document, sbml_path)

    print("Building the SED-ML experiment and packaging the COMBINE archive...")
    sedml_doc = experiment.build_uniform_time_course_sedml(
        "repressilator.xml",
        SPECIES_IDS,
        output_end_time=OUTPUT_END_TIME,
        number_of_steps=NUMBER_OF_STEPS,
    )
    experiment.write_sedml(sedml_doc, sedml_path)
    archive.package_combine_archive(
        archive_path, sbml_path, "repressilator.xml", sedml_path, "experiment.xml"
    )

    print("Running on Tellurium and COPASI to gather independent evidence...")
    import basico
    import tellurium as te

    tellurium_results = te.executeCombineArchive(archive_path, createOutputs=True)
    tellurium_report = next(iter(tellurium_results.values()))["dataGenerators"]
    tellurium_px = [row[0] for row in tellurium_report["dg_PX"]]

    copasi_model = basico.load_model(sbml_path)
    data_frame = basico.run_time_course(
        0.0, OUTPUT_END_TIME, NUMBER_OF_STEPS, model=copasi_model, method="deterministic"
    )
    species_info = basico.get_species(model=copasi_model)
    name_by_sbml_id = dict(zip(species_info["sbml_id"], species_info.index))
    copasi_px = data_frame[name_by_sbml_id["PX"]].tolist()

    tellurium_peaks = count_local_maxima(tellurium_px)
    copasi_peaks = count_local_maxima(copasi_px)
    tellurium_range = amplitude_range(tellurium_px)
    copasi_range = amplitude_range(copasi_px)

    print(f"Tellurium: {tellurium_peaks} peaks, range {tellurium_range}")
    print(f"COPASI:    {copasi_peaks} peaks, range {copasi_range}")

    evidence_checks = {
        "miriam_annotation_complete": True,  # build_annotated_document() already asserted this
        "tellurium_shows_sustained_oscillation": tellurium_peaks >= MIN_EXPECTED_PEAKS,
        "copasi_shows_sustained_oscillation": copasi_peaks >= MIN_EXPECTED_PEAKS,
        "tellurium_and_copasi_agree_on_peak_count": tellurium_peaks == copasi_peaks,
        "tellurium_and_copasi_agree_on_amplitude_range": (
            abs(tellurium_range[1] - copasi_range[1]) / max(tellurium_range[1], copasi_range[1])
            < 0.01
        ),
    }
    print("Evidence:", evidence_checks)

    record = promote_to_curated(
        model_curie="biomodels.db:BIOMD0000000012",
        title="Elowitz2000 - Repressilator",
        evidence_checks=evidence_checks,
        adapters_used=["tellurium", "copasi"],
    )
    write_curation_record(record, OUTPUT_DIR / "curation.json")
    print(f"\nPromoted to curated. Archive: {archive_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
