"""Бизнес-правила: какое действие нужно по каждому пользователю и какой текст ему отправить."""

# Действия (колонка Action)
RESOLVED = "Resolved by user"      # после ошибки пользователь сам успешно оплатил
CONTACT = "Contact user"           # нужен тикет/письмо пользователю
CRM = "Auto reminder (CRM)"        # «мягкая» ошибка — хватит автоматического напоминания
ESCALATE = "Escalate to provider"  # проблема на стороне провайдера, пользователь не виноват

# Пользователь сам бросил оплату — ему достаточно автоматического напоминания
SOFT_CODES = {"ERR_CANCELLED_BY_USER", "ERR_CANCELLED_TIMEOUT", "WAITING_3D_SECURE"}
PROVIDER_CODES = {"ERR_PROVIDER_UNAVAILABLE"}

# Шаблоны писем: код ошибки -> язык -> текст. (NAME) заменяется на имя пользователя.
TEMPLATES = {
    "ERR_DECLINED_NO_FUNDS": {
        "EN": "Hi (NAME), your payment didn't go through due to insufficient funds. "
              "You can try a smaller amount or another payment method.",
        "DE": "Hallo (NAME), Ihre Zahlung wurde wegen unzureichender Deckung abgelehnt. "
              "Versuchen Sie einen kleineren Betrag oder eine andere Zahlungsmethode.",
        "IT": "Ciao (NAME), il pagamento non è andato a buon fine per fondi insufficienti. "
              "Prova con un importo minore o un altro metodo di pagamento.",
    },
    "ERR_DECLINED_BANK_REFUSAL": {
        "EN": "Hi (NAME), your bank declined the payment. Please contact your bank "
              "to allow the transaction, or use another payment method.",
        "DE": "Hallo (NAME), Ihre Bank hat die Zahlung abgelehnt. Bitte kontaktieren Sie Ihre Bank "
              "oder verwenden Sie eine andere Zahlungsmethode.",
        "IT": "Ciao (NAME), la tua banca ha rifiutato il pagamento. Contatta la banca "
              "oppure usa un altro metodo di pagamento.",
    },
    "ERR_DECLINED_3D_EXPIRED": {
        "EN": "Hi (NAME), the 3D Secure confirmation time has expired. "
              "Please try again and confirm the payment in your banking app.",
        "DE": "Hallo (NAME), die Zeit für die 3D-Secure-Bestätigung ist abgelaufen. "
              "Bitte versuchen Sie es erneut und bestätigen Sie die Zahlung in Ihrer Banking-App.",
        "IT": "Ciao (NAME), il tempo per la conferma 3D Secure è scaduto. "
              "Riprova e conferma il pagamento nell'app della tua banca.",
    },
    "ERR_DECLINED_LIMIT_EXCEEDED": {
        "EN": "Hi (NAME), the payment exceeded your card limit. "
              "Try a smaller amount or increase the limit in your banking app.",
        "DE": "Hallo (NAME), die Zahlung hat Ihr Kartenlimit überschritten. "
              "Versuchen Sie einen kleineren Betrag oder erhöhen Sie das Limit in Ihrer Banking-App.",
        "IT": "Ciao (NAME), il pagamento ha superato il limite della carta. "
              "Prova con un importo minore o aumenta il limite nell'app della banca.",
    },
    "ERR_CRYPTO_UNDERPAID": {
        "EN": "Hi (NAME), we received less crypto than required — usually the network fee was deducted "
              "from the amount. Please send the remaining difference or contact us with the transaction hash.",
        "DE": "Hallo (NAME), wir haben weniger Krypto erhalten als erforderlich — meist wurde die Netzwerkgebühr "
              "abgezogen. Bitte senden Sie die Differenz oder kontaktieren Sie uns mit dem Transaktions-Hash.",
        "IT": "Ciao (NAME), abbiamo ricevuto meno crypto del necessario — di solito la commissione di rete è stata "
              "detratta dall'importo. Invia la differenza o contattaci con l'hash della transazione.",
    },
}
LANGUAGES = {"DEU": "DE", "AUT": "DE", "CHE": "DE", "ITA": "IT"}  # остальные страны — английский


def message_for(status_code: str, country: str, first_name: str) -> str:
    template = TEMPLATES.get(status_code, {})
    text = template.get(LANGUAGES.get(country, "EN")) or template.get("EN", "")
    return text.replace("(NAME)", first_name)


def decide(attempts: list[dict]) -> dict | None:
    """Решение по блоку «пользователь + день». attempts отсортированы по времени.

    Возвращает {"action", "message", "note"} для последней попытки
    или None, если у пользователя за день не было проблем.
    """
    if all(a["status_code"] == "SUCCESS" for a in attempts):
        return None

    last = attempts[-1]
    failed = [a for a in attempts if a["status_code"] != "SUCCESS"]
    note = f"{len(failed)} failed attempts" if len(failed) >= 3 else ""

    if last["status_code"] == "SUCCESS":
        return {"action": RESOLVED, "message": "", "note": note}
    if last["status_code"] in PROVIDER_CODES:
        return {"action": ESCALATE, "message": "", "note": f'{last["provider"]} unavailable'}
    if last["status_code"] in SOFT_CODES:
        return {"action": CRM, "message": "", "note": note}
    return {
        "action": CONTACT,
        "message": message_for(last["status_code"], last["country"], last["first_name"]),
        "note": note,
    }
