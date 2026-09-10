import { useState } from "react";
import { Button, FileButton, Group, Radio, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  api,
  apiUpload,
  openAttachment,
  type Attachment,
  type AttachmentStore,
  type Order,
  type OrderItem,
  type User,
} from "../api";

const ACCEPT = ".doc,.docx,.pdf,.dxf,.dwg,.xls,.xlsx,.png,.jpg,.jpeg,.webp";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
}

function DropZone({
  disabled,
  onFiles,
}: {
  disabled: boolean;
  onFiles: (files: File[]) => void;
}) {
  const [over, setOver] = useState(false);
  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        if (disabled) return;
        onFiles(Array.from(event.dataTransfer.files));
      }}
      style={{
        border: `1px dashed ${over ? "var(--mantine-color-blue-6)" : "var(--mantine-color-gray-4)"}`,
        borderRadius: 8,
        padding: 12,
        minHeight: 72,
        background: over ? "var(--mantine-color-blue-0)" : "transparent",
        opacity: disabled ? 0.6 : 1,
      }}
    >
      <Text size="sm" c="dimmed">
        Перетащите файлы сюда или выберите. Word, PDF, DXF/DWG, Excel, картинки. До 50 МБ.
      </Text>
      <FileButton disabled={disabled} multiple accept={ACCEPT} onChange={(files) => onFiles(files)}>
        {(props) => (
          <Button {...props} size="xs" variant="light" mt="xs" disabled={disabled}>
            Выбрать файлы
          </Button>
        )}
      </FileButton>
    </div>
  );
}

export function ItemDocs({
  order,
  item,
  files,
  user,
  canEdit,
  onChanged,
}: {
  order: Order;
  item: OrderItem;
  files: Attachment[];
  user: User;
  canEdit: boolean;
  onChanged: (order: Order, files: Attachment[]) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [procurement, setProcurement] = useState<string | null>(
    item.procurement_needed == null ? null : item.procurement_needed ? "yes" : "no",
  );
  const done = Boolean(item.construction_done_at);
  const editable = canEdit && !done && Boolean(item.id);
  const production = files.filter((row) => row.store === "production");
  const procurementFiles = files.filter((row) => row.store === "procurement");

  async function upload(store: AttachmentStore, incoming: File[]) {
    if (!item.id || incoming.length === 0) return;
    setBusy(true);
    try {
      let next = files;
      for (const file of incoming) {
        const form = new FormData();
        form.append("store", store);
        form.append("file", file);
        const row = await apiUpload<Attachment>(
          `/api/orders/${order.id}/items/${item.id}/attachments`,
          form,
        );
        next = [...next, row];
      }
      onChanged(order, next);
    } catch (err) {
      notifications.show({ color: "red", message: err instanceof Error ? err.message : "Ошибка загрузки" });
    } finally {
      setBusy(false);
    }
  }

  async function remove(row: Attachment) {
    setBusy(true);
    try {
      await api(`/api/attachments/${row.id}`, { method: "DELETE" });
      onChanged(
        order,
        files.filter((itemRow) => itemRow.id !== row.id),
      );
    } catch (err) {
      notifications.show({ color: "red", message: err instanceof Error ? err.message : "Не удалось удалить" });
    } finally {
      setBusy(false);
    }
  }

  async function complete() {
    if (!item.id) return;
    if (production.length === 0) {
      notifications.show({ color: "red", message: "Нужен хотя бы один производственный документ" });
      return;
    }
    if (procurement == null) {
      notifications.show({ color: "red", message: "Выберите: закупка нужна или не нужна" });
      return;
    }
    if (procurement === "yes" && procurementFiles.length === 0) {
      const ok = window.confirm("Закупка нужна, но в «Закупке» нет файлов. Всё равно завершить изделие?");
      if (!ok) return;
    }
    setBusy(true);
    try {
      const updated = await api<Order>(`/api/orders/${order.id}/items/${item.id}/complete`, {
        method: "POST",
        body: JSON.stringify({ procurement_needed: procurement === "yes" }),
      });
      onChanged(updated, files);
    } catch (err) {
      notifications.show({ color: "red", message: err instanceof Error ? err.message : "Не удалось завершить" });
    } finally {
      setBusy(false);
    }
  }

  void user;

  return (
    <Stack gap="sm" mt="sm">
      <Group align="flex-start" grow>
        <Stack gap={6}>
          <Text fw={600} size="sm">
            Производство
          </Text>
          <FileList files={production} canDelete={editable} onOpen={openAttachment} onDelete={remove} />
          {editable && <DropZone disabled={busy} onFiles={(incoming) => void upload("production", incoming)} />}
        </Stack>
        <Stack gap={6}>
          <Text fw={600} size="sm">
            Закупка
          </Text>
          <FileList files={procurementFiles} canDelete={editable} onOpen={openAttachment} onDelete={remove} />
          {editable && <DropZone disabled={busy} onFiles={(incoming) => void upload("procurement", incoming)} />}
        </Stack>
      </Group>
      {done ? (
        <Text size="sm" c="teal">
          Изделие готово. Закупка {item.procurement_needed ? "нужна → Комплектация" : "не нужна → сразу на Пилу"}.
        </Text>
      ) : editable ? (
        <Group>
          <Radio.Group value={procurement} onChange={setProcurement} label="Закупка">
            <Group mt={6}>
              <Radio value="yes" label="нужна" />
              <Radio value="no" label="не нужна" />
            </Group>
          </Radio.Group>
          <Button mt="lg" loading={busy} onClick={() => void complete()}>
            Изделие готово
          </Button>
        </Group>
      ) : null}
    </Stack>
  );
}

function FileList({
  files,
  canDelete,
  onOpen,
  onDelete,
}: {
  files: Attachment[];
  canDelete: boolean;
  onOpen: (id: number, name: string) => Promise<void>;
  onDelete: (row: Attachment) => void;
}) {
  if (files.length === 0) {
    return (
      <Text size="xs" c="dimmed">
        Файлов нет
      </Text>
    );
  }
  return (
    <Stack gap={4}>
      {files.map((row) => (
        <Group key={row.id} justify="space-between" gap="xs">
          <Button
            variant="subtle"
            size="compact-xs"
            onClick={() =>
              void onOpen(row.id, row.original_name).catch((err: Error) =>
                notifications.show({ color: "red", message: err.message }),
              )
            }
          >
            {row.original_name} · {formatSize(row.size_bytes)}
          </Button>
          {canDelete && (
            <Button size="compact-xs" color="red" variant="subtle" onClick={() => onDelete(row)}>
              Удалить
            </Button>
          )}
        </Group>
      ))}
    </Stack>
  );
}
