import sys, csv, calendar, re
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict, Counter
from typing import Any, Dict, List, Set, Tuple

sys.path.insert(0, 'code')
from data_loader import DataLoader, parse_date, parse_decimal

def add_months(d: date, months: int = 1) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    max_day = calendar.monthrange(year, month)[1]
    day = min(d.day, max_day)
    return date(year, month, day)

def format_amount(val: Decimal, currency: str = "") -> str:
    if val == val.to_integral_value():
        return str(int(val))
    return f"{val:.2f}"


def build_decision_explanation(best: Dict[str, Any], req_amt: Decimal, home_curr: str,
                               min_bal: Decimal, safe_today: Decimal,
                               earliest_full_date, due_date: date) -> str:
    """Deterministic, data-driven explanation built only from computed decision facts."""
    status = best["status"]
    method = best["method"]
    changes = best.get("changes", "none")
    plan = best.get("plan", "none")
    min_str = f"{home_curr} {format_amount(min_bal, home_curr)}"
    amt_str = f"{home_curr} {format_amount(req_amt, home_curr)}"
    safe_str = f"{home_curr} {format_amount(safe_today, home_curr)}"
    earliest = earliest_full_date.strftime("%Y-%m-%d") if earliest_full_date else ""
    paid_minbuf = best.get("minbuf")

    if status == "not_affordable":
        base = (f"No safe plan can complete {amt_str} by {due_date.strftime('%Y-%m-%d')} "
                f"while keeping the {min_str} minimum balance intact.")
        if earliest:
            base += f" The earliest fully safe date, {earliest}, is after the deadline."
        else:
            base += f" At most {safe_str} is safe to pay today."
        return base
    if status == "affordable_now":
        return (f"Pay {amt_str} in full today. The balance stays above the {min_str} "
                f"minimum over the next 90 days.")
    detail = ""
    if paid_minbuf is not None:
        detail = (f" The plan keeps the balance at least "
                  f"{home_curr} {format_amount(paid_minbuf, home_curr)} above the minimum "
                  f"throughout the 90-day forecast.")
    if method == "partial_payment":
        rem = req_amt - safe_today
        return (f"Pay {safe_str} today and the remaining {home_curr} "
                f"{format_amount(rem, home_curr)} on {earliest or plan}.{detail}")
    if method == "installments":
        first_amt = plan.split("|")[0].split(":")[1] if plan and plan != "none" else format_amount(req_amt, home_curr)
        start = best["start_date"].strftime("%Y-%m-%d") if best.get("start_date") else earliest
        return (f"Use {best.get('num_payments', 0)} installments of {home_curr} {first_amt}, "
                f"starting {start}.{detail}")
    if method == "wait":
        return (f"Wait and pay {amt_str} in full on {earliest or 'the earliest safe date'}. "
                f"The full amount is not safe before then while maintaining the {min_str} "
                f"minimum balance.")
    if changes and changes != "none":
        return (f"After applying the selected spending changes ({changes}), pay {amt_str} "
                f"in full today.{detail}")
    return f"Proceed with {method} per the recommended plan ({plan}).{detail}"

loader = DataLoader()
expected = {r['request_id']: r for r in csv.DictReader(open('dataset/sample_requests.csv'))}
samples = loader.load_requests('sample_requests.csv')

