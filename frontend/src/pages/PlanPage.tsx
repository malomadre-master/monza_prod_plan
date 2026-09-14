import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Badge,
  Button,
  Drawer,
  Group,
  Modal,
  SegmentedControl,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { api, type CalendarDay, type PlanPreview, type PlanSlot, type PlanVersionDetail, type PlanVersionRow, type WorkCenterRow } from "../api";
import { CENTER_LABEL, itemLabel, ITEM_FALLBACK } from "../labels";
import {
  addDays,
  formatDay,
  formatLong,
  monthEnd,
  monthStart,
  todayISO,
  visibleDays,
  weekdayLabel,
  type RangeMode,
} from "../plan/dates";
import {
  columnSpan,
  isOverdue,
  itemChain,
  loadByCell,
  orderColor,
  unitLabel,
  whyDate,
  withLanes,
} from "../plan/monitor";
import classes from "./PlanPage.module.css";

const VERSION_REASON: Record<string, string> = {
  pin: "Закрепление",
  unpin: "Снятие закрепления",
  queue: "Очередь канбана",
};

function versionReasonLabel(reason: string): string {
  return VERSION_REASON[reason] ?? reason;
}

function formatVersionTime(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleString("ru-RU");
}

export function PlanPage({ canPin = false }: { canPin?: boolean }) {
  const [slots, setSlots] = useState<PlanSlot[]>([]);
  const [centers, setCenters] = useState<WorkCenterRow[]>([]);
  const [holidays, setHolidays] = useState<Set<string>>(new Set());
  const [extraWork, setExtraWork] = useState<Set<string>>(new Set());
  const [holidayTitle, setHolidayTitle] = useState<Map<string, string>>(new Map());
  const [error, setError] = useState("");
  const [mode, setMode] = useState<RangeMode>("week");
  const [anchor, setAnchor] = useState(todayISO);
  const [selected, setSelected] = useState<PlanSlot | null>(null);
  const [dayOpen, setDayOpen] = useState<string | null>(null);
  const [pinStart, setPinStart] = useState("");
  const [pinFinish, setPinFinish] = useState("");
  const [preview, setPreview] = useState<PlanPreview | null>(null);
  const [previewRemove, setPreviewRemove] = useState(false);
  const [saving, setSaving] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [versions, setVersions] = useState<PlanVersionRow[]>([]);
  const [versionDetail, setVersionDetail] = useState<PlanVersionDetail | null>(null);
  const [historyError, setHistoryError] = useState("");
  const today = todayISO();

  useEffect(() => {
    Promise.all([api<PlanSlot[]>("/api/plan"), api<WorkCenterRow[]>("/api/catalog/work-centers")])
      .then(([plan, catalog]) => {
        setSlots(plan);
        setCenters(catalog);
        setError("");
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setPinStart(selected.start);
    setPinFinish(selected.finish);
  }, [selected]);

  useEffect(() => {
    const from = addDays(monthStart(anchor), -7);
    const to = addDays(monthEnd(anchor), 7);
    api<CalendarDay[]>(`/api/calendar/days?date_from=${from}&date_to=${to}`)
      .then((rows) => {
        const nextHolidays = new Set<string>();
        const nextExtra = new Set<string>();
        const titles = new Map<string, string>();
        for (const row of rows) {
          titles.set(row.day, row.title);
          if (row.kind === "holiday") nextHolidays.add(row.day);
          else nextExtra.add(row.day);
        }
        setHolidays(nextHolidays);
        setExtraWork(nextExtra);
        setHolidayTitle(titles);
      })
      .catch(() => undefined);
  }, [anchor]);

  const days = useMemo(
    () => visibleDays(mode, anchor, holidays, extraWork),
    [mode, anchor, holidays, extraWork],
  );
  const load = useMemo(
    () => loadByCell(slots, centers, days, holidays, extraWork),
    [slots, centers, days, holidays, extraWork],
  );
  const lanes = useMemo(() => withLanes(slots), [slots]);

  function shift(direction: number) {
    if (mode === "day") setAnchor(addDays(anchor, direction));
    else if (mode === "week") setAnchor(addDays(anchor, direction * 7));
    else {
      const start = monthStart(anchor);
      const [year, month] = start.split("-").map(Number);
      const next = new Date(year, month - 1 + direction, 1);
      setAnchor(
        `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, "0")}-${String(next.getDate()).padStart(2, "0")}`,
      );
    }
  }

  const daySlots = dayOpen ? slots.filter((row) => row.start <= dayOpen && dayOpen <= row.finish) : [];
  const chain = selected ? itemChain(selected, slots) : [];

  async function requestPreview(remove = false) {
    if (!selected) return;
    try {
      const data = await api<PlanPreview>("/api/plan/pins/preview", {
        method: "POST",
        body: JSON.stringify({
          item_id: selected.item_id,
          center_code: selected.center_code,
          start: remove ? undefined : pinStart,
          finish: remove ? undefined : pinFinish,
          remove,
        }),
      });
      setPreviewRemove(remove);
      setPreview(data);
    } catch (err) {
      notifications.show({ color: "red", title: "Предпросмотр не получен", message: (err as Error).message });
    }
  }

  async function applyPreview() {
    if (!selected) return;
    setSaving(true);
    try {
      const data = await api<PlanPreview>("/api/plan/pins", {
        method: "PUT",
        body: JSON.stringify({
          item_id: selected.item_id,
          center_code: selected.center_code,
          start: previewRemove ? undefined : pinStart,
          finish: previewRemove ? undefined : pinFinish,
          remove: previewRemove,
        }),
      });
      setSlots(data.slots);
      const next = data.slots.find(
        (row) => row.item_id === selected.item_id && row.center_code === selected.center_code,
      );
      if (next) {
        setSelected(next);
        setPinStart(next.start);
        setPinFinish(next.finish);
      }
      setPreview(null);
      notifications.show({
        color: "teal",
        message: previewRemove ? "Закрепление снято" : "Блок закреплён, незакреплённые слоты пересчитаны",
      });
    } catch (err) {
      notifications.show({ color: "red", title: "Не удалось применить", message: (err as Error).message });
    } finally {
      setSaving(false);
    }
  }

  async function openHistory() {
    setHistoryOpen(true);
    setVersionDetail(null);
    setHistoryError("");
    try {
      setVersions(await api<PlanVersionRow[]>("/api/plan/versions"));
    } catch (err) {
      setHistoryError((err as Error).message);
    }
  }

  async function loadVersion(id: number) {
    setHistoryError("");
    try {
      setVersionDetail(await api<PlanVersionDetail>(`/api/plan/versions/${id}`));
    } catch (err) {
      setHistoryError((err as Error).message);
    }
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>Монитор</Title>
          <Text c="dimmed" size="sm">
            Участки по дням, цвет — заказ, процент — загрузка мощности. Белая обводка — закреплённый блок.
          </Text>
        </div>
        <Group>
          {canPin && (
            <Button variant="light" onClick={() => void openHistory()}>
              История
            </Button>
          )}
          <Button variant="default" onClick={() => shift(-1)}>
            ←
          </Button>
          <Button variant="light" onClick={() => setAnchor(today)}>
            Сегодня
          </Button>
          <Button variant="default" onClick={() => shift(1)}>
            →
          </Button>
          <SegmentedControl
            value={mode}
            onChange={(value) => setMode(value as RangeMode)}
            data={[
              { value: "day", label: "День" },
              { value: "week", label: "Неделя" },
              { value: "month", label: "Месяц" },
            ]}
          />
        </Group>
      </Group>
      {error && <Text c="red">{error}</Text>}
      <Tabs defaultValue="monitor">
        <Tabs.List>
          <Tabs.Tab value="monitor">Сетка</Tabs.Tab>
          <Tabs.Tab value="list">Список слотов</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="monitor" pt="md">
          {error && <Text c="red">{error}</Text>}
          {!error && centers.length === 0 ? (
            <Text c="dimmed">Нет участков. Проверьте, что API стартовал.</Text>
          ) : (
            <MonitorGrid
              days={days}
              centers={centers}
              lanes={lanes}
              load={load}
              holidays={holidays}
              extraWork={extraWork}
              holidayTitle={holidayTitle}
              today={today}
              onDay={setDayOpen}
              onSlot={setSelected}
            />
          )}
        </Tabs.Panel>
        <Tabs.Panel value="list" pt="md">
          <SlotTable slots={slots} />
        </Tabs.Panel>
      </Tabs>

      <Drawer opened={Boolean(selected)} onClose={() => setSelected(null)} title="Изделие на участке" position="right">
        {selected && (
          <Stack>
            <Text fw={700}>
              <Link to={`/orders/${selected.order_id}`}>{selected.customer}</Link>
            </Text>
            <Text>
              {itemLabel(ITEM_FALLBACK, selected.item_type)} · изделие #{selected.item_id} · {selected.qty} шт
            </Text>
            <Group gap="xs">
              <Badge color={orderColor(selected.order_id)}>заказ приоритет {selected.order_priority}</Badge>
              <Badge variant="light">изделие приоритет {selected.item_priority}</Badge>
              {selected.pinned && <Badge color="blue">закреплено</Badge>}
              {isOverdue(selected) && <Badge color="red">план позже сегодняшнего</Badge>}
            </Group>
            <Text>
              {CENTER_LABEL[selected.center_code] ?? selected.center_code}: {selected.start} → {selected.finish}, объём{" "}
              {selected.volume}
            </Text>
            <Text size="sm">{whyDate(selected, slots)}</Text>
            {canPin && (
              <Stack gap="xs">
                <Group grow>
                  <TextInput type="date" label="Старт" value={pinStart} onChange={(event) => setPinStart(event.currentTarget.value)} />
                  <TextInput type="date" label="Финиш" value={pinFinish} onChange={(event) => setPinFinish(event.currentTarget.value)} />
                </Group>
                <Button onClick={() => requestPreview(false)}>Предпросмотр закрепления</Button>
                {selected.pinned && (
                  <Button variant="light" color="red" onClick={() => requestPreview(true)}>
                    Снять закрепление
                  </Button>
                )}
              </Stack>
            )}
            <Text size="sm" c="dimmed">
              Цепочка изделия
            </Text>
            {chain.map((row) => (
              <Text key={`${row.center_code}-${row.start}`} size="sm">
                {CENTER_LABEL[row.center_code] ?? row.center_code}: {row.start} — {row.finish}
                {row.center_code === selected.center_code ? " ← сейчас" : ""}
              </Text>
            ))}
            <Button component={Link} to={`/orders/${selected.order_id}`} variant="light">
              Открыть заказ
            </Button>
          </Stack>
        )}
      </Drawer>

      <Modal opened={Boolean(preview)} onClose={() => setPreview(null)} title="Пересчёт плана" size="lg">
        {preview && (
          <Stack>
            <Text size="sm">
              {previewRemove
                ? "Снятие закрепления. Незакреплённые слоты пересчитаются."
                : "Закреплённый блок станет жёстким ограничением, остальные сдвинутся вокруг."}
            </Text>
            {preview.changes.length === 0 ? (
              <Text c="dimmed">Даты слотов не изменятся.</Text>
            ) : (
              <Table.ScrollContainer minWidth={520}>
                <Table striped>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Заказчик</Table.Th>
                      <Table.Th>Участок</Table.Th>
                      <Table.Th>Было</Table.Th>
                      <Table.Th>Станет</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {preview.changes.map((row) => (
                      <Table.Tr key={`${row.item_id}-${row.center_code}`}>
                        <Table.Td>
                          {row.customer} #{row.item_id}
                        </Table.Td>
                        <Table.Td>{CENTER_LABEL[row.center_code] ?? row.center_code}</Table.Td>
                        <Table.Td>
                          {row.before_start ?? "—"}
                          {row.before_finish ? ` → ${row.before_finish}` : ""}
                        </Table.Td>
                        <Table.Td>
                          {row.after_start ?? "—"}
                          {row.after_finish ? ` → ${row.after_finish}` : ""}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )}
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setPreview(null)}>
                Отмена
              </Button>
              <Button loading={saving} onClick={applyPreview}>
                Применить
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      <Drawer
        opened={Boolean(dayOpen)}
        onClose={() => setDayOpen(null)}
        title={dayOpen ? formatLong(dayOpen) : "День"}
        position="right"
      >
        {dayOpen && (
          <Stack>
            {holidayTitle.get(dayOpen) && <Badge variant="light">{holidayTitle.get(dayOpen)}</Badge>}
            {centers.map((center) => {
              const rows = daySlots.filter((slot) => slot.center_code === center.code);
              const pct = load.get(`${center.code}:${dayOpen}`) ?? 0;
              return (
                <div key={center.code}>
                  <Group justify="space-between">
                    <Text fw={600}>{center.title}</Text>
                    <Text size="sm" c={pct > 100 ? "red" : "dimmed"}>
                      {pct}% · {unitLabel(center.unit)}
                    </Text>
                  </Group>
                  {rows.length === 0 ? (
                    <Text size="sm" c="dimmed">
                      Нет слотов
                    </Text>
                  ) : (
                    rows.map((slot) => (
                      <Button
                        key={`${slot.item_id}-${slot.center_code}`}
                        variant="light"
                        color={orderColor(slot.order_id)}
                        fullWidth
                        mt={6}
                        onClick={() => {
                          setDayOpen(null);
                          setSelected(slot);
                        }}
                      >
                        {slot.customer} · {itemLabel(ITEM_FALLBACK, slot.item_type)} #{slot.item_id}
                      </Button>
                    ))
                  )}
                </div>
              );
            })}
          </Stack>
        )}
      </Drawer>

      <Drawer
        opened={historyOpen}
        onClose={() => setHistoryOpen(false)}
        title="История плана"
        position="right"
        size="lg"
      >
        <Stack>
          <Text size="sm" c="dimmed">
            Снимки после закрепления, снятия пина и смены очереди канбана. Откат пока не применяем.
          </Text>
          {historyError && <Text c="red">{historyError}</Text>}
          {versions.length === 0 && !historyError ? (
            <Text c="dimmed">Пока нет сохранённых версий.</Text>
          ) : (
            versions.map((row) => (
              <Button
                key={row.id}
                variant={versionDetail?.id === row.id ? "filled" : "light"}
                justify="space-between"
                onClick={() => void loadVersion(row.id)}
              >
                {versionReasonLabel(row.reason)} · {formatVersionTime(row.created_at)} · {row.created_by_name} ·{" "}
                {row.change_count} сдвигов
              </Button>
            ))
          )}
          {versionDetail && (
            <Stack gap="xs">
              <Text fw={600}>
                {versionReasonLabel(versionDetail.reason)} #{versionDetail.id}
              </Text>
              {versionDetail.changes.length === 0 ? (
                <Text c="dimmed">Даты слотов не изменились.</Text>
              ) : (
                <Table.ScrollContainer minWidth={480}>
                  <Table striped>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Заказчик</Table.Th>
                        <Table.Th>Участок</Table.Th>
                        <Table.Th>Было</Table.Th>
                        <Table.Th>Стало</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {versionDetail.changes.map((row) => (
                        <Table.Tr key={`${row.item_id}-${row.center_code}`}>
                          <Table.Td>
                            {row.customer} #{row.item_id}
                          </Table.Td>
                          <Table.Td>{CENTER_LABEL[row.center_code] ?? row.center_code}</Table.Td>
                          <Table.Td>
                            {row.before_start ?? "—"}
                            {row.before_finish ? ` → ${row.before_finish}` : ""}
                          </Table.Td>
                          <Table.Td>
                            {row.after_start ?? "—"}
                            {row.after_finish ? ` → ${row.after_finish}` : ""}
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                </Table.ScrollContainer>
              )}
            </Stack>
          )}
        </Stack>
      </Drawer>
    </Stack>
  );
}

function MonitorGrid({
  days,
  centers,
  lanes,
  load,
  holidays,
  extraWork,
  holidayTitle,
  today,
  onDay,
  onSlot,
}: {
  days: string[];
  centers: WorkCenterRow[];
  lanes: ReturnType<typeof withLanes>;
  load: Map<string, number>;
  holidays: Set<string>;
  extraWork: Set<string>;
  holidayTitle: Map<string, string>;
  today: string;
  onDay: (iso: string) => void;
  onSlot: (slot: PlanSlot) => void;
}) {
  const colTemplate = `repeat(${Math.max(days.length, 1)}, minmax(64px, 1fr))`;
  return (
    <div className={classes.wrap}>
      <div className={classes.header}>
        <div className={classes.label}>
          {days[0] && days[days.length - 1] ? `${formatDay(days[0])} – ${formatDay(days[days.length - 1])}` : ""}
        </div>
        <div className={classes.track} style={{ gridTemplateColumns: colTemplate }}>
          {days.map((day) => (
            <button
              key={day}
              type="button"
              className={`${classes.dayHead} ${day === today ? classes.todayHead : ""} ${holidays.has(day) ? classes.holiday : extraWork.has(day) ? "" : weekdayLabel(day) === "сб" || weekdayLabel(day) === "вс" ? classes.weekend : ""}`}
              onClick={() => onDay(day)}
              title={holidayTitle.get(day) || formatLong(day)}
            >
              <div>{weekdayLabel(day)}</div>
              <div>{formatDay(day)}</div>
            </button>
          ))}
        </div>
      </div>
      {centers.map((center) => {
        const rowSlots = lanes.filter((slot) => slot.center_code === center.code);
        const laneCount = Math.max(1, ...rowSlots.map((slot) => slot.lanes), 1);
        const rowHeight = Math.max(64, laneCount * 30 + 18);
        return (
          <div key={center.code} className={classes.row}>
            <div className={classes.label}>
              {center.title}
              <Text size="xs" c="dimmed" fw={400}>
                {center.capacity_qty}/{center.capacity_days} {unitLabel(center.unit)}
              </Text>
            </div>
            <div className={classes.track} style={{ gridTemplateColumns: colTemplate, minHeight: rowHeight }}>
              {days.map((day) => {
                const pct = load.get(`${center.code}:${day}`) ?? 0;
                const heat = pct > 100 ? classes.hot : pct >= 80 ? classes.warm : "";
                const extra =
                  day === today ? classes.todayCell : holidays.has(day) ? classes.holiday : extraWork.has(day) ? "" : weekdayLabel(day) === "сб" || weekdayLabel(day) === "вс" ? classes.weekend : "";
                return (
                  <button
                    key={day}
                    type="button"
                    className={`${classes.cell} ${heat} ${extra}`}
                    style={{ minHeight: rowHeight }}
                    onClick={() => onDay(day)}
                  >
                    {pct > 0 && <span className={classes.load}>{pct}%</span>}
                  </button>
                );
              })}
              {rowSlots.map((slot) => {
                const span = columnSpan(slot, days);
                if (!span) return null;
                const color = orderColor(slot.order_id);
                return (
                  <button
                    key={`${slot.item_id}-${slot.center_code}-${slot.start}`}
                    type="button"
                    className={`${classes.block} ${isOverdue(slot) ? classes.overdue : ""} ${slot.pinned ? classes.pinned : ""}`}
                    style={{
                      left: `calc((100% / ${days.length}) * ${span.start} + 2px)`,
                      width: `calc((100% / ${days.length}) * ${span.end - span.start + 1} - 4px)`,
                      top: 4 + slot.lane * 28,
                      height: 26,
                      background: `var(--mantine-color-${color}-6)`,
                    }}
                    onClick={(event) => {
                      event.stopPropagation();
                      onSlot(slot);
                    }}
                    title={`${slot.customer} · ${CENTER_LABEL[slot.center_code]}${slot.pinned ? " · закреплено" : ""}`}
                  >
                    {slot.customer} · {itemLabel(ITEM_FALLBACK, slot.item_type)}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SlotTable({ slots }: { slots: PlanSlot[] }) {
  if (slots.length === 0) {
    return <Text c="dimmed">Нет заказов в очереди. Добавьте заказ не черновиком.</Text>;
  }
  return (
    <Table.ScrollContainer minWidth={720}>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Заказчик</Table.Th>
            <Table.Th>Изделие</Table.Th>
            <Table.Th>Участок</Table.Th>
            <Table.Th>Объём</Table.Th>
            <Table.Th>Старт</Table.Th>
            <Table.Th>Готовность</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {slots.map((row) => (
            <Table.Tr key={`${row.item_id}-${row.center_code}`}>
              <Table.Td>
                <Link to={`/orders/${row.order_id}`}>{row.customer}</Link>
              </Table.Td>
              <Table.Td>
                {itemLabel(ITEM_FALLBACK, row.item_type)} #{row.item_id}
              </Table.Td>
              <Table.Td>{CENTER_LABEL[row.center_code] ?? row.center_code}</Table.Td>
              <Table.Td>{row.volume}</Table.Td>
              <Table.Td>{row.start}</Table.Td>
              <Table.Td>{row.finish}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
