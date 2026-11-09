<div align="center">
  <img src="assets/hero-banner.png" width="100%" alt="jev-notion Hero Banner" />

  <br /><br />

  <a href="https://github.com/jeffloo886/jev-notion/stargazers"><img src="https://img.shields.io/github/stars/jeffloo886/jev-notion?style=for-the-badge&logo=star&color=ffb800&logoColor=white" alt="GitHub Stars" /></a>
  <a href="https://github.com/jeffloo886/jev-notion/releases/latest"><img src="https://img.shields.io/github/v/release/jeffloo886/jev-notion?style=for-the-badge&color=7928CA&logo=apple" alt="Latest Release" /></a>
  <a href="https://github.com/jeffloo886/jev-notion/actions/workflows/ci.yml"><img src="https://img.shields.io/badge/CI-Passing-10B981?style=for-the-badge&logo=githubactions&logoColor=white" alt="CI Status" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge" alt="License: MIT" /></a>
  <a href="#-8-language-dynamic-localization-showcase"><img src="https://img.shields.io/badge/Languages-8%20Supported-0070F3?style=for-the-badge&logo=googletranslate&logoColor=white" alt="8 Languages" /></a>

  <br /><br />

  <h1>🔮 jev-notion</h1>
  <p>
    <strong>Fill Notion database properties with calibrated AI judgments.</strong><br />
    Second-level latency (≤2s) • Micro-cent cost ($0.00004/row) • Native macOS App (SwiftUI) + CLI • Zero Server.
  </p>

  <p>
    <a href="#-quick-download-macos-app"><strong>📦 Download macOS App (2.8MB)</strong></a> •
    <a href="#-quick-start-cli"><strong>⚡ Run in Terminal</strong></a> •
    <a href="#-8-language-dynamic-localization-showcase"><strong>🌐 8-Language Preview</strong></a> •
    <a href="#-battle-tested-benchmarks"><strong>📊 Benchmarks</strong></a>
  </p>

  <p>
    <a href="README.md">English</a> • <a href="README.zh-CN.md">简体中文</a>
  </p>

  <br />
</div>

---

## ⚡ Highlights

| Feature | Description |
|:---|:---|
| ⚡ **Second-Level Latency (≤ 2s)** | Adaptive polling catches row edits in under 2 seconds — beating Notion's 5-minute webhook queues. |
| 🎯 **Calibrated Probabilities** | Jev returns typed outputs with mathematical confidence ($\ge 60\%$). Uncertain entries go to a review queue — no silent hallucinations. |
| 💰 **Micro-Cent Pricing** | ~$0.00004 per row ($0.042 / 1M input tokens, free output). 10,000 rows costs around forty cents. |
| 🖥️ **Native macOS Client (SwiftUI)** | Crafted in pure SwiftUI with Notion's iconic 9-color palette, Jev real-time telemetry HUD, and interactive card drawer. |
| 🌐 **8-Language Dynamic Localization** | Instant hot-switching between 8 languages with zero application restart required. |
| 🔐 **Keychain Hardware Security** | Credentials stored encrypted in Apple Keychain; zero plaintext tokens on disk. |
| 🛠️ **Universal CLI & Engine Library** | Fully autonomous terminal workflow (`npx jev-notion`) or embeddable TypeScript engine. |

---

## 📊 Battle-Tested Benchmarks

| Feature | **jev-notion** | Notion Native AI | Custom Webhook Server |
|:---|:---:|:---:|:---:|
| **Cost** | **~$0.00004 / row** (40¢ / 10k rows) | $10 / user / month | Server hosting + LLM bills |
| **Output Type** | **Calibrated Probabilities ($\ge 60\%$)** | Plain text (guesses) | Plain text (guesses) |
| **Detection Speed** | **≤ 2 seconds** | Manual trigger | 1 – 5 minutes (aggregated) |
| **Review Queue** | **Native Visual Cards** | None (overwrites) | None (needs custom UI) |
| **Client UI** | **Native macOS SwiftUI App** | Web/Electron only | None |
| **Multilingual** | **8 Languages Hot-Switching** | System default | English only |
| **Self-Hosted** | **100% Yours (MIT)** | Proprietary SaaS | High maintenance |

---

## 🌐 8-Language Dynamic Localization Showcase

Experience seamless, real-time hot-switching across **8 world languages**. Click any language tab below to see full-resolution macOS app screenshots:

<details open>
<summary><b>🇺🇸 English (Default)</b> — Click to expand</summary>
<br />
<img src="assets/lang_en.png" width="100%" alt="English Interface Preview" />
</details>

