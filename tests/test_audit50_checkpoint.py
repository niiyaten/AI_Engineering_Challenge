from pathlib import Path
import csv

ROOT=Path(__file__).resolve().parents[1]

def test_audit50_question_set_is_questions_only_and_50_unique():
    rows=list(csv.DictReader((ROOT/'questions/audit50_questions.csv').open(encoding='utf-8-sig',newline='')))
    assert len(rows)==50
    assert len({int(r['index']) for r in rows})==50
    assert set(rows[0])=={'index','question'}

def test_runtime_does_not_read_expected_or_prior_answers():
    runtime='\n'.join((ROOT/'src/rag_recovery'/name).read_text(encoding='utf-8') for name in ('audit50_cli.py','audit50_worker.py'))
    assert 'expected_audit50' not in runtime
    assert 'manual_audit50' not in runtime
    assert 'predictions_manual' not in runtime
    assert 'fact_catalog=None' in runtime

def test_validation_is_separate_from_runtime():
    assert (ROOT/'validation/expected_audit50.csv').exists()
    assert (ROOT/'src/rag_recovery/audit50_verify.py').exists()
