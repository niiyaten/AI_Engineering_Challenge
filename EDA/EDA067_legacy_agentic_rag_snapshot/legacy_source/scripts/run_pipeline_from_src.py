"""作業ツリーの src 実装を優先して正式パイプラインを起動する。"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# カレントディレクトリ直下の同名パッケージより、変更対象の src を必ず優先する。
sys.path.insert(0, str(SRC))

from rag_competition.pipeline import main  # noqa: E402


if __name__ == "__main__":
    main()
