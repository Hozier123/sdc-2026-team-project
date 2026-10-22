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


def test_email_with_numeric_local_part_is_masked_as_email_first():
    raw = "Email 900101145678@example.com, not an IC"
    result = mask_message(raw)
    assert result.masked_text == "Email [REDACTED_EMAIL], not an IC"
    assert [token.kind for token in result.tokens] == ["EMAIL"]


def test_international_phone_with_spaces_is_masked():
    raw = "Call +60 12-345 6789 now"
    result = mask_message(raw)
    assert "12-345 6789" not in result.masked_text
    assert "[REDACTED_PHONE]" in result.masked_text


def test_mask_is_deterministic_and_keeps_original_message_untouched():
    raw = "Hubungi 0123456789"
    first = mask_message(raw)
    second = mask_message(raw)
    assert first.masked_text == second.masked_text
    assert raw == "Hubungi 0123456789"


def test_masked_positions_map_back_to_original_code_points():
    raw = "Hi 0123456789, email ali@example.com!"
    result = mask_message(raw)
    assert result.original_index(0) == 0
    assert result.original_index(len(result.masked_text)) == len(raw)

    phone = next(token for token in result.tokens if token.kind == "PHONE")
    mask_start = result.masked_text.index(phone.token)
    assert result.original_index(mask_start) == phone.start

    after_phone = mask_start + len(phone.token)
    assert result.original_index(after_phone) == phone.end
