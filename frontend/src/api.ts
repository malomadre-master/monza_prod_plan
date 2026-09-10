const TOKEN_KEY = "monza_token";

export type Role = "admin" | "planner" | "designer" | "supply" | "worker" | "observer";
export type OrderStatus = "draft" | "queued" | "in_design" | "in_production";
export type AttachmentStore = "production" | "procurement";
export type ItemType = "kitchen" | "wardrobe" | "cabinet" | "hallway" | "mirror" | "appliance" | "other";

export type User = {
  id: number;
  username: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  efficiency?: string;
};

export type OrderItem = {
  id?: number;
  item_type: ItemType;
  comment: string;
  qty: number;
  priority: number;
  constructor_coeff?: string;
  area_m2: string;
  linear_m?: string;
  procurement_needed?: boolean | null;
  construction_done_at?: string | null;
};

export type Order = {
  id: number;
  customer: string;
  contract_number: string;
  contract_date: string;
  launch_date: string;
  priority: number;
  status: OrderStatus;
  notes: string;
  created_by_id: number;
  claimed_by_id: number | null;
  claimed_by_name?: string | null;
  created_at: string;
  items: OrderItem[];
  total_area_m2: string;
  total_qty: number;
};

export type OrderListRow = {
  id: number;
  customer: string;
  contract_number: string;
  contract_date: string;
  launch_date: string;
  priority: number;
  status: OrderStatus;
  item_count: number;
  total_area_m2: string;
  created_by_name: string;
  claimed_by_id?: number | null;
  claimed_by_name?: string | null;
};

export type Attachment = {
  id: number;
  item_id: number;
  store: AttachmentStore;
  original_name: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
};

export type ItemTypeRow = { value: ItemType; label: string; coeff: string };

export type PlanSlot = {
  order_id: number;
  item_id: number;
  customer: string;
  center_code: string;
  volume: string;
  start: string;
  finish: string;
};

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    setToken(null);
    if (!path.startsWith("/api/auth/login")) {
      window.location.assign("/login");
    }
    throw new ApiError(401, "Нужна авторизация");
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep status text */
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return api<T>(path, { method: "POST", body: form, headers });
}

const INLINE_NAME = /\.(pdf|png|jpe?g|webp)$/i;

export async function openAttachment(id: number, name: string): Promise<void> {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`/api/attachments/${id}`, { headers });
  if (!response.ok) {
    throw new ApiError(response.status, "Не удалось открыть файл");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  if (INLINE_NAME.test(name)) {
    window.open(url, "_blank", "noopener,noreferrer");
    return;
  }
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
