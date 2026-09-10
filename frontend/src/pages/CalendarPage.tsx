import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Checkbox,
  Group,
  Paper,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { api, type AttendanceMonth, type CalendarDay, type CalendarDayKind } from "../api";
import { CENTER_LABEL, ROLE_LABEL } from "../labels";

const MONTHS = [
  "Январь",
  "Февраль",
  "Март",
  "Апрель",
  "Май",
  "Июнь",
  "Июль",
  "Август",
  "Сентябрь",
  "Октябрь",
  "Ноябрь",
  "Декабрь",
];
const WEEKDAY = ["вс", "пн", "вт", "ср", "чт", "пт", "сб"];

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function isoDate(year: number, month: number, day: number): string {
  return `${year}-${pad(month)}-${pad(day)}`;
}

function weekdayIndex(iso: string): number {
  return new Date(`${iso}T12:00:00`).getDay();
}

function isWeekend(iso: string): boolean {
  const day = weekdayIndex(iso);
  return day === 0 || day === 6;
}

export function CalendarPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [attendance, setAttendance] = useState<AttendanceMonth>({ staff: [], absences: [] });
  const [saving, setSaving] = useState(false);
  const [newDay, setNewDay] = useState(isoDate(today.getFullYear(), today.getMonth() + 1, today.getDate()));
  const [newKind, setNewKind] = useState<CalendarDayKind>("holiday");
  const [newTitle, setNewTitle] = useState("");

  const dateFrom = isoDate(year, month, 1);
  const dateTo = isoDate(year, month, new Date(year, month, 0).getDate());
  const monthDays = useMemo(() => {
    const last = new Date(year, month, 0).getDate();
    return Array.from({ length: last }, (_, index) => isoDate(year, month, index + 1));
  }, [year, month]);

  const dayMap = useMemo(() => new Map(days.map((row) => [row.day, row])), [days]);
  const absent = useMemo(() => {
    const set = new Set(attendance.absences.map((row) => `${row.user_id}:${row.day}`));
    return set;
  }, [attendance.absences]);

  function reload() {
    Promise.all([
      api<CalendarDay[]>(`/api/calendar/days?date_from=${dateFrom}&date_to=${dateTo}`),
      api<AttendanceMonth>(`/api/calendar/attendance?date_from=${dateFrom}&date_to=${dateTo}`),
    ])
      .then(([calendarDays, monthAttendance]) => {
        setDays(calendarDays);
        setAttendance(monthAttendance);
      })
      .catch((error: Error) => notifications.show({ color: "red", message: error.message }));
  }

  useEffect(() => {
    reload();
  }, [dateFrom, dateTo]);

  function shiftMonth(delta: number) {
    const next = new Date(year, month - 1 + delta, 1);
    setYear(next.getFullYear());
    setMonth(next.getMonth() + 1);
  }

  async function addDay(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await api("/api/calendar/days", {
        method: "POST",
        body: JSON.stringify({ day: newDay, kind: newKind, title: newTitle }),
      });
      setNewTitle("");
      notifications.show({ color: "green", message: "День календаря сохранён" });
      reload();
    } catch (error) {
      notifications.show({ color: "red", message: (error as Error).message });
    } finally {
      setSaving(false);
    }
  }

  async function removeDay(day: string) {
    try {
      await api(`/api/calendar/days/${day}`, { method: "DELETE" });
      reload();
    } catch (error) {
      notifications.show({ color: "red", message: (error as Error).message });
    }
  }

  async function togglePresent(userId: number, day: string, present: boolean) {
    try {
      const updated = await api<{ user_id: number; day: string; present: boolean }>("/api/calendar/attendance", {
        method: "PUT",
        body: JSON.stringify({ user_id: userId, day, present }),
      });
      setAttendance((current) => {
        const rest = current.absences.filter((row) => !(row.user_id === userId && row.day === day));
        return {
          ...current,
          absences: updated.present ? rest : [...rest, { user_id: userId, day, present: false }],
        };
      });
    } catch (error) {
      notifications.show({ color: "red", message: (error as Error).message });
    }
  }

  return (
    <Stack>
      <div>
        <Title order={2}>Календарь и явка</Title>
        <Text c="dimmed" size="sm">
          Праздники и переносы вычитаются из плана. Пустая ячейка — человек на месте; снимите галочку, если отсутствует.
          Участок у рабочего задаётся в «Сотрудниках».
        </Text>
      </div>
      <Group>
        <Button variant="light" onClick={() => shiftMonth(-1)}>
          ←
        </Button>
        <Title order={4}>
          {MONTHS[month - 1]} {year}
        </Title>
        <Button variant="light" onClick={() => shiftMonth(1)}>
          →
        </Button>
      </Group>
      <Paper withBorder p="md">
        <form onSubmit={addDay}>
          <Group grow align="flex-end" wrap="wrap">
            <TextInput label="Дата" type="date" value={newDay} onChange={(e) => setNewDay(e.currentTarget.value)} required />
            <Select
              label="Тип"
              data={[
                { value: "holiday", label: "Праздник / выходной" },
                { value: "extra_work", label: "Рабочий выходной" },
              ]}
              value={newKind}
              onChange={(value) => setNewKind((value as CalendarDayKind) || "holiday")}
            />
            <TextInput label="Название" value={newTitle} onChange={(e) => setNewTitle(e.currentTarget.value)} />
            <Button type="submit" loading={saving}>
              Сохранить день
            </Button>
          </Group>
        </form>
        {days.length > 0 && (
          <Stack gap={6} mt="md">
            {days.map((row) => (
              <Group key={row.day} justify="space-between">
                <Text size="sm">
                  {row.day} · {row.kind === "holiday" ? "праздник" : "рабочий выходной"}
                  {row.title ? ` · ${row.title}` : ""}
                </Text>
                <Button size="xs" variant="subtle" color="red" onClick={() => void removeDay(row.day)}>
                  Убрать
                </Button>
              </Group>
            ))}
          </Stack>
        )}
      </Paper>
      {attendance.staff.length === 0 ? (
        <Text c="dimmed">Нет активных конструкторов, снабженцев или рабочих — явку отмечать некому.</Text>
      ) : (
        <Table.ScrollContainer minWidth={920}>
          <Table striped withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Сотрудник</Table.Th>
                {monthDays.map((day) => {
                  const mark = dayMap.get(day);
                  const weekend = isWeekend(day) && mark?.kind !== "extra_work";
                  const holiday = mark?.kind === "holiday";
                  return (
                    <Table.Th key={day} ta="center" c={holiday ? "red" : weekend ? "dimmed" : undefined}>
                      <Text size="xs">{Number(day.slice(8))}</Text>
                      <Text size="xs">{WEEKDAY[weekdayIndex(day)]}</Text>
                    </Table.Th>
                  );
                })}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {attendance.staff.map((user) => (
                <Table.Tr key={user.id}>
                  <Table.Td>
                    <Text size="sm">{user.display_name}</Text>
                    <Text size="xs" c="dimmed">
                      {ROLE_LABEL[user.role]}
                      {user.work_center_code ? ` · ${CENTER_LABEL[user.work_center_code] ?? user.work_center_code}` : ""}
                    </Text>
                  </Table.Td>
                  {monthDays.map((day) => {
                    const mark = dayMap.get(day);
                    const working = mark?.kind === "extra_work" || (!isWeekend(day) && mark?.kind !== "holiday");
                    return (
                      <Table.Td key={day} ta="center">
                        {working ? (
                          <Checkbox
                            aria-label={`${user.display_name} ${day}`}
                            checked={!absent.has(`${user.id}:${day}`)}
                            onChange={(event) => void togglePresent(user.id, day, event.currentTarget.checked)}
                          />
                        ) : (
                          <Text size="xs" c="dimmed">
                            —
                          </Text>
                        )}
                      </Table.Td>
                    );
                  })}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Stack>
  );
}
