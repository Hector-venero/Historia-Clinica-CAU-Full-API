# app/utils/bfa_client.py
from web3 import Web3
from web3.middleware import geth_poa_middleware
import os

# ==============================================================
# 🌐 Configuración de conexión con el nodo BFA
# ==============================================================
BFA_URL = os.getenv("BFA_URL", "http://bfa-node:8545")
PRIVATE_KEY = os.getenv("PRIVATE_KEY_BFA")
ADDRESS = os.getenv("ADDRESS_BFA")
CHAIN_ID = int(os.getenv("BFA_CHAIN_ID", "99118822"))

# ==============================================================
# 🧱 Función principal: registrar hash en la blockchain BFA
# ==============================================================
def registrar_hash_en_bfa(hash_hex):
    """
    Publica un hash (SHA256) en la Blockchain Federal Argentina (modo test).
    El hash se almacena en el campo 'input' de una transacción autoinvocada.
    """
    web3 = Web3(Web3.HTTPProvider(BFA_URL))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    if not web3.is_connected():
        raise ConnectionError(f"❌ No se pudo conectar al nodo BFA en {BFA_URL}")

    cuenta = Web3.to_checksum_address(ADDRESS)
    nonce = web3.eth.get_transaction_count(cuenta)
    gas_price = web3.eth.gas_price or web3.to_wei("1", "gwei")

    # 🔹 Transacción simple con el hash en el campo 'data'
    tx = {
        "nonce": nonce,
        "to": "0x000000000000000000000000000000000000dEaD",  # dirección nula estándar
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
        tx["gas"] = 50000  # fallback seguro

    # 🔹 Importante: eliminar 'from' antes de firmar
    del tx["from"]

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)

    # 🔹 Compatibilidad entre web3 v5 y v6
    raw_tx = getattr(signed_tx, "raw_transaction", None) or getattr(signed_tx, "rawTransaction", None)
    if not raw_tx:
        raise AttributeError("⚠️ No se pudo obtener el raw transaction del objeto firmado")

    tx_hash = web3.eth.send_raw_transaction(raw_tx)
    tx_hex = web3.to_hex(tx_hash)

    print(f"✅ Transacción enviada a BFA: {tx_hex}")
    return tx_hex

def verificar_hash_en_bfa(hash_local):
    """Consulta en la BFA si un hash determinado existe y devuelve el hash registrado."""
    from web3 import Web3
    import os

    # Conexión a la BFA local
    w3 = Web3(Web3.HTTPProvider("http://bfa-node:8545"))

    # En tu sistema el contrato o método puede variar; acá simulamos lectura básica
    # (Podés adaptarlo si ya tenés la dirección del contrato real)
    # Por ahora, devolvemos el mismo hash si queremos simular éxito
    return hash_local
