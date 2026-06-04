# 🌉 Cross-Chain Bridge Monitor

> Monitor cross-chain bridge tokens, routes & activity across Stargate, Hop, Across, Wormhole & more — with real-time Telegram alerts powered by CoinGecko API + LI.FI API.

![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python)
![CoinGecko](https://img.shields.io/badge/CoinGecko-API-8DC63F?style=flat-square)
![LI.FI](https://img.shields.io/badge/LI.FI-API-blueviolet?style=flat-square)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram)
![Ethereum](https://img.shields.io/badge/Ethereum-Mainnet-627EEA?style=flat-square&logo=ethereum)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 🔍 What is Cross-Chain Bridge Monitoring?

Cross-chain bridge monitoring tracks bridge token prices, market caps, trading volumes, and available routes between blockchains — helping DeFi participants identify bridging opportunities and stay informed about bridge health before moving assets cross-chain.

This bot tracks bridges using:
- 📊 **CoinGecko API** — free token price, market cap, volume & 24h/7d changes (no API key needed)
- 🔗 **LI.FI API** — live bridge routes & connections between chains (no API key needed)
- 🌉 **8 Major Bridges** — Stargate, Hop, Across, Celer, Synapse, Wormhole, Axelar, deBridge

---

## ✨ Features

- 📊 **Bridge Token Stats** — price, market cap, 24h volume, % change
- 🌉 **Route Finder** — find available bridges between any 2 chains
- 🏆 **Bridge Ranking** — all bridges ranked by market cap
- 🔔 **Price Alerts** — Telegram alert on token price spike/drop > 10%
- 📡 **Auto Monitor** — background polling every 5 minutes
- 🔗 **LI.FI Integration** — live route data from 20+ bridge aggregators
- 🤖 **Telegram Bot** — 9 interactive commands
- ⛓️ **Multi-Chain** — supports 10 chains including Base, ZkSync, Solana

---

## 🚀 Quick Start

### 1. Install dependencies

    pip install requests

### 2. Set credentials

Open `cross_chain_bridge_monitor.py` and configure:

    TELEGRAM_TOKEN   = "your_telegram_bot_token"
    TELEGRAM_CHAT_ID = "your_chat_id"

> No additional API keys needed — CoinGecko & LI.FI are free and open!

### 3. Run as Telegram Bot

    python cross_chain_bridge_monitor.py

### 4. Quick CLI check (one-time)

    python cross_chain_bridge_monitor.py check stargate
    python cross_chain_bridge_monitor.py check wormhole

---

## 🤖 Telegram Commands

| Command | Description |
|---------|-------------|
| `/bridge_info <bridge>` | Bridge token stats & info |
| `/bridge_add <bridge>` | Add bridge to watchlist |
| `/bridge_remove <bridge>` | Remove bridge from watchlist |
| `/bridge_list` | Show watched bridges |
| `/bridge_tvl` | All bridges overview by market cap |
| `/bridge_route <from> <to>` | Available routes between chains |
| `/bridge_monitor on/off` | Toggle auto price monitoring |
| `/bridge_bridges` | List all available bridges |
| `/bridge_chains` | List supported chains |

---

## 📊 Sample Output

    ⭐ Stargate
    ━━━━━━━━━━━━━━━━━━━━━━
    📝 Native asset bridge built on LayerZero

    💎 Token: $STG
    💵 Price       : $0.2841
    📊 Market Cap  : $284.1M
    📈 Vol 24h     : $12.3M
    📈 Change 24h  : +5.24%
    📅 Change 7d   : +12.80%
    🔁 LI.FI       : Supported ✅

    🔗 Supported Chains (7):
    Ethereum • BSC • Polygon • Avalanche • Arbitrum • Optimism • Base

    🌐 https://stargate.finance
    ⏰ 2026-06-04 09:00:00

---

## 🚨 Alert System

| Alert | Trigger |
|-------|---------|
| 📈 Token Pump | 24h price change > +20% |
| 📉 Token Drop | 24h price change < -10% |

---

## 🏗️ Architecture

    cross_chain_bridge_monitor.py
    ├── CoinGeckoClient     → Token price & market data
    │   ├── get_token_data()      → single token price/mcap/vol
    │   ├── get_multi_tokens()    → batch fetch all bridge tokens
    │   └── get_eth_price()       → ETH USD price
    ├── LiFiClient          → Bridge routes & tools
    │   ├── get_tools()           → list all supported bridges
    │   ├── get_connections()     → routes between 2 chains
    │   ├── get_chains()          → supported chain list
    │   └── find_bridge_tool()    → lookup bridge by key
    ├── BridgeMonitor       → Core monitoring engine
    │   ├── get_bridge_info()          → full bridge info (token + routes)
    │   ├── get_all_bridges_overview() → market cap ranking
    │   ├── check_price_alerts()       → detect price anomalies
    │   ├── get_bridge_route()         → fetch live routes
    │   └── get_price_trend()          → session price history trend
    └── BridgeBot           → Telegram bot with 9 commands
        └── _monitor_loop()       → background polling thread

---

## 📡 Data Sources

| Source | Usage | Auth |
|--------|-------|------|
| [CoinGecko API](https://www.coingecko.com/api) | Token prices, market cap, volume | Free, no key |
| [LI.FI API](https://docs.li.fi) | Bridge routes & connections | Free, no key |

---

## 🌉 Supported Bridges

| Bridge | Token | Chains | Type |
|--------|-------|--------|------|
| ⭐ Stargate | STG | 7 chains | Native asset (LayerZero) |
| 🐰 Hop Protocol | HOP | 6 chains | Fast rollup bridge |
| 🌉 Across | ACX | 6 chains | Intent-based bridge |
| 🔵 Celer cBridge | CELR | 6 chains | Liquidity network |
| 🔴 Synapse | SYN | 6 chains | Cross-chain AMM |
| 🌀 Wormhole | W | 6 chains | Generic messaging |
| 🔮 Axelar | AXL | 6 chains | Interchain protocol |
| 🟣 deBridge | DBR | 6 chains | Zero-TVL intent bridge |

---

## ⛓️ Supported Chains

| Chain | ID |
|-------|----|
| Ethereum | 1 |
| BSC | 56 |
| Polygon | 137 |
| Avalanche | 43114 |
| Arbitrum | 42161 |
| Optimism | 10 |
| Base | 8453 |
| Fantom | 250 |
| Gnosis | 100 |
| ZkSync | 324 |

---

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POLL_INTERVAL` | 300s | How often to check prices |
| `TVL_DROP_ALERT` | 10% | Price drop threshold for alert |
| `TVL_PUMP_ALERT` | 20% | Price pump threshold for alert |

---

## 📱 Caption

    🌉 Cross-Chain Bridge Monitor — Python Tool

    Track 8 major DeFi bridges in real-time via Telegram bot:
    ⭐ Stargate • 🐰 Hop • 🌉 Across • 🌀 Wormhole
    🔮 Axelar • 🔴 Synapse • 🔵 Celer • 🟣 deBridge

    ✅ Token price, mcap & 24h/7d change
    ✅ Live route finder between 10 chains
    ✅ Price alerts (pump/drop)
    ✅ Auto monitor every 5 min
    ✅ 100% free APIs — no key needed

    Built with CoinGecko + LI.FI API 🔥

    🛠️ Web3 Python Toolkit by @rizalcodes
    🔗 github.com/rizalcodes/cross-chain-bridge-monitor

    #Python #Web3 #DeFi #Crypto #Bridge #CrossChain #Ethereum #Blockchain #OpenSource #BuidlSzn

---

## 💬 Commit Messages

    # Main file
    feat: add Cross-Chain Bridge Monitor Telegram bot

    - CoinGecko API for bridge token price, mcap, vol, 24h/7d change
    - LI.FI API for live bridge routes between 10 chains
    - 8 bridges: Stargate, Hop, Across, Celer, Synapse, Wormhole, Axelar, deBridge
    - 9 Telegram commands: /bridge_info, /bridge_route, /bridge_tvl, etc
    - Background monitor thread with price alerts
    - No API keys required, zero external dependencies beyond requests

    # README
    docs: add README for Cross-Chain Bridge Monitor

    - Setup instructions, commands table, sample output
    - Architecture overview, supported bridges & chains table
    - Data sources, configuration reference, disclaimer

---

## 🏷️ Topics / Tags

    python web3 defi crypto bridge cross-chain ethereum telegram-bot
    coingecko lifi stargate wormhole axelar blockchain monitor

---

## ⚠️ Disclaimer

> **This tool is for informational purposes only. Token price data reflects bridge governance tokens, not bridge TVL or volume directly. Always do your own research before bridging assets cross-chain.**

---

## 🔧 Requirements

    requests>=2.28.0

No Web3.py required — uses REST APIs only!

---

## 👤 Author

**Rizal** — [@rizalcodes](https://github.com/rizalcodes)

> Building Web3 tools with Python 🐍⛓️

---

## 📄 License

MIT License — free to use, modify, and distribute.
