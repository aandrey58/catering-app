export type Day = "mon" | "tue" | "wed" | "thu" | "fri";

export type SelectionPayload = {
  breakfast: string;
  soup: string;
  hot: string;
  side: string;
  salad: string;
  dessert: string;
};

export type WeeksResponse = {
  current: string;
  next: string;
  week1_enabled: boolean;
  week2_enabled: boolean;
};

export type Feedback = {
  rating: number;
  feedback_text: string;
};
