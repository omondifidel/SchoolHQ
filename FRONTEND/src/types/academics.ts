export type RevenueCategory = "tuition" | "uniform" | "feeding_programme" | "transport" | "other";
export type InvoiceStatus = "unpaid" | "partially_paid" | "paid" | "overdue";

export interface Invoice {
  id: string;
  student_id: string;
  category: RevenueCategory;
  term: string;
  amount_due: number;
  amount_paid: number;
  status: InvoiceStatus;
  due_date: string | null;
  created_at: string;
}

export interface InvoiceCreate {
  student_id: string;
  category: RevenueCategory;
  term: string;
  amount_due: number;
  due_date?: string | null;
}

export interface UnreconciledTransaction {
  id: string;
  mpesa_receipt_number: string;
  phone_number: string;
  amount: number;
  paid_at: string;
}