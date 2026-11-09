"""Synthesizes and curates a multi-domain operational decision dataset for Von-1.1.

Produces balanced training and validation sets across all three System One primitives:
1. Choice (Multi-class routing): Customer support intent, department triage, email intent
2. Noul (Binary verification): Temporal policy compliance, refund eligibility, secret leaks, urgency
3. Score (Ordinal rating): Frustration scale (0-2), incident severity (0-4), sentiment (0-4)
4. Adversarial Core: ANLI + WANLI deduction pairs to preserve deep reasoning

Output format: JSONL files where each record matches Von's DecisionDataset schema.
"""

import argparse
import json
import os
import random
import re
from typing import Dict, List, Optional
from datasets import load_dataset


# =====================================================================
# 1. Programmatic Policy & Decision Case Generators (Noul & Score)
# =====================================================================

def generate_refund_policy_cases(n: int = 6000) -> List[dict]:
    """Generates varied temporal policy compliance cases for money-back guarantees."""
    records = []
    
    # Positive templates (within window, unused)
    pos_time_phrases = [
        "yesterday", "two days ago", "three days ago", "five days ago",
        "last week", "six days ago", "12 days ago", "two weeks ago",
        "this morning", "earlier today", "48 hours ago", "three weeks ago",
        "eighteen days ago", "four days ago"
    ]
    pos_plans = ["annual plan", "Starter plan", "Pro subscription", "Team license", "Enterprise pilot", "addon credits package"]
    pos_unused_phrases = [
        "never activated it", "haven't created an account yet", "nobody on our team started using it",
        "ended up not using the product at all", "bought for a project that got cancelled",
        "zero API calls were made", "completely unused", "not a single login was recorded",
        "never touched the dashboard", "we purchased by accident and never deployed",
        "nothing was ever used", "bought a different tool instead and never logged in"
    ]
    
    # Implicit entitlement cases (facts satisfy precondition without using the word "refund")
    implicit_pos_cases = [
        "My annual subscription charge went through yesterday. I have not even created an account yet.",
        "It has been three weeks since checkout. We ended up not using the product at all because we bought a different tool.",
        "I bought this yesterday for a project that got cancelled. Nothing was ever used.",
        "The trial converted to a paid plan this morning and nobody on my team has started using it yet.",
        "Purchased five days ago for an engineer who left the company before ever logging in.",
        "Our invoice was paid last week, but our procurement team rejected the software before deployment.",
        "Account was charged 48 hours ago. We never integrated the SDK or made any requests.",
    ]
    
    # Negative templates (exceeds window OR used)
    neg_overdue_phrases = [
        "activated fourteen weeks ago", "renewed eleven months ago", "bought four months ago",
        "activated 45 days ago", "it has been sixty days since checkout", "subscribed five months ago",
        "signed up 90 days ago", "eight weeks ago"
    ]
    neg_used_phrases = [
        "my team has been using the product every day for the past month",
        "we consumed nearly all thirty thousand API credits",
        "the consulting onboarding package was fully delivered last week",
        "we have exported over 500 reports during our production usage",
        "our active users have been logged in daily",
        "used it extensively for our launch campaign and now want to be reimbursed",
        "logged in hundreds of times across 10 developer accounts"
    ]

    instruction = "The customer is entitled to a refund under the 30-day money-back guarantee for unused services"

    for _ in range(n // 2):
        # Positive case (Eligible)
        if random.random() < 0.35 and implicit_pos_cases:
            # Inject implicit fact-based entitlement
            state_text = random.choice(implicit_pos_cases)
        else:
            t = random.choice(pos_time_phrases)
            p = random.choice(pos_plans)
            u = random.choice(pos_unused_phrases)
            templates = [
                f"I purchased the {p} {t}, {u}, and would like my money back.",
                f"My {p} charge went through {t}. We {u}. Please process a refund.",
                f"We bought the {p} {t} for a test run. {u.capitalize()}. Looking for a full reimbursement.",
                f"Subscription for {p} renewed {t}. {u.capitalize()}, can you please refund?",
            ]
            state_text = random.choice(templates)

        records.append({
            "state": state_text,
            "question": instruction,
            "options": [
                {"id": "yes", "description": "The condition holds true and the customer is entitled to a refund."},
                {"id": "no", "description": "The condition is false and the customer is not eligible."},
            ],
            "label": "yes",
            "source": "synthetic_refund_pos",
        })

        # Negative case (Ineligible)
        reason = random.choice(["overdue", "used"])
        if reason == "overdue":
            t_neg = random.choice(neg_overdue_phrases)
            p = random.choice(pos_plans)
            templates_neg = [
                f"The {p} was {t_neg}. I would like to be reimbursed for the seats we no longer need.",
                f"I bought the {p} {t_neg} and only realized today that we forgot to cancel.",
                f"We subscribed {t_neg} to {p}. Requesting a courtesy refund.",
            ]
        else:
            p = random.choice(pos_plans)
            u_neg = random.choice(neg_used_phrases)
            templates_neg = [
                f"We purchased the {p}. {u_neg.capitalize()} and would like a refund.",
                f"Regarding our {p}: {u_neg}. Can we get our money back?",
                f"I want to cancel our {p} and receive a reimbursement. {u_neg.capitalize()}.",
            ]
        records.append({
            "state": random.choice(templates_neg),
            "question": instruction,
            "options": [
                {"id": "yes", "description": "The condition holds true and the customer is entitled to a refund."},
                {"id": "no", "description": "The condition is false and the customer is not eligible."},
            ],
            "label": "no",
            "source": "synthetic_refund_neg",
        })

    return records


def generate_secret_leak_cases(n: int = 5000) -> List[dict]:
    """Generates secret token leaks vs safe references for credential detection."""
    records = []
    instruction = "The text contains a password, API key, token, or private key that should be handled as a secret"

    fake_keys = [
        "sk-test-4f83bb71c2ea9d0825f7fa61",
        "mock_oauth_secret_access_key_99281a8b",
        "AKIAIOSFODNN7EXAMPLE",
        "test_bearer_token_val_481092a017cb83e",
        "mock_webhook_secret_signing_key_4410",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA7vZxTestOnlyKeyMaterial\n-----END RSA PRIVATE KEY-----",
        "eyJhYmMiOiJkZWYifQ.eyJhYmMiOiJkZWYifQ.testsignatureonly1234567890"
    ]
    passwords = [
        "hunter2!", "correct-horse-battery-staple", "P@ssw0rd2026!",
        "AdminSecret99#", "ProdDbRootPass2026", "blue-tiger-lemon-window",
        "temporary-support-password-44"
    ]

    pos_templates = [
        "Deploy using API_KEY={key}",
        "The WIFI_PASSWORD for the conference room is {pwd}",
        "Here is the key for support replication: {key}",
        "You can log in as admin with the password {pwd}.",
        "DATABASE_URL=postgres://admin:{pwd}@db.internal:5432/main",
        "curl -H 'Authorization: Bearer {key}' https://api.service.internal",
        "Secret token leaked in logs: TOKEN={key}",
        "Emergency root access credentials: user=root pass={pwd}",
    ]

    neg_templates = [
        "We rotate our access tokens every ninety days as part of security policy.",
        "Set the credential in the X-Auth-Token header; values are injected automatically by CI.",
        "The environment variable MQTT_PASSWORD was not set, so the client refused to start.",
        "See the docs: pass the token via the Authorization Bearer header.",
        "Passwords must be at least 12 characters and contain uppercase and special symbols.",
        "The API key should never be committed to public GitHub repositories.",
        "Make sure to configure AWS_SECRET_ACCESS_KEY in AWS Secrets Manager.",
        "All secrets are encrypted at rest using AES-256 in HashiCorp Vault.",
        "When authentication fails, check that your bearer token has not expired.",
        "Rotate your SSH keys annually according to SOC2 compliance guidelines."
    ]

    for _ in range(n // 2):
        # Pos
        tmpl = random.choice(pos_templates)
        text_pos = tmpl.format(key=random.choice(fake_keys), pwd=random.choice(passwords))
        records.append({
            "state": text_pos,
            "question": instruction,
            "options": [
                {"id": "yes", "description": "Yes, text contains sensitive secret credentials or keys."},
                {"id": "no", "description": "No, text does not contain active credentials."},
            ],
            "label": "yes",
            "source": "synthetic_secret_pos",
        })

        # Neg
        records.append({
            "state": random.choice(neg_templates),
            "question": instruction,
            "options": [
                {"id": "yes", "description": "Yes, text contains sensitive secret credentials or keys."},
                {"id": "no", "description": "No, text does not contain active credentials."},
            ],
            "label": "no",
            "source": "synthetic_secret_neg",
        })

    return records


def generate_operational_urgency_cases(n: int = 5000) -> List[dict]:
    """Generates high-urgency operational incidents vs low-urgency general queries."""
    records = []
    instruction = "The message conveys urgency or time-sensitivity"

    urgent_cases = [
        "Checkout is completely down and we are losing sales every minute. Help ASAP.",
        "Our launch event is in two hours and the invite emails have not been sent yet. Please prioritize this.",
        "The production app has been unavailable since this morning and customers are complaining on social media.",
        "I am about to board a flight and need this approved before I lose connectivity.",
        "Database deadlock on primary shard, entire payment pipeline blocked.",
        "CRITICAL: 500 errors on /api/v1/auth across all availability zones. Immediate fix required.",
        "Security breach detected: multiple suspicious logins from unrecognized IPs right now.",
        "All customer webhook deliveries failing for the last 45 minutes, queue is overflowing.",
        "Production SSL certificate expired ten minutes ago, site is throwing security warnings to all visitors.",
    ]

    non_urgent_cases = [
        "Whenever you get a chance, could you look at the export feature?",
        "For our planning for next quarter, it would help to know your roadmap.",
        "Great product! Just wanted to share some feedback on the onboarding flow.",
        "Could you clarify whether invoices can include a PO number?",
        "Where is your office located? Asking because my company ships hardware nearby.",
        "Is there a dark mode planned for the dashboard in the future?",
        "One quick formatting suggestion for the documentation page on webhooks.",
        "No rush at all on this, but let me know if CSV exports support custom delimiters.",
        "Just dropping a note to say thanks for the fast support yesterday!",
    ]

    for _ in range(n // 2):
        records.append({
            "state": random.choice(urgent_cases),
            "question": instruction,
            "options": [
                {"id": "yes", "description": "The message conveys critical urgency or immediate time-sensitivity."},
                {"id": "no", "description": "The message is non-urgent or informational."},
            ],
            "label": "yes",
            "source": "synthetic_urgency_pos",
        })
        records.append({
            "state": random.choice(non_urgent_cases),
            "question": instruction,
            "options": [
                {"id": "yes", "description": "The message conveys critical urgency or immediate time-sensitivity."},
                {"id": "no", "description": "The message is non-urgent or informational."},
            ],
            "label": "no",
            "source": "synthetic_urgency_neg",
        })

    return records


def generate_frustration_score_cases(n: int = 5000) -> List[dict]:
    """Generates 3-level customer frustration ratings (0: calm, 1: frustrated, 2: angry)."""
    records = []
    instruction = "How frustrated does the customer appear?"
    levels = [
        {"id": "0", "description": "The condition is calm, polite, or just stating factual questions."},
        {"id": "1", "description": "The condition is frustrated, annoyed, or expressing mild dissatisfaction."},
        {"id": "2", "description": "The condition is very angry, using hostile words, caps, or extreme outrage."},
    ]

    calm_pool = [
        "Quick question: does the exporter support CSV?",
        "The report looks good overall. One small thing: the date format is off.",
        "Thanks a lot for the fast update, everything is working as expected now.",
        "Could you clarify how seat licensing works for annual contracts?",
        "Just checking in on the status of our ticket from yesterday, thanks!",
        "The new dashboard release looks clean, appreciate the team's work.",
    ]
    frustrated_pool = [
        "This is the third time this week the sync has failed. It is getting really annoying.",
        "I have been waiting two days for a reply and this is blocking my work. Please get back to me.",
        "Honestly the new UI makes simple tasks tedious. I hope this gets some attention.",
        "I submitted a bug report last Monday and haven't heard anything. Starting to feel ignored.",
        "The export feature is constantly timing out on large files. Can someone look into this?",
        "It is frustrating having to re-authenticate every 20 minutes when working.",
    ]
    angry_pool = [
        "This is ABSURD. Your garbage app destroyed three hours of work. Fix it NOW.",
        "Are you KIDDING me? Fourth outage this month. I am done with this pathetic service.",
        "STOP billing my card. I have asked five times and nobody on your useless team listens.",
        "Your software is completely broken. We are losing thousands of dollars and demanding a full refund immediately.",
        "Worst customer experience I have ever had. Incompetent support and useless developers.",
    ]

    for _ in range(n // 3):
        for lvl_id, pool in [("0", calm_pool), ("1", frustrated_pool), ("2", angry_pool)]:
            records.append({
                "state": random.choice(pool),
                "question": instruction,
                "options": levels,
                "label": lvl_id,
                "source": f"synthetic_frustration_{lvl_id}",
            })

    return records


def generate_incident_severity_cases(n: int = 5000) -> List[dict]:
    """Generates 5-level operational severity score ratings (0: minor, 1: low, 2: major, 3: critical, 4: catastrophic)."""
    records = []
    instruction = "Rate the operational severity of this incident report."
    levels = [
        {"id": "0", "description": "Minor cosmetic issue with no functional impact."},
        {"id": "1", "description": "Low impact; a workaround exists or non-core feature degraded."},
        {"id": "2", "description": "Major annoyance; a core feature is degraded with no easy workaround."},
        {"id": "3", "description": "Critical; a core feature is unusable for most users with no workaround."},
        {"id": "4", "description": "Catastrophic; the entire service is down or data has been permanently lost."},
    ]

    pools = {
        "0": [
            "The logo is slightly stretched on the login page for a few screen sizes.",
            "There is a typo in the tagline on the About page.",
            "Padding is misaligned by 2px in the user settings modal.",
            "Copyright year in the footer still says 2024.",
        ],
        "1": [
            "The CSV export occasionally drops the final row; re-running the export fixes it.",
            "Push notifications are arriving several hours late.",
            "Search autocomplete dropdown is sluggish on mobile browsers.",
            "Report download button requires a double-click on Firefox.",
        ],
        "2": [
            "Search results are stale until the user manually refreshes the page.",
            "The admin dashboard now takes minutes to load each page.",
            "Webhook notifications are failing intermittently for 30% of accounts.",
            "Analytics charts fail to render for users in the EU region.",
        ],
        "3": [
            "Checkout fails for every customer and there is no alternative way to pay.",
            "All user logins via SSO/SAML are throwing 500 Internal Server Error.",
            "The primary PostgreSQL database pool is 100% exhausted, rejecting all writes.",
            "Mobile app crashes immediately on launch for all iOS 18 users.",
        ],
        "4": [
            "All customer data in the EU region has been permanently deleted.",
            "The entire platform has been unreachable for all customers for the past hour.",
            "Ransomware attack encrypted production databases and backups.",
            "Complete data center power loss taking down all regional clusters simultaneously.",
        ],
    }

    for _ in range(n // 5):
        for lvl_id, pool in pools.items():
            records.append({
                "state": random.choice(pool),
                "question": instruction,
                "options": levels,
                "label": lvl_id,
                "source": f"synthetic_severity_{lvl_id}",
            })

    return records


def generate_department_triage_cases(n: int = 8000) -> List[dict]:
    """Generates 5-class department queue routing cases (billing, tech, sales, account, other)."""
    instruction = "Which team should handle this support message?"
    criteria = {
        "billing": "Refunds, payments, invoices, subscriptions, or unexpected charges",
        "tech": "Bugs, errors, crashes, downtime, or integration failures",
        "sales": "Pricing questions, quotes, upgrades, demos, or new purchases",
        "account": "Login issues, password resets, profile changes, or data deletion requests",
        "other": "Anything that does not match the other categories",
    }
    options = [{"id": k, "description": v} for k, v in criteria.items()]

    tickets = {
        "billing": [
            "I was charged twice on my card this month for the same subscription, how do I get that fixed?",
            "I want to cancel my annual plan and get a refund for the unused months.",
            "The invoice PDF shows the wrong VAT number on line 3.",
            "Payment failed on credit card ending in 4242. How do I update payment method?",
            "Can you send a receipt for our last three billing cycles for accounting?",
            "We were billed for 50 seats but only 35 users are currently active.",
        ],
        "tech": [
            "The iOS app crashes immediately every time I try to open a report.",
            "The API returns a 500 error whenever we upload files larger than 10MB.",
            "Our SSO integration with Okta started returning empty profiles this morning after your release.",
            "PostgreSQL connection pool exhausted on port 5432, throwing connection refused.",
            "Webhook deliveries are failing intermittently with timeout errors.",
            "Database deadlock during concurrent writes on the events table.",
            "Frontend displays a blank white screen on Safari 17.",
        ],
        "sales": [
            "Do you offer a discount if we buy 50 seats for our team?",
            "Can I book a demo of the enterprise features for next Tuesday?",
            "What does the Pro plan cost per seat per month?",
            "We need a formal quote including on-prem hosting for a 3-year term.",
            "Looking to speak with an account executive regarding custom SLA tiers.",
            "Can we negotiate pricing for annual commitment with 500 seats?",
        ],
        "account": [
            "I forgot my password and the reset email never arrives.",
            "How do I change the email address associated with my account?",
            "Please permanently delete all of my personal data under GDPR.",
            "Our primary administrator left the company; how do we transfer account ownership?",
            "Unable to log in due to lost Google Authenticator 2FA device.",
            "Update our company profile name and billing contact email.",
        ],
        "other": [
            "I just want to say the new dashboard looks amazing.",
            "Where is your office located? Asking because my company ships hardware nearby.",
            "Is your team hiring senior backend engineers in London?",
            "Are you speaking at the upcoming KubeCon conference?",
            "Just wanted to share a podcast recommendation with your design team.",
            "Happy holidays to the team! Appreciate all the help this year.",
        ],
    }

    records = []
    for _ in range(n // 5):
        for dept, pool in tickets.items():
            records.append({
                "state": random.choice(pool),
                "question": instruction,
                "options": options,
                "label": dept,
                "source": f"synthetic_dept_{dept}",
            })
    return records


# =====================================================================
# 2. Curated Open Datasets: Banking77 (Intent) & Emotion (Sentiment)
# =====================================================================

def prepare_banking_choice(max_samples: int = 15000) -> List[dict]:
    """Prepares multi-class choice questions from Banking77 with dynamic distractor pools."""
    print("Fetching mteb/banking77...")
    ds = load_dataset("mteb/banking77", split="train")
    
    # Collect all distinct labels and descriptions
    label_to_desc = {}
    for row in ds:
        lbl_clean = row["label_text"]
        if lbl_clean not in label_to_desc:
            desc = lbl_clean.replace("_", " ").capitalize()
            label_to_desc[lbl_clean] = desc
            
    all_labels = list(label_to_desc.keys())
    records = []

    for row in ds:
        gold = row["label_text"]
        # In 20% of cases, test explicit catch-all negative rejection ("other")
        include_other = (random.random() < 0.20)
        
        distractors = [l for l in all_labels if l != gold]
        k = random.randint(3, 4)
        sampled = random.sample(distractors, k)
        
        if include_other:
            # Gold label is omitted from options; target is 'other'
            pool = sampled
            options = [{"id": l, "description": label_to_desc[l]} for l in pool]
            options.append({"id": "other", "description": "Anything that does not match the other categories"})
            target = "other"
        else:
            pool = [gold] + sampled
            random.shuffle(pool)
            options = [{"id": l, "description": label_to_desc[l]} for l in pool]
            target = gold

        records.append({
            "state": row["text"],
            "question": "Which banking customer support category best matches this inquiry?",
            "options": options,
            "label": target,
            "source": "banking77",
        })

        if len(records) >= max_samples:
            break

    print(f"  -> Processed {len(records)} Banking77 Choice records")
    return records


def prepare_emotion_sentiment(max_samples: int = 10000) -> List[dict]:
    """Prepares emotion and sentiment cases from dair-ai/emotion."""
    print("Fetching dair-ai/emotion...")
    ds = load_dataset("dair-ai/emotion", split="train")
    
    # 0: sadness, 1: joy, 2: love, 3: anger, 4: fear, 5: surprise
    label_names = ["sadness", "joy", "love", "anger", "fear", "surprise"]
    
    records = []
    for row in ds:
        label_idx = row["label"]
        if label_idx < len(label_names):
            lbl = label_names[label_idx]
            
            # Map into a Choice task: What emotion does the text express?
            options = [
                {"id": "joy", "description": "Positive emotion, happiness, or satisfaction."},
                {"id": "sadness", "description": "Disappointment, sadness, or regret."},
                {"id": "anger", "description": "Frustration, annoyance, or anger."},
                {"id": "fear", "description": "Anxiety, worry, or fear."},
            ]
            if lbl in ("joy", "sadness", "anger", "fear"):
                records.append({
                    "state": row["text"],
                    "question": "What primary emotional state is conveyed by this text?",
                    "options": options,
                    "label": lbl,
                    "source": "dair_emotion",
                })
                if len(records) >= max_samples:
                    break

    print(f"  -> Processed {len(records)} Emotion records")
    return records


# =====================================================================
# 3. Adversarial Reasoning Core (ANLI + WANLI)
# =====================================================================

def prepare_adversarial_core(max_samples: int = 20000) -> List[dict]:
    """Loads balanced adversarial multi-hop reasoning pairs from ANLI and WANLI."""
    print("Fetching ANLI & WANLI for reasoning core...")
    records = []
    
    # ANLI
    for r in ["train_r1", "train_r2", "train_r3"]:
        split = load_dataset("facebook/anli", split=r)
        label_map = {0: "supported", 1: "insufficient", 2: "contradicted"}
        for row in split:
            p = (row.get("premise") or "").strip()
            h = (row.get("hypothesis") or "").strip()
            lbl = row.get("label")
            if p and h and lbl in label_map:
                records.append({
                    "state": p,
                    "question": f"Is the following claim supported, contradicted, or is evidence insufficient: '{h}'?",
                    "options": [
                        {"id": "supported", "description": f"The evidence establishes that: {h}."},
                        {"id": "contradicted", "description": f"The evidence contradicts that: {h}."},
                        {"id": "insufficient", "description": f"The evidence is insufficient to verify: {h}."},
                    ],
                    "label": label_map[lbl],
                    "source": f"anli_{r}",
                })

    # WANLI
    wanli_train = load_dataset("alisawuffles/WANLI", split="train")
    gold_to_id = {"entailment": "supported", "neutral": "insufficient", "contradiction": "contradicted"}
    for row in wanli_train:
        p = (row.get("premise") or "").strip()
        h = (row.get("hypothesis") or "").strip()
        g = (row.get("gold") or "").lower().strip()
        if p and h and g in gold_to_id:
            records.append({
                "state": p,
                "question": f"Is the following claim supported, contradicted, or is evidence insufficient: '{h}'?",
                "options": [
                    {"id": "supported", "description": f"The evidence establishes that: {h}."},
                    {"id": "contradicted", "description": f"The evidence contradicts that: {h}."},
                    {"id": "insufficient", "description": f"The evidence is insufficient to verify: {h}."},
                ],
                "label": gold_to_id[g],
                "source": "wanli",
            })

    random.shuffle(records)
    selected = records[:max_samples]
    print(f"  -> Retained {len(selected)} Adversarial Core reasoning pairs")
    return selected


# =====================================================================
# Main Corpus Assembly
# =====================================================================

def build_decision_corpus(
    output_dir: str = "data_decision",
    max_train: int = 80000,
    val_samples: int = 4000,
    seed: int = 42,
):
    random.seed(seed)
    os.makedirs(output_dir, exist_ok=True)

    print("=============================================================")
    print("Building Von-1.1 Operational Decision Dataset")
    print("=============================================================")

    # 1. Operational Policy & Verification (Noul)
    refund_cases = generate_refund_policy_cases(6000)
    secret_cases = generate_secret_leak_cases(5000)
    urgency_cases = generate_operational_urgency_cases(5000)
    noul_cases = refund_cases + secret_cases + urgency_cases
    print(f"Synthesized {len(noul_cases)} Noul verification cases")

    # 2. Ordinal Scoring (Score)
    frustration_cases = generate_frustration_score_cases(5000)
    severity_cases = generate_incident_severity_cases(5000)
    score_cases = frustration_cases + severity_cases
    print(f"Synthesized {len(score_cases)} Score ordinal cases")

    # 3. Categorical Routing (Choice)
    dept_cases = generate_department_triage_cases(8000)
    banking_cases = prepare_banking_choice(15000)
    emotion_cases = prepare_emotion_sentiment(10000)
    choice_cases = dept_cases + banking_cases + emotion_cases
    print(f"Curated {len(choice_cases)} Choice routing cases (including department triage)")

    # 4. Adversarial Reasoning Core
    reasoning_cases = prepare_adversarial_core(20000)

    # Combine
    all_records = noul_cases + score_cases + choice_cases + reasoning_cases
    random.shuffle(all_records)
    print(f"\nTotal collected operational decision samples: {len(all_records):,}")

    val_records = all_records[:val_samples]
    train_records = all_records[val_samples : val_samples + max_train]

    print(f"Final Train Set: {len(train_records):,} records")
    print(f"Final Val Set:   {len(val_records):,} records")

    # Export
    train_path = os.path.join(output_dir, "train.jsonl")
    val_path = os.path.join(output_dir, "val.jsonl")

    with open(train_path, "w", encoding="utf-8") as f:
        for rec in train_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with open(val_path, "w", encoding="utf-8") as f:
        for rec in val_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"\nSuccessfully written to {train_path} and {val_path}!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=str, default="data_decision")
    parser.add_argument("--max_train", type=int, default=80000)
    parser.add_argument("--val_samples", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    build_decision_corpus(
        output_dir=args.output_dir,
        max_train=args.max_train,
        val_samples=args.val_samples,
        seed=args.seed,
    )
