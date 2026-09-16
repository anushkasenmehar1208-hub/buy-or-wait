"""
Data loading and preprocessing module for Buy or Wait? financial decision engine.
Handles dataset file resolution, robust Decimal conversions, currency exchange,
image-extracted missing amounts, and structured record representation.
"""

from __future__ import annotations
import csv
import os
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Look for dataset in code/dataset if present, otherwise dataset/ at project root
if (PROJECT_ROOT / "code" / "dataset").exists():
    DATASET_DIR = PROJECT_ROOT / "code" / "dataset"
else:
    DATASET_DIR = PROJECT_ROOT / "dataset"

# Missing financial event amounts verified and extracted from dataset/media/images/*.png
IMAGE_EVENT_AMOUNTS: Dict[str, Decimal] = {
    "event_253": Decimal("4365000"),       # image_01: net pay IDR 4,365,000
    "event_1442": Decimal("100000"),      # image_02: rent balance due INR 1,00,000
    "event_1545": Decimal("41272"),       # image_03: bulk groceries INR 41,272
    "event_1700": Decimal("2854"),        # image_04: grocery order INR 2,854
    "event_1786": Decimal("822.05"),      # image_05: telecom bill after due date INR 822.05
    "event_3051": Decimal("1995"),        # image_06: grocery invoice INR 1,995
    "event_3231": Decimal("8528"),        # image_07: restaurant invoice INR 8,528
    "event_4535": Decimal("15339"),       # image_08: property maintenance INR 15,339
    "event_5170": Decimal("723"),         # image_09: water bill INR 723
    "event_6033": Decimal("79679.26"),    # image_10: large grocery invoice INR 79,679.26
    "event_6859": Decimal("3650"),        # image_11: hospital bill payable INR 3,650
    "event_7307": Decimal("33.50"),       # image_12: taxi fare USD 33.50
    "event_7941": Decimal("2298"),        # image_13: tote bag order INR 2,298
    "event_9421": Decimal("4543"),        # image_14: pharmacy purchase INR 4,543
    "event_9806": Decimal("9968"),        # image_15: airline ticket INR 9,968
    "event_10521": Decimal("393.22"),     # image_16: EV charging wallet INR 393.22
}


