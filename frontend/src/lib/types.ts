export type Role = "student" | "staff" | "admin";
export interface User {
  id: string;
  full_name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
export interface Equipment {
  id: string;
  code: string;
  name: string;
  product_type: string;
  quantity_total: number;
  quantity_reserved: number;
  quantity_available: number;
  unit: string;
  price: string;
  description: string | null;
  image_path: string | null;
  created_at: string;
  updated_at: string;
}
export type EquipmentInput = Pick<
  Equipment,
  | "code"
  | "name"
  | "product_type"
  | "quantity_total"
  | "unit"
  | "price"
  | "description"
>;
export interface ImportResult {
  valid: boolean;
  total: number;
  imported: number;
  errors: { row: number; message: string }[];
  preview: EquipmentInput[];
}
export type LoanStatus =
  "PENDING" | "APPROVED" | "BORROWED" | "RETURNED" | "REJECTED" | "CANCELLED";
export interface ChainTransaction {
  id: string;
  event_type: string;
  operation_id: string;
  data_hash: string;
  tx_hash: string | null;
  block_number: number | null;
  status: string;
  error_message: string | null;
}
export interface Loan {
  id: string;
  code: string;
  student_id: string;
  status: LoanStatus;
  requested_at: string;
  due_at: string;
  created_at: string;
  rejection_reason: string | null;
  items: {
    equipment_id: string;
    code: string;
    name: string;
    quantity: number;
    unit: string;
  }[];
  transactions: ChainTransaction[];
  timeline?: {
    action: string;
    created_at: string;
    details: Record<string, unknown>;
  }[];
}
