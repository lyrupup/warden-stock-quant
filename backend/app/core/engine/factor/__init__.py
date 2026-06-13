"""因子引擎包。"""

from app.core.engine.factor.analysis import run_factor_analysis
from app.core.engine.factor.compute import (
    BUILTIN_FACTORS,
    compute_factor_matrix,
    list_builtin_factors,
    resolve_builtin_window,
    values_for_date,
)

__all__ = [
    "BUILTIN_FACTORS",
    "compute_factor_matrix",
    "list_builtin_factors",
    "resolve_builtin_window",
    "run_factor_analysis",
    "values_for_date",
]
