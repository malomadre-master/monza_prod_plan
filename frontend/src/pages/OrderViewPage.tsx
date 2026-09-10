import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge, Button, Group, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { api, type Attachment, type ItemTypeRow, type Order, type User } from "../api";
import { ITEM_FALLBACK, STATUS_LABEL, canEditOrders, canWorkAsDesigner, itemLabel, statusColor } from "../labels";
import { ItemDocs } from "./ItemDocs";

export function OrderViewPage({ user }: { user: User }) {
  const { id } = useParams();
  const [order, setOrder] = useState<Order | null>(null);
  const [types, setTypes] = useState<ItemTypeRow[]>(ITEM_FALLBACK);
  const [filesByItem, setFilesByItem] = useState<Record<number, Attachment[]>>({});
  const [error, setError] = useState("");
  const [claiming, setClaiming] = useState(false);

  function loadFiles(next: Order) {
    Promise.all(
      next.items
        .filter((item) => item.id)
        .map((item) =>
          api<Attachment[]>(`/api/orders/${next.id}/items/${item.id}/attachments`).then((files) => [
            item.id as number,
            files,
          ]),
        ),
    )
      .then((pairs) => setFilesByItem(Object.fromEntries(pairs)))
      .catch(() => undefined);
  }

  useEffect(() => {
    if (!id) return;
    api<Order>(`/api/orders/${id}`)
      .then((next) => {
        setOrder(next);
        loadFiles(next);
      })
      .catch((err: Error) => setError(err.message));
    api<ItemTypeRow[]>("/api/catalog/item-types").then(setTypes).catch(() => undefined);
  }, [id]);

  async function claim() {
    if (!order) return;
    setClaiming(true);
    try {
      const next = await api<Order>(`/api/orders/${order.id}/claim`, { method: "POST" });
      setOrder(next);
      notifications.show({ color: "teal", message: "Заказ взят" });
    } catch (err) {
      notifications.show({ color: "red", message: err instanceof Error ? err.message : "Не удалось взять" });
    } finally {
      setClaiming(false);
    }
  }

  if (error) return <Text c="red">{error}</Text>;
  if (!order) return <Text c="dimmed">Загрузка…</Text>;

  const canEditDocs =
    user.role === "admin" ||
    user.role === "planner" ||
    (user.role === "designer" && order.claimed_by_id === user.id);
  const canClaim =
    canWorkAsDesigner(user.role) && order.status === "queued" && !order.claimed_by_id;

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>{order.customer}</Title>
        <Group>
          <Badge color={statusColor(order.status)}>{STATUS_LABEL[order.status]}</Badge>
          {canEditOrders(user.role) && order.status === "draft" && (
            <Button component={Link} to={`/orders/${order.id}/edit`}>
              Править черновик
            </Button>
          )}
          {canClaim && (
            <Button loading={claiming} onClick={() => void claim()}>
              Взять заказ
            </Button>
          )}
        </Group>
      </Group>
      <Paper withBorder p="md">
        <Text>Договор: {order.contract_number || "—"} от {order.contract_date}</Text>
        <Text>Запуск: {order.launch_date}</Text>
        <Text>Приоритет заказа: {order.priority}</Text>
        <Text>Конструктор: {order.claimed_by_name || "ещё не взят"}</Text>
        {order.notes && <Text mt="xs">{order.notes}</Text>}
      </Paper>
      {order.items.map((item) => (
        <Paper withBorder p="md" key={item.id ?? `${item.item_type}-${item.comment}`}>
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Вид</Table.Th>
                <Table.Th>Кол-во</Table.Th>
                <Table.Th>м²</Table.Th>
                <Table.Th>м.пог</Table.Th>
                <Table.Th>Приоритет</Table.Th>
                <Table.Th>Комментарий</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              <Table.Tr>
                <Table.Td>{itemLabel(types, item.item_type)}</Table.Td>
                <Table.Td>{item.qty}</Table.Td>
                <Table.Td>{item.area_m2}</Table.Td>
                <Table.Td>{item.linear_m}</Table.Td>
                <Table.Td>{item.priority}</Table.Td>
                <Table.Td>{item.comment || "—"}</Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>
          {item.id && (
            <ItemDocs
              order={order}
              item={item}
              files={filesByItem[item.id] ?? []}
              user={user}
              canEdit={canEditDocs}
              onChanged={(next, files) => {
                setOrder(next);
                setFilesByItem((prev) => ({ ...prev, [item.id as number]: files }));
              }}
            />
          )}
        </Paper>
      ))}
      <Text>
        Итого {order.total_qty} изд., {order.total_area_m2} м²
      </Text>
      <Button variant="subtle" component={Link} to={user.role === "designer" ? "/constructor" : "/orders"}>
        Назад
      </Button>
    </Stack>
  );
}
