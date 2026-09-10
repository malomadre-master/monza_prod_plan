import { useEffect, useState } from "react";
import { Button, Group, NumberInput, Paper, PasswordInput, Select, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { api, type Role, type User } from "../api";
import { ROLE_LABEL } from "../labels";

const ROLE_OPTIONS = (Object.keys(ROLE_LABEL) as Role[]).map((value) => ({
  value,
  label: ROLE_LABEL[value],
}));

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("planner");
  const [efficiency, setEfficiency] = useState(1);
  const [saving, setSaving] = useState(false);

  function reload() {
    api<User[]>("/api/users").then(setUsers);
  }

  useEffect(() => {
    reload();
  }, []);

  async function createUser(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await api("/api/users", {
        method: "POST",
        body: JSON.stringify({
          username,
          display_name: displayName,
          password,
          role,
          is_active: true,
          efficiency: String(efficiency),
        }),
      });
      setUsername("");
      setDisplayName("");
      setPassword("");
      setEfficiency(1);
      notifications.show({ color: "green", message: "Сотрудник добавлен" });
      reload();
    } catch (error) {
      notifications.show({ color: "red", message: (error as Error).message });
    } finally {
      setSaving(false);
    }
  }

  async function saveEfficiency(user: User, value: number) {
    try {
      const updated = await api<User>(`/api/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ efficiency: String(value) }),
      });
      setUsers((current) => current.map((row) => (row.id === user.id ? updated : row)));
    } catch (error) {
      notifications.show({ color: "red", message: (error as Error).message });
    }
  }

  return (
    <Stack>
      <Title order={2}>Сотрудники</Title>
      <Paper withBorder p="md">
        <form onSubmit={createUser}>
          <Group grow align="flex-end" wrap="wrap">
            <TextInput label="Логин" value={username} onChange={(e) => setUsername(e.currentTarget.value)} required />
            <TextInput label="Имя" value={displayName} onChange={(e) => setDisplayName(e.currentTarget.value)} required />
            <PasswordInput label="Пароль" value={password} onChange={(e) => setPassword(e.currentTarget.value)} required />
            <Select label="Роль" data={ROLE_OPTIONS} value={role} onChange={(v) => setRole((v as Role) || "planner")} />
            <NumberInput
              label="КПД"
              description="1 = норма"
              min={0.1}
              max={2}
              step={0.1}
              decimalScale={2}
              value={efficiency}
              onChange={(v) => setEfficiency(Number(v) || 1)}
            />
            <Button type="submit" loading={saving}>
              Добавить
            </Button>
          </Group>
        </form>
      </Paper>
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Логин</Table.Th>
            <Table.Th>Имя</Table.Th>
            <Table.Th>Роль</Table.Th>
            <Table.Th>КПД</Table.Th>
            <Table.Th>Статус</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {users.map((user) => (
            <Table.Tr key={user.id}>
              <Table.Td>{user.username}</Table.Td>
              <Table.Td>{user.display_name}</Table.Td>
              <Table.Td>{ROLE_LABEL[user.role]}</Table.Td>
              <Table.Td w={140}>
                <NumberInput
                  size="xs"
                  min={0.1}
                  max={2}
                  step={0.1}
                  decimalScale={2}
                  value={Number(user.efficiency ?? 1)}
                  onChange={(v) => {
                    const next = Number(v);
                    if (next > 0) void saveEfficiency(user, next);
                  }}
                />
              </Table.Td>
              <Table.Td>
                <Text c={user.is_active ? "green" : "red"}>{user.is_active ? "активен" : "выключен"}</Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  );
}
