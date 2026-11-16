import { useEffect, useState } from "react";
import {
  Alert,
  App,
  Button,
  Card,
  Input,
  Modal,
  Space,
  Typography,
} from "antd";
import { ScanOutlined } from "@ant-design/icons";
import { api } from "../lib/api";
interface Result {
  engine: string;
  raw_text: string;
  confidence: number | null;
  suggestions: {
    name: string | null;
    code_candidate: string | null;
    description: string | null;
  };
  warning: string;
}
export default function OcrAssistant({
  apply,
}: {
  apply: (values: {
    name?: string;
    code?: string;
    description?: string;
  }) => void;
}) {
  const { message } = App.useApp();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState("");
  useEffect(() => {
    if (!file) {
      setImagePreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setImagePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  async function scan() {
    if (!file) return;
    setLoading(true);
    setResult(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const data = await api<Result>("/ai/ocr/equipment", {
        method: "POST",
        body,
      });
      setResult(data);
      setName(data.suggestions.name || "");
      setCode(data.suggestions.code_candidate || "");
      setDescription(data.suggestions.description || "");
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  return (
    <>
      <Card size="small" style={{ marginBottom: 24, background: "#f2f5ec" }}>
        <Space>
          <ScanOutlined />
          <div>
            <b>Điền nhanh bằng AI OCR</b>
            <p className="muted" style={{ margin: 0 }}>
              Đọc nhãn thiết bị, kiểm tra rồi áp dụng vào biểu mẫu.
            </p>
          </div>
        </Space>
        <Button
          style={{ marginTop: 12 }}
          block
          onClick={() => {
            setOpen(true);
            setResult(null);
            setFile(null);
          }}
        >
          Quét ảnh nhãn thiết bị
        </Button>
      </Card>
      <Modal
        title="Trợ lý OCR · Đọc nhãn thiết bị"
        open={open}
        onCancel={() => setOpen(false)}
        footer={
          <Space>
            <Button onClick={() => setOpen(false)}>Hủy</Button>
            <Button loading={loading} disabled={!file} onClick={scan}>
              Đọc ảnh bằng OCR
            </Button>
            <Button
              type="primary"
              disabled={!result || loading}
              onClick={() => {
                apply({
                  ...(name ? { name } : {}),
                  ...(code ? { code } : {}),
                  ...(description ? { description } : {}),
                });
                setOpen(false);
                message.success(
                  "Đã điền gợi ý. Kiểm tra các trường rồi bấm Lưu thiết bị.",
                );
              }}
            >
              Áp dụng gợi ý vào biểu mẫu
            </Button>
          </Space>
        }
      >
        <Alert
          showIcon
          type="info"
          title="OCR chỉ đưa gợi ý. Thiết bị chỉ được tạo sau khi bạn bấm Lưu thiết bị trong biểu mẫu."
        />
        <input
          type="file"
          aria-label="Ảnh nhãn cho OCR"
          accept="image/png,image/jpeg,image/webp"
          onChange={(e) => {
            const f = e.target.files?.[0] || null;
            if (f && f.size > 5242880) {
              message.error("Ảnh vượt quá 5 MB");
              setFile(null);
              setResult(null);
              return;
            }
            setFile(f);
            setResult(null);
          }}
        />
        {imagePreview && (
          <img
            className="detail-image"
            src={imagePreview}
            alt="Nhãn thiết bị cần đọc OCR"
          />
        )}
        {loading && (
          <p className="muted">
            Đang đọc ảnh… Lần đầu có thể cần tải model OCR.
          </p>
        )}
        {result && (
          <>
            <p>
              <Typography.Text type="secondary">
                {result.engine} · Độ tin cậy{" "}
                {result.confidence === null
                  ? "không có"
                  : `${Math.round(result.confidence * 100)}%`}
              </Typography.Text>
            </p>
            <Alert type="warning" title={result.warning} />
            <label>
              Tên thiết bị
              <Input
                value={name}
                maxLength={200}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label>
              Mã gợi ý
              <Input
                value={code}
                maxLength={80}
                onChange={(e) => setCode(e.target.value)}
              />
            </label>
            <label>
              Mô tả
              <Input.TextArea
                value={description}
                rows={4}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
            <Typography.Paragraph
              style={{ marginTop: 16, whiteSpace: "pre-wrap", fontSize: 12 }}
            >
              Văn bản gốc: {result.raw_text || "(không có chữ)"}
            </Typography.Paragraph>
          </>
        )}
      </Modal>
    </>
  );
}