<details>
<summary><b>🇨🇳 简体中文 (Simplified Chinese)</b> — Click to expand</summary>
<br />
<img src="assets/lang_zh-Hans.png" width="100%" alt="Simplified Chinese Interface Preview" />
</details>

<details>
<summary><b>🇭🇰 繁體中文 (Traditional Chinese)</b> — Click to expand</summary>
<br />
<img src="assets/lang_zh-Hant.png" width="100%" alt="Traditional Chinese Interface Preview" />
</details>

<details>
<summary><b>🇯🇵 日本語 (Japanese)</b> — Click to expand</summary>
<br />
<img src="assets/lang_ja.png" width="100%" alt="Japanese Interface Preview" />
</details>

<details>
<summary><b>🇰🇷 한국어 (Korean)</b> — Click to expand</summary>
<br />
<img src="assets/lang_ko.png" width="100%" alt="Korean Interface Preview" />
</details>

<details>
<summary><b>🇫🇷 Français (French)</b> — Click to expand</summary>
<br />
<img src="assets/lang_fr.png" width="100%" alt="French Interface Preview" />
</details>

<details>
<summary><b>🇩🇪 Deutsch (German)</b> — Click to expand</summary>
<br />
<img src="assets/lang_de.png" width="100%" alt="German Interface Preview" />
</details>

<details>
<summary><b>🇪🇸 Español (Spanish)</b> — Click to expand</summary>
<br />
<img src="assets/lang_es.png" width="100%" alt="Spanish Interface Preview" />
</details>

---

## 📦 Quick Download (macOS App)

Download the ultra-lightweight **2.8 MB** pre-compiled app:

<div align="center">
  <a href="https://github.com/jeffloo886/jev-notion/releases/download/v0.1.0/JevNotion-v0.1.0-macOS.zip">
    <img src="https://img.shields.io/badge/Download-JevNotion_v0.1.0_(2.8MB)-7928CA?style=for-the-badge&logo=apple&logoColor=white" alt="Download macOS App" height="42" />
  </a>
</div>

1. Download [`JevNotion-v0.1.0-macOS.zip`](https://github.com/jeffloo886/jev-notion/releases/download/v0.1.0/JevNotion-v0.1.0-macOS.zip).
2. Unzip and drag `JevNotion.app` to your `/Applications` folder.
3. Launch `JevNotion` and enter your Notion & Jev credentials in Settings (`⌘,`).

---

## ⚡ Quick Start (CLI)

Prefer running from your terminal or a remote server?

### 1. Setup Keys
Create an internal integration at [notion.so/profile/integrations](https://www.notion.so/profile/integrations) and get a Jev key from [typesafe.ai](https://typesafe.ai). Put them in `.env`:

```bash
NOTION_TOKEN=ntn_...
TYPESAFE_API_KEY=ts_...
```

### 2. Run
```bash
# Automated one-command sync
npx jev-notion

# Read-only inspection (prints suggestions without writing)
npx jev-notion scan

# Apply approved suggestions from JSON
npx jev-notion apply

# Install as a background launchd daemon (macOS)
npx jev-notion install
```

---

## 🏗️ Architecture

```
                                  ┌────────────────────────┐
                                  │ Notion Database Table  │
                                  └───────────┬────────────┘
                                              │ (≤2s Polling)
                                              ▼
┌───────────────────────┐         ┌────────────────────────┐
│ Native macOS Client   │ ◄─────► │   jev-notion Core      │
│ (SwiftUI + 8-Lang)    │         │  (Token Bucket Limiter)│
└───────────────────────┘         └───────────┬────────────┘
                                              │ Typed Evidence
                                              ▼
                                  ┌────────────────────────┐
                                  │   Jev Precision Model  │
                                  │  (Calibrated Prob >=60)│
                                  └───────────┬────────────┘
                                              │ Atomic Writes
                                              ▼
                                  ┌────────────────────────┐
                                  │ Notion Properties Set  │
                                  └────────────────────────┘
```

---

## 🤝 Contributing

Contributions are welcome! Please check out [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, running tests (`npm test`, 269 tests), and compiling the macOS app (`./app/build.sh`).

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security Policy](SECURITY.md)

---

## 📄 License

[MIT](LICENSE) © 2026 [jeffloo886](https://github.com/jeffloo886) & contributors.

<div align="center">
  <sub>⭐ If you find jev-notion useful, please consider giving it a star on GitHub!</sub>
</div>
