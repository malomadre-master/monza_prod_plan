import { useEffect, useState } from "react";
import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { AppShell, Burger, Button, Group, Text, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { api, getToken, setToken, type User } from "./api";
import { ROLE_LABEL, canEditOrders, canManageCalendar, canWorkAsDesigner } from "./labels";
import { CalendarPage } from "./pages/CalendarPage";
import { ConstructorPage } from "./pages/ConstructorPage";
import { LoginPage } from "./pages/LoginPage";
import { OrderFormPage } from "./pages/OrderFormPage";
import { OrderViewPage } from "./pages/OrderViewPage";
import { OrdersPage } from "./pages/OrdersPage";
import { PlanPage } from "./pages/PlanPage";
import { UsersPage } from "./pages/UsersPage";

const navStyle = ({ isActive }: { isActive: boolean }) => ({
  display: "block",
  padding: "8px 0",
  textDecoration: "none",
  fontWeight: isActive ? 700 : 500,
  color: "inherit",
});

function Protected({ user, children }: { user: User | null; children: React.ReactNode }) {
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function ConstructorRoute({ user }: { user: User | null }) {
  if (!user) return <Navigate to="/login" replace />;
  if (!canWorkAsDesigner(user.role)) return <Navigate to="/orders" replace />;
  return <ConstructorPage user={user} />;
}

function CalendarRoute({ user }: { user: User | null }) {
  if (!user) return <Navigate to="/login" replace />;
  if (!canManageCalendar(user.role)) return <Navigate to="/orders" replace />;
  return <CalendarPage />;
}

function UsersRoute({ user }: { user: User | null }) {
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/orders" replace />;
  return <UsersPage />;
}

export function App() {
  const [opened, { toggle, close }] = useDisclosure();
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    api<User>("/api/auth/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  function logout() {
    setToken(null);
    setUser(null);
    navigate("/login");
  }

  if (!ready) {
    return (
      <Text p="md" c="dimmed">
        Загрузка…
      </Text>
    );
  }

  return (
    <AppShell
      header={{ height: 56 }}
      navbar={{ width: 220, breakpoint: "sm", collapsed: { mobile: !opened } }}
      padding="md"
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Group>
            <Burger opened={opened} onClick={toggle} hiddenFrom="sm" size="sm" />
            <Title order={4}>MONZA</Title>
          </Group>
          {user && (
            <Text size="sm" visibleFrom="sm">
              {user.display_name} · {ROLE_LABEL[user.role]}
            </Text>
          )}
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="md">
        {user ? (
          <>
            <NavLink to="/plan" end onClick={close} style={navStyle}>
              План
            </NavLink>
            <NavLink to="/orders" end onClick={close} style={navStyle}>
              Заказы
            </NavLink>
            {canWorkAsDesigner(user.role) && (
              <NavLink to="/constructor" onClick={close} style={navStyle}>
                Конструктор
              </NavLink>
            )}
            {canEditOrders(user.role) && (
              <NavLink to="/orders/new" onClick={close} style={navStyle}>
                Новый заказ
              </NavLink>
            )}
            {canManageCalendar(user.role) && (
              <NavLink to="/calendar" onClick={close} style={navStyle}>
                Календарь
              </NavLink>
            )}
            {user.role === "admin" && (
              <NavLink to="/users" onClick={close} style={navStyle}>
                Сотрудники
              </NavLink>
            )}
            <Text size="sm" mt="md" hiddenFrom="sm">
              {user.display_name} · {ROLE_LABEL[user.role]}
            </Text>
            <Button mt="md" variant="light" onClick={logout}>
              Выйти
            </Button>
          </>
        ) : (
          <Text c="dimmed" size="sm">
            Войдите, чтобы работать
          </Text>
        )}
      </AppShell.Navbar>
      <AppShell.Main>
        <Routes>
          <Route path="/login" element={<LoginPage onLogin={setUser} />} />
          <Route path="/constructor" element={<ConstructorRoute user={user} />} />
          <Route
            path="/plan"
            element={
              <Protected user={user}>
                <PlanPage />
              </Protected>
            }
          />
          <Route
            path="/orders"
            element={
              <Protected user={user}>
                <OrdersPage user={user!} />
              </Protected>
            }
          />
          <Route
            path="/orders/new"
            element={
              <Protected user={user}>
                <OrderFormPage />
              </Protected>
            }
          />
          <Route
            path="/orders/:id/edit"
            element={
              <Protected user={user}>
                <OrderFormPage />
              </Protected>
            }
          />
          <Route
            path="/orders/:id"
            element={
              <Protected user={user}>
                <OrderViewPage user={user!} />
              </Protected>
            }
          />
          <Route path="/calendar" element={<CalendarRoute user={user} />} />
          <Route path="/users" element={<UsersRoute user={user} />} />
          <Route path="*" element={<Navigate to={user ? "/orders" : "/login"} replace />} />
        </Routes>
      </AppShell.Main>
    </AppShell>
  );
}
