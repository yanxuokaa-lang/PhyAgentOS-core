#!/usr/bin/env python3
"""Build the deterministic, labeled decision case set (24 cases).

Usage:
    .venv/bin/python quality-eval/make_cases.py            # writes quality-eval/cases.json
    .venv/bin/python quality-eval/make_cases.py --check     # exit 1 if cases.json is stale

Two families
------------
Family A "payment risk" (12 cases), schema:
    fraud  boolean
    risk   enum  LOW | ELEVATED | HIGH | CRITICAL
    action enum  APPROVE | REVIEW | BLOCK

Family B "support triage" (12 cases), schema:
    category    enum  BILLING | TECHNICAL | ACCOUNT | SHIPPING
    priority    enum  P1 | P2 | P3
    needs_human boolean

Ground truth is constructed, not hand-annotated. Every case carries structured
features; the policy a real deployment would prefill is part of the context, and
the strict labels are computed by the rule tables below. Cases marked ambiguous
carry an explicit acceptable-alternative set per field: a strict miss that lands
in that set is counted separately by analyze.py (the field is still a strict
miss, because the policy does not resolve it).

Rule tables
-----------
Family A (first matching rule wins):
    A1  authentication/2FA bypassed or session hijacked
            -> fraud=true,  risk=CRITICAL, action=BLOCK
    A2  anonymizing proxy/Tor AND unrecognized device
            -> fraud=true,  risk=CRITICAL if amount>=2000 else HIGH, action=BLOCK
    A3  unrecognized device AND amount>=2000
            -> fraud=true,  risk=HIGH, action=BLOCK
    A4  no fraud under A1-A3, but any of: proxy/Tor; unrecognized device;
        velocity burst; foreign merchant AND amount>=2000
            -> fraud=false, risk=ELEVATED, action=REVIEW
    A5  otherwise
            -> fraud=false, risk=LOW, action=APPROVE

    The policy does not define "several payments in a short window". A10 (3
    payments in 6 minutes) pins the intended reading as a burst via
    STRICT_OVERRIDE_A, and its acceptable set also allows the opposite reading.

Family B:
    category:    direct map from the issue type (B_CATEGORY below)
    priority:    P3 for questions and routine updates (see B_ROUTINE); P1 if the
                 issue blocks work and either affects more than one user or has
                 no workaround (B_BLOCKING); otherwise P2
    needs_human: true if priority==P1, or a refund/credit/invoice correction
                 above 100 USD, or an account unlock/security check, or a
                 lost/damaged/disputed parcel; otherwise false
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SCHEMA_A = {
    "fraud": {"type": "boolean", "description": "Whether the transaction is fraudulent"},
    "risk": {
        "type": "enum",
        "choices": ["LOW", "ELEVATED", "HIGH", "CRITICAL"],
        "description": "Risk tier",
    },
    "action": {
        "type": "enum",
        "choices": ["APPROVE", "REVIEW", "BLOCK"],
        "description": "Recommended action",
    },
}

SCHEMA_B = {
    "category": {
        "type": "enum",
        "choices": ["BILLING", "TECHNICAL", "ACCOUNT", "SHIPPING"],
        "description": "Main issue category",
    },
    "priority": {
        "type": "enum",
        "choices": ["P1", "P2", "P3"],
        "description": "Triage priority",
    },
    "needs_human": {"type": "boolean", "description": "Whether a human must handle the ticket"},
}

POLICY_A = (
    "PAYMENT RISK POLICY - apply the first matching rule\n"
    "A1. 2FA bypassed, or the session was hijacked: fraud=true, risk=CRITICAL, action=BLOCK.\n"
    "A2. Connection via anonymizing proxy or Tor exit node AND unrecognized device: "
    "fraud=true; risk=CRITICAL if amount >= 2000 USD, otherwise HIGH; action=BLOCK.\n"
    "A3. Unrecognized device AND amount >= 2000 USD: fraud=true, risk=HIGH, action=BLOCK.\n"
    "A4. No fraud under A1-A3, but any of: connection via anonymizing proxy or Tor exit node; "
    "unrecognized device; several payments in a short window (velocity burst); "
    "foreign merchant AND amount >= 2000 USD: fraud=false, risk=ELEVATED, action=REVIEW.\n"
    "A5. Otherwise: fraud=false, risk=LOW, action=APPROVE."
)

POLICY_B = (
    "SUPPORT TRIAGE POLICY - apply the first matching rule\n"
    "B1. Category: BILLING for charges, invoices, refunds and pricing; TECHNICAL for errors, "
    "crashes, outages, performance and integrations; ACCOUNT for sign-in, passwords, 2FA, "
    "permissions and profile; SHIPPING for delivery, tracking, parcels and addresses.\n"
    "B2. Priority: P3 for questions, routine updates, cosmetic issues and feature requests; "
    "P1 if the issue blocks the customer's work and either affects more than one user or "
    "has no workaround; otherwise P2.\n"
    "B3. needs_human=true if any of: priority is P1; a refund, credit or invoice correction "
    "above 100 USD is requested or warranted; the account requires unlocking or a security "
    "check; a parcel is lost, damaged or in dispute. Otherwise needs_human=false (an "
    "automated or self-service flow resolves it)."
)


# --------------------------------------------------------------------------- #
# Family A
# --------------------------------------------------------------------------- #

A_CASES = [
    dict(
        id="A01",
        amount=42.50,
        merchant="Harbor Market",
        country="US",
        country_name="United States",
        device="known",
        channel="residential",
        auth="ok",
        velocity="normal",
        note="Clear low: small domestic purchase on a known device.",
    ),
    dict(
        id="A02",
        amount=2400.00,
        merchant="Aurora Electronics",
        country="US",
        country_name="United States",
        device="new",
        channel="residential",
        auth="ok",
        velocity="normal",
        note="Rule A3: unrecognized device plus amount >= 2000.",
    ),
    dict(
        id="A03",
        amount=2600.00,
        merchant="Alpen Motoren",
        country="DE",
        country_name="Germany",
        device="known",
        channel="residential",
        auth="ok",
        velocity="normal",
        note="Rule A4: foreign merchant and high amount, but no device or transport signal.",
    ),
    dict(
        id="A04",
        amount=89.00,
        merchant="Streamly",
        country="US",
        country_name="United States",
        device="known",
        channel="proxy",
        auth="ok",
        velocity="normal",
        note="Rule A4: Tor alone, small amount and known device, so not fraud.",
    ),
    dict(
        id="A05",
        amount=3100.00,
        merchant="CipherTrade Exchange",
        country="CY",
        country_name="Cyprus",
        device="new",
        channel="proxy",
        auth="ok",
        velocity="burst",
        note="Rule A2: Tor plus unrecognized device plus high amount, the CRITICAL branch.",
    ),
    dict(
        id="A06",
        amount=19.99,
        merchant="PixelPlay Games",
        country="US",
        country_name="United States",
        device="known",
        channel="residential",
        auth="bypassed",
        velocity="normal",
        note="Rule A1: tiny amount but the session was hijacked.",
    ),
    dict(
        id="A07",
        amount=640.00,
        merchant="Nimbus Hosting",
        country="US",
        country_name="United States",
        device="known",
        channel="residential",
        auth="ok",
        velocity="burst",
        note="Rule A4: velocity burst without any takeover signal.",
    ),
    dict(
        id="A08",
        amount=120.00,
        merchant="Metro Pharmacy",
        country="US",
        country_name="United States",
        device="known",
        channel="residential",
        auth="ok",
        velocity="normal",
        note="Clear low: routine repeat merchant.",
    ),
    dict(
        id="A09",
        amount=1950.00,
        merchant="Britannia Jewels",
        country="GB",
        country_name="United Kingdom",
        device="new",
        channel="residential",
        auth="ok",
        velocity="normal",
        note="Rule A4: unrecognized device but amount is just under the 2000 "
        "threshold, so not fraud.",
    ),
    dict(
        id="A10",
        amount=300.00,
        merchant="QuickShip Courier",
        country="US",
        country_name="United States",
        device="known",
        channel="residential",
        auth="ok",
        velocity="borderline",
        note="Ambiguous: 3 payments in 6 minutes is only arguably a velocity burst.",
    ),
    dict(
        id="A11",
        amount=2450.00,
        merchant="LuxTime Jewelers",
        country="US",
        country_name="United States",
        device="verified",
        channel="residential",
        auth="ok",
        velocity="normal",
        note="Ambiguous: device is new but enrolled and verified through the bank app.",
    ),
    dict(
        id="A12",
        amount=890.00,
        merchant="Northline Travel",
        country="US",
        country_name="United States",
        device="known",
        channel="residential",
        auth="ok_new_phone",
        velocity="normal",
        note="Ambiguous: 2FA was approved, but from a phone number replaced the day before.",
    ),
]

# Strict misses that the policy itself leaves open. Fields are scored independently.
ACCEPTABLE_A = {
    "A10": {"risk": ["LOW"], "action": ["APPROVE"]},
    "A11": {"fraud": [True], "risk": ["HIGH"], "action": ["BLOCK"]},
    "A12": {"fraud": [True], "risk": ["ELEVATED"], "action": ["REVIEW"]},
}

# Policy-silent inputs where the generator pins the intended reading as strict.
STRICT_OVERRIDE_A = {
    "A10": {"fraud": False, "risk": "ELEVATED", "action": "REVIEW"},  # 3-in-6-min = burst
}

A_NAMES = [
    "Sarah Jenkins",
    "Daniel Okafor",
    "Mei Lin",
    "Tomas Novak",
    "Priya Raman",
    "Elena Petrova",
    "Marcus Webb",
    "Aisha Karim",
    "Jonas Berg",
    "Clara Moreau",
    "Victor Salazar",
    "Hannah Cole",
]
A_CITIES = ["Seattle, WA", "Austin, TX", "Chicago, IL", "Denver, CO", "Portland, OR", "Boston, MA"]
A_IPS = [
    "73.162.44.18",
    "24.19.201.77",
    "98.114.6.203",
    "67.183.90.12",
    "47.210.55.31",
    "71.9.128.240",
]
A_AVG = [1100, 2400, 780, 3200, 560, 1890, 4150, 940, 1675, 2280, 3025, 690]


def money(amount: float, style: int) -> str:
    return f"${amount:,.2f}" if style % 2 == 0 else f"USD {amount:,.2f}"


def label_a(f: dict) -> dict:
    """Family A rule table, first matching rule wins."""
    high = f["amount"] >= 2000
    proxy = f["channel"] == "proxy"
    new = f["device"] == "new"
    if f["auth"] == "bypassed":
        return {"fraud": True, "risk": "CRITICAL", "action": "BLOCK"}
    if proxy and new:
        return {"fraud": True, "risk": "CRITICAL" if high else "HIGH", "action": "BLOCK"}
    if new and high:
        return {"fraud": True, "risk": "HIGH", "action": "BLOCK"}
    foreign = f["country"] != "US"
    if proxy or new or f["velocity"] == "burst" or (foreign and high):
        return {"fraud": False, "risk": "ELEVATED", "action": "REVIEW"}
    return {"fraud": False, "risk": "LOW", "action": "APPROVE"}


def render_a(f: dict) -> str:
    """Render the prefilled policy plus an alert whose wording carries each feature."""
    i = int(f["id"][1:])
    style = i % 3
    if f["device"] == "known":
        months = 8 + (i * 5) % 40
        prior = 20 + (i * 13) % 180
        device_text = (
            f"recognized cardholder device (enrolled {months} months ago, {prior} prior purchases)"
            if style != 1
            else f"device recognition: known device, active for {months} "
            f"months, {prior} prior transactions"
        )
    elif f["device"] == "new":
        device_text = (
            f"UNRECOGNIZED device, first seen {4 + i * 3} minutes before the "
            f"alert, no prior purchases"
            if style != 1
            else f"device fingerprint not recognized: new device, "
            f"first seen {4 + i * 3} minutes ago"
        )
    else:  # verified
        device_text = (
            "device enrolled through the bank app 2 days ago after a verified one-time code; "
            "no prior purchase on this device"
        )
    if f["channel"] == "proxy":
        connection_text = "anonymizing proxy / Tor exit node (185.220.101.5, Frankfurt, Germany)"
    else:
        connection_text = (
            f"residential ISP ({A_IPS[i % len(A_IPS)]}, {A_CITIES[i % len(A_CITIES)]})"
        )
    auth_text = {
        "ok": "2FA completed on the phone number on file",
        "bypassed": "2FA bypassed: the session was hijacked with a stolen cookie",
        "ok_new_phone": (
            "2FA code approved on a phone number the cardholder replaced yesterday; "
            "the cardholder confirms the purchase by chat"
        ),
    }[f["auth"]]
    velocity_text = {
        "normal": "1 payment in the last 24 hours",
        "burst": "5 payments in the last 10 minutes, 2 declined",
        "borderline": "3 payments in the last 6 minutes, 1 declined then retried",
    }[f["velocity"]]
    years = 2 + i % 8
    lines = [
        POLICY_A,
        "",
        f"TRANSACTION ALERT #TX-{98100 + i * 7}",
        f"Cardholder: {A_NAMES[i % len(A_NAMES)]} "
        f"({years}-year account, average monthly spend ${A_AVG[i % len(A_AVG)]:,})",
        f"Merchant: {f['merchant']} ({f['country_name']}, "
        f"{'domestic' if f['country'] == 'US' else 'foreign'} merchant)",
        f"Amount: {money(f['amount'], style)}",
        f"Device: {device_text}",
        f"Connection: {connection_text}",
        f"Authentication: {auth_text}",
        f"Recent activity: {velocity_text}",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Family B
# --------------------------------------------------------------------------- #

B_CATEGORY = {
    "duplicate_charge": "BILLING",
    "pricing_question": "BILLING",
    "refund_request": "BILLING",
    "mixed_charge_slow_app": "BILLING",
    "app_crash": "TECHNICAL",
    "outage": "TECHNICAL",
    "performance": "TECHNICAL",
    "integration": "TECHNICAL",
    "reset_email": "ACCOUNT",
    "lockout": "ACCOUNT",
    "sso_loop": "ACCOUNT",
    "address_update": "SHIPPING",
    "parcel_lost": "SHIPPING",
}
B_BLOCKING = {"outage", "lockout", "sso_loop"}
B_ROUTINE = {"pricing_question", "address_update"}

B_CASES = [
    dict(
        id="B01",
        scenario="duplicate_charge",
        money=29.99,
        scope="single",
        workaround=False,
        plan="Pro",
        who="Dana Whitfield, operations lead",
        subject="Charged twice for my Pro plan this month",
        body="Invoice INV-8891 lists two charges of USD 29.99 for the same billing period. "
        "I authorised one payment only. Please refund the duplicate charge "
        "to the card ending 4412.",
        note="Clear: wrong bill, refund under 100 USD.",
    ),
    dict(
        id="B02",
        scenario="outage",
        money=0.0,
        scope="production",
        workaround=False,
        plan="Enterprise",
        who="Marcus Vance, CTO",
        subject="Production API down: every checkout returns 502",
        body="Our production checkout integration has returned 502 Bad Gateway on every request "
        "for 40 minutes. All customers are affected and no orders are completing. "
        "This is our busiest "
        "trading window and we have no workaround.",
        note="Clear: production outage, everyone blocked.",
    ),
    dict(
        id="B03",
        scenario="reset_email",
        money=0.0,
        scope="single",
        workaround=True,
        plan="Free",
        who="Ravi Patel, sole trader",
        subject="Password reset email never arrives",
        body="I request a reset link from the sign-in page and nothing arrives, "
        "not even in spam. I have "
        "tried three times today. I can still use the mobile app session that is already open, but "
        "I cannot sign in from a new browser.",
        note="Clear ACCOUNT: self-service reset flow.",
    ),
    dict(
        id="B04",
        scenario="lockout",
        money=0.0,
        scope="team",
        workaround=False,
        plan="Team",
        who="Ingrid Halvorsen, workspace owner",
        subject="Workspace owner locked out after failed sign-in attempts",
        body="My account was locked after five failed sign-in attempts because my "
        "password manager had a "
        "stale entry. I am the workspace owner and my team of 12 cannot reach the "
        "shared dashboards "
        "until this is unlocked.",
        note="Clear ACCOUNT: unlock plus team-wide impact.",
    ),
    dict(
        id="B05",
        scenario="parcel_lost",
        money=75.0,
        scope="single",
        workaround=False,
        plan="Pro",
        who="Owen Brady, subscriber",
        subject="Parcel marked delivered but never arrived",
        body="Tracking for order ORD-55210 says delivered on Tuesday, "
        "but nothing was left at my address. "
        "The carrier told me to contact the sender. The contents are worth USD 75.",
        note="Clear SHIPPING: lost parcel investigation.",
    ),
    dict(
        id="B06",
        scenario="app_crash",
        money=0.0,
        scope="single",
        workaround=True,
        plan="Team",
        who="Lucia Ferreira, analyst",
        subject="CSV export crashes the app on large reports",
        body="Exporting reports above roughly 10,000 rows crashes the desktop app "
        "every time. Smaller "
        "exports work, so I can split the report and finish my work, but this costs me about "
        "20 minutes each morning.",
        note="Clear TECHNICAL: reproducible, workaround exists.",
    ),
    dict(
        id="B07",
        scenario="address_update",
        money=0.0,
        scope="single",
        workaround=True,
        plan="Pro",
        who="Noah Kim, subscriber",
        subject="Change delivery address before dispatch",
        body="Please change the delivery address on order ORD-55988 to my office "
        "address before it ships. "
        "The order is still marked processing and nothing has shipped yet.",
        note="Clear SHIPPING: routine pre-dispatch update.",
    ),
    dict(
        id="B08",
        scenario="refund_request",
        money=480.0,
        scope="single",
        workaround=False,
        plan="Enterprise",
        who="Grace Lindqvist, finance manager",
        subject="Correct invoice INV-9021: USD 480 overage charge",
        body="INV-9021 charges USD 480 for API overages in August. Our own logs "
        "show 20,000 calls where "
        "the invoice counts 120,000. Please refund the USD 400 difference and reissue the invoice, "
        "our accounting close is next week.",
        note="Clear BILLING: invoice correction above the 100 USD threshold.",
    ),
    dict(
        id="B09",
        scenario="pricing_question",
        money=0.0,
        scope="single",
        workaround=True,
        plan="Free",
        who="Felix Braun, founder",
        subject="Pricing question: difference between Pro and Team plans",
        body="We are four people and want to know whether the Team plan "
        "includes the same API limits as "
        "Pro. No urgency, we are planning next quarter's budget.",
        note="Clear BILLING: pricing question, no action needed.",
    ),
    dict(
        id="B10",
        scenario="sso_loop",
        money=0.0,
        scope="team",
        workaround=False,
        plan="Enterprise",
        who="Amara Nwosu, IT manager",
        subject="SSO login loop for our whole team since this morning",
        body="Since about 08:00 UTC every member of our team of 30 "
        "authenticates with SSO successfully "
        "and is then bounced back to the sign-in page. Nothing in our configuration changed. There "
        "is no workaround: nobody can reach the dashboard.",
        note="Ambiguous: sign-in failure (ACCOUNT) or SSO integration defect (TECHNICAL).",
    ),
    dict(
        id="B11",
        scenario="mixed_charge_slow_app",
        money=89.0,
        scope="single",
        workaround=True,
        plan="Pro",
        who="Theo Marsh, consultant",
        subject="Duplicate charge and very slow dashboard",
        body="Two things: I was charged USD 89 twice for the same month, "
        "please refund one charge; and "
        "since the last update the dashboard takes about 15 seconds to load for me. The charge is "
        "the more urgent item.",
        note="Ambiguous: billing refund or technical performance issue.",
    ),
    dict(
        id="B12",
        scenario="performance",
        money=0.0,
        scope="team",
        workaround=True,
        plan="Team",
        who="Sofia Marchetti, engineering manager",
        subject="Dashboards slow for the whole team after yesterday's release",
        body="Since yesterday's release our dashboards take 12-15 seconds to "
        "load for all 8 team members. "
        "Everything still works and we can keep shipping, it is just painful.",
        note="Ambiguous: team-wide impairment, but nothing is blocked.",
    ),
]

ACCEPTABLE_B = {
    "B10": {"category": ["TECHNICAL"]},
    "B11": {"category": ["TECHNICAL"]},
    "B12": {"priority": ["P3"]},
}


def label_b(f: dict) -> dict:
    """Family B rule table."""
    category = B_CATEGORY[f["scenario"]]
    if f["scenario"] in B_ROUTINE:
        priority = "P3"
    elif f["scenario"] in B_BLOCKING and (f["scope"] != "single" or not f["workaround"]):
        priority = "P1"
    else:
        priority = "P2"
    needs_human = (
        priority == "P1"
        or f["money"] > 100.0
        or f["scenario"] in ("lockout", "sso_loop")
        or f["scenario"] == "parcel_lost"
    )
    return {"category": category, "priority": priority, "needs_human": needs_human}


def render_b(f: dict) -> str:
    i = int(f["id"][1:])
    return "\n".join(
        [
            POLICY_B,
            "",
            f"SUPPORT TICKET #INC-{44000 + i * 13}",
            f"From: {f['who']}",
            f"Plan: {f['plan']}",
            f"Subject: {f['subject']}",
            "",
            f["body"],
        ]
    )


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #


def build() -> dict:
    family_a = []
    for f in A_CASES:
        labels = STRICT_OVERRIDE_A.get(f["id"]) or label_a(f)
        family_a.append(
            {
                "id": f["id"],
                "family": "payment_risk",
                "primary_field": "fraud",
                "context": render_a(f),
                "labels": labels,
                "acceptable": ACCEPTABLE_A.get(f["id"], {}),
                "ambiguous": f["id"] in ACCEPTABLE_A,
                "note": f["note"],
            }
        )
    family_b = []
    for f in B_CASES:
        family_b.append(
            {
                "id": f["id"],
                "family": "support_triage",
                "primary_field": "category",
                "context": render_b(f),
                "labels": label_b(f),
                "acceptable": ACCEPTABLE_B.get(f["id"], {}),
                "ambiguous": f["id"] in ACCEPTABLE_B,
                "note": f["note"],
            }
        )
    ambiguous = [c["id"] for c in family_a + family_b if c["ambiguous"]]
    return {
        "version": 1,
        "generated_by": "benchmarks/make_cases.py",
        "primary_metric_note": "primary field: fraud (family A) / category (family B)",
        "counts": {
            "total": len(family_a) + len(family_b),
            "family_a": len(family_a),
            "family_b": len(family_b),
            "ambiguous": len(ambiguous),
            "ambiguous_ids": ambiguous,
        },
        "families": {
            "payment_risk": {"schema": SCHEMA_A, "policy": POLICY_A, "cases": family_a},
            "support_triage": {"schema": SCHEMA_B, "policy": POLICY_B, "cases": family_b},
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the labeled decision cases.")
    ap.add_argument("--out", default=os.path.join(HERE, "cases.json"))
    ap.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if the file on disk differs from the generated set",
    )
    args = ap.parse_args()

    payload = json.dumps(build(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not os.path.exists(args.out):
            print(f"stale: {args.out} does not exist")
            return 1
        with open(args.out) as fh:
            current = fh.read()
        if current != payload:
            print(f"stale: {args.out} differs from make_cases.py output")
            return 1
        print(f"ok: {args.out} is up to date")
        return 0
    with open(args.out, "w") as fh:
        fh.write(payload)
    data = json.loads(payload)
    print(
        f"wrote {args.out}: "
        f"{data['counts']['family_a']} payment-risk "
        f"+ {data['counts']['family_b']} support-triage cases, "
        f"{data['counts']['ambiguous']} ambiguous ({', '.join(data['counts']['ambiguous_ids'])})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
