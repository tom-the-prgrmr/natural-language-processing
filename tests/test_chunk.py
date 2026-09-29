"""Test tối thiểu cho ingest: đếm điều, không chunk rỗng/trùng, so tay vài chunk
đã biết đáp án đúng (đối chiếu bằng mắt với data/raw/ và ảnh trang ND238)."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(script: str) -> None:
    subprocess.run([PY, str(ROOT / script)], check=True, cwd=ROOT)


def load_chunks() -> list[dict]:
    run("src/ingest/clean.py")
    run("src/ingest/chunk.py")
    path = ROOT / "data/processed/chunks.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_no_empty_or_duplicate_ids():
    chunks = load_chunks()
    assert all(c["text"].strip() for c in chunks)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_dieu_counts_match_source():
    chunks = load_chunks()
    for law, expected_max in [("L36", 89), ("168", 55)]:
        dieu_nums = {c["dieu"] for c in chunks if c["law"] == law}
        assert dieu_nums == set(range(1, expected_max + 1)), (law, sorted(dieu_nums))


def test_known_fine_mu_bao_hiem():
    """ND168 Điều 7 khoản 2 điểm h: không đội mũ bảo hiểm, 400.000-600.000 đồng."""
    chunks = {c["id"]: c for c in load_chunks()}
    c = chunks["168_D7_K2_h"]
    assert "400.000" in c["text"] and "600.000" in c["text"]
    assert "mũ bảo hiểm" in c["text"]


def test_known_nd238_warning_child_seat():
    """ND238 sửa Điều 6 ND168: bổ sung khoản 1a, phạt cảnh cáo chở trẻ em không
    ghế an toàn (đã xem ảnh trang 4, xem data/raw/SOURCES.md)."""
    chunks = {c["id"]: c for c in load_chunks()}
    c = chunks["238_D2_1"]
    assert c["amends_dieu"] == 6
    assert "Phạt cảnh cáo" in c["text"] and "trẻ em" in c["text"]


def test_khoan_zero_is_rare():
    """Khoản '0' (Điều không mở đầu bằng số) chỉ là ngoại lệ, không phải đa số —
    nếu nhiều bất thường thì parser đang lỗi."""
    chunks = load_chunks()
    for law in ("L36", "168", "238"):
        law_chunks = [c for c in chunks if c["law"] == law]
        k0 = sum(1 for c in law_chunks if c["khoan"] == "0")
        assert k0 / len(law_chunks) < 0.2, (law, k0, len(law_chunks))
