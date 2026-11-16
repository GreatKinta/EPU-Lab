import { useEffect } from "react";
export function useShortcuts(actions: {
  create?: () => void;
  save?: () => void;
  search?: () => void;
}) {
  useEffect(() => {
    function handler(event: KeyboardEvent) {
      if (!event.altKey || event.ctrlKey || event.metaKey || event.repeat)
        return;
      const key = event.key.toLowerCase();
      const action =
        key === "n"
          ? actions.create
          : key === "s"
            ? actions.save
            : key === "f"
              ? actions.search
              : undefined;
      if (action) {
        event.preventDefault();
        action();
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [actions.create, actions.save, actions.search]);
}
export function readColumns(): string[] {
  try {
    const value = JSON.parse(
      localStorage.getItem("labchain-columns") || "null",
    );
    return Array.isArray(value) && value.every((x) => typeof x === "string")
      ? value
      : ["code", "product_type", "stock", "price", "updated_at"];
  } catch {
    return ["code", "product_type", "stock", "price", "updated_at"];
  }
}
