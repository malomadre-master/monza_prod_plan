export type RangeMode = "day" | "week" | "month";

export function pad(value: number): string {
  return String(value).padStart(2, "0");
}

export function toISO(day: Date): string {
  return `${day.getFullYear()}-${pad(day.getMonth() + 1)}-${pad(day.getDate())}`;
}

export function parseISO(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function todayISO(): string {
  return toISO(new Date());
}

export function addDays(iso: string, count: number): string {
  const day = parseISO(iso);
  day.setDate(day.getDate() + count);
  return toISO(day);
}

export function weekdayIndex(iso: string): number {
  return parseISO(iso).getDay();
}

export function isWeekend(iso: string): boolean {
  const day = weekdayIndex(iso);
  return day === 0 || day === 6;
}

export function isWorkingDay(iso: string, holidays: Set<string>, extraWork: Set<string>): boolean {
  if (extraWork.has(iso)) return true;
  if (isWeekend(iso)) return false;
  if (holidays.has(iso)) return false;
  return true;
}

export function mondayOf(iso: string): string {
  const day = parseISO(iso);
  const weekday = day.getDay();
  const offset = weekday === 0 ? -6 : 1 - weekday;
  day.setDate(day.getDate() + offset);
  return toISO(day);
}

export function monthStart(iso: string): string {
  const day = parseISO(iso);
  day.setDate(1);
  return toISO(day);
}

export function monthEnd(iso: string): string {
  const day = parseISO(iso);
  day.setMonth(day.getMonth() + 1, 0);
  return toISO(day);
}

export function enumerate(fromIso: string, toIso: string): string[] {
  const days: string[] = [];
  let cursor = fromIso;
  while (cursor <= toIso) {
    days.push(cursor);
    cursor = addDays(cursor, 1);
  }
  return days;
}

export function workingDaysIn(fromIso: string, toIso: string, holidays: Set<string>, extraWork: Set<string>): string[] {
  return enumerate(fromIso, toIso).filter((day) => isWorkingDay(day, holidays, extraWork));
}

export function visibleDays(
  mode: RangeMode,
  anchor: string,
  holidays: Set<string>,
  extraWork: Set<string>,
): string[] {
  if (mode === "day") return [anchor];
  if (mode === "week") return enumerate(mondayOf(anchor), addDays(mondayOf(anchor), 6));
  return enumerate(monthStart(anchor), monthEnd(anchor)).filter(
    (day) => isWorkingDay(day, holidays, extraWork) || extraWork.has(day),
  );
}

export function formatDay(iso: string): string {
  const day = parseISO(iso);
  return `${pad(day.getDate())}.${pad(day.getMonth() + 1)}`;
}

export function formatLong(iso: string): string {
  return parseISO(iso).toLocaleDateString("ru-RU", { weekday: "short", day: "numeric", month: "long" });
}

const WEEKDAY = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"];

export function weekdayLabel(iso: string): string {
  return WEEKDAY[weekdayIndex(iso)];
}
