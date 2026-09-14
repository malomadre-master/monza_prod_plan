import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Badge, Button, Drawer, Group, Modal, SegmentedControl, Stack, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { api, type BoardCard, type BoardStatus, type PlanPreview, type WorkCenterRow } from "../api";
import { BOARD_STATUS_COLOR, BOARD_STATUS_LABEL, CENTER_LABEL, itemLabel, ITEM_FALLBACK, STATUS_LABEL } from "../labels";
import { orderColor } from "../plan/monitor";
import classes from "./KanbanPage.module.css";

const STATUS_COLUMNS: BoardStatus[] = ["waiting", "in_progress", "done"];

type PendingQueue = {
  centerCode: string;
  itemIds: number[];
  snapshot: BoardCard[];
};

function CardBody({ card, group }: { card: BoardCard; group: "center" | "status" }) {
  return (
    <>
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
    </>
  );
}

function StaticCard({
  card,
  group,
  onOpen,
}: {
  card: BoardCard;
  group: "center" | "status";
  onOpen: (card: BoardCard) => void;
}) {
  return (
    <button
      type="button"
      className={classes.card}
      style={{ background: `var(--mantine-color-${orderColor(card.order_id)}-6)` }}
      onClick={() => onOpen(card)}
    >
      <CardBody card={card} group={group} />
    </button>
  );
}

function SortableCard({
  card,
  group,
  onOpen,
}: {
  card: BoardCard;
  group: "center" | "status";
  onOpen: (card: BoardCard) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: card.item_id,
  });
  return (
    <button
      ref={setNodeRef}
      type="button"
      className={`${classes.card} ${classes.sortable}${isDragging ? ` ${classes.dragging}` : ""}`}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        background: `var(--mantine-color-${orderColor(card.order_id)}-6)`,
      }}
      onClick={() => onOpen(card)}
      {...attributes}
      {...listeners}
    >
      <CardBody card={card} group={group} />
    </button>
  );
}

function waitingIds(cards: BoardCard[], centerCode: string): number[] {
  return cards.filter((card) => card.center_code === centerCode && card.board_status === "waiting").map((card) => card.item_id);
}

function reorderWaiting(cards: BoardCard[], centerCode: string, nextIds: number[]): BoardCard[] {
  const waiting = nextIds
    .map((id) => cards.find((card) => card.item_id === id))
    .filter((card): card is BoardCard => Boolean(card));
  let index = 0;
  return cards.map((card) => {
    if (card.center_code === centerCode && card.board_status === "waiting") {
      return waiting[index++] ?? card;
    }
    return card;
  });
}

