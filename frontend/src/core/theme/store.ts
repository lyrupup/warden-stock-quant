import { create } from "zustand";
import { persist } from "zustand/middleware";

export type TTheme = "light" | "dark";

type TThemeState = {
  theme: TTheme;
  setTheme: (theme: TTheme) => void;
  toggle: () => void;
};

export const useThemeStore = create<TThemeState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      setTheme: (theme) => set({ theme }),
      toggle: () => set({ theme: get().theme === "dark" ? "light" : "dark" }),
    }),
    { name: "wsq-theme" },
  ),
);
