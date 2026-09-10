from decimal import Decimal

ITEM_TYPES: list[dict[str, str | Decimal]] = [
    {"value": "kitchen", "label": "Кухня", "coeff": Decimal("1.0")},
    {"value": "wardrobe", "label": "Шкаф", "coeff": Decimal("0.8")},
    {"value": "cabinet", "label": "Тумба", "coeff": Decimal("0.6")},
    {"value": "hallway", "label": "Прихожая", "coeff": Decimal("0.8")},
    {"value": "mirror", "label": "Зеркало", "coeff": Decimal("0.3")},
    {"value": "appliance", "label": "Техника", "coeff": Decimal("0.3")},
    {"value": "other", "label": "Другое", "coeff": Decimal("0.6")},
]

ITEM_TYPE_VALUES = tuple(str(row["value"]) for row in ITEM_TYPES)

ROLE_LABELS = {
    "admin": "Администратор",
    "planner": "Планировщик",
    "designer": "Конструктор",
    "supply": "Снабжение",
    "worker": "Рабочий участка",
    "observer": "Наблюдатель",
}

ORDER_CREATE_ROLES = ("admin", "planner")
LINEAR_PER_M2 = Decimal("10")
