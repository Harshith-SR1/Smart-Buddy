import os
import tempfile

from smart_buddy.memory import MemoryBank


def test_memory_set_get_delete():
    fd, path = tempfile.mkstemp(prefix="sb_mem_", suffix=".db")
    os.close(fd)
    try:
        m = MemoryBank(db_path=path)
        m.set("ns1", "k1", {"a": 1})
        assert m.get("ns1", "k1") == {"a": 1}
        m.append_to_list("ns1", "lst", "x")
        m.append_to_list("ns1", "lst", "y")
        assert m.get("ns1", "lst") == ["x", "y"]
        assert "k1" in m.keys("ns1")
        assert m.delete("ns1", "k1") is True
        assert m.get("ns1", "k1") is None
    finally:
        try:
            m.close()
        except Exception:
            pass
        os.remove(path)
