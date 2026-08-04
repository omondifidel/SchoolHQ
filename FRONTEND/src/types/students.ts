export type MessageStatus = "queued" | "sent" | "delivered" | "failed";

export interface MessageTemplate {
  id: string;
  name: string;
  body: string;
}

export interface MessageTemplateCreate {
  name: string;
  body: string;
}

export interface BalanceReminderResponse {
  queued: number;
  detail: string;
}

export interface MessageLogEntry {
  id: string;
  guardian_id: string;
  body: string;
  trigger_reason: string | null;
  status: MessageStatus;
  sent_at: string | null;
  created_at: string;
}