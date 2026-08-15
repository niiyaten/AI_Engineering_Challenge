from pathlib import Path

from rag_recovery.executors.tm_invoice_difference import assess_tm_invoice_evidence


def test_id6_evidence_handles_visual_line_break_in_timesheet() -> None:
    chunks = [
        {
            "locator": "page:1",
            "text": (
                "本契約はTime & Materialsであり、実績工数に基づき精算する。"
                "実績工数の最終確定値は提示資料に含まれないため、請求金額欄は"
                "見込工数170時間を用いた精算想定値として記載する。"
                "実請求時は月次タイム\nシート確定値を正とする。"
            ),
        }
    ]
    result = assess_tm_invoice_evidence(chunks)
    assert result["indeterminable"] is True
    assert result["timesheet_is_authoritative"] is True


def test_specialized_executors_are_actually_executed_before_remaining_fallback() -> None:
    worker = Path("src/rag_recovery/audit50_worker.py").read_text(encoding="utf-8")
    loop = worker.index("for executor in SPECIALIZED_EXECUTORS")
    execute = worker.index("candidate = executor.execute", loop)
    remaining = worker.index("Remaining50GeneralizationExecutor().execute")
    assert loop < execute < remaining


def test_third_audit_remaining_fixes_are_present() -> None:
    source = Path(
        "src/rag_recovery/executors/remaining50_generalization.py"
    ).read_text(encoding="utf-8")
    assert "fixed settlement fallback from contract gross" in source
    assert "shown=f'{d:.8f}'" in source or 'shown=f"{d:.8f}"' in source
    assert "math.trunc(d*10**8)/10**8" not in source
