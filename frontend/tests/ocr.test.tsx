import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "antd";
import OcrAssistant from "../src/features/OcrAssistant";
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("previews OCR output and applies only after explicit user review without saving equipment", async () => {
  const apply = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            engine: "EasyOCR (CPU)",
            raw_text: "ARDUINO UNO R3",
            confidence: 0.97,
            suggestions: {
              name: "ARDUINO UNO R3",
              code_candidate: "UNO-R3",
              description: "ARDUINO UNO R3",
            },
            warning: "Kiểm tra trước khi lưu",
          }),
          { status: 200 },
        ),
    ),
  );
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    writable: true,
    value: vi.fn(() => "blob:label"),
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    writable: true,
    value: vi.fn(),
  });
  const user = userEvent.setup();
  render(
    <App>
      <OcrAssistant apply={apply} />
    </App>,
  );
  await user.click(
    screen.getByRole("button", { name: "Quét ảnh nhãn thiết bị" }),
  );
  expect(
    screen.getByRole("button", { name: "Áp dụng gợi ý vào biểu mẫu" }),
  ).toBeDisabled();
  await user.upload(
    screen.getByLabelText("Ảnh nhãn cho OCR"),
    new File(["label"], "label.png", { type: "image/png" }),
  );
  expect(
    await screen.findByAltText("Nhãn thiết bị cần đọc OCR"),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Đọc ảnh bằng OCR" }));
  const name = await screen.findByRole("textbox", { name: "Tên thiết bị" });
  expect(name).toHaveValue("ARDUINO UNO R3");
  expect(apply).not.toHaveBeenCalled();
  await user.clear(name);
  await user.type(name, "Arduino đã kiểm tra");
  await user.click(
    screen.getByRole("button", { name: "Áp dụng gợi ý vào biểu mẫu" }),
  );
  expect(apply).toHaveBeenCalledWith({
    name: "Arduino đã kiểm tra",
    code: "UNO-R3",
    description: "ARDUINO UNO R3",
  });
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/ai/ocr/equipment",
    expect.anything(),
  );
});
