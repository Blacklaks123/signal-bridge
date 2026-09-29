from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import httpx
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Signal Bridge", version="1.0")

META_TOKEN   = os.environ.get("META_TOKEN", "")
ACCOUNT_ID   = os.environ.get("META_ACCOUNT_ID", "")
META_URL     = f"https://mt-client-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts/{ACCOUNT_ID}/trade"

class Signal(BaseModel):
    action: str        # "buy" ou "sell"
    symbol: str        # ex: "WINM25"
    volume: float = 1.0
    sl: float = 0.0    # stop loss em pontos (0 = sem stop)
    tp: float = 0.0    # take profit em pontos (0 = sem take)
    comment: str = "SignalBridge"

@app.get("/")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.post("/webhook")
async def webhook(signal: Signal):
    logger.info(f"Sinal recebido: {signal}")

    if not META_TOKEN or not ACCOUNT_ID:
        raise HTTPException(status_code=500, detail="META_TOKEN ou META_ACCOUNT_ID não configurados")

    action = signal.action.lower()
    if action not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail=f"Ação inválida: {signal.action}")

    payload = {
        "actionType": "ORDER_TYPE_BUY" if action == "buy" else "ORDER_TYPE_SELL",
        "symbol":     signal.symbol,
        "volume":     signal.volume,
        "comment":    signal.comment,
    }
    if signal.sl > 0:
        payload["stopLoss"]   = signal.sl
    if signal.tp > 0:
        payload["takeProfit"] = signal.tp

    headers = {
        "auth-token":   META_TOKEN,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(META_URL, json=payload, headers=headers)

    logger.info(f"MetaApi response: {resp.status_code} — {resp.text}")

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"MetaApi erro: {resp.text}")

    return {"status": "executed", "signal": signal.dict(), "metaapi": resp.json()}
