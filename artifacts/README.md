# Artifacts

Generated CSV outputs are grouped here so the project root stays clean.

- `final_answers/`: raw agent outputs, usually `id,question,answer`.
- `submissions/`: submission-ready or submission-like CSVs, usually `id,response`.
- `reports/`: evaluation or accuracy report CSVs.
- `ground_truth/`: local ground-truth CSVs used only for evaluation, not by the runtime pipeline.

Keep `questions.csv` and `sample_submission.csv` in the project root because the scripts use them as default inputs.
