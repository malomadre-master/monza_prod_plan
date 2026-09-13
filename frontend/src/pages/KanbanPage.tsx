import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Drawer, Group, SegmentedControl, Stack, Text, Title } from "@mantine/core";
import { api, type BoardCard, type BoardStatus, type WorkCenterRow } from "../api";
import { BOARD_STATUS_COLOR, BOARD_STATUS_LABEL, CENTER_LABEL, itemLabel, ITEM_FALLBACK, STATUS_LABEL } from "../labels";
import { orderColor } from "../plan/monitor";
import classes from "./KanbanPage.module.css";

const STATUS_COLUMNS: BoardStatus[] = ["waiting", "in_progress", "done"];

export function KanbanPage() {
  const [cards, setCards] = useState<BoardCard[]>([]);
  const [centers, setCenters] = useState<WorkCenterRow[]>([]);
  const [error, setError] = useState("");
  const [group, setGroup] = useState<"center" | "status">("center");
  const [selected, setSelected] = useState<BoardCard | null>(null);

  useEffect(() => {
    Promise.all([api<BoardCard[]>("/api/plan/board"), api<WorkCenterRow[]>("/api/catalog/work-centers")])
      .then(([board, catalog]) => {
        setCards(board);
        setCenters(catalog);
        setError("");
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  const columns = useMemo(() => {
    if (group === "status") {
      return STATUS_COLUMNS.map((status) => ({
        key: status,
        title: BOARD_STATUS_LABEL[status],
        cards: cards.filter((card) => card.board_status === status),
      }));
    }
    return centers.map((center) => ({
      key: center.code,
      title: center.title,
      cards: cards.filter((card) => card.center_code === center.code),
    }));
  }, [cards, centers, group]);

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>Канбан</Title>
          <Text c="dimmed" size="sm">
            Карточка — текущий шаг изделия. Статус из событий «взял / готово». Перетаскивание очереди — следующим шагом.
          </Text>
        </div>
        <SegmentedControl
          value={group}
          onChange={(value) => setGroup(value as "center" | "status")}
          data={[
            { value: "center", label: "Участки" },
            { value: "status", label: "Статусы" },
          ]}
        />
      </Group>
      {error && <Text c="red">{error}</Text>}
      <div className={classes.board}>
        {columns.map((column) => (
          <div key={column.key} className={classes.column}>
            <div className={classes.head}>
              <Text fw={700} size="sm">
                {column.title}
              </Text>
              <Text size="xs" c="dimmed">
                {column.cards.length}
              </Text>
            </div>
            {column.cards.length === 0 && (
              <Text size="sm" c="dimmed">
                Пусто
              </Text>
            )}
            {column.cards.map((card) => (
              <button
                key={`${card.item_id}-${card.center_code}`}
                type="button"
                className={classes.card}
                style={{ background: `var(--mantine-color-${orderColor(card.order_id)}-6)` }}
                onClick={() => setSelected(card)}
              >
                <Text fw={700} size="sm">
                  {card.customer}
                </Text>
                <div className={classes.meta}>
                  {itemLabel(ITEM_FALLBACK, card.item_type)} #{card.item_id} · {card.qty} шт
                </div>
                {group === "center" ? (
                  <div className={classes.meta}>{BOARD_STATUS_LABEL[card.board_status]}</div>
                ) : (
                  <div className={classes.meta}>{CENTER_LABEL[card.center_code] ?? card.center_code}</div>
                )}
                {card.start && (
                  <div className={classes.meta}>
                    план {card.start}
                    {card.finish && card.finish !== card.start ? ` → ${card.finish}` : ""}
                  </div>
                )}
              </button>
            ))}
          </div>
        ))}
      </div>

      <Drawer opened={Boolean(selected)} onClose={() => setSelected(null)} title="Изделие на участке" position="right">
        {selected && (
          <Stack>
            <Text fw={700}>
              <Link to={`/orders/${selected.order_id}`}>{selected.customer}</Link>
            </Text>
            <Text>
              {itemLabel(ITEM_FALLBACK, selected.item_type)} · изделие #{selected.item_id} · {selected.qty} шт
            </Text>
            {selected.comment && <Text size="sm">{selected.comment}</Text>}
            <Group gap="xs">
              <Badge color={BOARD_STATUS_COLOR[selected.board_status]}>{BOARD_STATUS_LABEL[selected.board_status]}</Badge>
              <Badge variant="light">{CENTER_LABEL[selected.center_code] ?? selected.center_code}</Badge>
              <Badge variant="outline">{STATUS_LABEL[selected.order_status]}</Badge>
            </Group>
            {selected.taken_by_name && <Text size="sm">Взял: {selected.taken_by_name}</Text>}
            {selected.start && (
              <Text size="sm">
                План: {selected.start}
                {selected.finish ? ` → ${selected.finish}` : ""}
              </Text>
            )}
            <Text size="sm">Приоритет заказа {selected.order_priority}, изделия {selected.item_priority}</Text>
            <Link to={`/orders/${selected.order_id}`}>Открыть заказ</Link>
          </Stack>
        )}
      </Drawer>
    </Stack>
  );
}
