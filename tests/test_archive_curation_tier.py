from __future__ import annotations

from cradle.substrate import archive, experiment, model
from cradle.substrate.examples.toggle_switch import build_annotated_document


def _build_archive(tmp_path) -> str:
    sbml_path = str(tmp_path / "toggle_switch.xml")
    sedml_path = str(tmp_path / "experiment.xml")
    archive_path = str(tmp_path / "toggle_switch.omex")

    model.write_sbml(build_annotated_document(), sbml_path)
    sedml_doc = experiment.build_uniform_time_course_sedml(
        "toggle_switch.xml", ["U", "V"], output_end_time=1.0, number_of_steps=5
    )
    experiment.write_sedml(sedml_doc, sedml_path)
    archive.package_combine_archive(
        archive_path, sbml_path, "toggle_switch.xml", sedml_path, "experiment.xml"
    )
    return archive_path


def test_freshly_built_archive_defaults_to_non_curated(tmp_path):
    archive_path = _build_archive(tmp_path)
    assert archive.read_curation_tier(archive_path) == {
        "tier": "non-curated",
        "model_curie": "",
    }


def test_embedding_the_tier_survives_a_plain_file_copy(tmp_path):
    import shutil

    archive_path = _build_archive(tmp_path)
    archive.embed_curation_tier(archive_path, "curated", "biomodels.db:BIOMD0000000507")

    copied_path = str(tmp_path / "copied_elsewhere.omex")
    shutil.copy(archive_path, copied_path)

    assert archive.read_curation_tier(copied_path) == {
        "tier": "curated",
        "model_curie": "biomodels.db:BIOMD0000000507",
    }
