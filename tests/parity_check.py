"""
tests/parity_check.py — Verifica que el motor nuevo (backend.core) produce
EXACTAMENTE los mismos resultados que la lógica original de Streamlit (app.py).

Para importar `app.py` sin un runtime de Streamlit, se inyecta un stub mínimo
del módulo `streamlit` en sys.modules antes de importarlo. El stub solo registra
los mensajes; no altera ningún cálculo.

Uso:
    python tests/parity_check.py
"""

import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ----------------------------------------------------------------------
# Stub de streamlit
# ----------------------------------------------------------------------
class _SessionState(dict):
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)

    def __setattr__(self, k, v):
        self[k] = v


def _make_streamlit_stub():
    st = types.ModuleType("streamlit")
    st.session_state = _SessionState()

    def noop(*a, **k):
        return None

    for name in [
        "set_page_config", "markdown", "error", "warning", "info", "success",
        "write", "subheader", "header", "caption", "metric", "dataframe",
        "balloons", "divider", "rerun", "spinner",
    ]:
        setattr(st, name, noop)
    return st


sys.modules["streamlit"] = _make_streamlit_stub()

# Importar DESPUÉS de inyectar el stub
import app as legacy            # noqa: E402
from backend.core import MusicianPaymentSystem as NewSystem  # noqa: E402


DATA = str(ROOT / "Data" / "Actes.xlsx")


def load_legacy():
    sys.modules["streamlit"].session_state = _SessionState()
    s = legacy.MusicianPaymentSystem()
    s.load_from_uploaded_file(DATA)
    # La versión legacy inicializa editing_weights de forma perezosa en la UI;
    # se replica aquí igual que en show_weights_editor.
    ss = sys.modules["streamlit"].session_state
    ew = s.configuracion_df.copy()
    for col in ["A", "B", "C", "D", "E"]:
        ew[col] = ew[col].astype(float)
    ss.editing_weights = ew
    return s


def load_new():
    s = NewSystem()
    s.load_from_uploaded_file(DATA)
    return s


def assert_frame(name, a, b):
    a = a.reset_index(drop=True)
    b = b.reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b, check_dtype=False, rtol=1e-9, atol=1e-9)
    print(f"  ✓ {name} idéntico ({a.shape[0]} filas)")


def main():
    print("Cargando datos en ambos motores…")
    L = load_legacy()
    N = load_new()

    failures = 0

    # 1) calculate_budget_difference
    lb = L.calculate_budget_difference()
    nb = N.calculate_budget_difference()
    for i, label in enumerate(["total_budget", "total_distributed", "difference"]):
        if abs(lb[i] - nb[i]) < 1e-6:
            print(f"  ✓ budget_difference.{label}: {nb[i]:.6f}")
        else:
            print(f"  ✗ budget_difference.{label}: legacy={lb[i]} new={nb[i]}")
            failures += 1

    # 2) process_payments con cada criterio
    for crit, kwargs in [
        ("manual", {}),
        ("fixed", {"fixed_penalty_amount": 50}),
        ("average", {}),
    ]:
        print(f"process_payments(criterio={crit})")
        lr = L.process_payments(crit, kwargs.get("fixed_penalty_amount", 0))
        nr = N.process_payments(crit, kwargs.get("fixed_penalty_amount", 0))
        try:
            assert_frame(f"musician_summary[{crit}]", lr["musician_summary"], nr["musician_summary"])
            assert_frame(f"budget_comparison[{crit}]", lr["budget_comparison"], nr["budget_comparison"])
            assert_frame(f"musicians_by_category[{crit}]", lr["musicians_by_category"], nr["musicians_by_category"])
            assert_frame(f"payment_pivot[{crit}]", lr["payment_pivot"], nr["payment_pivot"])
            assert abs(lr["total_band_retention"] - nr["total_band_retention"]) < 1e-9
        except AssertionError as e:
            print(f"  ✗ DIFERENCIA en {crit}: {e}")
            failures += 1

    print()
    if failures == 0:
        print("✅ PARIDAD TOTAL: el motor nuevo es idéntico a la lógica original.")
    else:
        print(f"❌ {failures} discrepancia(s) detectada(s).")
        sys.exit(1)


if __name__ == "__main__":
    main()
