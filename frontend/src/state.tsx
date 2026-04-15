import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getMe, getAccessToken, setAccessToken } from "./api";

type AppContextValue = {
  userLogin: string;
  userNote: string;
  isDark: boolean;
  setAuth: (login: string, note: string, accessToken: string) => void;
  logout: () => void;
  setThemeDark: (dark: boolean) => void;
  toggleTheme: () => void;
};

const AppContext = createContext<AppContextValue | null>(null);

const LS_LOGIN = "userLogin";
const LS_NOTE = "userNote";
const LS_THEME = "theme";

export function AppProvider({ children }: { children: ReactNode }) {
  const [userLogin, setUserLogin] = useState(() => localStorage.getItem(LS_LOGIN) ?? "");
  const [userNote, setUserNote] = useState(() => localStorage.getItem(LS_NOTE) ?? "");
  const [isDark, setIsDark] = useState(() => localStorage.getItem(LS_THEME) === "dark");

  useEffect(() => {
    document.body.classList.toggle("dark-theme", isDark);
    const favicon = document.getElementById("favicon") as HTMLLinkElement | null;
    if (favicon) {
      favicon.href = isDark ? "/src/icon_dark.png" : "/src/icon_light.png";
    }
  }, [isDark]);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      return;
    }
    getMe()
      .then((data) => {
        setUserLogin(data.login);
        setUserNote(data.note ?? "");
        localStorage.setItem(LS_LOGIN, data.login);
        localStorage.setItem(LS_NOTE, data.note ?? "");
      })
      .catch(() => {
        setAccessToken(null);
        setUserLogin("");
        setUserNote("");
        localStorage.removeItem(LS_LOGIN);
        localStorage.removeItem(LS_NOTE);
      });
  }, []);

  const value = useMemo<AppContextValue>(
    () => ({
      userLogin,
      userNote,
      isDark,
      setAuth(login, note, accessToken) {
        setAccessToken(accessToken);
        setUserLogin(login);
        setUserNote(note);
        localStorage.setItem(LS_LOGIN, login);
        localStorage.setItem(LS_NOTE, note);
      },
      logout() {
        setAccessToken(null);
        setUserLogin("");
        setUserNote("");
        localStorage.removeItem(LS_LOGIN);
        localStorage.removeItem(LS_NOTE);
      },
      setThemeDark(dark) {
        setIsDark(dark);
        localStorage.setItem(LS_THEME, dark ? "dark" : "light");
      },
      toggleTheme() {
        setIsDark((prev) => {
          const next = !prev;
          localStorage.setItem(LS_THEME, next ? "dark" : "light");
          return next;
        });
      }
    }),
    [userLogin, userNote, isDark]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppContext);
  if (!ctx) {
    throw new Error("useAppState must be used inside AppProvider");
  }
  return ctx;
}
