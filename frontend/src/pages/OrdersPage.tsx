import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Badge, Button, Group, Stack, Table, Text, Title } from "@mantine/core";
import { api, type OrderListRow, type User } from "../api";
import { STATUS_LABEL, canEditOrders } from "../labels";

export function OrdersPage({ user }: { user: User }) {
  const [rows, setRows] = useState<OrderListRow[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api<OrderListRow[]>("/api/orders")
      .then(setRows)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <Stack>
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={2}>Заказы</Title>
          <Text c="dimmed" size="sm">
            Сортировка: приоритет заказа → дата запуска
          </Text>
        </div>
        {canEditOrders(user.role) && (
          <Button component={Link} to="/orders/new">
            Новый заказ
          </Button>
        )}
      </Group>
      {error && <Text c="red">{error}</Text>}
      {rows.length === 0 && !error ? (
        <Text c="dimmed">Пока нет заказов. Планировщик добавляет их формой.</Text>
      ) : (
        <Table.ScrollContainer minWidth={720}>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Приоритет</Table.Th>
                <Table.Th>Заказчик</Table.Th>
                <Table.Th>Договор</Table.Th>
                <Table.Th>Запуск</Table.Th>
                <Table.Th>Изделия</Table.Th>
                <Table.Th>м²</Table.Th>
                <Table.Th>Статус</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {rows.map((row) => (
                <Table.Tr key={row.id}>
                  <Table.Td>{row.priority}</Table.Td>
                  <Table.Td>
                    <Link to={`/orders/${row.id}`}>{row.customer}</Link>
                  </Table.Td>
                  <Table.Td>
                    {row.contract_number || "—"}
                    <Text size="xs" c="dimmed">
                      {row.contract_date}
                    </Text>
                  </Table.Td>
                  <Table.Td>{row.launch_date}</Table.Td>
                  <Table.Td>{row.item_count}</Table.Td>
                  <Table.Td>{row.total_area_m2}</Table.Td>
                  <Table.Td>
                    <Badge color={row.status === "draft" ? "gray" : "blue"} variant="light">
                      {STATUS_LABEL[row.status]}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Stack>
  );
}
