from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class CenterSpec:
    code: str
    unit: str
    capacity_qty: Decimal
    capacity_days: Decimal
    is_gate: bool = False


@dataclass(frozen=True)
class ConstructorSpec:
    id: int
    efficiency: Decimal = Decimal("1.00")


@dataclass(frozen=True)
class Job:
    order_id: int
    item_id: int
    order_priority: int
    item_priority: int
    launch_date: date
    contract_date: date
    qty: int
    area_m2: Decimal
    linear_m: Decimal
    procurement_needed: bool = True
    construction_done: date | None = None
    materials_confirmed: date | None = None


@dataclass(frozen=True)
class Slot:
    order_id: int
    item_id: int
    center_code: str
    volume: Decimal
    start: date
    finish: date


SHOP_ROUTE = ("saw", "edgebanding", "drilling", "milling", "assembly", "qc")

DEFAULT_CENTERS = (
    CenterSpec("construction", "item", Decimal("1"), Decimal("2")),
    CenterSpec("complectation", "order", Decimal("4"), Decimal("1"), is_gate=True),
    CenterSpec("saw", "m2", Decimal("100"), Decimal("1")),
    CenterSpec("edgebanding", "linear_m", Decimal("500"), Decimal("1")),
    CenterSpec("drilling", "m2", Decimal("140"), Decimal("1")),
    CenterSpec("milling", "m2", Decimal("30"), Decimal("1")),
    CenterSpec("assembly", "m2", Decimal("80"), Decimal("1")),
    CenterSpec("qc", "m2", Decimal("80"), Decimal("1")),
)
