# Jevons Autonomous Agent (Jev)

Jev is an autonomous AI agent running entirely in the browser that manages the **Jevons** token ecosystem on the Robinhood Chain. Jev is equipped with a retro-industrial terminal UI and a highly optimized on-chain engine designed to interact seamlessly with **Pons V2 Bonding Curves** and the **Uniswap V4 Universal Router**.

**Jevons CA:** `0xBe90cf5857E1Ba0D911Bc9E6E9495da91543d746`

## The Deflationary Flywheel (Buyback & Burn Tech)

The core technology behind Jev is its autonomous tracking and execution loop. 

Every 60 seconds, without any human intervention or multisig delays, Jev performs the following on-chain sequence:
1. **Sweep & Claim:** Monitors the Pons V2 Fee Escrow and claims accrued protocol creator fees.
2. **Split:** Splits the claimed ETH 50/50—sending half to a secure treasury and retaining half for the buyback.
3. **V4 Swap:** Integrates natively with the Uniswap V4 Universal Router using custom calldata (`V4_SWAP` and `SWEEP`) to market-buy Jevons tokens using the retained ETH.
4. **Burn:** Automatically sends the acquired tokens to `0x000000000000000000000000000000000000dEaD` for permanent supply reduction.

## Tech Stack
* **Frontend:** Vite + Vanilla JS (No bloated frameworks, just raw speed and a beautiful retro terminal UI).
* **Web3/Blockchain:** `ethers.js` v6.
* **Integrations:**
  * Pons V2 Bonding Curve & Factory
  * Pons V2 Fee Escrow
  * Uniswap V4 Universal Router (Robinhood Chain)
* **Security:** All private keys (Treasury, Deployer) are generated on the client and stored securely in the local browser session (`localStorage` & `.env`). No keys are checked into source control.

## Running Locally

To run the Jevons Agent locally, you will need to provide your own API keys for the AI integration. OpenRouter API (for LLM reasoning) and FAL AI API (for image generation) are used. 

1. Install dependencies:
   ```bash
   npm install
   ```
2. Create a `.env` file in the root directory and add your API keys:
   ```env
   VITE_OPENROUTER_API_KEY=your_key_here
   VITE_FAL_API_KEY=your_key_here
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```
4. Open your browser and type `track Jevons` into the terminal UI to kick off the autonomous buyback cycle!

![Jev Agent Terminal UI](terminal.png)

## License
MIT
