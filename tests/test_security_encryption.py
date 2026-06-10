from __future__ import annotations

import pytest
from cryptography.fernet import InvalidToken
from app.security import encrypt_json, decrypt_json, encrypt_json_legacy

def test_encrypt_decrypt_fernet():
    secret = "my-secure-test-secret-key"
    data = {"token": "my-secret-token", "email": "test@example.com"}
    
    ciphertext = encrypt_json(data, secret=secret)
    assert ciphertext is not None
    assert "token" not in ciphertext
    
    decrypted = decrypt_json(ciphertext, secret=secret)
    assert decrypted == data

def test_decrypt_fails_with_incorrect_key():
    secret = "my-secure-test-secret-key"
    wrong_secret = "the-wrong-secret-key"
    data = {"token": "my-secret-token"}
    
    ciphertext = encrypt_json(data, secret=secret)
    
    with pytest.raises(ValueError, match="Invalid encrypted payload or incorrect key"):
        decrypt_json(ciphertext, secret=wrong_secret)

def test_legacy_xor_fallback():
    secret = "legacy-test-secret-key"
    data = {"api_key": "old-xor-key"}
    
    # Encrypt using the old XOR method
    legacy_ciphertext = encrypt_json_legacy(data, secret=secret)
    
    # Decrypt using the new method, which should fall back to XOR automatically
    decrypted = decrypt_json(legacy_ciphertext, secret=secret)
    assert decrypted == data

def test_legacy_xor_fails_with_incorrect_key():
    secret = "legacy-test-secret-key"
    wrong_secret = "wrong-secret-key"
    data = {"api_key": "old-xor-key"}
    
    legacy_ciphertext = encrypt_json_legacy(data, secret=secret)
    
    with pytest.raises(ValueError):
        decrypt_json(legacy_ciphertext, secret=wrong_secret)