class TimelineBuilder:
    def __init__(self, user_id: str, request_id: str, request_date: date, loader: DataLoader):
        self.user_id = user_id
        self.request_id = request_id
        self.request_date = request_date
        self.loader = loader
        self.prof = loader.profiles[user_id]
        self.home_curr = self.prof["home_currency"]
        self.start_bal = self.prof["current_available_balance"]
        self.min_bal = self.prof["minimum_balance_to_keep"]
        
        self.salary_ended = False
        self.salary_override_amt = None
        self.salary_override_date = None
        self.rent_increase_pct = None
        self.confirmed_incomes = []
        self.retried_debits = []
        self._parse_messages()
        
    def _parse_messages(self):
        msgs = []
        if self.user_id in self.loader.messages_by_user:
            msgs.extend(self.loader.messages_by_user[self.user_id])
        if self.request_id and self.request_id in self.loader.messages_by_request:
            for m in self.loader.messages_by_request[self.request_id]:
                if m not in msgs:
                    msgs.append(m)
        msgs.sort(key=lambda m: m.get("sent_at", ""))
        
        for m in msgs:
            t = m.get("message_text", "").lower()
            orig_t = m.get("message_text", "")
            
            # Ended contracts
            if any(k in t for k in ["seasonal contract has ended", "kontrak musiman saat ini telah berakhir", "employment has ended", "no regular salary"]):
                self.salary_ended = True
                
            # Date change
            dm = re.search(r"(\d{4}-\d{2}-\d{2})", orig_t)
            if any(k in t for k in ["replaces the payroll date", "confirmed salary is now expected on", "gaji yang sudah dikonfirmasi kini diperkirakan pada", "confirmed credit date is"]):
                if dm:
                    try:
                        self.salary_override_date = date.fromisoformat(dm.group(1))
                    except Exception: pass
                    
            # Salary amount change
            if any(k in t for k in ["salary has increased to", "gaji bulanan anda naik menjadi", "temporary monthly pay is", "next salary is reduced to", "first salary will be", "gaji bulanan sementara anda adalah", "confirmed base salary is", "gaji pokok yang dikonfirmasi adalah"]):
                am = re.search(r"(?:EUR|USD|IDR|INR|ZAR)\s*([0-9,]+(?:\.[0-9]+)?)", orig_t, re.IGNORECASE)
                if am:
                    try:
                        self.salary_override_amt = Decimal(am.group(1).replace(",", ""))
                    except Exception: pass
                    
            # Rent increase
            if ("rent" in t or "sewa" in t) and ("increase" in t or "naik" in t):
                pm = re.search(r"(\d+(?:\.\d+)?)\s*%", orig_t)
                if pm:
                    try:
                        self.rent_increase_pct = Decimal(pm.group(1))
                    except Exception: pass
                    
            # Invoices
            if "invoice payment of" in t or "pembayaran faktur sebesar" in t:
                am = re.search(r"(?:EUR|USD|IDR|INR|ZAR)\s*([0-9,]+(?:\.[0-9]+)?)", orig_t, re.IGNORECASE)
                if am and dm:
                    try:
                        self.confirmed_incomes.append((date.fromisoformat(dm.group(1)), Decimal(am.group(1).replace(",", ""))))
                    except Exception: pass
                    
            # Retried debit
            if "attempt the payment again on" in t and dm:
                try:
                    rd = date.fromisoformat(dm.group(1))
                    reid = m.get("related_event_id")
                    if reid and reid in self.loader.events_by_id:
                        ev = self.loader.events_by_id[reid]
                        self.retried_debits.append((rd, ev["amount"], ev["category"], ev["event_id"]))
                except Exception: pass

    def build_timeline(self, stopped_event_ids: Set[str] = None, reduced_events: Dict[str, Decimal] = None) -> Dict[date, Decimal]:
        stopped = stopped_event_ids or set()
        reduced = reduced_events or {}
        
        daily_deltas = defaultdict(lambda: Decimal("0"))
        end_date = self.request_date + timedelta(days=90)
        
        # 1. Pending debits
        for e in self.loader.events_by_user.get(self.user_id, []):
            if e["status"] == "pending" and e["direction"] == "debit":
                if e["event_id"] in stopped:
                    continue
                sd = e["settlement_date"] or self.request_date
                if sd < self.request_date:
                    sd = self.request_date
                if sd <= end_date:
                    amt = self.loader.fx.convert(e["amount"], e["currency"], self.home_curr, sd)
                    if e["event_id"] in reduced:
                        amt = self.loader.fx.convert(reduced[e["event_id"]], e["currency"], self.home_curr, sd)
                    daily_deltas[sd] -= amt
                    
        # 2. Scheduled events
        scheduled_salaries = []
        for e in self.loader.events_by_user.get(self.user_id, []):
            if e["status"] == "scheduled":
                if e["event_id"] in stopped:
                    continue
                sd = e["settlement_date"] or self.request_date
                if e["category"] == "salary" and self.salary_override_date:
                    sd = self.salary_override_date
                if sd >= self.request_date and sd <= end_date:
                    amt = self.loader.fx.convert(e["amount"], e["currency"], self.home_curr, sd)
                    if e["category"] == "salary" and self.salary_override_amt:
                        amt = self.salary_override_amt
                    if e["direction"] == "credit":
                        if e["category"] == "salary":
                            scheduled_salaries.append((sd, amt))
                        daily_deltas[sd] += amt
                    else:
                        if e["event_id"] in reduced:
                            amt = self.loader.fx.convert(reduced[e["event_id"]], e["currency"], self.home_curr, sd)
                        daily_deltas[sd] -= amt

        # 3. Confirmed invoices
        for inv_date, inv_amt in self.confirmed_incomes:
            if self.request_date <= inv_date <= end_date:
                daily_deltas[inv_date] += inv_amt
                
        # 4. Retried debits
        for ret_date, ret_amt, ret_cat, ret_eid in self.retried_debits:
            if self.request_date <= ret_date <= end_date and ret_eid not in stopped:
                daily_deltas[ret_date] -= ret_amt

        # 5. Recurring Salary projection
        if not self.salary_ended:
            user_evs = self.loader.events_by_user.get(self.user_id, [])
            salary_evs = [e for e in user_evs if e["category"] == "salary" and e["status"] in ("settled", "scheduled") and e["settlement_date"] <= self.request_date]
            last_sal_desc = (salary_evs[-1].get("description") or "").lower() if salary_evs else ""
            is_terminal = any(w in last_sal_desc for w in ["final", "last payment", "termination", "severance", "temporary"])
            
            if not is_terminal:
                base_amt = None
                if self.salary_override_amt:
                    base_amt = self.salary_override_amt
                elif scheduled_salaries:
                    base_amt = scheduled_salaries[-1][1]
                elif salary_evs:
                    base_amt = salary_evs[-1]["amount"]
                    
                if base_amt:
                    # Find typical day of month
                    sal_days = [e["settlement_date"].day for e in salary_evs if e["settlement_date"]]
                    mode_day = Counter(sal_days).most_common(1)[0][0] if sal_days else 15
                    if scheduled_salaries:
                        mode_day = scheduled_salaries[0][0].day
                    if self.salary_override_date:
                        mode_day = self.salary_override_date.day
                        
                    # Project monthly
                    cur_y = self.request_date.year
                    cur_m = self.request_date.month
                    for _ in range(4): # 4 months
                        max_d = calendar.monthrange(cur_y, cur_m)[1]
                        sal_d = date(cur_y, cur_m, min(mode_day, max_d))
                        if sal_d >= self.request_date and sal_d <= end_date:
                            # Avoid duplicate if scheduled salary already on this date
                            if not any(abs((sal_d - s[0]).days) <= 3 for s in scheduled_salaries):
                                daily_deltas[sal_d] += base_amt
                        cur_m += 1
                        if cur_m > 12:
                            cur_m = 1
                            cur_y += 1

        # 6. Recurring Debits projection
        user_evs = self.loader.events_by_user.get(self.user_id, [])
        history = [e for e in user_evs if e["direction"] == "debit" and e["status"] in ("settled", "scheduled") and e["settlement_date"] <= self.request_date]
        groups = defaultdict(list)
        for e in history:
            groups[(e["category"], e["currency"])].append(e)
            
        for (cat, curr), evs in groups.items():
            if len(evs) < 2:
                continue
            evs.sort(key=lambda x: x["settlement_date"])
            dates = [e["settlement_date"] for e in evs]
            diffs = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            avg_diff = sum(diffs) / len(diffs)
            
            last_ev = evs[-1]
            eid = last_ev["event_id"]
            if eid in stopped:
                continue
                
            last_desc = (last_ev.get("description") or "").lower()
            if any(w in last_desc for w in ["final instalment", "final payment", "last instalment", "loan payoff"]):
                continue
                
            # Variable daily-living categories are not projected as deterministic
            # recurring debits (they are absorbed within the safety buffer).
            if cat in ("groceries", "transport", "dining"):
                continue
                
            amt = last_ev["amount"]
            if eid in reduced:
                amt = reduced[eid]
            elif cat in ("rent", "housing") and self.rent_increase_pct:
                amt = amt * (Decimal("1") + self.rent_increase_pct / Decimal("100"))
                
            conv_amt = self.loader.fx.convert(amt, curr, self.home_curr, self.request_date)
            
            if 25.0 <= avg_diff <= 35.0:
                # Monthly: find mode day
                days = [d.day for d in dates]
                mode_day = Counter(days).most_common(1)[0][0]
                cur_y = self.request_date.year
                cur_m = self.request_date.month
                for _ in range(4):
                    max_d = calendar.monthrange(cur_y, cur_m)[1]
                    rec_d = date(cur_y, cur_m, min(mode_day, max_d))
                    if rec_d >= self.request_date and rec_d <= end_date:
                        daily_deltas[rec_d] -= conv_amt
                    cur_m += 1
                    if cur_m > 12:
                        cur_m = 1
                        cur_y += 1
            else:
                interval = 7
                if 4.0 <= avg_diff <= 5.5: interval = 5
                elif 5.5 < avg_diff <= 8.5: interval = 7
                elif 8.5 < avg_diff <= 11.5: interval = 10
                elif 11.5 < avg_diff <= 17.0: interval = 14
                elif 17.0 < avg_diff <= 24.0: interval = 21
                
                cur_d = dates[-1] + timedelta(days=interval)
                while cur_d <= end_date:
                    if cur_d >= self.request_date:
                        daily_deltas[cur_d] -= conv_amt
                    cur_d += timedelta(days=interval)
                    
        return daily_deltas

    def simulate(self, payments: List[Tuple[date, Decimal]] = None, stopped: Set[str] = None, reduced: Dict[str, Decimal] = None, horizon_date: date = None) -> Tuple[bool, Decimal, Decimal]:
        deltas = self.build_timeline(stopped, reduced)
        if payments:
            for pdate, pamt in payments:
                deltas[pdate] -= pamt
                
        bal = self.start_bal
        min_buf = bal - self.min_bal
        min_b = bal
        
        end_date = horizon_date or (self.request_date + timedelta(days=90))
        cur_d = self.request_date
        while cur_d <= end_date:
            if cur_d in deltas:
                bal += deltas[cur_d]
            buf = bal - self.min_bal
            if buf < min_buf:
                min_buf = buf
            if bal < min_b:
                min_b = bal
            cur_d += timedelta(days=1)
            
        return (min_buf >= Decimal("0"), min_buf, min_b)

