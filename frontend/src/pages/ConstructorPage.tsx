import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Group, Stack, Table, Tabs, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { api, type Order, type OrderListRow, type User } from "../api";
import { STATUS_LABEL, statusColor } from "../labels";

export function ConstructorPage({ user }: { user: User }) {
  const [rows, setRows] = useState<OrderListRow[]>([]);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  function reload() {
    api<OrderListRow[]>("/api/orders")
      .then(setRows)
      .catch((err: Error) => setError(err.message));
  }

  useEffect(reload, []);

  const mine = rows.filter((row) => row.claimed_by_id === user.id && row.status === "in_design");
  const available = rows.filter((row) => row.status === "queued" && !row.claimed_by_id);
  const blocked = mine.length > 0;

  async function claim(id: number) {
    setBusyId(id);
    try {
      await api<Order>(`/api/orders/${id}/claim`, { method: "POST" });
      notifications.show({ color: "teal", message: "Заказ взят. Завершите изделия, чтобы взять следующий." });
      reload();
    } catch (err) {
      notifications.show({ color: "red", message: err instanceof Error ? err.message : "Не удалось взять" });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Stack>
      <div>
        <Title order={2}>Рабочее место конструктора</Title>
        <Text c="dimmed" size="sm">
          Берёте заказ целиком. Пока он у вас, следующий взять нельзя. Взятый заказ другим не виден.
        </Text>
      </div>
      {error && <Text c="red">{error}</Text>}
      <Tabs defaultValue={mine.length ? "mine" : "available"}>
        <Tabs.List>
          <Tabs.Tab value="available">Доступные ({available.length})</Tabs.Tab>
          <Tabs.Tab value="mine">Мой заказ ({mine.length})</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="available" pt="md">
          {blocked && (
            <Text size="sm" c="orange" mb="sm">
              Сначала завершите изделия текущего заказа.
            </Text>
          )}
          <OrderTable
            rows={available}
            empty="Свободных заказов нет."
            action={(row) => (
              <Button
                size="xs"
                disabled={blocked}
                loading={busyId === row.id}
                onClick={() => void claim(row.id)}
              >
                Взять
              </Button>
            )}
          />
        </Tabs.Panel>
        <Tabs.Panel value="mine" pt="md">
          <OrderTable
            rows={mine}
            empty="Сейчас нет взятого заказа."
            action={(row) => (
              <Button size="xs" component={Link} to={`/orders/${row.id}`}>
                Документы
              </Button>
            )}
          />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}

function OrderTable({
  rows,
  empty,
  action,
}: {
  rows: OrderListRow[];
  empty: string;
  action: (row: OrderListRow) => ReactNode;
}) {
  if (rows.length === 0) return <Text c="dimmed">{empty}</Text>;
  return (
    <Table.ScrollContainer minWidth={640}>
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Приоритет</Table.Th>
            <Table.Th>Заказчик</Table.Th>
            <Table.Th>Запуск</Table.Th>
            <Table.Th>Изделия</Table.Th>
            <Table.Th>Статус</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((row) => (
            <Table.Tr key={row.id}>
              <Table.Td>{row.priority}</Table.Td>
              <Table.Td>
                <Link to={`/orders/${row.id}`}>{row.customer}</Link>
              </Table.Td>
              <Table.Td>{row.launch_date}</Table.Td>
              <Table.Td>{row.item_count}</Table.Td>
              <Table.Td>
                <Badge color={statusColor(row.status)} variant="light">
                  {STATUS_LABEL[row.status]}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Group justify="flex-end">{action(row)}</Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
