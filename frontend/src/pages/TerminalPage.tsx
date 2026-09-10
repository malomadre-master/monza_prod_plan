import { useEffect, useState } from "react";
import { Badge, Button, Card, Group, Select, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { api, openAttachment, type TerminalCard, type TerminalQueue, type User, type WorkCenterRow } from "../api";
import { CENTER_LABEL, ITEM_FALLBACK, STEP_STATUS_LABEL, itemLabel } from "../labels";

function defaultCenter(user: User): string {
  if (user.role === "supply") return "complectation";
  return user.work_center_code || "saw";
}

export function TerminalPage({ user }: { user: User }) {
  const locked = user.role === "worker" || user.role === "supply";
  const [center, setCenter] = useState(defaultCenter(user));
  const [centers, setCenters] = useState<WorkCenterRow[]>([]);
  const [cards, setCards] = useState<TerminalCard[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  function reload(nextCenter = center) {
    api<TerminalQueue>(`/api/terminal/queue?center=${nextCenter}`)
      .then((data) => {
        setCenter(data.center_code);
        setCards(data.cards);
        setError("");
      })
      .catch((err: Error) => setError(err.message));
  }

  useEffect(() => {
    api<WorkCenterRow[]>("/api/catalog/work-centers").then(setCenters).catch(() => undefined);
    reload(center);
  }, []);

  const mine = cards.filter((row) => row.step_status === "mine");
  const waiting = cards.filter((row) => row.step_status === "waiting");
  const taken = cards.filter((row) => row.step_status === "taken");
  const blocked = user.role !== "admin" && mine.length > 0;
  const isGate = center === "complectation";

  async function send(card: TerminalCard, kind: "taken" | "done" | "materials_confirmed") {
    setBusy(`${card.item_id}-${kind}`);
    try {
      await api("/api/terminal/events", {
        method: "POST",
        body: JSON.stringify({ order_id: card.order_id, item_id: card.item_id, kind, center_code: center }),
      });
      notifications.show({
        color: "teal",
        message: kind === "taken" ? "Взято в работу" : kind === "done" ? "Готово" : "Материалы подтверждены",
      });
      reload();
    } catch (err) {
      notifications.show({ color: "red", message: err instanceof Error ? err.message : "Не удалось" });
    } finally {
      setBusy(null);
    }
  }

  if (user.role === "worker" && !user.work_center_code) {
    return (
      <Stack>
        <Title order={2}>Терминал участка</Title>
        <Text c="orange">У этой учётки не задан участок. Попросите администратора указать его в «Сотрудниках».</Text>
      </Stack>
    );
  }

  return (
    <Stack>
      <div>
        <Title order={2}>Терминал участка</Title>
        <Text c="dimmed" size="sm">
          {isGate
            ? "Подтвердите наличие материалов по изделию — оно уйдёт на пилу, не дожидаясь остальных."
            : "Одна карточка в работе. Документы открываются с телефона."}
        </Text>
      </div>
      {!locked && (
        <Select
          label="Участок"
          data={centers.map((row) => ({ value: row.code, label: row.title }))}
          value={center}
          onChange={(value) => {
            if (!value) return;
            setCenter(value);
            reload(value);
          }}
        />
      )}
      <Text fw={700}>{CENTER_LABEL[center] ?? center}</Text>
      {error && <Text c="red">{error}</Text>}
      {mine.length > 0 && (
        <Stack gap="sm">
          <Text size="sm" c="orange">
            Сначала завершите взятое изделие.
          </Text>
          {mine.map((card) => (
            <ItemCard
              key={card.item_id}
              card={card}
              busy={busy}
              onDone={() => void send(card, "done")}
            />
          ))}
        </Stack>
      )}
      <Stack gap="sm">
        {waiting.length === 0 && mine.length === 0 && !error ? (
          <Text c="dimmed">Очередь пуста.</Text>
        ) : (
          waiting.map((card) => (
            <ItemCard
              key={card.item_id}
              card={card}
              busy={busy}
              disabled={blocked}
              onTake={isGate ? undefined : () => void send(card, "taken")}
              onConfirm={isGate ? () => void send(card, "materials_confirmed") : undefined}
            />
          ))
        )}
        {taken.map((card) => (
          <ItemCard key={card.item_id} card={card} busy={busy} />
        ))}
      </Stack>
    </Stack>
  );
}

function ItemCard({
  card,
  busy,
  disabled,
  onTake,
  onDone,
  onConfirm,
}: {
  card: TerminalCard;
  busy: string | null;
  disabled?: boolean;
  onTake?: () => void;
  onDone?: () => void;
  onConfirm?: () => void;
}) {
  return (
    <Card withBorder padding="md" radius="md">
      <Group justify="space-between" mb={6}>
        <Text fw={700}>{card.customer}</Text>
        <Badge variant="light">{STEP_STATUS_LABEL[card.step_status]}</Badge>
      </Group>
      <Text>
        {itemLabel(ITEM_FALLBACK, card.item_type)} · {card.qty} шт · {card.area_m2} м²
      </Text>
      {card.comment && (
        <Text size="sm" c="dimmed">
          {card.comment}
        </Text>
      )}
      {card.taken_by_name && card.step_status === "taken" && (
        <Text size="sm" c="orange">
          У {card.taken_by_name}
        </Text>
      )}
      {card.files.length > 0 && (
        <Stack gap={4} mt="sm">
          {card.files.map((file) => (
            <Button
              key={file.id}
              variant="subtle"
              size="compact-sm"
              justify="flex-start"
              onClick={() => void openAttachment(file.id, file.original_name).catch((err: Error) => notifications.show({ color: "red", message: err.message }))}
            >
              {file.original_name}
            </Button>
          ))}
        </Stack>
      )}
      <Group mt="md" grow>
        {onTake && (
          <Button size="md" disabled={disabled} loading={busy === `${card.item_id}-taken`} onClick={onTake}>
            Взять
          </Button>
        )}
        {onDone && (
          <Button size="md" color="teal" loading={busy === `${card.item_id}-done`} onClick={onDone}>
            Готово
          </Button>
        )}
        {onConfirm && (
          <Button size="md" color="teal" loading={busy === `${card.item_id}-materials_confirmed`} onClick={onConfirm}>
            Всё в наличии
          </Button>
        )}
      </Group>
    </Card>
  );
}
