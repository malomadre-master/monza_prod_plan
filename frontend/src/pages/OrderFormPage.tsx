import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Button,
  Group,
  NumberInput,
  Paper,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { api, type ItemType, type ItemTypeRow, type Order, type OrderItem } from "../api";
import { ITEM_FALLBACK } from "../labels";

type DraftItem = {
  key: string;
  item_type: ItemType;
  comment: string;
  qty: number;
  priority: number;
  area_m2: number;
};

function newItem(types: ItemTypeRow[], key = crypto.randomUUID()): DraftItem {
  const first = types[0] ?? ITEM_FALLBACK[0];
  return {
    key,
    item_type: first.value,
    comment: "",
    qty: 1,
    priority: 3,
    area_m2: 1,
  };
}

export function OrderFormPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const editing = Boolean(id);
  const [types, setTypes] = useState<ItemTypeRow[]>(ITEM_FALLBACK);
  const [customers, setCustomers] = useState<string[]>([]);
  const [customer, setCustomer] = useState("");
  const [contractNumber, setContractNumber] = useState("");
  const [contractDate, setContractDate] = useState("");
  const [launchDate, setLaunchDate] = useState("");
  const [priority, setPriority] = useState(3);
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<DraftItem[]>(() => [newItem(ITEM_FALLBACK)]);
  const [saving, setSaving] = useState<"draft" | "queued" | null>(null);

  useEffect(() => {
    api<ItemTypeRow[]>("/api/catalog/item-types").then(setTypes).catch(() => undefined);
    api<string[]>("/api/customers").then(setCustomers).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!id) return;
    api<Order>(`/api/orders/${id}`).then((order) => {
      setCustomer(order.customer);
      setContractNumber(order.contract_number);
      setContractDate(order.contract_date);
      setLaunchDate(order.launch_date);
      setPriority(order.priority);
      setNotes(order.notes);
      setItems(
        order.items.map((item) => ({
          key: crypto.randomUUID(),
          item_type: item.item_type,
          comment: item.comment,
          qty: item.qty,
          priority: item.priority,
          area_m2: Number(item.area_m2),
        })),
      );
    });
  }, [id]);

  const totals = useMemo(() => {
    const area = items.reduce((sum, item) => sum + item.area_m2, 0);
    const linear = area * 10;
    return { area, linear, qty: items.reduce((sum, item) => sum + item.qty, 0) };
  }, [items]);

  function setItem(key: string, patch: Partial<DraftItem>) {
    setItems((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  }

  function changeType(key: string, value: string | null) {
    if (!value) return;
    setItem(key, { item_type: value as ItemType });
  }

  async function save(status: "draft" | "queued") {
    if (!customer.trim() || !contractDate || !launchDate) {
      notifications.show({ color: "red", message: "Заполните заказчика и даты" });
      return;
    }
    setSaving(status);
    const payload = {
      customer: customer.trim(),
      contract_number: contractNumber.trim(),
      contract_date: contractDate,
      launch_date: launchDate,
      priority,
      status,
      notes,
      items: items.map(
        (item): OrderItem => ({
          item_type: item.item_type,
          comment: item.comment,
          qty: item.qty,
          priority: item.priority,
          area_m2: String(item.area_m2),
        }),
      ),
    };
    try {
      const order = editing
        ? await api<Order>(`/api/orders/${id}`, { method: "PUT", body: JSON.stringify(payload) })
        : await api<Order>("/api/orders", { method: "POST", body: JSON.stringify(payload) });
      notifications.show({
        color: "green",
        message: status === "draft" ? "Черновик сохранён" : "Заказ в очереди конструкторов",
      });
      navigate(`/orders/${order.id}`);
    } catch (error) {
      notifications.show({ color: "red", title: "Не сохранилось", message: (error as Error).message });
    } finally {
      setSaving(null);
    }
  }

  return (
    <Stack>
      <Title order={2}>{editing ? "Черновик заказа" : "Новый заказ"}</Title>
      <Paper withBorder p="md">
        <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
          <TextInput
            label="Заказчик"
            value={customer}
            onChange={(e) => setCustomer(e.currentTarget.value)}
            list="customer-suggest"
            required
          />
          <datalist id="customer-suggest">
            {customers.map((name) => (
              <option key={name} value={name} />
            ))}
          </datalist>
          <TextInput label="Номер договора" value={contractNumber} onChange={(e) => setContractNumber(e.currentTarget.value)} />
          <TextInput type="date" label="Дата договора" value={contractDate} onChange={(e) => setContractDate(e.currentTarget.value)} required />
          <TextInput type="date" label="Дата запуска" value={launchDate} onChange={(e) => setLaunchDate(e.currentTarget.value)} required />
          <NumberInput label="Приоритет заказа (1 — высший)" min={1} max={9} value={priority} onChange={(v) => setPriority(Number(v) || 3)} />
        </SimpleGrid>
        <Textarea mt="sm" label="Комментарий к заказу" value={notes} onChange={(e) => setNotes(e.currentTarget.value)} />
      </Paper>

      <Title order={4}>Изделия</Title>
      {items.map((item, index) => (
        <Paper key={item.key} withBorder p="md">
          <Group justify="space-between" mb="xs">
            <Text fw={600}>Изделие {index + 1}</Text>
            <Group gap="xs">
              <Button variant="light" size="xs" onClick={() => setItems((cur) => [...cur, { ...item, key: crypto.randomUUID() }])}>
                Дублировать
              </Button>
              <Button
                variant="subtle"
                color="red"
                size="xs"
                disabled={items.length === 1}
                onClick={() => setItems((cur) => cur.filter((row) => row.key !== item.key))}
              >
                Удалить
              </Button>
            </Group>
          </Group>
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="sm">
            <Select
              label="Вид"
              data={types.map((row) => ({ value: row.value, label: row.label }))}
              value={item.item_type}
              onChange={(value) => changeType(item.key, value)}
            />
            <NumberInput label="Количество" min={1} value={item.qty} onChange={(v) => setItem(item.key, { qty: Number(v) || 1 })} />
            <NumberInput
              label="м²"
              min={0.01}
              step={0.1}
              decimalScale={2}
              value={item.area_m2}
              onChange={(v) => setItem(item.key, { area_m2: Number(v) || 0 })}
            />
            <TextInput label="м.пог (м² × 10)" value={(item.area_m2 * 10).toFixed(2)} readOnly />
            <NumberInput
              label="Приоритет изделия"
              min={1}
              max={9}
              value={item.priority}
              onChange={(v) => setItem(item.key, { priority: Number(v) || 3 })}
            />
          </SimpleGrid>
          <TextInput mt="sm" label="Комментарий" value={item.comment} onChange={(e) => setItem(item.key, { comment: e.currentTarget.value })} />
        </Paper>
      ))}
      <Button variant="light" onClick={() => setItems((cur) => [...cur, newItem(types)])}>
        Добавить изделие
      </Button>

      <Paper withBorder p="md">
        <Text>
          Итого: {totals.qty} изд., {totals.area.toFixed(2)} м², {totals.linear.toFixed(2)} м.пог
        </Text>
      </Paper>

      <Group>
        <Button variant="default" loading={saving === "draft"} onClick={() => save("draft")}>
          Сохранить черновик
        </Button>
        <Button loading={saving === "queued"} onClick={() => save("queued")}>
          В очередь конструкторов
        </Button>
      </Group>
    </Stack>
  );
}
