import type { Day } from "../types";

export type Category = "breakfast" | "soup" | "hot" | "side" | "salad" | "dessert";

export const CATEGORIES: Category[] = ["breakfast", "soup", "hot", "side", "salad", "dessert"];

export const DAY_LABELS: Record<Day, string> = {
  mon: "Monday",
  tue: "Tuesday",
  wed: "Wednesday",
  thu: "Thursday",
  fri: "Friday"
};

export const DAY_SHORT: Record<Day, string> = {
  mon: "Mon",
  tue: "Tue",
  wed: "Wed",
  thu: "Thu",
  fri: "Fri"
};

const dayMapping: Record<string, Day> = {
  Monday: "mon",
  Tuesday: "tue",
  Wednesday: "wed",
  Thursday: "thu",
  Friday: "fri",
  Понедельник: "mon",
  Вторник: "tue",
  Среда: "wed",
  Четверг: "thu",
  Пятница: "fri",
  ПН: "mon",
  ВТ: "tue",
  СР: "wed",
  ЧТ: "thu",
  ПТ: "fri"
};

const categoryMapping: Record<number, Category> = {
  1: "breakfast",
  2: "soup",
  3: "hot",
  4: "side",
  5: "salad",
  6: "dessert"
};

export type MenuData = Record<Day, Record<Category, string[]>>;

export const NO_OPTION_LABELS: Record<Category, string> = {
  breakfast: "Не нужно/No breakfast",
  soup: "Не нужно/No soup",
  hot: "Не нужно/No main course",
  side: "Не нужно/No side dish",
  salad: "Не нужно/No salad",
  dessert: "Не нужно/No dessert"
};

export function parseMenuData(data: string[][]): MenuData {
  const menuData = {} as MenuData;
  if (!data?.length) {
    return menuData;
  }

  let currentDay: Day | null = null;

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    if (!row?.length) continue;

    const dayName = row[0]?.trim();
    if (dayName && dayMapping[dayName]) {
      currentDay = dayMapping[dayName];
      if (!menuData[currentDay]) {
        menuData[currentDay] = {
          breakfast: [],
          soup: [],
          hot: [],
          side: [],
          salad: [],
          dessert: []
        };
      }
    }

    if (!currentDay || !menuData[currentDay]) continue;

    for (let catIndex = 1; catIndex <= 6; catIndex++) {
      const category = categoryMapping[catIndex];
      const cellValue = row[catIndex];
      if (cellValue?.trim()) {
        menuData[currentDay][category].push(cellValue.trim());
      }
    }
  }

  return menuData;
}

export function isNoOptionLabel(label: string): boolean {
  const lower = label.toLowerCase();
  return (
    lower.includes("no ") ||
    lower.includes("not needed") ||
    lower.includes("не нужно")
  );
}

export function buildSavePayload(selectionsByCategory: Partial<Record<Category, string>>): Record<string, string> {
  const selections: Record<string, string> = {};
  for (const category of CATEGORIES) {
    const label = selectionsByCategory[category];
    if (!label || isNoOptionLabel(label)) {
      selections[category] = "";
    } else {
      selections[category] = label;
    }
  }
  return selections;
}
