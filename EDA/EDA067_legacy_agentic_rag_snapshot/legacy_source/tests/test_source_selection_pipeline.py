from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class SourceSelectionPipelineTest(unittest.TestCase):
    def test_fresh_build_from_artificial_raw(self) -> None:
        root = Path(__file__).resolve().parents[1]
        run_id = "unittest_source_selection"
        work_dir = root / "data" / "work" / run_id
        output_dir = root / "data" / "output" / run_id
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(output_dir, ignore_errors=True)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            raw_root = tmp_root / "共有ドライブ"
            project_dir = raw_root / "プロジェクト" / "テスト株式会社" / "06.報告書"
            project_dir.mkdir(parents=True)
            (project_dir / "最終報告.md").write_text("# 最終報告\nKPIはRecallです。\n", encoding="utf-8")
            data_dir = raw_root / "プロジェクト" / "テスト株式会社" / "03.データ"
            data_dir.mkdir(parents=True)
            (data_dir / "train.csv").write_text("id,value\n1,10\n2,20\n", encoding="utf-8")
            glossary_dir = raw_root / "社内管理"
            glossary_dir.mkdir(parents=True)
            (glossary_dir / "用語.md").write_text("# 用語\n", encoding="utf-8")
            questions_path = tmp_root / "questions_valid.csv"
            questions_path.write_text(
                "index,question,answer\n0,テスト株式会社の最終報告でKPIは何ですか。,Recall\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "rag_competition.pipeline",
                    "--mode",
                    "source-selection",
                    "--fresh",
                    "--split",
                    "valid",
                    "--run-id",
                    run_id,
                    "--raw-root",
                    str(raw_root),
                    "--questions-path",
                    str(questions_path),
                    "--api-mode",
                    "off",
                    "--no-render-pdf-pages",
                ],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        manifest = json.loads((work_dir / "run_manifest.json").read_text(encoding="utf-8"))
        summary = json.loads((output_dir / "source_selection_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "completed")
        self.assertGreaterEqual(summary["raw_file_count"], 2)
        self.assertGreaterEqual(summary["search_record_count"], 2)
        self.assertEqual(summary["execution_plan_count"], 1)
        self.assertNotIn("data/processed", manifest["raw_root"])
        self.assertNotIn("EDA/", manifest["raw_root"])
        self.assertTrue((work_dir / "planning" / "execution_plans.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
