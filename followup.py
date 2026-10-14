"""Обработка выгрузки: группировка по пользователю и дню, решения по каждому блоку, сводки."""

from pathlib import Path

import pandas as pd

import rules

REQUIRED = ["id", "user_id", "created", "state", "status_code", "method", "provider",
            "amount", "currency", "email", "first_name", "country"]


def load_export(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"user_id": str, "id": str})
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SystemExit(f"В выгрузке нет колонок: {', '.join(missing)}")

    df = df.drop_duplicates("id")
    df["created"] = pd.to_datetime(df["created"])
    df["date"] = df["created"].dt.date
    df["status_code"] = df["status_code"].str.strip().str.upper()
    df["is_success"] = df["status_code"] == "SUCCESS"
    df["success_amount"] = df["amount"].where(df["is_success"], 0)
    return df.sort_values(["date", "user_id", "created"])


def build_followup(df: pd.DataFrame) -> list[dict]:
    """Блоки для листа Follow-up: только пользователи, у которых за день была ошибка."""
    blocks = []
    for (date, user_id), group in df.groupby(["date", "user_id"], sort=True):
        attempts = group.to_dict("records")
        decision = rules.decide(attempts)
        if decision:
            blocks.append({"date": date, "user_id": user_id, "attempts": attempts, **decision})
    return blocks


def _rate(series) -> float:
    return round(series.mean() * 100, 1)


def build_summaries(df: pd.DataFrame, blocks: list[dict]) -> dict[str, pd.DataFrame]:
    actions = pd.DataFrame([{"date": b["date"], "action": b["action"]} for b in blocks])

    daily = df.groupby("date").agg(
        transactions=("id", "count"),
        users=("user_id", "nunique"),
        success_rate=("is_success", _rate),
        volume_eur=("success_amount", "sum"),
    )
    if not actions.empty:
        daily = daily.join(pd.crosstab(actions["date"], actions["action"]), how="left").fillna(0)

    providers = (df.groupby(["method", "provider"])
                   .agg(transactions=("id", "count"), success_rate=("is_success", _rate))
                   .reset_index()
                   .sort_values("success_rate"))

    failed = df[~df["is_success"]]
    errors = (failed.groupby("status_code")
                    .agg(count=("id", "count"), users=("user_id", "nunique"))
                    .assign(share=lambda t: (t["count"] / t["count"].sum() * 100).round(1))
                    .sort_values("count", ascending=False)
                    .reset_index())

    return {"daily": daily.reset_index(), "providers": providers, "errors": errors}
