"""
cross_chain_bridge_monitor.py - Cross-Chain Bridge Monitor
By Rizal | github.com/rizalcodes
Monitor cross-chain bridge info & routes
Multi-source: CoinGecko (token prices) + LI.FI API (routes) + static data
Output: Real-time alerts + Telegram bot
"""

import os
import time
import logging
import requests
from datetime import datetime
from collections import defaultdict

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN",   "Your_Telegram_Token_Bot_Here")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "Your_Chat_ID_Here")

POLL_INTERVAL  = 300
TVL_DROP_ALERT = 10.0
TVL_PUMP_ALERT = 20.0

# Bridge definitions
# coingecko_id → untuk fetch token price/mcap bridge token
# lifi_key     → nama bridge di LI.FI tools API
BRIDGES = {
    "stargate"  : {
        "name"       : "Stargate",
        "color"      : "⭐",
        "token"      : "STG",
        "coingecko"  : "stargate-finance",
        "lifi_key"   : "stargate",
        "website"    : "https://stargate.finance",
        "chains"     : ["Ethereum","BSC","Polygon","Avalanche","Arbitrum","Optimism","Base"],
        "description": "Native asset bridge built on LayerZero",
    },
    "hop"       : {
        "name"       : "Hop Protocol",
        "color"      : "🐰",
        "token"      : "HOP",
        "coingecko"  : "hop-protocol",
        "lifi_key"   : "hop",
        "website"    : "https://hop.exchange",
        "chains"     : ["Ethereum","Polygon","Arbitrum","Optimism","Gnosis","Base"],
        "description": "Fast cross-rollup token bridge",
    },
    "across"    : {
        "name"       : "Across",
        "color"      : "🌉",
        "token"      : "ACX",
        "coingecko"  : "across-protocol",
        "lifi_key"   : "across",
        "website"    : "https://across.to",
        "chains"     : ["Ethereum","Polygon","Arbitrum","Optimism","Base","ZkSync"],
        "description": "Intent-based bridge, fastest UX",
    },
    "celer"     : {
        "name"       : "Celer cBridge",
        "color"      : "🔵",
        "token"      : "CELR",
        "coingecko"  : "celer-network",
        "lifi_key"   : "cbridge",
        "website"    : "https://cbridge.celer.network",
        "chains"     : ["Ethereum","BSC","Polygon","Avalanche","Arbitrum","Optimism"],
        "description": "Multi-chain liquidity network",
    },
    "synapse"   : {
        "name"       : "Synapse",
        "color"      : "🔴",
        "token"      : "SYN",
        "coingecko"  : "synapse-2",
        "lifi_key"   : "synapse",
        "website"    : "https://synapseprotocol.com",
        "chains"     : ["Ethereum","BSC","Polygon","Avalanche","Arbitrum","Optimism"],
        "description": "Cross-chain AMM & bridge",
    },
    "wormhole"  : {
        "name"       : "Wormhole",
        "color"      : "🌀",
        "token"      : "W",
        "coingecko"  : "wormhole",
        "lifi_key"   : "wormhole",
        "website"    : "https://wormhole.com",
        "chains"     : ["Ethereum","BSC","Polygon","Avalanche","Solana","Arbitrum"],
        "description": "Generic messaging bridge for many chains",
    },
    "axelar"    : {
        "name"       : "Axelar",
        "color"      : "🔮",
        "token"      : "AXL",
        "coingecko"  : "axelar",
        "lifi_key"   : "axelar",
        "website"    : "https://axelar.network",
        "chains"     : ["Ethereum","BSC","Polygon","Avalanche","Cosmos","Arbitrum"],
        "description": "Interchain communication protocol",
    },
    "debridge"  : {
        "name"       : "deBridge",
        "color"      : "🟣",
        "token"      : "DBR",
        "coingecko"  : "debridge",
        "lifi_key"   : "deBridge",
        "website"    : "https://debridge.finance",
        "chains"     : ["Ethereum","BSC","Polygon","Avalanche","Arbitrum","Solana"],
        "description": "Zero-TVL intent-based bridge",
    },
}