def parse_date(date_str: str) -> Optional[date]:
    if not date_str or not date_str.strip():
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def parse_decimal(val: Any) -> Optional[Decimal]:
    if val is None:
        return None
    s = str(val).strip().replace(",", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


class FXConverter:
    """Handles currency conversions using exchange_rates.csv with direct, inverted, and cross rates."""
    def __init__(self, rates_file: Path):
        self.rates: Dict[Tuple[str, str, str], Decimal] = {}
        self.all_dates: List[str] = []
        self._load(rates_file)

    def _load(self, filepath: Path):
        if not filepath.exists():
            return
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            dates_set = set()
            for r in reader:
                d = r["rate_date"].strip()
                fc = r["from_currency"].strip().upper()
                tc = r["to_currency"].strip().upper()
                rate = Decimal(r["rate"].strip())
                self.rates[(d, fc, tc)] = rate
                dates_set.add(d)
            self.all_dates = sorted(dates_set)

    def get_rate(self, from_curr: str, to_curr: str, as_of_date: date) -> Decimal:
        fc = from_curr.strip().upper()
        tc = to_curr.strip().upper()
        if fc == tc:
            return Decimal("1")

        date_str = as_of_date.strftime("%Y-%m-%d")
        
        # 1. Try exact date direct
        if (date_str, fc, tc) in self.rates:
            return self.rates[(date_str, fc, tc)]
        # 2. Try exact date inverse
        if (date_str, tc, fc) in self.rates:
            inv = self.rates[(date_str, tc, fc)]
            if inv != 0:
                return Decimal("1") / inv

        # Find latest available rate date on or before as_of_date
        candidate_dates = [d for d in self.all_dates if d <= date_str]
        if not candidate_dates:
            candidate_dates = self.all_dates  # fallback to nearest available

        for d in reversed(candidate_dates):
            if (d, fc, tc) in self.rates:
                return self.rates[(d, fc, tc)]
            if (d, tc, fc) in self.rates:
                inv = self.rates[(d, tc, fc)]
                if inv != 0:
                    return Decimal("1") / inv

        # 3. Cross-rate via intermediate currencies (USD, EUR)
        for mid in ["USD", "EUR"]:
            if mid != fc and mid != tc:
                r1 = self._find_single_rate(fc, mid, date_str)
                r2 = self._find_single_rate(mid, tc, date_str)
                if r1 is not None and r2 is not None:
                    return r1 * r2

        return Decimal("1")

    def _find_single_rate(self, fc: str, tc: str, date_str: str) -> Optional[Decimal]:
        if (date_str, fc, tc) in self.rates:
            return self.rates[(date_str, fc, tc)]
        if (date_str, tc, fc) in self.rates:
            inv = self.rates[(date_str, tc, fc)]
            if inv != 0:
                return Decimal("1") / inv
        candidate_dates = [d for d in self.all_dates if d <= date_str]
        if not candidate_dates:
            candidate_dates = self.all_dates
        for d in reversed(candidate_dates):
            if (d, fc, tc) in self.rates:
                return self.rates[(d, fc, tc)]
            if (d, tc, fc) in self.rates:
                inv = self.rates[(d, tc, fc)]
                if inv != 0:
                    return Decimal("1") / inv
        return None

    def convert(self, amount: Decimal, from_curr: str, to_curr: str, as_of_date: date) -> Decimal:
        if from_curr.strip().upper() == to_curr.strip().upper():
            return amount
        rate = self.get_rate(from_curr, to_curr, as_of_date)
        return amount * rate


class DataLoader:
    def __init__(self, dataset_dir: Optional[Path] = None):
        self.dir = dataset_dir or DATASET_DIR
        self.fx = FXConverter(self.dir / "exchange_rates.csv")
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.events_by_user: Dict[str, List[Dict[str, Any]]] = {}
        self.events_by_id: Dict[str, Dict[str, Any]] = {}
        self.payment_options_by_request: Dict[str, List[Dict[str, Any]]] = {}
        self.messages_by_user: Dict[str, List[Dict[str, Any]]] = {}
        self.messages_by_request: Dict[str, List[Dict[str, Any]]] = {}
        self.images_by_event: Dict[str, str] = {}
        self._load_all()

    def _load_all(self):
        self._load_profiles()
        self._load_images_map()
        self._load_events()
        self._load_payment_options()
        self._load_messages()

    def _load_profiles(self):
        filepath = self.dir / "financial_profiles.csv"
        if not filepath.exists():
            return
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                uid = r["user_id"].strip()
                max_inst = r.get("max_installment_months", "").strip()
                self.profiles[uid] = {
                    "user_id": uid,
                    "home_currency": r["home_currency"].strip().upper(),
                    "current_available_balance": parse_decimal(r["current_available_balance"]) or Decimal("0"),
                    "minimum_balance_to_keep": parse_decimal(r["minimum_balance_to_keep"]) or Decimal("0"),
                    "financial_priorities": [x.strip() for x in r.get("financial_priorities", "").split("|") if x.strip()],
                    "expense_categories_to_protect": [x.strip() for x in r.get("expense_categories_to_protect", "").split("|") if x.strip()],
                    "expense_categories_user_is_willing_to_reduce": [x.strip() for x in r.get("expense_categories_user_is_willing_to_reduce", "").split("|") if x.strip()],
                    "expense_categories_user_is_willing_to_stop": [x.strip() for x in r.get("expense_categories_user_is_willing_to_stop", "").split("|") if x.strip()],
                    "payment_methods_user_will_consider": [x.strip() for x in r.get("payment_methods_user_will_consider", "").split("|") if x.strip()],
                    "max_installment_months": int(max_inst) if max_inst and max_inst.isdigit() else None,
                }

    def _load_images_map(self):
        filepath = self.dir / "images.csv"
        if not filepath.exists():
            return
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                eid = r.get("related_event_id", "").strip()
                iid = r.get("image_id", "").strip()
                if eid:
                    self.images_by_event[eid] = iid

    def _load_events(self):
        filepath = self.dir / "financial_events.csv"
        if not filepath.exists():
            return
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                eid = r["event_id"].strip()
                uid = r["user_id"].strip()
                raw_amt = r.get("amount", "").strip()
                if not raw_amt and eid in IMAGE_EVENT_AMOUNTS:
                    amt = IMAGE_EVENT_AMOUNTS[eid]
                else:
                    amt = parse_decimal(raw_amt) or Decimal("0")

                min_amt = parse_decimal(r.get("minimum_allowed_amount", ""))

                ev = {
                    "event_id": eid,
                    "user_id": uid,
                    "event_type": r.get("event_type", "").strip(),
                    "description": r.get("description", "").strip(),
                    "category": r.get("category", "").strip().lower(),
                    "direction": r.get("direction", "").strip().lower(),
                    "amount": amt,
                    "currency": r.get("currency", "").strip().upper(),
                    "event_date": parse_date(r.get("event_date", "")),
                    "settlement_date": parse_date(r.get("settlement_date", "")),
                    "status": r.get("status", "").strip().lower(),
                    "linked_event_id": r.get("linked_event_id", "").strip(),
                    "flexibility": r.get("flexibility", "").strip().lower(),
                    "minimum_allowed_amount": min_amt,
                }
                if uid not in self.events_by_user:
                    self.events_by_user[uid] = []
                self.events_by_user[uid].append(ev)
                self.events_by_id[eid] = ev

    def _load_payment_options(self):
        filepath = self.dir / "request_payment_options.csv"
        if not filepath.exists():
            return
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                req_id = r["request_id"].strip()
                num_payments = int(r["number_of_payments"]) if r.get("number_of_payments") else 1
                freq = int(r["payment_frequency_days"]) if r.get("payment_frequency_days") and r["payment_frequency_days"].strip().isdigit() else None
                opt = {
                    "payment_option_id": r["payment_option_id"].strip(),
                    "request_id": req_id,
                    "payment_method": r["payment_method"].strip().lower(),
                    "payment_amount": parse_decimal(r.get("payment_amount")) or Decimal("0"),
                    "number_of_payments": num_payments,
                    "first_payment_date": parse_date(r.get("first_payment_date")),
                    "payment_frequency_days": freq,
                    "financing_fee": parse_decimal(r.get("financing_fee")) or Decimal("0"),
                    "total_payable_amount": parse_decimal(r.get("total_payable_amount")) or Decimal("0"),
                }
                if req_id not in self.payment_options_by_request:
                    self.payment_options_by_request[req_id] = []
                self.payment_options_by_request[req_id].append(opt)

    def _load_messages(self):
        filepath = self.dir / "messages.csv"
        if not filepath.exists():
            return
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                uid = r.get("user_id", "").strip()
                req_id = r.get("request_id", "").strip()
                msg = {
                    "message_id": r["message_id"].strip(),
                    "user_id": uid,
                    "request_id": req_id,
                    "related_event_id": r.get("related_event_id", "").strip(),
                    "sent_at": r.get("sent_at", "").strip(),
                    "source_type": r.get("source_type", "").strip().lower(),
                    "message_text": r.get("message_text", "").strip(),
                }
                if uid:
                    if uid not in self.messages_by_user:
                        self.messages_by_user[uid] = []
                    self.messages_by_user[uid].append(msg)
                if req_id:
                    if req_id not in self.messages_by_request:
                        self.messages_by_request[req_id] = []
                    self.messages_by_request[req_id].append(msg)

    def load_requests(self, filename: str = "requests.csv") -> List[Dict[str, Any]]:
        filepath = self.dir / filename
        reqs = []
        if not filepath.exists():
            return reqs
        with open(filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                partial_str = r.get("allows_partial_payment", "").strip().lower()
                reqs.append({
                    "request_id": r["request_id"].strip(),
                    "user_id": r["user_id"].strip(),
                    "request_date": parse_date(r["request_date"]),
                    "request_type": r.get("request_type", "").strip().lower(),
                    "requested_amount": parse_decimal(r["requested_amount"]) or Decimal("0"),
                    "desired_completion_date": parse_date(r["desired_completion_date"]),
                    "allows_partial_payment": partial_str in ("true", "1", "yes"),
                    "request_text": r.get("request_text", "").strip(),
                })
        return reqs
