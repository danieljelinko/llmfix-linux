import base64

import llmfix_linux as m

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def test_resize_img_returns_same_image_when_under_budget(make_img):
    # Given an image well under the pixel budget
    img = make_img(100, 100)

    # When we resize with a large budget
    result = m.resize_img(img, max_px=1_000_000)

    # Then the same image object is returned untouched
    assert result is img


def test_resize_img_shrinks_within_budget_and_keeps_aspect_when_over(make_img):
    # Given a wide image whose pixel count exceeds the budget
    img = make_img(2000, 1000)

    # When we resize to a small budget
    result = m.resize_img(img, max_px=100_000)

    # Then the result fits the budget and preserves the 2:1 aspect ratio
    w, h = result.size
    assert w * h <= 100_000
    assert round(w / h) == 2


def test_img_b64_encodes_a_decodable_png(make_img):
    # Given a small image
    img = make_img(4, 4)

    # When we base64-encode it
    enc = m.img_b64(img)

    # Then the decoded bytes are a PNG
    assert base64.b64decode(enc).startswith(PNG_SIGNATURE)


def test_create_icon_image_returns_rgba_of_requested_size():
    # Given a requested icon size
    size = 48

    # When we create the tray icon image
    icon = m.create_icon_image(size)

    # Then it is an RGBA image of that size
    assert icon.mode == "RGBA"
    assert icon.size == (size, size)