export function KanbanPage({ canReorder = false }: { canReorder?: boolean }) {
  const [cards, setCards] = useState<BoardCard[]>([]);
  const [centers, setCenters] = useState<WorkCenterRow[]>([]);
  const [error, setError] = useState("");
  const [group, setGroup] = useState<"center" | "status">("center");
  const [selected, setSelected] = useState<BoardCard | null>(null);
  const [pending, setPending] = useState<PendingQueue | null>(null);
  const [preview, setPreview] = useState<PlanPreview | null>(null);
  const [saving, setSaving] = useState(false);
  const queueSeq = useRef(0);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  const reload = () => {
    Promise.all([api<BoardCard[]>("/api/plan/board"), api<WorkCenterRow[]>("/api/catalog/work-centers")])
      .then(([board, catalog]) => {
        setCards(board);
        setCenters(catalog);
        setError("");
      })
      .catch((err: Error) => setError(err.message));
  };

  useEffect(() => {
    reload();
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

  const dragEnabled = canReorder && group === "center";

  const onDragEnd = (event: DragEndEvent) => {
    if (!dragEnabled) return;
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const activeCard = cards.find((card) => card.item_id === active.id);
    const overCard = cards.find((card) => card.item_id === over.id);
    if (!activeCard || !overCard) return;
    if (activeCard.center_code !== overCard.center_code) return;
    if (activeCard.board_status !== "waiting" || overCard.board_status !== "waiting") return;
    const centerCode = activeCard.center_code;
    const currentIds = waitingIds(cards, centerCode);
    const oldIndex = currentIds.indexOf(Number(active.id));
    const newIndex = currentIds.indexOf(Number(over.id));
    if (oldIndex < 0 || newIndex < 0) return;
    const nextIds = arrayMove(currentIds, oldIndex, newIndex);
    const snapshot = cards;
    const seq = ++queueSeq.current;
    setCards(reorderWaiting(cards, centerCode, nextIds));
    setPending({ centerCode, itemIds: nextIds, snapshot });
    setPreview(null);
    api<PlanPreview>("/api/plan/queue/preview", {
      method: "POST",
      body: JSON.stringify({ center_code: centerCode, item_ids: nextIds }),
    })
      .then((data) => {
        if (queueSeq.current !== seq) return;
        setPreview(data);
      })
      .catch((err: Error) => {
        if (queueSeq.current !== seq) return;
        setCards(snapshot);
        setPending(null);
        notifications.show({ color: "red", title: "Предпросмотр не получен", message: err.message });
      });
  };

  const cancelPreview = () => {
    queueSeq.current += 1;
    if (pending) setCards(pending.snapshot);
    setPending(null);
    setPreview(null);
  };

  const applyPreview = async () => {
    if (!pending) return;
    setSaving(true);
    try {
      await api<PlanPreview>("/api/plan/queue", {
        method: "PUT",
        body: JSON.stringify({ center_code: pending.centerCode, item_ids: pending.itemIds }),
      });
      setPending(null);
      setPreview(null);
      reload();
    } catch (err) {
      notifications.show({ color: "red", title: "Не удалось применить", message: (err as Error).message });
    } finally {
      setSaving(false);
    }
  };

  const hint = dragEnabled
    ? "Карточка — текущий шаг изделия. Статус из событий «взял / готово». Перетащите очередь ожидания внутри участка — план покажет, что сдвинется."
    : canReorder
      ? "Карточка — текущий шаг изделия. Статус из событий «взял / готово». Чтобы менять очередь, переключитесь на участки."
      : "Карточка — текущий шаг изделия. Статус из событий «взял / готово». Очередь меняет планировщик.";

  const board = (
    <div className={classes.board}>
      {columns.map((column) => {
        const inProgress = column.cards.filter((card) => card.board_status === "in_progress");
        const waiting = column.cards.filter((card) => card.board_status === "waiting");
        const done = column.cards.filter((card) => card.board_status === "done");
        const sortable = dragEnabled && group === "center";
        return (
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
            {sortable ? (
              <>
                {inProgress.map((card) => (
                  <StaticCard key={`${card.item_id}-${card.center_code}`} card={card} group={group} onOpen={setSelected} />
                ))}
                <SortableContext items={waiting.map((card) => card.item_id)} strategy={verticalListSortingStrategy}>
                  {waiting.map((card) => (
                    <SortableCard key={`${card.item_id}-${card.center_code}`} card={card} group={group} onOpen={setSelected} />
                  ))}
                </SortableContext>
                {done.map((card) => (
                  <StaticCard key={`${card.item_id}-${card.center_code}`} card={card} group={group} onOpen={setSelected} />
                ))}
              </>
            ) : (
              column.cards.map((card) => (
                <StaticCard key={`${card.item_id}-${card.center_code}`} card={card} group={group} onOpen={setSelected} />
              ))
            )}
          </div>
        );
      })}
    </div>
  );

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>Канбан</Title>
          <Text c="dimmed" size="sm">
            {hint}
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
      {dragEnabled ? (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          {board}
        </DndContext>
      ) : (
        board
      )}

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
            <Text size="sm">
              Приоритет заказа {selected.order_priority}, изделия {selected.item_priority}
            </Text>
            <Link to={`/orders/${selected.order_id}`}>Открыть заказ</Link>
          </Stack>
        )}
      </Drawer>

      <Modal opened={Boolean(pending)} onClose={cancelPreview} title="Пересчёт плана" size="lg">
        {!preview ? (
          <Text size="sm" c="dimmed">
            Считаем, что сдвинется…
          </Text>
        ) : (
          <Stack>
            <Text size="sm">Новый порядок очереди задаёт приоритеты. Незапущенные слоты пересчитаются вокруг.</Text>
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
              <Button variant="default" onClick={cancelPreview}>
                Отмена
              </Button>
              <Button loading={saving} onClick={() => void applyPreview()}>
                Применить
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
