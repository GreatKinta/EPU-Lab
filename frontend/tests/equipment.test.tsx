import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App, ConfigProvider } from "antd";
import { MemoryRouter } from "react-router-dom";
import EquipmentPage from "../src/features/EquipmentPage";
import { readColumns, useShortcuts } from "../src/lib/shortcuts";
vi.mock("../src/features/auth", () => ({
  useAuth: () => ({ user: { role: "staff" } }),
}));
const item = {
  id: "a",
  code: "EQ-001",
  name: "Arduino Uno",
  product_type: "Điện tử",
  quantity_total: 5,
  quantity_reserved: 1,
  quantity_available: 4,
  unit: "cái",
  price: "150000",
  description: "Thiết bị thử",
  image_path: null,
  created_at: "2026-11-11T01:00:00Z",
  updated_at: "2026-11-11T01:00:00Z",
};
function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <ConfigProvider>
          <App>
            <EquipmentPage />
          </App>
        </ConfigProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({ items: [item], total: 30, page: 1, page_size: 10 }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
    ),
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
describe("Equipment workflow", () => {
  it("loads server data, resets selection on search and requests page size 15", async () => {
    mount();
    await screen.findByText("Arduino Uno");
    const user = userEvent.setup();
    const checks = screen.getAllByRole("checkbox");
    await user.click(checks[1]);
    expect(await screen.findByText("Đã chọn 1 thiết bị")).toBeInTheDocument();
    await user.type(
      screen.getByRole("textbox", { name: "Tìm thiết bị" }),
      "Uno",
    );
    await waitFor(() =>
      expect(screen.queryByText("Đã chọn 1 thiết bị")).not.toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("search=Uno"),
        expect.anything(),
      ),
    );
    const pageSize = document.querySelector(
      ".ant-pagination-options-size-changer",
    )!;
    await user.click(pageSize);
    await user.click(await screen.findByText("15 / page"));
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("page_size=15"),
        expect.anything(),
      ),
    );
  });
  it("persists column choice and supports keyboard new/save/search with cleanup", async () => {
    const view = mount();
    await screen.findByText("Arduino Uno");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Cột hiển thị" }));
    const code = await screen.findByRole("checkbox", { name: "Mã thiết bị" });
    await user.click(code);
    expect(JSON.parse(localStorage.getItem("labchain-columns")!)).not.toContain(
      "code",
    );
    fireEvent.keyDown(window, { key: "f", altKey: true });
    expect(screen.getByRole("textbox", { name: "Tìm thiết bị" })).toHaveFocus();
    fireEvent.keyDown(window, { key: "n", altKey: true });
    expect(
      await screen.findByText("Mã thiết bị", { selector: "label" }),
    ).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "s", altKey: true });
    expect(await screen.findByText("Nhập tên thiết bị")).toBeInTheDocument();
    view.unmount();
  });
  it("recovers corrupted stored preferences", () => {
    localStorage.setItem("labchain-columns", "broken");
    expect(readColumns()).toContain("code");
  });
});
it("removes keyboard handlers on unmount", () => {
  const create = vi.fn();
  function Harness() {
    useShortcuts({ create });
    return null;
  }
  const view = render(<Harness />);
  fireEvent.keyDown(window, { key: "n", altKey: true });
  expect(create).toHaveBeenCalledTimes(1);
  view.unmount();
  fireEvent.keyDown(window, { key: "n", altKey: true });
  expect(create).toHaveBeenCalledTimes(1);
});
