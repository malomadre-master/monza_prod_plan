import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Paper, PasswordInput, Stack, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { api, setToken, type User } from "../api";

type LoginResponse = { access_token: string; user: User };

export function LoginPage({ onLogin }: { onLogin: (user: User) => void }) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      const data = await api<LoginResponse>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setToken(data.access_token);
      onLogin(data.user);
      navigate("/orders");
    } catch (error) {
      notifications.show({ color: "red", title: "Вход не выполнен", message: (error as Error).message });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Stack align="center" justify="center" mih="80vh" px="md">
      <Paper withBorder p="lg" radius="md" maw={420} w="100%">
        <Title order={3} mb="xs">
          MONZA
        </Title>
        <Text c="dimmed" mb="md">
          Планирование производства. Войдите со своей учёткой.
        </Text>
        <form onSubmit={submit}>
          <Stack>
            <TextInput label="Логин" value={username} onChange={(e) => setUsername(e.currentTarget.value)} required />
            <PasswordInput label="Пароль" value={password} onChange={(e) => setPassword(e.currentTarget.value)} required />
            <Button type="submit" loading={loading}>
              Войти
            </Button>
          </Stack>
        </form>
      </Paper>
    </Stack>
  );
}
