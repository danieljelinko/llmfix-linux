import llmfix_linux as m

MON_A = {"left": 0, "top": 0, "width": 100, "height": 100}
MON_B = {"left": 100, "top": 0, "width": 100, "height": 100}


def test_pick_monitor_returns_monitor_containing_the_point():
    # Given two side-by-side monitors and a point inside the right one
    monitors = [MON_A, MON_B]

    # When we pick for a point at x=150
    picked = m.pick_monitor_for_pos(monitors, (150, 50))

    # Then the right monitor is chosen
    assert picked is MON_B


def test_pick_monitor_returns_first_when_point_outside_all():
    # Given two monitors and a point beyond both
    monitors = [MON_A, MON_B]

    # When we pick for a far-off point
    picked = m.pick_monitor_for_pos(monitors, (9999, 9999))

    # Then it falls back to the first monitor
    assert picked is MON_A


def test_pick_monitor_returns_first_when_coordinates_are_none():
    # Given monitors but an unknown mouse position
    monitors = [MON_A, MON_B]

    # When we pick with None coordinates
    picked = m.pick_monitor_for_pos(monitors, (None, None))

    # Then it falls back to the first monitor
    assert picked is MON_A


def test_pick_monitor_returns_none_when_no_monitors():
    # Given no monitors at all
    monitors: list[dict] = []

    # When we pick for any point
    picked = m.pick_monitor_for_pos(monitors, (10, 10))

    # Then there is nothing to pick
    assert picked is None


def test_get_mouse_pos_returns_int_coords_from_controller(monkeypatch):
    # Given a mouse controller reporting a float position
    monkeypatch.setattr(m.mouse, "position", (12.7, 34.2))

    # When we read the mouse position
    x, y = m.get_mouse_pos()

    # Then integer coordinates are returned
    assert (x, y) == (12, 34)


def test_get_mouse_pos_returns_none_when_controller_raises(monkeypatch):
    # Given a mouse controller whose position access raises
    class Boom:
        @property
        def position(self): raise RuntimeError("no display")
    monkeypatch.setattr(m, "mouse", Boom())

    # When we read the mouse position
    result = m.get_mouse_pos()

    # Then it degrades to unknown coordinates
    assert result == (None, None)


def test_capture_screen_grabs_picked_monitor_and_returns_image(monkeypatch):
    # Given a fake mss that reports two monitors and a 2x2 grab
    class FakeShot:
        size = (2, 2)
        rgb = b"\x00" * 12
    class FakeSct:
        monitors = [MON_A, MON_A, MON_B]  # index 0 is the "all monitors" entry
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def grab(self, mon): return FakeShot()
    monkeypatch.setattr(m, "mss", lambda: FakeSct())

    # When we capture the screen
    img = m.capture_screen()

    # Then a PIL image of the grabbed size is returned
    assert img.size == (2, 2)
    assert img.mode == "RGB"