CHAIN_IDS = {
    "Ethereum" : 1,
    "BSC"      : 56,
    "Polygon"  : 137,
    "Avalanche": 43114,
    "Arbitrum" : 42161,
    "Optimism" : 10,
    "Base"     : 8453,
    "Fantom"   : 250,
    "Gnosis"   : 100,
    "ZkSync"   : 324,
}


# ─────────────────────────────────────────────
# 1. COINGECKO CLIENT  — free, no key needed
# ─────────────────────────────────────────────
class CoinGeckoClient:
    """
    CoinGecko free API — token price, mcap, 24h change.
    No API key required for basic endpoints.
    Rate limit: ~10-30 req/min free tier.
    """
    BASE = "https://api.coingecko.com/api/v3"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept"    : "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; bridge-monitor/3.0)",
        })
        self._cache    = {}
        self._cache_ts = {}

    def _get(self, path: str, params: dict = None) -> dict | list | None:
        try:
            r = self.session.get(f"{self.BASE}{path}", params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            log.error(f"CoinGecko HTTP {r.status_code} {path}: {e}")
            return None
        except Exception as e:
            log.error(f"CoinGecko error {path}: {e}")
            return None

    def get_token_data(self, coingecko_id: str) -> dict:
        """Get price, mcap, 24h change, 7d change untuk satu token."""
        now = time.time()
        if coingecko_id in self._cache and now - self._cache_ts.get(coingecko_id, 0) < 300:
            return self._cache[coingecko_id]
        data = self._get(
            "/simple/price",
            params={
                "ids"                    : coingecko_id,
                "vs_currencies"          : "usd",
                "include_market_cap"     : "true",
                "include_24hr_vol"       : "true",
                "include_24hr_change"    : "true",
                "include_7d_change"      : "true",
            }
        )
        if not data or coingecko_id not in data:
            return {}
        result = {
            "price_usd"  : float(data[coingecko_id].get("usd",              0) or 0),
            "mcap_usd"   : float(data[coingecko_id].get("usd_market_cap",   0) or 0),
            "vol_24h"    : float(data[coingecko_id].get("usd_24h_vol",      0) or 0),
            "change_24h" : float(data[coingecko_id].get("usd_24h_change",   0) or 0),
            "change_7d"  : float(data[coingecko_id].get("usd_7d_change",    0) or 0),
        }
        self._cache[coingecko_id]    = result
        self._cache_ts[coingecko_id] = now
        log.info(f"✅ CoinGecko {coingecko_id}: ${result['price_usd']:.4f} ({result['change_24h']:+.2f}%)")
        return result

    def get_multi_tokens(self, ids: list) -> dict:
        """Fetch multiple tokens sekaligus — lebih efisien."""
        ids_str = ",".join(ids)
        now     = time.time()
        data    = self._get(
            "/simple/price",
            params={
                "ids"                : ids_str,
                "vs_currencies"      : "usd",
                "include_market_cap" : "true",
                "include_24hr_vol"   : "true",
                "include_24hr_change": "true",
                "include_7d_change"  : "true",
            }
        )
        if not data:
            return {}
        result = {}
        for cg_id, vals in data.items():
            result[cg_id] = {
                "price_usd" : float(vals.get("usd",            0) or 0),
                "mcap_usd"  : float(vals.get("usd_market_cap", 0) or 0),
                "vol_24h"   : float(vals.get("usd_24h_vol",    0) or 0),
                "change_24h": float(vals.get("usd_24h_change", 0) or 0),
                "change_7d" : float(vals.get("usd_7d_change",  0) or 0),
            }
        return result

    def get_eth_price(self) -> float:
        data = self.get_token_data("ethereum")
        return data.get("price_usd", 3000)


# ─────────────────────────────────────────────
# 2. LIFI CLIENT  — free, confirmed working
# ─────────────────────────────────────────────
class LiFiClient:
    """
    LI.FI API — bridge routes & tools.
    Free, no API key needed.
    Docs: https://docs.li.fi
    """
    BASE = "https://li.quest/v1"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept"    : "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; bridge-monitor/3.0)",
        })
        self._tools_cache    = []
        self._tools_cache_ts = 0

    def get_tools(self) -> dict:
        """GET /tools — list semua supported bridges & exchanges."""
        now = time.time()
        if self._tools_cache and now - self._tools_cache_ts < 600:
            return self._tools_cache
        try:
            r = self.session.get(f"{self.BASE}/tools", timeout=15)
            r.raise_for_status()
            data = r.json()
            self._tools_cache    = data
            self._tools_cache_ts = now
            bridges = data.get("bridges", [])
            log.info(f"✅ LI.FI tools loaded: {len(bridges)} bridges")
            return data
        except Exception as e:
            log.error(f"LiFi tools error: {e}")
            return {}

    def get_bridges(self) -> list:
        """Return list of bridge tools."""
        tools = self.get_tools()
        return tools.get("bridges", [])

    def get_connections(self, from_chain: int, to_chain: int) -> list:
        """GET /connections antara 2 chains."""
        try:
            r = self.session.get(
                f"{self.BASE}/connections",
                params={"fromChain": from_chain, "toChain": to_chain},
                timeout=15
            )
            r.raise_for_status()
            return r.json().get("connections", [])
        except Exception as e:
            log.error(f"LiFi connections error: {e}")
            return []

    def get_chains(self) -> list:
        """GET /chains — supported chains."""
        try:
            r = self.session.get(f"{self.BASE}/chains", timeout=15)
            r.raise_for_status()
            return r.json().get("chains", [])
        except Exception as e:
            log.error(f"LiFi chains error: {e}")
            return []

    def find_bridge_tool(self, lifi_key: str) -> dict:
        """Cari bridge info by key."""
        bridges = self.get_bridges()
        key_lower = lifi_key.lower()
        for b in bridges:
            if b.get("key", "").lower() == key_lower:
                return b
            if b.get("name", "").lower() == key_lower:
                return b
        return {}