def evaluate_request(req: Dict[str, Any], loader: DataLoader) -> Dict[str, Any]:
    rid = req["request_id"]
    uid = req["user_id"]
    rdate = req["request_date"]
    due_date = req["desired_completion_date"]
    req_amt = req["requested_amount"]
    allows_partial = req["allows_partial_payment"]
    
    prof = loader.profiles[uid]
    home_curr = prof["home_currency"]
    user_methods = prof["payment_methods_user_will_consider"]
    max_inst_months = prof["max_installment_months"]
    
    builder = TimelineBuilder(uid, rid, rdate, loader)
    
    # 1. Baseline simulation (90 days)
    is_safe, min_buf, _ = builder.simulate()
    safe_today = max(Decimal("0"), min(req_amt, min_buf))
    
    # 2. Earliest date for full payment
    earliest_full_date = None
    end_date = rdate + timedelta(days=90)
    
    if safe_today >= req_amt:
        earliest_full_date = rdate
    else:
        cur_d = rdate + timedelta(days=1)
        while cur_d <= end_date:
            # Check if paying on cur_d leaves balance >= min_bal on cur_d and until end_date
            safe_d, _, _ = builder.simulate(payments=[(cur_d, req_amt)])
            if safe_d:
                earliest_full_date = cur_d
                break
            cur_d += timedelta(days=1)
            
    # 3. Candidate generation
    candidates = []
    
    # Candidate A: full_payment today
    if safe_today >= req_amt and "full_payment" in user_methods:
        candidates.append({
            "status": "affordable_now",
            "method": "full_payment",
            "plan": f"{rdate}:{format_amount(req_amt, home_curr)}",
            "earliest": rdate,
            "changes": "none",
            "has_changes": False,
            "total_cost": req_amt,
            "start_date": rdate,
            "num_payments": 1,
            "option_id": "0",
            "completes_by_deadline": True,
        })
        
    # Candidate B: partial_payment
    if allows_partial and "partial_payment" in user_methods and Decimal("0") < safe_today < req_amt:
        if earliest_full_date and earliest_full_date <= due_date:
            rem_amt = req_amt - safe_today
            safe_plan, minbuf_pp, _ = builder.simulate(payments=[(rdate, safe_today), (earliest_full_date, rem_amt)])
            if safe_plan:
                candidates.append({
                    "status": "affordable_with_plan",
                    "method": "partial_payment",
                    "plan": f"{rdate}:{format_amount(safe_today, home_curr)}|{earliest_full_date}:{format_amount(rem_amt, home_curr)}",
                    "earliest": earliest_full_date,
                    "changes": "none",
                    "has_changes": False,
                    "total_cost": req_amt,
                    "start_date": rdate,
                    "num_payments": 2,
                    "minbuf": minbuf_pp,
                    "option_id": "0",
                    "completes_by_deadline": True,
                })
                
    # Candidate C: Installment options
    if "installments" in user_methods and max_inst_months:
        options = loader.payment_options_by_request.get(rid, [])
        for opt in options:
            if opt["payment_method"] != "installments":
                continue
            num_p = opt["number_of_payments"]
            freq = opt["payment_frequency_days"] or 30
            p_amt = opt["payment_amount"]
            first_d = opt["first_payment_date"] or rdate
            
            total_days = (num_p - 1) * freq
            approx_months = (total_days + 29) // 30
            if approx_months > max_inst_months:
                continue
                
            p_schedule = []
            cur_p_date = first_d
            for _ in range(num_p):
                p_schedule.append((cur_p_date, p_amt))
                cur_p_date += timedelta(days=freq)
                
            final_p_date = p_schedule[-1][0]
            completes_by_due = (final_p_date <= due_date)
            
            # Check safety over the plan horizon
            safe_inst, minbuf_inst, _ = builder.simulate(payments=p_schedule)
            if safe_inst:
                plan_str = "|".join(f"{d}:{format_amount(a, home_curr)}" for d, a in p_schedule)
                candidates.append({
                    "status": "affordable_with_plan",
                    "method": "installments",
                    "plan": plan_str,
                    "earliest": earliest_full_date,
                    "changes": "none",
                    "has_changes": False,
                    "total_cost": opt["total_payable_amount"],
                    "start_date": first_d,
                    "num_payments": num_p,
                    "minbuf": minbuf_inst,
                    "option_id": opt["payment_option_id"],
                    "completes_by_deadline": completes_by_due,
                })

    # Candidate D: Spending changes (if not already completed by deadline without changes)
    ready_no_change = [c for c in candidates if c["completes_by_deadline"] and not c["has_changes"]]
    if not ready_no_change:
        w_stop = set(prof["expense_categories_user_is_willing_to_stop"])
        w_reduce = set(prof["expense_categories_user_is_willing_to_reduce"])
        
        user_evs = loader.events_by_user.get(uid, [])
        flexible_events = []
        for e in user_evs:
            if e["direction"] == "debit" and e["settlement_date"] and e["settlement_date"] <= rdate:
                cat = e["category"]
                flex = e["flexibility"]
                min_amt = e["minimum_allowed_amount"]
                eid = e["event_id"]
                if cat in prof["expense_categories_to_protect"]:
                    continue
                can_stop = (cat in w_stop) and (flex in ("stoppable", "reducible_or_stoppable"))
                can_reduce = (cat in w_reduce) and (flex in ("reducible", "reducible_or_stoppable")) and (min_amt is not None)
                if can_stop or can_reduce:
                    flexible_events.append((e, can_stop, can_reduce))
                    
        flexible_events.sort(key=lambda x: x[0]["settlement_date"], reverse=True)
        seen_cats = set()
        unique_flex = []
        for fe in flexible_events:
            c = fe[0]["category"]
            if c not in seen_cats:
                seen_cats.add(c)
                unique_flex.append(fe)
                
        from itertools import combinations
        actions = []
        for ev, c_stop, c_red in unique_flex:
            eid = ev["event_id"]
            if c_stop:
                actions.append(("stop", eid, Decimal("0"), f"stop:{eid}"))
            if c_red:
                actions.append(("reduce", eid, ev["minimum_allowed_amount"], f"reduce_to:{eid}:{format_amount(ev['minimum_allowed_amount'], home_curr)}"))
                
        found_change = False
        for k in [1, 2, 3]:
            if found_change: break
            for action_set in combinations(actions, k):
                eids = [a[1] for a in action_set]
                if len(eids) != len(set(eids)):
                    continue
                stopped = set(a[1] for a in action_set if a[0] == "stop")
                reduced = {a[1]: a[2] for a in action_set if a[0] == "reduce"}
                
                # Test full payment today with these changes
                safe_wc, minbuf_wc, _ = builder.simulate(payments=[(rdate, req_amt)], stopped=stopped, reduced=reduced)
                if safe_wc and "full_payment" in user_methods:
                    change_str = "|".join(a[3] for a in action_set)
                    candidates.append({
                        "status": "affordable_with_plan",
                        "method": "full_payment",
                        "plan": f"{rdate}:{format_amount(req_amt, home_curr)}",
                        "earliest": earliest_full_date,
                        "changes": change_str,
                        "has_changes": True,
                        "total_cost": req_amt,
                        "start_date": rdate,
                        "num_payments": 1,
                        "minbuf": minbuf_wc,
                        "option_id": "0",
                        "completes_by_deadline": True,
                    })
                    found_change = True
                    break

    # Candidate E: wait (only if user accepts full_payment and earliest_full_date <= due_date)
    if earliest_full_date and earliest_full_date <= due_date and "full_payment" in user_methods:
        candidates.append({
            "status": "affordable_later",
            "method": "wait",
            "plan": f"{earliest_full_date}:{format_amount(req_amt, home_curr)}",
            "earliest": earliest_full_date,
            "changes": "none",
            "has_changes": False,
            "total_cost": req_amt,
            "start_date": earliest_full_date,
            "num_payments": 1,
            "option_id": "999",
            "completes_by_deadline": True,
        })
        
    valid_candidates = [c for c in candidates if c["completes_by_deadline"]]
    
    if not valid_candidates:
        return {
            "amount_safe_to_pay": safe_today,
            "affordability_status": "not_affordable",
            "recommended_payment_method": "not_recommended",
            "payment_plan": "none",
            "earliest_date_for_full_payment": "",
            "spending_changes_needed": "none",
            "decision_explanation": build_decision_explanation(
                {"status": "not_affordable", "method": "not_recommended", "changes": "none",
                 "plan": "none", "num_payments": 0},
                req_amt, home_curr, builder.min_bal, safe_today, earliest_full_date, due_date),
        }
        
    valid_candidates.sort(key=lambda c: (
        c["has_changes"],
        c["total_cost"],
        c["start_date"],
        c["num_payments"],
        c["option_id"],
    ))
    
    best = valid_candidates[0]
    return {
        "amount_safe_to_pay": safe_today,
        "affordability_status": best["status"],
        "recommended_payment_method": best["method"],
        "payment_plan": best["plan"],
        "earliest_date_for_full_payment": earliest_full_date.strftime("%Y-%m-%d") if earliest_full_date else "",
        "spending_changes_needed": best["changes"],
        "decision_explanation": build_decision_explanation(
            best, req_amt, home_curr, builder.min_bal, safe_today, earliest_full_date, due_date),
    }

