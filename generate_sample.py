"""Генерирует выдуманную выгрузку транзакций из бэк-офиса платёжной системы (CSV).

Все данные синтетические: пользователи, почты и суммы случайные.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).parent / "input" / "sample_export.csv"
random.seed(42)

FIRST_NAMES = ["Anna", "Lukas", "Marco", "Julia", "Piotr", "Elena", "Jonas", "Sofia",
               "Mateo", "Laura", "Felix", "Chiara", "Tomasz", "Emma", "David", "Nina"]
COUNTRIES = ["DEU", "DEU", "DEU", "AUT", "ITA", "ITA", "POL", "ESP", "GBR"]
# метод оплаты -> (провайдеры, базовая вероятность успеха)
METHODS = {
    "Card":          (["PayFlow", "CardHub"], 0.62),
    "Apple Pay":     (["PayFlow"], 0.80),
    "E-wallet":      (["WalletPro"], 0.75),
    "Bank transfer": (["OpenBankX"], 0.68),
    "Crypto":        (["CoinGate"], 0.85),
}
# Коды ошибок и их частота — у каждого метода свои (у крипты нет 3DS, у банковского перевода нет лимита карты)
CARD_CODES = {
    "ERR_DECLINED_NO_FUNDS": 22, "ERR_DECLINED_BANK_REFUSAL": 16, "ERR_DECLINED_3D_EXPIRED": 12,
    "ERR_CANCELLED_BY_USER": 18, "ERR_CANCELLED_TIMEOUT": 9, "ERR_DECLINED_LIMIT_EXCEEDED": 8,
    "ERR_PROVIDER_UNAVAILABLE": 6, "WAITING_3D_SECURE": 9,
}
FAIL_CODES = {
    "Card": CARD_CODES,
    "Apple Pay": {"ERR_DECLINED_NO_FUNDS": 10, "ERR_DECLINED_BANK_REFUSAL": 8, "ERR_CANCELLED_BY_USER": 10},
    "E-wallet": {"ERR_DECLINED_NO_FUNDS": 12, "ERR_CANCELLED_BY_USER": 10, "ERR_CANCELLED_TIMEOUT": 6,
                 "ERR_PROVIDER_UNAVAILABLE": 3},
    "Bank transfer": {"ERR_DECLINED_BANK_REFUSAL": 10, "ERR_CANCELLED_BY_USER": 12, "ERR_CANCELLED_TIMEOUT": 8},
    "Crypto": {"ERR_CRYPTO_UNDERPAID": 10, "ERR_CANCELLED_TIMEOUT": 8, "ERR_PROVIDER_UNAVAILABLE": 2},
}
BAD_PROVIDER = "CardHub"  # у этого провайдера конверсия заметно хуже — увидим в сводке


def make_users(n: int) -> list[dict]:
    users = []
    for i in range(n):
        name = random.choice(FIRST_NAMES)
        users.append({
            "user_id": str(100000 + i * 37),
            "first_name": name,
            "email": f"{name.lower()}.{random.randint(10, 99)}@example.com",
            "country": random.choice(COUNTRIES),
            "method": random.choice(list(METHODS)),
        })
    return users


def make_attempts(user: dict, day: datetime, tx_counter: list) -> list[dict]:
    providers, success_rate = METHODS[user["method"]]
    provider = random.choice(providers)
    if provider == BAD_PROVIDER:
        success_rate -= 0.2
    time = day + timedelta(hours=random.randint(8, 22), minutes=random.randint(0, 59))
    amount = random.choice([20, 25, 50, 50, 100, 100, 150, 200, 500])

    rows = []
    for _ in range(random.choice([1, 1, 1, 2, 2, 3, 4])):  # пользователь может пробовать несколько раз
        ok = random.random() < success_rate
        codes = FAIL_CODES[user["method"]]
        code = "SUCCESS" if ok else random.choices(list(codes), weights=codes.values())[0]
        state = "SUCCESS" if ok else ("PENDING" if code.startswith("WAITING") else "FAILED")
        tx_counter[0] += 1
        rows.append({
            "id": f"TX{tx_counter[0]:07d}", "user_id": user["user_id"],
            "created": time.strftime("%Y-%m-%d %H:%M:%S"), "state": state, "status_code": code,
            "method": user["method"], "provider": provider, "amount": amount, "currency": "EUR",
            "email": user["email"], "first_name": user["first_name"], "country": user["country"],
        })
        if ok:
            break
        time += timedelta(minutes=random.randint(1, 25))
    return rows


def main():
    users = make_users(260)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    counter, rows = [0], []
    for days_ago in (3, 2, 1):
        day = today - timedelta(days=days_ago)
        for user in random.sample(users, 140):
            rows += make_attempts(user, day, counter)

    random.shuffle(rows)  # в реальных выгрузках порядок строк обычно произвольный
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Сгенерировано транзакций: {len(rows)} → {OUT}")


if __name__ == "__main__":
    main()
