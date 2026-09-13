import type { PlanSlot, WorkCenterRow } from "../api";
import { CENTER_LABEL } from "../labels";
import { isWorkingDay, todayISO } from "./dates";

export const ROUTE_ORDER = [
  "construction",
  "complectation",
  "saw",
  "edgebanding",
  "drilling",
  "milling",
  "assembly",
  "qc",
];

const ORDER_COLORS = ["blue", "teal", "violet", "orange", "grape", "cyan", "indigo", "pink"] as const;

export type OrderColor = (typeof ORDER_COLORS)[number];

export function orderColor(orderId: number): OrderColor {
  return ORDER_COLORS[Math.abs(orderId) % ORDER_COLORS.length];
}

export function dailyCapacity(center: WorkCenterRow): number {
  const days = Number(center.capacity_days);
  if (!days) return 0;
  return Number(center.capacity_qty) / days;
}

export function unitLabel(unit: string): string {
  if (unit === "item") return "изд.";
  if (unit === "order") return "зак.";
  if (unit === "m2") return "м²";
  if (unit === "linear_m") return "м.п.";
  return unit;
}

export function slotOverlaps(slot: PlanSlot, iso: string): boolean {
  return slot.start <= iso && iso <= slot.finish;
}

export function workingSpan(
  slot: PlanSlot,
  holidays: Set<string>,
  extraWork: Set<string>,
): string[] {
  const days: string[] = [];
  let cursor = slot.start;
  while (cursor <= slot.finish) {
    if (isWorkingDay(cursor, holidays, extraWork)) days.push(cursor);
    const [year, month, day] = cursor.split("-").map(Number);
    const next = new Date(year, month - 1, day + 1);
    cursor = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}-${String(next.getDate()).padStart(2, "0")}`;
  }
  return days.length ? days : [slot.start];
}

export function loadByCell(
  slots: PlanSlot[],
  centers: WorkCenterRow[],
  days: string[],
  holidays: Set<string>,
  extraWork: Set<string>,
): Map<string, number> {
  const used = new Map<string, number>();
  for (const slot of slots) {
    const span = workingSpan(slot, holidays, extraWork);
    const share = Number(slot.volume) / span.length;
    for (const day of span) {
      if (!days.includes(day)) continue;
      const key = `${slot.center_code}:${day}`;
      used.set(key, (used.get(key) ?? 0) + share);
    }
  }
  const pct = new Map<string, number>();
  for (const center of centers) {
    const cap = dailyCapacity(center);
    for (const day of days) {
      const raw = used.get(`${center.code}:${day}`) ?? 0;
      pct.set(`${center.code}:${day}`, cap > 0 ? Math.round((raw / cap) * 100) : 0);
    }
  }
  return pct;
}

export function whyDate(slot: PlanSlot, all: PlanSlot[]): string {
  const same = all.filter((row) => row.item_id === slot.item_id);
  const index = ROUTE_ORDER.indexOf(slot.center_code);
  for (let prev = index - 1; prev >= 0; prev -= 1) {
    const found = same.find((row) => row.center_code === ROUTE_ORDER[prev]);
    if (found) {
      const title = CENTER_LABEL[found.center_code] ?? found.center_code;
      return `После «${title}» (готовность ${found.finish})`;
    }
  }
  if (slot.center_code === "construction") {
    return `Дата запуска заказа ${slot.launch_date}`;
  }
  return `Дата запуска ${slot.launch_date}`;
}

export function itemChain(slot: PlanSlot, all: PlanSlot[]): PlanSlot[] {
  const same = all.filter((row) => row.item_id === slot.item_id);
  return [...same].sort(
    (a, b) => ROUTE_ORDER.indexOf(a.center_code) - ROUTE_ORDER.indexOf(b.center_code),
  );
}

export function isOverdue(slot: PlanSlot, today = todayISO()): boolean {
  return slot.finish < today;
}

export type LaneSlot = PlanSlot & { lane: number; lanes: number };

export function withLanes(slots: PlanSlot[]): LaneSlot[] {
  const grouped = new Map<string, PlanSlot[]>();
  for (const slot of slots) {
    const list = grouped.get(slot.center_code) ?? [];
    list.push(slot);
    grouped.set(slot.center_code, list);
  }
  const result: LaneSlot[] = [];
  for (const list of grouped.values()) {
    const sorted = [...list].sort((a, b) => a.start.localeCompare(b.start) || a.item_id - b.item_id);
    const laneEnd: string[] = [];
    const assigned: LaneSlot[] = [];
    for (const slot of sorted) {
      let lane = laneEnd.findIndex((end) => end < slot.start);
      if (lane < 0) {
        lane = laneEnd.length;
        laneEnd.push(slot.finish);
      } else {
        laneEnd[lane] = slot.finish;
      }
      assigned.push({ ...slot, lane, lanes: 1 });
    }
    const lanes = Math.max(1, laneEnd.length);
    for (const row of assigned) result.push({ ...row, lanes });
  }
  return result;
}

export function columnSpan(slot: PlanSlot, days: string[]): { start: number; end: number } | null {
  const first = days.findIndex((day) => day >= slot.start);
  const last = findLastIndex(days, (day) => day <= slot.finish);
  if (first < 0 || last < 0 || last < first) return null;
  if (slot.finish < days[0] || slot.start > days[days.length - 1]) return null;
  return { start: first, end: last };
}

function findLastIndex<T>(list: T[], pred: (item: T) => boolean): number {
  for (let i = list.length - 1; i >= 0; i -= 1) {
    if (pred(list[i])) return i;
  }
  return -1;
}