if __name__ == "__main__":
    print("\n--- Running Evaluation on all 25 Samples ---")
    match_status = 0
    match_method = 0
    match_changes = 0

    for req in samples:
        rid = req["request_id"]
        exp = expected[rid]
        res = evaluate_request(req, loader)
        
        s_ok = (res["affordability_status"] == exp["affordability_status"])
        m_ok = (res["recommended_payment_method"] == exp["recommended_payment_method"])
        c_ok = (res["spending_changes_needed"] == exp["spending_changes_needed"])
        
        if s_ok: match_status += 1
        if m_ok: match_method += 1
        if c_ok: match_changes += 1
        
        flag = "MATCH" if (s_ok and m_ok and c_ok) else "MISMATCH"
        print(f"{rid} [{flag}]:")
        print(f"  Status:  got={res['affordability_status']} | exp={exp['affordability_status']}")
        print(f"  Method:  got={res['recommended_payment_method']} | exp={exp['recommended_payment_method']}")
        print(f"  Changes: got={res['spending_changes_needed']} | exp={exp['spending_changes_needed']}")
        print(f"  Plan:    got={res['payment_plan']} | exp={exp['payment_plan']}")
        print()

    print(f"Summary: Status match: {match_status}/25, Method match: {match_method}/25, Changes match: {match_changes}/25")