# ─────────────────────────────────────────────
# 3. BRIDGE MONITOR ENGINE
# ─────────────────────────────────────────────
class BridgeMonitor:
    def __init__(self):
        self.coingecko   = CoinGeckoClient()
        self.lifi        = LiFiClient()
        self.watchlist   = set()
        self.price_history = defaultdict(list)   # key → [{price, ts}]
        self.alert_state   = defaultdict(dict)

    def add_bridge(self, key: str) -> bool:
        if key.lower() not in BRIDGES:
            return False
        self.watchlist.add(key.lower())
        return True

    def remove_bridge(self, key: str):
        self.watchlist.discard(key.lower())

    def get_watched_bridges(self) -> list:
        return list(self.watchlist)

    def get_bridge_info(self, key: str) -> dict:
        """
        Get bridge info dari CoinGecko (token price/mcap/vol)
        + LI.FI (supported chains & tools info).
        """
        key = key.lower()
        if key not in BRIDGES:
            return {}

        b      = BRIDGES[key]
        cg_id  = b.get("coingecko", "")
        token  = self.coingecko.get_token_data(cg_id) if cg_id else {}

        # LI.FI bridge tool info
        lifi_tool = self.lifi.find_bridge_tool(b.get("lifi_key", key))

        # Track price history untuk change detection
        price = token.get("price_usd", 0)
        if price > 0:
            self.price_history[key].append({
                "price"    : price,
                "timestamp": datetime.now().isoformat(),
            })
            if len(self.price_history[key]) > 100:
                self.price_history[key] = self.price_history[key][-100:]

        change_24h = token.get("change_24h", 0)

        return {
            "key"           : key,
            "name"          : b["name"],
            "color"         : b["color"],
            "token"         : b["token"],
            "chains"        : b["chains"],
            "website"       : b.get("website", ""),
            "description"   : b.get("description", ""),
            # Token metrics dari CoinGecko
            "price_usd"     : token.get("price_usd", 0),
            "mcap_usd"      : token.get("mcap_usd", 0),
            "vol_24h_usd"   : token.get("vol_24h", 0),
            "change_24h"    : change_24h,
            "change_7d"     : token.get("change_7d", 0),
            "direction"     : "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️",
            # LI.FI info
            "lifi_supported": bool(lifi_tool),
            "lifi_name"     : lifi_tool.get("name", ""),
            "lifi_url"      : lifi_tool.get("websiteUrl", b.get("website", "")),
            "timestamp"     : datetime.now().isoformat(),
        }

    def get_all_bridges_overview(self) -> list:
        """
        Fetch semua bridge tokens sekaligus dari CoinGecko.
        Return sorted by mcap.
        """
        ids    = [b["coingecko"] for b in BRIDGES.values() if b.get("coingecko")]
        tokens = self.coingecko.get_multi_tokens(ids)

        result = []
        for key, b in BRIDGES.items():
            cg_id = b.get("coingecko", "")
            t     = tokens.get(cg_id, {})
            mcap  = t.get("mcap_usd", 0)
            vol   = t.get("vol_24h", 0)
            chg   = t.get("change_24h", 0)
            result.append({
                "key"    : key,
                "name"   : b["name"],
                "color"  : b["color"],
                "token"  : b["token"],
                "price"  : t.get("price_usd", 0),
                "mcap"   : mcap,
                "vol_24h": vol,
                "change" : chg,
                "chains" : len(b["chains"]),
                "mcap_str": (
                    f"${mcap/1e9:.2f}B" if mcap >= 1e9
                    else f"${mcap/1e6:.1f}M" if mcap >= 1e6
                    else f"${mcap:,.0f}" if mcap > 0
                    else "N/A"
                ),
                "vol_str": (
                    f"${vol/1e9:.2f}B" if vol >= 1e9
                    else f"${vol/1e6:.1f}M" if vol >= 1e6
                    else f"${vol:,.0f}" if vol > 0
                    else "N/A"
                ),
            })
        return sorted(result, key=lambda x: x["mcap"], reverse=True)

    def check_price_alerts(self, key: str, info: dict) -> list:
        """Alert kalau token price berubah drastis."""
        alerts  = []
        chg     = info.get("change_24h", 0)
        if chg <= -TVL_DROP_ALERT:
            alerts.append({
                "type"    : "PRICE_DROP",
                "bridge"  : info["name"],
                "color"   : info["color"],
                "token"   : info["token"],
                "change"  : chg,
                "severity": "HIGH 🔴" if chg <= -20 else "MEDIUM 🟡",
            })
        elif chg >= TVL_PUMP_ALERT:
            alerts.append({
                "type"    : "PRICE_PUMP",
                "bridge"  : info["name"],
                "color"   : info["color"],
                "token"   : info["token"],
                "change"  : chg,
                "severity": "HIGH 🟢" if chg >= 50 else "MEDIUM 🟡",
            })
        return alerts

    def get_bridge_route(self, from_chain: str, to_chain: str) -> list:
        from_id = CHAIN_IDS.get(from_chain, 0)
        to_id   = CHAIN_IDS.get(to_chain, 0)
        if not from_id or not to_id:
            return []
        connections = self.lifi.get_connections(from_id, to_id)
        result      = []
        for c in connections[:5]:
            tools = c.get("bridges", []) or c.get("tools", [])
            if tools:
                result.append({
                    "from_chain": from_chain,
                    "to_chain"  : to_chain,
                    "bridges"   : tools[:4],
                })
        return result

    def get_price_trend(self, key: str) -> dict:
        history = self.price_history.get(key, [])
        if len(history) < 2:
            return {"trend": "N/A", "direction": "➡️", "change_pct": 0.0}
        first  = history[0]["price"]
        last   = history[-1]["price"]
        change = round((last - first) / first * 100, 2) if first > 0 else 0.0
        return {
            "trend"     : "RISING" if change > 1 else "FALLING" if change < -1 else "STABLE",
            "direction" : "📈" if change > 1 else "📉" if change < -1 else "➡️",
            "change_pct": change,
        }


