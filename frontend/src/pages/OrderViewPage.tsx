import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Badge, Button, Group, Paper, Stack, Table, Text, Title } from "@mantine/core";
import { api, type ItemTypeRow, type Order, type User } from "../api";
import { ITEM_FALLBACK, STATUS_LABEL, canEditOrders, itemLabel } from "../labels";

export function OrderViewPage({ user }: { user: User }) {
  const { id } = useParams();
  const [order, setOrder] = useState<Order | null>(null);
  const [types, setTypes] = useState<ItemTypeRow[]>(ITEM_FALLBACK);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    api<Order>(`/api/orders/${id}`)
      .then(setOrder)
      .catch((err: Error) => setError(err.message));
    api<ItemTypeRow[]>("/api/catalog/item-types").then(setTypes).catch(() => undefined);
  }, [id]);

  if (error) return <Text c="red">{error}</Text>;
  if (!order) return <Text c="dimmed">Загрузка…</Text>;

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>{order.customer}</Title>
        <Group>
          <Badge color={order.status === "draft" ? "gray" : "blue"}>{STATUS_LABEL[order.status]}</Badge>
          {canEditOrders(user.role) && order.status === "draft" && (
            <Button component={Link} to={`/orders/${order.id}/edit`}>
              Править черновик
            </Button>
          )}
        </Group>
      </Group>
      <Paper withBorder p="md">
        <Text>Договор: {order.contract_number || "—"} от {order.contract_date}</Text>
        <Text>Запуск: {order.launch_date}</Text>
        <Text>Приоритет заказа: {order.priority}</Text>
        {order.notes && <Text mt="xs">{order.notes}</Text>}
      </Paper>
      <Table.ScrollContainer minWidth={640}>
        <Table>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Вид</Table.Th>
              <Table.Th>Кол-во</Table.Th>
              <Table.Th>м²</Table.Th>
              <Table.Th>м.пог</Table.Th>
              <Table.Th>Приоритет</Table.Th>
              <Table.Th>Коэф.</Table.Th>
              <Table.Th>Комментарий</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {order.items.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td>{itemLabel(types, item.item_type)}</Table.Td>
                <Table.Td>{item.qty}</Table.Td>
                <Table.Td>{item.area_m2}</Table.Td>
                <Table.Td>{item.linear_m}</Table.Td>
                <Table.Td>{item.priority}</Table.Td>
                <Table.Td>{item.constructor_coeff}</Table.Td>
                <Table.Td>{item.comment || "—"}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
      <Text>
        Итого {order.total_qty} изд., {order.total_area_m2} м²
      </Text>
      <Button variant="subtle" component={Link} to="/orders">
        К списку
      </Button>
    </Stack>
  );
}
