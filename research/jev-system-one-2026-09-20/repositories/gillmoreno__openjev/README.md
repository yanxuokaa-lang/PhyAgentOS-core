# openjev

Local examples for [Laya](https://huggingface.co/convaiinnovations/laya), a 421M System 1 decision model. It fills typed slots (`choice`, `score`, `noul`) over JSON state. It does not generate text.

Needs the Python 3.11 venv in this repo (torch 2.4 + Metal). From this directory:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install laya
```

If `python3` has no torch, the scripts hop into `.venv` automatically.

```bash
python3 example.py           # support-email triage
python3 trading_example.py   # toy trading tick (fake book, no orders)
```

`example.py` is the email: department, urgency, churn, phishing. `trading_example.py` is the same three slot types on a fake order-book snapshot. Neither places trades.
