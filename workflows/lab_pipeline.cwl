#!/usr/bin/env cwl-runner
# Phase 11: fit -> apply -> simulate (2 adapters) -> benchmark, as a real
# CWL workflow (roadmap bullet: "CWL pipeline definitions for common
# multi-step workflows"). Each step is a thin CommandLineTool wrapping one
# of scripts/lab_pipeline/*.py, which in turn call the same cradle.lab
# functions tests/test_lab_api.py already verifies directly — this file
# adds orchestration, not new logic.
#
# Run: cwltool workflows/lab_pipeline.cwl --sbml <model.xml> \
#        --observed_data <data.json> --fit_spec <fit_spec.json> \
#        --species U --species V --tolerance 0.01
cwlVersion: v1.2
class: Workflow

requirements:
  MultipleInputFeatureRequirement: {}

inputs:
  sbml: File
  observed_data: File
  fit_spec: File
  species: "string[]"
  benchmark_species: string
  tolerance: float

outputs:
  estimation_report:
    type: File
    outputSource: fit/estimation_report
  fitted_sbml:
    type: File
    outputSource: apply/fitted_sbml
  benchmark_report:
    type: File
    outputSource: benchmark/benchmark_report

steps:
  fit:
    run:
      class: CommandLineTool
      baseCommand: [python]
      arguments: ["--output", "estimation_report.json"]
      inputs:
        script:
          type: File
          default: {class: File, location: "../scripts/lab_pipeline/fit_step.py"}
          inputBinding: {position: 1}
        sbml: {type: File, inputBinding: {prefix: --sbml}}
        observed_data: {type: File, inputBinding: {prefix: --observed-data}}
        fit_spec: {type: File, inputBinding: {prefix: --fit-spec}}
      outputs:
        estimation_report:
          type: File
          outputBinding: {glob: estimation_report.json}
    in:
      sbml: sbml
      observed_data: observed_data
      fit_spec: fit_spec
    out: [estimation_report]

  apply:
    run:
      class: CommandLineTool
      baseCommand: [python]
      arguments: ["--sbml-out", "model_fitted.xml"]
      inputs:
        script:
          type: File
          default: {class: File, location: "../scripts/lab_pipeline/apply_step.py"}
          inputBinding: {position: 1}
        sbml_in: {type: File, inputBinding: {prefix: --sbml-in}}
        estimation_report: {type: File, inputBinding: {prefix: --estimation-report}}
      outputs:
        fitted_sbml:
          type: File
          outputBinding: {glob: model_fitted.xml}
    in:
      sbml_in: sbml
      estimation_report: fit/estimation_report
    out: [fitted_sbml]

  simulate_tellurium:
    run:
      class: CommandLineTool
      baseCommand: [python]
      arguments: ["--adapter", "tellurium", "--output", "result_tellurium.json"]
      inputs:
        script:
          type: File
          default: {class: File, location: "../scripts/lab_pipeline/simulate_step.py"}
          inputBinding: {position: 1}
        sbml: {type: File, inputBinding: {prefix: --sbml}}
        species: {type: "string[]", inputBinding: {prefix: --species}}
      outputs:
        result:
          type: File
          outputBinding: {glob: result_tellurium.json}
    in:
      sbml: apply/fitted_sbml
      species: species
    out: [result]

  simulate_copasi:
    run:
      class: CommandLineTool
      baseCommand: [python]
      arguments: ["--adapter", "copasi", "--output", "result_copasi.json"]
      inputs:
        script:
          type: File
          default: {class: File, location: "../scripts/lab_pipeline/simulate_step.py"}
          inputBinding: {position: 1}
        sbml: {type: File, inputBinding: {prefix: --sbml}}
        species: {type: "string[]", inputBinding: {prefix: --species}}
      outputs:
        result:
          type: File
          outputBinding: {glob: result_copasi.json}
    in:
      sbml: apply/fitted_sbml
      species: species
    out: [result]

  benchmark:
    run:
      class: CommandLineTool
      baseCommand: [python]
      arguments: ["--output", "benchmark.json"]
      inputs:
        script:
          type: File
          default: {class: File, location: "../scripts/lab_pipeline/benchmark_step.py"}
          inputBinding: {position: 1}
        results:
          type: File[]
          inputBinding: {prefix: --results}
        species: {type: string, inputBinding: {prefix: --species}}
        tolerance: {type: float, inputBinding: {prefix: --tolerance}}
      outputs:
        benchmark_report:
          type: File
          outputBinding: {glob: benchmark.json}
    in:
      results:
        source: [simulate_tellurium/result, simulate_copasi/result]
        linkMerge: merge_flattened
      species: benchmark_species
      tolerance: tolerance
    out: [benchmark_report]