# ─────────────────────────────────────────────
# 4. TELEGRAM BOT
# ─────────────────────────────────────────────
class BridgeBot:
    def __init__(self):
        self.token      = TELEGRAM_TOKEN
        self.chat_id    = TELEGRAM_CHAT_ID
        self.base       = f"https://api.telegram.org/bot{self.token}"
        self.monitor    = BridgeMonitor()
        self.offset     = 0
        self.running    = True
        self.monitoring = False
        log.info("🤖 BridgeBot initialized")

    def send(self, chat_id: str, text: str):
        for attempt in range(3):
            try:
                requests.post(
                    f"{self.base}/sendMessage",
                    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                    timeout=15
                )
                return
            except Exception as e:
                log.error(f"Send error (attempt {attempt+1}): {e}")
                time.sleep(2)

    def get_updates(self) -> list:
        try:
            r = requests.get(
                f"{self.base}/getUpdates",
                params={"offset": self.offset, "timeout": 10},
                timeout=15
            )
            return r.json().get("result", [])
        except Exception:
            return []

    # ─────────────────────────────────────────
    # Formatters
    # ─────────────────────────────────────────
    @staticmethod
    def _fmt(v: float, prefix: str = "$") -> str:
        if v <= 0:      return "N/A"
        if v >= 1e9:    return f"{prefix}{v/1e9:.2f}B"
        if v >= 1e6:    return f"{prefix}{v/1e6:.1f}M"
        if v >= 1e3:    return f"{prefix}{v/1e3:.1f}K"
        return f"{prefix}{v:,.2f}"

    def _format_bridge_info(self, info: dict) -> str:
        chains    = info.get("chains", [])
        chain_str = " • ".join(chains[:6]) if chains else "Multi-chain"
        price     = info.get("price_usd", 0)
        price_str = f"${price:.4f}" if price < 1 else f"${price:.2f}" if price < 1000 else f"${price:,.0f}"

        lifi_line = ""
        if info.get("lifi_supported"):
            lifi_line = f"\n🔁 LI.FI       : `Supported ✅`"

        return (
            f"{info['color']} *{info['name']}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📝 {info.get('description', '')}\n\n"
            f"💎 *Token: ${info['token']}*\n"
            f"💵 Price       : `{price_str}`\n"
            f"📊 Market Cap  : `{self._fmt(info.get('mcap_usd', 0))}`\n"
            f"📈 Vol 24h     : `{self._fmt(info.get('vol_24h_usd', 0))}`\n"
            f"{info['direction']} Change 24h  : `{info.get('change_24h', 0):+.2f}%`\n"
            f"📅 Change 7d   : `{info.get('change_7d', 0):+.2f}%`"
            f"{lifi_line}\n\n"
            f"🔗 *Supported Chains ({len(chains)}):*\n"
            f"`{chain_str}`\n\n"
            f"🌐 {info.get('website', '')}\n"
            f"⏰ `{info.get('timestamp','')[:19]}`"
        )

    def _format_price_alert(self, alert: dict) -> str:
        emoji = "📉" if alert["type"] == "PRICE_DROP" else "📈"
        title = "TOKEN DROP" if alert["type"] == "PRICE_DROP" else "TOKEN PUMP"
        return (
            f"{alert['color']} *BRIDGE {title} ALERT* {emoji}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌉 Bridge   : *{alert['bridge']}*\n"
            f"🪙 Token    : *${alert['token']}*\n"
            f"📊 Change   : `{alert['change']:+.2f}%`\n"
            f"⚡ Severity : {alert['severity']}\n"
            f"\n⏰ `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
        )

    # ─────────────────────────────────────────
    # Commands
    # ─────────────────────────────────────────
    def cmd_start(self, chat_id: str):
        self.send(chat_id, (
            "🌉 *Cross-Chain Bridge Monitor*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Monitor bridge tokens, routes & cross-chain activity!\n\n"
            "📋 *Commands:*\n"
            "/bridge_info `<bridge>` — Bridge stats & token\n"
            "/bridge_add `<bridge>` — Add to watchlist\n"
            "/bridge_remove `<bridge>` — Remove from watchlist\n"
            "/bridge_list — Show watched bridges\n"
            "/bridge_tvl — All bridges overview\n"
            "/bridge_route `<from>` `<to>` — Available routes\n"
            "/bridge_monitor on/off — Auto monitor token prices\n"
            "/bridge_bridges — List all bridges\n"
            "/bridge_chains — List supported chains\n\n"
            "*Available bridges:*\n"
            "`stargate` • `hop` • `across` • `celer`\n"
            "`synapse` • `wormhole` • `axelar` • `debridge`\n\n"
            "*Example:*\n"
            "`/bridge_info stargate`\n"
            "`/bridge_route Ethereum Arbitrum`"
        ))

    def cmd_bridge_info(self, chat_id: str, args: list):
        if not args:
            self.send(chat_id, "⚠️ Usage: `/bridge_info <bridge>`\n\nAvailable: `stargate` `hop` `across` `celer` `synapse` `wormhole` `axelar` `debridge`")
            return
        key = args[0].lower()
        if key not in BRIDGES:
            self.send(chat_id, f"❌ `{key}` not found.\nUse `/bridge_bridges` to see all.")
            return
        b = BRIDGES[key]
        self.send(chat_id, f"{b['color']} Fetching *{b['name']}* data...\n⏳ Please wait...")
        try:
            info = self.monitor.get_bridge_info(key)
            if not info:
                self.send(chat_id, f"❌ Could not fetch data for *{b['name']}*.")
                return
            self.send(chat_id, self._format_bridge_info(info))
        except Exception as e:
            self.send(chat_id, f"❌ Error: `{str(e)[:200]}`")

    def cmd_bridge_add(self, chat_id: str, args: list):
        if not args:
            self.send(chat_id, "⚠️ Usage: `/bridge_add <bridge>`")
            return
        key = args[0].lower()
        if self.monitor.add_bridge(key):
            b = BRIDGES[key]
            self.send(chat_id, (
                f"✅ *{b['color']} {b['name']}* added to watchlist!\n\n"
                f"🪙 Tracking token: *${b['token']}*\n"
                f"🔔 Alerts on price changes > {TVL_DROP_ALERT}%"
            ))
        else:
            self.send(chat_id, f"❌ `{key}` not found.\nUse `/bridge_bridges` to see all.")

    def cmd_bridge_remove(self, chat_id: str, args: list):
        if not args:
            self.send(chat_id, "⚠️ Usage: `/bridge_remove <bridge>`")
            return
        key = args[0].lower()
        if key in self.monitor.watchlist:
            self.monitor.remove_bridge(key)
            self.send(chat_id, f"✅ *{BRIDGES[key]['name']}* removed from watchlist.")
        else:
            self.send(chat_id, f"❌ `{key}` not in watchlist.")

    def cmd_bridge_list(self, chat_id: str):
        watched = self.monitor.get_watched_bridges()
        if not watched:
            self.send(chat_id, "📭 No bridges in watchlist.\nUse `/bridge_add <bridge>` to start.")
            return
        lines = [f"👀 *Watched Bridges ({len(watched)})*\n━━━━━━━━━━━━━━━━━━━━━━"]
        for key in watched:
            b     = BRIDGES[key]
            trend = self.monitor.get_price_trend(key)
            hist  = self.monitor.price_history.get(key, [])
            price = hist[-1]["price"] if hist else 0
            pstr  = f"${price:.4f}" if 0 < price < 1 else f"${price:.2f}" if price > 0 else "N/A"
            lines.append(
                f"{b['color']} *{b['name']}* (${b['token']})\n"
                f"   Price: `{pstr}` {trend['direction']} `{trend['change_pct']:+.2f}%`"
            )
        self.send(chat_id, "\n\n".join(lines))

    def cmd_bridge_tvl(self, chat_id: str):
        self.send(chat_id, "🔍 Fetching all bridges overview...\n⏳ Please wait ~10s...")
        try:
            bridges = self.monitor.get_all_bridges_overview()
            if not bridges:
                self.send(chat_id, "❌ Could not fetch data. Try again later.")
                return
            msg = "🏆 *BRIDGE TOKENS OVERVIEW*\n━━━━━━━━━━━━━━━━━━━━━━\n_(Sorted by Market Cap)_\n\n"
            for i, b in enumerate(bridges, 1):
                e    = "📈" if b["change"] > 0 else "📉" if b["change"] < 0 else "➡️"
                msg += (
                    f"{i}. {b['color']} *{b['name']}* (${b['token']})\n"
                    f"   MCap: `{b['mcap_str']}` | Vol: `{b['vol_str']}`\n"
                    f"   {e} `{b['change']:+.2f}%` | ⛓️ `{b['chains']} chains`\n\n"
                )
            msg += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            self.send(chat_id, msg)
        except Exception as e:
            self.send(chat_id, f"❌ Error: `{str(e)[:200]}`")

    def cmd_bridge_route(self, chat_id: str, args: list):
        if len(args) < 2:
            chains = " • ".join(CHAIN_IDS.keys())
            self.send(chat_id, f"⚠️ Usage: `/bridge_route <from> <to>`\n\nChains:\n`{chains}`")
            return
        from_c = args[0].capitalize()
        to_c   = args[1].capitalize()
        if from_c not in CHAIN_IDS:
            self.send(chat_id, f"❌ `{from_c}` not supported.\nUse `/bridge_chains`.")
            return
        if to_c not in CHAIN_IDS:
            self.send(chat_id, f"❌ `{to_c}` not supported.\nUse `/bridge_chains`.")
            return
        self.send(chat_id, f"🔍 Finding routes: *{from_c}* → *{to_c}*...\n⏳ Please wait...")
        try:
            routes    = self.monitor.get_bridge_route(from_c, to_c)
            supported = [b for b in BRIDGES.values() if from_c in b["chains"] and to_c in b["chains"]]
            msg = f"🌉 *Routes: {from_c} → {to_c}*\n━━━━━━━━━━━━━━━━━━━━━━\n"
            if supported:
                msg += f"\n✅ *Bridges that support this route ({len(supported)}):*"
                for b in supported:
                    msg += f"\n{b['color']} {b['name']} — `{b['website']}`"
            if routes:
                msg += f"\n\n🔗 *LI.FI Active Routes ({len(routes)}):*"
                for r in routes[:3]:
                    msg += f"\n• Via: `{' • '.join(r.get('bridges',[])[:4])}`"
            if not supported and not routes:
                msg += "\n\n❌ No direct routes found."
            msg += f"\n\n⏰ `{datetime.now().strftime('%Y-%m-%d %H:%M')}`"
            self.send(chat_id, msg)
        except Exception as e:
            self.send(chat_id, f"❌ Error: `{str(e)[:200]}`")

    def cmd_bridge_monitor(self, chat_id: str, args: list):
        if not args:
            status = "ON ✅" if self.monitoring else "OFF ❌"
            self.send(chat_id, (
                f"📡 Bridge Monitor: *{status}*\n"
                f"Use `/bridge_monitor on` or `/bridge_monitor off`\n\n"
                f"🔔 Monitors bridge token prices.\n"
                f"Alerts when 24h change > `±{TVL_DROP_ALERT}%`"
            ))
            return
        if args[0].lower() == "on":
            if not self.monitor.watchlist:
                self.send(chat_id, "⚠️ No bridges watched.\nUse `/bridge_add <bridge>` first.")
                return
            self.monitoring = True
            watched = ", ".join(f"`{k}`" for k in self.monitor.watchlist)
            self.send(chat_id, f"✅ *Bridge Monitor ON*\nTracking: {watched}\nChecks every {POLL_INTERVAL//60} min.")
        elif args[0].lower() == "off":
            self.monitoring = False
            self.send(chat_id, "❌ *Bridge Monitor OFF*")

    def cmd_bridge_bridges(self, chat_id: str):
        lines = [f"🌉 *Available Bridges ({len(BRIDGES)})*\n━━━━━━━━━━━━━━━━━━━━━━"]
        for key, b in BRIDGES.items():
            chains = " • ".join(b["chains"][:4])
            lines.append(
                f"{b['color']} *{b['name']}* (${b['token']})\n"
                f"  Key: `{key}`\n"
                f"  Chains: `{chains}`"
            )
        self.send(chat_id, "\n\n".join(lines))

    def cmd_bridge_chains(self, chat_id: str):
        lines = [f"⛓️ *Supported Chains ({len(CHAIN_IDS)})*\n━━━━━━━━━━━━━━━━━━━━━━"]
        for chain, cid in CHAIN_IDS.items():
            lines.append(f"• *{chain}* — ID: `{cid}`")
        self.send(chat_id, "\n".join(lines))

    # ─────────────────────────────────────────
    # Router
    # ─────────────────────────────────────────
    def handle(self, message: dict):
        text    = message.get("text", "").strip()
        chat_id = str(message.get("chat", {}).get("id", ""))
        if not text or not chat_id:
            return
        parts   = text.split()
        command = parts[0].lower()
        args    = parts[1:]
        log.info(f"📨 {command} from {chat_id}")

        if   command in ("/start", "/help"): self.cmd_start(chat_id)
        elif command == "/bridge_info":      self.cmd_bridge_info(chat_id, args)
        elif command == "/bridge_add":       self.cmd_bridge_add(chat_id, args)
        elif command == "/bridge_remove":    self.cmd_bridge_remove(chat_id, args)
        elif command == "/bridge_list":      self.cmd_bridge_list(chat_id)
        elif command == "/bridge_tvl":       self.cmd_bridge_tvl(chat_id)
        elif command == "/bridge_route":     self.cmd_bridge_route(chat_id, args)
        elif command == "/bridge_monitor":   self.cmd_bridge_monitor(chat_id, args)
        elif command == "/bridge_bridges":   self.cmd_bridge_bridges(chat_id)
        elif command == "/bridge_chains":    self.cmd_bridge_chains(chat_id)
        else:
            self.send(chat_id, "❓ Unknown command. Type /help for commands.")

    # ─────────────────────────────────────────
    # Background monitor
    # ─────────────────────────────────────────
    def _monitor_loop(self):
        log.info("🌉 Bridge monitor loop started")
        while self.running:
            if self.monitoring and self.monitor.watchlist:
                try:
                    for key in list(self.monitor.watchlist):
                        info   = self.monitor.get_bridge_info(key)
                        if not info:
                            continue
                        alerts = self.monitor.check_price_alerts(key, info)
                        for alert in alerts:
                            self.send(self.chat_id, self._format_price_alert(alert))
                            time.sleep(1)
                        time.sleep(1)   # rate limit CoinGecko
                    log.info(f"✅ Monitor scan — {len(self.monitor.watchlist)} bridges checked")
                except Exception as e:
                    log.error(f"Monitor error: {e}")
            time.sleep(POLL_INTERVAL)

    # ─────────────────────────────────────────
    # Main loop
    # ─────────────────────────────────────────
    def run(self):
        import threading
        log.info("🚀 BridgeBot started!")
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        while self.running:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    if msg:
                        self.handle(msg)
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                log.error(f"Polling error: {e}")
                time.sleep(5)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "check":
        key     = sys.argv[2] if len(sys.argv) > 2 else "stargate"
        monitor = BridgeMonitor()

        print(f"\n🌉 Checking: {BRIDGES.get(key, {}).get('name', key)}")
        print("─" * 50)

        # Test CoinGecko
        print("📡 Testing CoinGecko API...")
        cg_id = BRIDGES.get(key, {}).get("coingecko", "")
        token = monitor.coingecko.get_token_data(cg_id)
        if token:
            print(f"   ✅ Price     : ${token['price_usd']:.4f}")
            print(f"   ✅ Market Cap: ${token['mcap_usd']:,.0f}")
            print(f"   ✅ Vol 24h   : ${token['vol_24h']:,.0f}")
            print(f"   ✅ Change 24h: {token['change_24h']:+.2f}%")
        else:
            print("   ❌ CoinGecko failed")

        # Test LI.FI
        print("\n📡 Testing LI.FI API...")
        bridges = monitor.lifi.get_bridges()
        print(f"   ✅ {len(bridges)} bridges available in LI.FI")
        if bridges:
            names = [b.get("name","") for b in bridges[:8]]
            print(f"   Sample: {', '.join(names)}")

        # Test connections
        print("\n📡 Testing LI.FI connections (Ethereum → Arbitrum)...")
        conns = monitor.lifi.get_connections(1, 42161)
        print(f"   ✅ {len(conns)} connections found")
        for c in conns[:3]:
            tools = c.get("bridges",[]) or c.get("tools",[])
            print(f"   • {tools[:3]}")

        # Full info
        print(f"\n📊 Full bridge_info for '{key}':")
        info = monitor.get_bridge_info(key)
        for k, v in info.items():
            if k not in ("timestamp", "chains"):
                print(f"   {k:20}: {v}")

        # All overview
        print("\n🏆 All Bridges Overview (by Market Cap):")
        overview = monitor.get_all_bridges_overview()
        for i, b in enumerate(overview, 1):
            print(f"  {i:2}. {b['color']} {b['name']:20} MCap={b['mcap_str']:10} Vol={b['vol_str']:10} {b['change']:+.2f}%")
    else:
        bot = BridgeBot()
        bot.run()