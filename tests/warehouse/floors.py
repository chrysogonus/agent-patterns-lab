"""Hand-built warehouse floors for the tests (specs/012 T005)."""

from apl.warehouse.model import Floor
from apl.warehouse.plans import with_reference


def p2_floor() -> Floor:
    """9 columns, 3 aisles (rows 1, 3, 5); dock A2, D I2; packages 1 at B5, 2 at E1, 3 at G5.

    Aisle 1 holds one package, aisle 2 none, aisle 3 two: the mock-up's uneven spread.
    """
    packages = (("package 1", (1, 4)), ("package 2", (4, 0)), ("package 3", (6, 4)))
    return with_reference(Floor(None, None, 9, 3, packages))
