# app/utils/bfa_client.py
from web3 import Web3
from web3.middleware import geth_poa_middleware
import os, time

# ==============================================================
# 🌐 Configuración de conexión con el nodo BFA
# ==============================================================
BFA_URL = os.getenv("BFA_URL", "http://bfa-node:8545")
ADDRESS = os.getenv("ADDRESS_BFA")
CHAIN_ID = int(os.getenv("BFA_CHAIN_ID", "1337"))

# ==============================================================
# 🧱 Función principal: registrar hash en la blockchain BFA
# ==============================================================
def registrar_hash_en_bfa(hash_hex):
    """
    Publica un hash (SHA256) en la Blockchain Federal Argentina (modo test).
    El hash se almacena en el campo 'input' de una transacción autoinvocada.
    Reintenta automáticamente si hay error 'underpriced' o 'already known'.
    """
    web3 = Web3(Web3.HTTPProvider(BFA_URL))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    if not web3.is_connected():
        raise ConnectionError(f"❌ No se pudo conectar al nodo BFA en {BFA_URL}")

    cuenta = Web3.to_checksum_address(ADDRESS)
    nonce = web3.eth.get_transaction_count(cuenta)
    base_gas_price = web3.eth.gas_price or web3.to_wei("1", "gwei")

    # Intentamos hasta 3 veces
    for intento in range(3):
        gas_price = base_gas_price + web3.to_wei(intento, "gwei")

        tx = {
            "nonce": nonce,
            "to": "0x000000000000000000000000000000000000dEaD",
            "value": 0,
            "data": web3.to_bytes(hexstr=hash_hex),
            "gasPrice": gas_price,
            "chainId": CHAIN_ID,
            "from": cuenta
        }

        try:
            estimated_gas = web3.eth.estimate_gas(tx)
            tx["gas"] = max(estimated_gas, 21000)
        except Exception:
            tx["gas"] = 50000

        try:
            # ✅ Enviar directamente al nodo (sin firmar manualmente)
            tx_hash = web3.eth.send_transaction(tx)
            tx_hex = web3.to_hex(tx_hash)
            print(f"✅ Transacción enviada a BFA: {tx_hex} (gasPrice={gas_price})")
            return tx_hex

        except Exception as e:
            msg = str(e)
            if "already known" in msg:
                print("⚠️ El hash ya se encuentra registrado en la Blockchain BFA.")
                return "already_known"
            elif "underpriced" in msg or "replacement transaction underpriced" in msg:
                print(f"⚠️ Transacción rechazada por underpriced, reintentando con mayor gas... intento {intento+1}")
                time.sleep(1)
                continue
            else:
                print(f"❌ Error al enviar transacción: {msg}")
                raise

    # Si fallan los 3 intentos:
    raise RuntimeError("❌ No se pudo enviar la transacción tras 3 intentos consecutivos (underpriced).")


# ==============================================================
# 🧩 Verificación simulada del hash
# ==============================================================
def verificar_hash_en_bfa(hash_local):
    """Simula la verificación del hash en la BFA (modo test)."""
    w3 = Web3(Web3.HTTPProvider(BFA_URL))
    if not w3.is_connected():
        raise ConnectionError(f"❌ No se pudo conectar al nodo BFA en {BFA_URL}")
    return hash_local
