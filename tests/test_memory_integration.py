import os
import tempfile

from smart_buddy.memory import MemoryBank


def test_memory_persistence_and_operations():
    fd, path = tempfile.mkstemp(prefix="sb_mem_", suffix=".db")
    os.close(fd)
    try:
        # create a memory bank and set some keys
        m = MemoryBank(db_path=path)
        m.set("ns1", "k1", {"v": 1})
        assert m.get("ns1", "k1")["v"] == 1

        # append to list
        m.append_to_list("ns1", "alist", "a")
        m.append_to_list("ns1", "alist", "b")
        assert m.get("ns1", "alist") == ["a", "b"]

        # delete key
        assert m.delete("ns1", "k1") is True
        assert m.get("ns1", "k1") is None

        # close and reopen to test persistence
        m.close()
        m2 = MemoryBank(db_path=path)
        assert m2.get("ns1", "alist") == ["a", "b"]
        m2.close()
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
