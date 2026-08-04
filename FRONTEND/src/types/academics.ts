export type RubricLevel = "exceeding_expectation" | "meeting_expectation" | "approaching_expectation" | "below_expectation";

export const RUBRIC_LABELS: Record<RubricLevel, string> = {
  exceeding_expectation: "EE",
  meeting_expectation: "ME",
  approaching_expectation: "AE",
  below_expectation: "BE",
};

export interface LearningArea {
  id: string;
  name: string;
}

export interface RubricEntry {
  id: string;
  student_id: string;
  learning_area_id: string;
  term: string;
  strand: string | null;
  level: RubricLevel;
  recorded_by: string;
  created_at: string;
}

export interface RubricEntryCreate {
  student_id: string;
  learning_area_id: string;
  term: string;
  strand?: string | null;
  level: RubricLevel;
}

export interface ReportCard {
  id: string;
  student_id: string;
  term: string;
  compiled_data: Record<string, { strand: string | null; level: RubricLevel }[]>;
  generated_at: string;
}
