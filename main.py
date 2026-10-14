"""Payment Follow-up: превращает сырую выгрузку транзакций в готовый рабочий отчёт для саппорта.

Запуск:  python main.py                       — обработать input/sample_export.csv
         python main.py путь/к/выгрузке.csv   — обработать свою выгрузку
"""

import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import followup
import report

ROOT = Path(__file__).parent


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "input" / "sample_export.csv"
    df = followup.load_export(source)
    blocks = followup.build_followup(df)
    summaries = followup.build_summaries(df, blocks)

    out = report.save_report(blocks, summaries, ROOT / "output" / f"followup_{datetime.now():%Y-%m-%d_%H-%M-%S}.xlsx")

    print(f"Транзакций: {len(df)}, пользователей с проблемами: {len(blocks)}")
    for action, count in Counter(b["action"] for b in blocks).most_common():
        print(f"  {action}: {count}")
    print(f"Отчёт: {out}")


if __name__ == "__main__":
    main()
