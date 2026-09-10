import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Stack, Table, Text, Title } from "@mantine/core";
import { api, type PlanSlot } from "../api";
import { CENTER_LABEL } from "../labels";

export function PlanPage() {
  const [rows, setRows] = useState<PlanSlot[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api<PlanSlot[]>("/api/plan")
      .then(setRows)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <Stack>
      <div>
        <Title order={2}>План</Title>
        <Text c="dimmed" size="sm">
          Черновик автоплана: рабочие дни 5/2, мощность «X за N дней», КПД конструктора. Монитор и Гант — позже.
        </Text>
      </div>
      {error && <Text c="red">{error}</Text>}
      {rows.length === 0 && !error ? (
        <Text c="dimmed">Нет заказов в очереди. Добавьте заказ не черновиком.</Text>
      ) : (
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
              {rows.map((row) => (
                <Table.Tr key={`${row.item_id}-${row.center_code}`}>
                  <Table.Td>
                    <Link to={`/orders/${row.order_id}`}>{row.customer}</Link>
                  </Table.Td>
                  <Table.Td>#{row.item_id}</Table.Td>
                  <Table.Td>{CENTER_LABEL[row.center_code] ?? row.center_code}</Table.Td>
                  <Table.Td>{row.volume}</Table.Td>
                  <Table.Td>{row.start}</Table.Td>
                  <Table.Td>{row.finish}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Stack>
  );
}
