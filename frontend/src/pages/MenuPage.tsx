import { useCallback, useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import {
  deleteSelections,
  getMenu,
  getMenuEnabled,
  getSelections,
  saveSelections
} from "../api";
import {
  buildSavePayload,
  CATEGORIES,
  type Category,
  DAY_LABELS,
  DAY_SHORT,
  type MenuData,
  NO_OPTION_LABELS,
  parseMenuData
} from "../legacy/menuLogic";
import { useAppState } from "../state";
import type { Day, SelectionPayload } from "../types";

const DAYS: Day[] = ["mon", "tue", "wed", "thu", "fri"];

const CATEGORY_META: { category: Category; icon: string; title: string }[] = [
  { category: "breakfast", icon: "/src/breakfast.png", title: "Завтрак/Breakfast" },
  { category: "soup", icon: "/src/soup.png", title: "Суп/Soup" },
  { category: "hot", icon: "/src/hot.png", title: "Основное блюдо/Main course" },
  { category: "side", icon: "/src/garnish.png", title: "Гарнир/Side dish" },
  { category: "salad", icon: "/src/salad.png", title: "Салат/Salad" },
  { category: "dessert", icon: "/src/dessert.png", title: "Десерт/Dessert" }
];

function emptySelectionsMap(): Partial<Record<Category, string>> {
  const m: Partial<Record<Category, string>> = {};
  for (const c of CATEGORIES) {
    m[c] = NO_OPTION_LABELS[c];
  }
  return m;
}

export function MenuPage() {
  const navigate = useNavigate();
  const { userLogin, isDark, setThemeDark } = useAppState();
  const [menuDisabled, setMenuDisabled] = useState(false);
  const [loadingHidden, setLoadingHidden] = useState(false);
  const [parsedMenu, setParsedMenu] = useState<MenuData>(() => ({} as MenuData));
  const [activeDay, setActiveDay] = useState<Day>("mon");
  const [selectionsByDay, setSelectionsByDay] = useState<
    Record<Day, Partial<Record<Category, string>>>
  >({
    mon: {},
    tue: {},
    wed: {},
    thu: {},
    fri: {}
  });
  const [daySaved, setDaySaved] = useState<Record<Day, boolean>>({
    mon: false,
    tue: false,
    wed: false,
    thu: false,
    fri: false
  });
  const [notification, setNotification] = useState({ message: "", show: false });
  const [busy, setBusy] = useState(false);

  const showNotification = useCallback((message: string) => {
    setNotification({ message, show: true });
    window.setTimeout(() => setNotification((n) => ({ ...n, show: false })), 3000);
  }, []);

  const applySelectionsFromApi = useCallback((day: Day, selections: SelectionPayload | null) => {
    const next: Partial<Record<Category, string>> = {};
    for (const c of CATEGORIES) {
      const v = selections?.[c];
      next[c] = v && String(v).trim() ? String(v).trim() : NO_OPTION_LABELS[c];
    }
    setSelectionsByDay((prev) => ({ ...prev, [day]: next }));
  }, []);

  const checkAllDaysCompleted = useCallback(
    (saved: Record<Day, boolean>) => {
      if (DAYS.every((d) => saved[d])) {
        window.setTimeout(() => navigate("/feedback"), 1000);
      }
    },
    [navigate]
  );

  useEffect(() => {
    if (!userLogin) return;

    let cancelled = false;

    async function init() {
      setLoadingHidden(false);
      try {
        try {
          const enabled = await getMenuEnabled();
          if (!enabled.enabled) {
            setMenuDisabled(true);
          }
        } catch {
          // как в HTML: при ошибке считаем меню доступным
        }

        const rows = await getMenu();
        if (cancelled) return;
        setParsedMenu(parseMenuData(rows));

        const results = await Promise.all(DAYS.map((d) => getSelections(d)));
        if (cancelled) return;

        const saved: Record<Day, boolean> = {} as Record<Day, boolean>;
        DAYS.forEach((d, i) => {
          saved[d] = results[i].selections != null;
        });
        setDaySaved(saved);

        const sel: Record<Day, Partial<Record<Category, string>>> = {
          mon: {},
          tue: {},
          wed: {},
          thu: {},
          fri: {}
        };
        DAYS.forEach((d, i) => {
          const s = results[i].selections;
          for (const c of CATEGORIES) {
            const v = s?.[c];
            sel[d][c] = v && String(v).trim() ? String(v).trim() : NO_OPTION_LABELS[c];
          }
        });
        setSelectionsByDay(sel);

        showNotification("Menu loaded successfully!");
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Load error";
        showNotification(`Error: ${msg}`);
      } finally {
        if (!cancelled) {
          window.setTimeout(() => setLoadingHidden(true), 200);
        }
      }
    }

    void init();
    return () => {
      cancelled = true;
    };
  }, [userLogin, showNotification]);

  const summaryHtml = useMemo(() => {
    const dayLabel = DAY_LABELS[activeDay];
    const chosen: string[] = [];
    for (const cat of CATEGORIES) {
      const label = selectionsByDay[activeDay]?.[cat] ?? NO_OPTION_LABELS[cat];
      chosen.push(label);
    }
    const chosenText = chosen.length ? chosen.join(", ") : "nothing";
    return (
      <>
        For <span className="summary-highlight">{dayLabel}</span> you selected:{" "}
        <span className="summary-highlight">{chosenText}</span>. Confirm?
      </>
    );
  }, [activeDay, selectionsByDay]);

  async function onSelectDay(day: Day) {
    if (menuDisabled) {
      return;
    }
    const enabled = await getMenuEnabled();
    if (!enabled.enabled) {
      setMenuDisabled(true);
      return;
    }

    setLoadingHidden(false);
    try {
      const { selections } = await getSelections(day);
      applySelectionsFromApi(day, selections);
      setActiveDay(day);
    } catch {
      showNotification("Failed to load day selections");
    } finally {
      window.setTimeout(() => setLoadingHidden(true), 200);
    }
  }

  async function onPickOption(category: Category, label: string) {
    if (menuDisabled) return;
    const enabled = await getMenuEnabled();
    if (!enabled.enabled) {
      setMenuDisabled(true);
      return;
    }
    setSelectionsByDay((prev) => ({
      ...prev,
      [activeDay]: { ...prev[activeDay], [category]: label }
    }));
  }

  async function onSave() {
    if (menuDisabled) return;
    const enabled = await getMenuEnabled();
    if (!enabled.enabled) {
      setMenuDisabled(true);
      return;
    }

    const payload = buildSavePayload(selectionsByDay[activeDay] ?? {}) as SelectionPayload;
    setBusy(true);
    setLoadingHidden(false);
    try {
      await saveSelections(activeDay, payload);
      setDaySaved((prev) => {
        const next = { ...prev, [activeDay]: true };
        checkAllDaysCompleted(next);
        return next;
      });
      showNotification("Your choices have been saved!");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Save failed";
      showNotification(`Failed to save: ${msg}`);
    } finally {
      setBusy(false);
      window.setTimeout(() => setLoadingHidden(true), 300);
    }
  }

  async function onReset() {
    if (menuDisabled) return;
    const enabled = await getMenuEnabled();
    if (!enabled.enabled) {
      setMenuDisabled(true);
      return;
    }

    const label = DAY_SHORT[activeDay];
    if (!window.confirm(`Are you sure you want to clear the saved selections for ${label}?`)) {
      return;
    }

    setBusy(true);
    setLoadingHidden(false);
    try {
      const result = await deleteSelections(activeDay);
      setSelectionsByDay((prev) => ({
        ...prev,
        [activeDay]: emptySelectionsMap()
      }));
      setDaySaved((prev) => ({ ...prev, [activeDay]: false }));
      if (result.deleted) {
        showNotification(`Saved selections for ${label} have been deleted from the table.`);
      } else {
        showNotification(`Saved selections for ${label} have been cleared (row not found in table).`);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Delete failed";
      showNotification(msg);
    } finally {
      setBusy(false);
      window.setTimeout(() => setLoadingHidden(true), 300);
    }
  }

  function renderDayBtn(d: Day) {
    const saved = daySaved[d];
    return (
      <div
        key={d}
        className={`day-btn ${activeDay === d ? "active" : ""} ${!saved ? "no-selections" : ""}`}
        data-day={d}
        data-label={DAY_SHORT[d]}
        role="button"
        tabIndex={0}
        onClick={() => void onSelectDay(d)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            void onSelectDay(d);
          }
        }}
      >
        {saved ? <img src="/src/done.png" alt="Done" /> : DAY_SHORT[d]}
      </div>
    );
  }

  function renderThemeSwitch(id: string) {
    return (
      <label className="theme-switch" htmlFor={id}>
        <input
          id={id}
          type="checkbox"
          checked={isDark}
          onChange={(e) => setThemeDark(e.target.checked)}
        />
        <span className="theme-slider">
          <span className="theme-thumb">
            <span className="theme-thumb-icon sun">{"\u2600\uFE0F"}</span>
            <span className="theme-thumb-icon moon">{"\uD83C\uDF19"}</span>
          </span>
        </span>
      </label>
    );
  }

  useEffect(() => {
    document.body.classList.toggle("menu-disabled", menuDisabled);
    return () => document.body.classList.remove("menu-disabled");
  }, [menuDisabled]);

  if (!userLogin) {
    return <Navigate to="/" replace />;
  }

  return (
    <>
      <div className={`loading-overlay ${loadingHidden ? "hidden" : ""}`}>
        <div className="loading-content">
          <div className="loading-spinner" />
          <div className="loading-text">{busy ? "Saving..." : "Loading menu..."}</div>
        </div>
      </div>

      <div className="container">
        <div className="app-header">
          <div className="language-theme">{renderThemeSwitch("themeToggle")}</div>
          <div className="navigation-arrows">
            <img
              src={isDark ? "/src/emblem_dark.png" : "/src/emblem.png"}
              alt="Emblem"
              className="emblem-img"
            />
          </div>
          <div className="nav-buttons">{DAYS.map(renderDayBtn)}</div>
        </div>

        <div className={`menu-container ${loadingHidden ? "" : "loading"}`} id="menuContainer">
          {CATEGORY_META.map(({ category, icon, title }) => {
            const items = parsedMenu[activeDay]?.[category] ?? [];
            const selected =
              selectionsByDay[activeDay]?.[category] ?? NO_OPTION_LABELS[category];
            const noLabel = NO_OPTION_LABELS[category];
            return (
              <div className="menu-category" data-category={category} key={category}>
                <div className="category-header">
                  <div className="category-icon">
                    <img src={icon} alt={category} />
                  </div>
                  <div className="category-title">{title}</div>
                </div>
                <div className="options-grid">
                  <div
                    className={`option-item ${selected === noLabel ? "selected" : ""}`}
                    data-value={`no-${category}`}
                    role="button"
                    tabIndex={0}
                    onClick={() => void onPickOption(category, noLabel)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        void onPickOption(category, noLabel);
                      }
                    }}
                  >
                    <div className={`option-radio ${selected === noLabel ? "selected" : ""}`} />
                    <div className="option-label">{noLabel}</div>
                  </div>
                  {items.map((itemText, index) => (
                    <div
                      key={`${category}-${index}`}
                      className={`option-item ${selected === itemText ? "selected" : ""}`}
                      data-value={`${category}-${activeDay}-${index}`}
                      role="button"
                      tabIndex={0}
                      onClick={() => void onPickOption(category, itemText)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          void onPickOption(category, itemText);
                        }
                      }}
                    >
                      <div className={`option-radio ${selected === itemText ? "selected" : ""}`} />
                      <div className="option-label">{itemText}</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <div className="gradient-bg">
          <div className="footer-row-top">
            <div className="language-theme">{renderThemeSwitch("themeToggleBottom")}</div>
            <div className="navigation-arrows">
              <img
                src={isDark ? "/src/emblem_dark.png" : "/src/emblem.png"}
                alt="Emblem"
                className="emblem-img"
              />
            </div>
            <div className="nav-buttons">{DAYS.map(renderDayBtn)}</div>
          </div>
          <div className="footer-row-bottom">
            <div className="summary-text" id="summaryText">
              {summaryHtml}
            </div>
            <div className="footer-actions">
              <button type="button" className="save-button" id="saveButton" onClick={() => void onSave()}>
                Сохранить/Save
              </button>
              <button
                type="button"
                className="reset-button"
                id="resetButton"
                title="Reset day"
                onClick={() => void onReset()}
              >
                ↻
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className={`notification${notification.show ? " show" : ""}`}>{notification.message}</div>

      <div className={`menu-disabled-overlay ${menuDisabled ? "" : "hidden"}`} id="menuDisabledOverlay">
        <div className="menu-disabled-modal">
          <h2>Меню временно недоступно / Menu Temporarily Unavailable</h2>
          <p>В данный момент невозможно выбрать блюда! Пожалуйста, попробуйте позже!</p>
          <p>It is currently impossible to select dishes! Please try again later!</p>
        </div>
      </div>
    </>
  );
}
