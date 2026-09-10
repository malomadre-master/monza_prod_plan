import type { ItemType, OrderStatus, Role } from "./api";

export const ROLE_LABEL: Record<Role, string> = {
  admin: "Администратор",
  planner: "Планировщик",
  designer: "Конструктор",
  supply: "Снабжение",
  worker: "Рабочий участка",
  observer: "Наблюдатель",
};

export const STATUS_LABEL: Record<OrderStatus, string> = {
  draft: "Черновик",
  queued: "В очереди конструкторов",
};

export const ITEM_FALLBACK: { value: ItemType; label: string; coeff: string }[] = [
  { value: "kitchen", label: "Кухня", coeff: "1.0" },
  { value: "wardrobe", label: "Шкаф", coeff: "0.8" },
  { value: "cabinet", label: "Тумба", coeff: "0.6" },
  { value: "hallway", label: "Прихожая", coeff: "0.8" },
  { value: "mirror", label: "Зеркало", coeff: "0.3" },
  { value: "appliance", label: "Техника", coeff: "0.3" },
  { value: "other", label: "Другое", coeff: "0.6" },
];

export function itemLabel(types: { value: string; label: string }[], value: string): string {
  return types.find((row) => row.value === value)?.label ?? value;
}

export function canEditOrders(role: Role): boolean {
  return role === "admin" || role === "planner";
}
