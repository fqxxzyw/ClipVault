import pytest

from clipvault.core.hotkeys import HotkeyError, HotkeyManager, parse_hotkey


@pytest.mark.parametrize(
    "value", ["V", "Shift+A", "Ctrl+Ctrl+V", "Ctrl+F12", "Ctrl+未知", "Ctrl++V"]
)
def test_invalid_hotkeys(value):
    with pytest.raises(ValueError):
        parse_hotkey(value)


def test_hotkey_canonical_form():
    binding = parse_hotkey("shift + ctrl + v")
    assert binding.display == "Ctrl+Shift+V"
    assert binding.modifiers == 6 and binding.key == ord("V")
    assert parse_hotkey("Ctrl+Alt+F11").key == 0x7A


class FakeHotkeyAPI:
    def __init__(self):
        self.entries = {}
        self.fail = False

    def register(self, identifier, hotkey):
        if self.fail:
            return False
        self.entries[identifier] = hotkey
        return True

    def unregister(self, identifier):
        self.entries.pop(identifier, None)


def test_live_rebinding_conflict_and_release(qapp):
    api = FakeHotkeyAPI()
    manager = HotkeyManager(qapp, api=api)
    manager.register("Ctrl+Shift+V")
    first_id = manager.identifier
    api.fail = True
    with pytest.raises(HotkeyError):
        manager.register("Ctrl+Alt+V")
    assert manager.identifier == first_id and len(api.entries) == 1
    api.fail = False
    manager.register("Ctrl+Alt+V")
    assert manager.identifier != first_id
    assert first_id not in api.entries and len(api.entries) == 1
    manager.close()
    assert not api.entries
