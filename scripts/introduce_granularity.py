"""Generate event-level support and finance sources from the aggregate seeds."""

import csv
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"
RAW = ROOT / "data" / "raw"
GROUND_TRUTH = ROOT / "data" / "ground_truth" / "entity_mapping.csv"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generate_support():
    tickets = []
    sequence = 1
    first_date = date(2025, 2, 1)

    for customer_index, customer in enumerate(
        read_csv(SEED / "support_customers.csv")
    ):
        for ticket_index in range(int(customer["ticket_count"])):
            tickets.append(
                {
                    "ticket_id": f"TICKET-{sequence:06d}",
                    "customer_ref": customer["customer_ref"],
                    "full_name": customer["full_name"],
                    "mail": customer["mail"],
                    "country_name": customer["country_name"],
                    "created_at": str(
                        first_date + timedelta(days=customer_index + ticket_index)
                    ),
                }
            )
            sequence += 1

    write_csv(
        RAW / "support.csv",
        [
            "ticket_id",
            "customer_ref",
            "full_name",
            "mail",
            "country_name",
            "created_at",
        ],
        tickets,
    )
    return {row["customer_ref"] for row in tickets}, len(tickets)


def generate_finance():
    transactions = []
    sequence = 1
    first_date = date(2025, 2, 3)

    for account_index, account in enumerate(read_csv(SEED / "finance_accounts.csv")):
        transaction_count = account_index % 4 + 1
        total_cents = int(Decimal(account["revenue"]) * 100)
        base_cents, remainder = divmod(total_cents, transaction_count)

        for transaction_index in range(transaction_count):
            amount_cents = base_cents + (
                1 if transaction_index < remainder else 0
            )
            transactions.append(
                {
                    "transaction_id": f"TX-{sequence:06d}",
                    "account_id": account["account_id"],
                    "customer_name": account["customer_name"],
                    "contact_email": account["contact_email"],
                    "country_code": account["country_code"],
                    "amount": f"{Decimal(amount_cents) / 100:.2f}",
                    "transaction_date": str(
                        first_date + timedelta(days=account_index + transaction_index)
                    ),
                }
            )
            sequence += 1

    write_csv(
        RAW / "finance.csv",
        [
            "transaction_id",
            "account_id",
            "customer_name",
            "contact_email",
            "country_code",
            "amount",
            "transaction_date",
        ],
        transactions,
    )
    return len(transactions)


def update_entity_ground_truth(observed_support_refs):
    rows = read_csv(GROUND_TRUTH)
    for row in rows:
        if row["support_customer_ref"] not in observed_support_refs:
            row["support_customer_ref"] = ""
    write_csv(GROUND_TRUTH, list(rows[0]), rows)


def main():
    support_refs, ticket_count = generate_support()
    transaction_count = generate_finance()
    update_entity_ground_truth(support_refs)
    print(f"Generated {ticket_count} support tickets")
    print(f"Generated {transaction_count} finance transactions")
    print(f"Observed support customers: {len(support_refs)}")


if __name__ == "__main__":
    main()
