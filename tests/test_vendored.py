"""t2av_eval/data/build_items.py is a vendored copy of T2AV_data/real_av_pilot/build_items.py: verbatim apart from the header,
the paths import and the ANN line. Checked against the md5 recorded in its header (the origin file itself is not read, so the
test also runs without T2AV_data)."""
import hashlib, re
from pathlib import Path

F = Path(__file__).resolve().parents[1] / "t2av_eval/data/build_items.py"


def test_build_items_is_verbatim():
    s = F.read_text()
    md5 = re.search(r"^# VENDORED from \S+ \(md5 ([0-9a-f]{32})", s, re.M).group(1)
    first, rest = s.split("\n", 1)
    rest = re.sub(r"\A(# .*\n)+", "", rest)
    rest = rest.replace("from t2av_eval import paths as _P\n", "", 1)
    rest = re.sub(r'(?m)^ANN = _P\.DATA / "real_av_pilot" / "annotations" .*\n', 'ANN = Path(__file__).resolve().parent / "annotations"\n', rest)
    assert hashlib.md5((first + "\n" + rest).encode()).hexdigest() == md5
