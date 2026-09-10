import { useEffect, useState } from "react";
import { AppShell, Badge, Container, Group, Text, Title } from "@mantine/core";

export function App() {
  const [health, setHealth] = useState<"checking" | "ok" | "down">("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? setHealth("ok") : setHealth("down")))
      .catch(() => setHealth("down"));
  }, []);

  return (
    <AppShell header={{ height: 56 }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Title order={4}>MONZA Production Planner</Title>
          <Badge color={health === "ok" ? "green" : health === "down" ? "red" : "gray"}>
            API {health === "checking" ? "…" : health}
          </Badge>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        <Container size="sm">
          <Title order={2}>Планирование мебельного производства</Title>
          <Text mt="sm" c="dimmed">
            Каркас фазы 1: форма заказа, участки и движок появятся следующими шагами. Откройте
            этот экран на ПК или телефоне — вёрстка адаптивная.
          </Text>
        </Container>
      </AppShell.Main>
    </AppShell>
  );
}
