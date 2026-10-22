from app.pii import mask_message


def test_phone_mykad_and_email_are_replaced_with_exact_tokens():
    raw = "Call 012-3456789, IC 900101-14-5678, email ali@example.com"
    result = mask_message(raw)
    assert "012-3456789" not in result.masked_text
    assert "900101-14-5678" not in result.masked_text
    assert "ali@example.com" not in result.masked_text
    assert "[REDACTED_PHONE]" in result.masked_text
    assert "[REDACTED_MYKAD]" in result.masked_text
    assert "[REDACTED_EMAIL]" in result.masked_text
    assert {token.kind for token in result.tokens} == {"PHONE", "MYKAD", "EMAIL"}


def test_ordinary_order_numbers_are_not_pii():
    raw = "Tepung 5 ctn, stock code A95, RM95"
    result = mask_message(raw)
    assert result.masked_text == raw
    assert result.tokens == ()


def test_mask_is_deterministic_and_keeps_original_message_untouched():
    raw = "Hubungi 0123456789"
    first = mask_message(raw)
    second = mask_message(raw)
    assert first.masked_text == second.masked_text
    assert raw == "Hubungi 0123456789"
