# crypto_ops.py
# Termux-friendly version using PyCryptodome.
#
# Install on Termux:
#   pkg update
#   pkg install python
#   pip install pycryptodome
#
# Cipher format is kept compatible with the original implementation:
# Base64(nonce[12] + tag[16] + ciphertext)

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
import base64 as b64
import os as osy

from config import MASTER_KEY as M1, IV_KEY as I1


def dyk(pwd=M1, slt=I1, l=16):
    """
    Derive the AES key using PBKDF2-HMAC-SHA256.

    Parameters intentionally match the original:
      - SHA256
      - 100000 iterations
      - 16-byte key
    """
    pw = pwd.encode()
    sl = slt.encode()

    return PBKDF2(
        password=pw,
        salt=sl,
        dkLen=l,
        count=100000,
        hmac_hash_module=SHA256,
    )


def ecs(s):
    """
    Encrypt string using AES-GCM.

    Output:
        Base64(nonce + authentication_tag + ciphertext)
    """
    k = dyk()

    # AES-GCM standard nonce used by the original implementation.
    n = osy.urandom(12)

    cipher = AES.new(k, AES.MODE_GCM, nonce=n)

    p = s.encode()
    ct, tg = cipher.encrypt_and_digest(p)

    encd = b64.b64encode(n + tg + ct).decode()
    return encd


def dcs(ed):
    """
    Decrypt string produced by ecs().
    """
    k = dyk()

    dat = b64.b64decode(ed.encode())

    # Original layout:
    # 12 bytes nonce
    # 16 bytes GCM authentication tag
    # remaining bytes ciphertext
    n = dat[:12]
    tg = dat[12:28]
    ct = dat[28:]

    cipher = AES.new(k, AES.MODE_GCM, nonce=n)

    res = cipher.decrypt_and_verify(ct, tg)
    return res.decode()
