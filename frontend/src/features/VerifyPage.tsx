import { useState } from "react";
import {
  Alert,
  App,
  Button,
  Card,
  Collapse,
  Descriptions,
  Input,
  Select,
  Space,
  Tag,
  Typography,
} from "antd";
import { ReloadOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api, json } from "../lib/api";
import type { Loan, Page } from "../lib/types";
interface Verification {
  status: string;
  network: string;
  records: {
    event_id: string;
    event_type: string;
    status: string;
    reason: string;
    tx_hash: string | null;
    block_number: number | null;
    stored_hash: string;
    computed_hash: string;
    chain_hash: string | null;
    snapshot: unknown;
    error: string | null;
  }[];
}
const labels: Record<string, string> = {
  VERIFIED: "Đã xác minh",
  MISMATCH: "Dữ liệu không khớp",
  PENDING: "Đang chờ ghi nhận",
  NOT_RECORDED: "Chưa được ghi nhận",
  CHAIN_UNAVAILABLE: "Không kết nối được Blockchain",
};
export default function VerifyPage() {
  const [params, setParams] = useSearchParams();
  const id = params.get("loan") || "";
  const [input, setInput] = useState(id);
  const { message } = App.useApp();
  const loans = useQuery({
    queryKey: ["verify-loans"],
    queryFn: () => api<Page<Loan>>("/loans?page_size=100"),
  });
  const query = useQuery({
    queryKey: ["verify", id],
    queryFn: () => api<Verification>(`/loans/${encodeURIComponent(id)}/verify`),
    enabled: !!id,
    refetchInterval: 10000,
  });
  function pick(value: string) {
    setInput(value);
    setParams({ loan: value });
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">BẰNG CHỨNG SỐ · LOCAL EVM</span>
          <h1>Xác minh Blockchain</h1>
          <p className="muted">
            Đối chiếu snapshot gốc với dữ liệu đọc trực tiếp từ smart contract.
          </p>
        </div>
        <SafetyCertificateOutlined style={{ fontSize: 36, color: "#6c8962" }} />
      </div>
      <Card>
        <Space wrap>
          <Select
            showSearch
            optionFilterProp="label"
            placeholder="Chọn phiếu mượn"
            style={{ width: 300 }}
            value={id || undefined}
            onChange={pick}
            options={loans.data?.items.map((l) => ({
              value: l.id,
              label: l.code,
            }))}
          />
          <Input
            placeholder="Hoặc nhập UUID phiếu mượn"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            style={{ width: 320 }}
          />
          <Button type="primary" onClick={() => pick(input.trim())}>
            Xác minh
          </Button>
          <Button
            icon={<ReloadOutlined />}
            disabled={!id}
            loading={query.isFetching}
            onClick={() => query.refetch()}
          >
            Đọc lại từ chain
          </Button>
        </Space>
      </Card>
      <Alert
        style={{ marginTop: 20 }}
        type="info"
        showIcon
        title="Blockchain xác minh tính toàn vẹn của snapshot đã ghi nhận; không chứng minh sự thật của việc bàn giao hoặc tình trạng thiết bị ngoài đời."
      />
      {query.error && <Alert type="error" title={query.error.message} />}{" "}
      {query.data && (
        <>
          <Card style={{ marginTop: 20 }}>
            <Space>
              <Tag
                color={
                  query.data.status === "VERIFIED"
                    ? "green"
                    : query.data.status === "MISMATCH"
                      ? "red"
                      : "gold"
                }
              >
                {labels[query.data.status] || query.data.status}
              </Tag>
              <span className="muted">{query.data.network}</span>
            </Space>
            {query.data.records.length === 0 && (
              <p>Phiếu chưa có sự kiện duyệt/trả để xác minh.</p>
            )}
          </Card>
          {query.data.records.map((record) => (
            <Card
              key={record.event_id}
              title={
                record.event_type === "BorrowApproved"
                  ? "Duyệt mượn thiết bị"
                  : "Nhận trả thiết bị"
              }
              style={{ marginTop: 20 }}
              extra={
                <Tag
                  color={
                    record.status === "VERIFIED"
                      ? "green"
                      : record.status === "MISMATCH"
                        ? "red"
                        : "gold"
                  }
                >
                  {labels[record.status]}
                </Tag>
              }
            >
              <p>{record.reason}</p>
              <Descriptions
                column={1}
                bordered
                items={[
                  {
                    key: "computed",
                    label: "Hash snapshot tính lại",
                    children: (
                      <Typography.Text copyable className="chain-hash">
                        {record.computed_hash}
                      </Typography.Text>
                    ),
                  },
                  {
                    key: "stored",
                    label: "Hash đã lưu trong DB",
                    children: (
                      <Typography.Text copyable className="chain-hash">
                        {record.stored_hash}
                      </Typography.Text>
                    ),
                  },
                  {
                    key: "chain",
                    label: "Hash đọc từ contract",
                    children: record.chain_hash ? (
                      <Typography.Text copyable className="chain-hash">
                        {record.chain_hash}
                      </Typography.Text>
                    ) : (
                      "Chưa có / chưa đọc được"
                    ),
                  },
                  {
                    key: "tx",
                    label: "Transaction hash",
                    children: record.tx_hash ? (
                      <Typography.Text copyable className="chain-hash">
                        {record.tx_hash}
                      </Typography.Text>
                    ) : (
                      "Chưa gửi"
                    ),
                  },
                  {
                    key: "block",
                    label: "Block",
                    children: record.block_number ?? "—",
                  },
                ]}
              />
              {record.error && (
                <Alert
                  style={{ marginTop: 15 }}
                  type="error"
                  title={`Lỗi đồng bộ: ${record.error}`}
                  action={
                    <Button
                      onClick={() =>
                        api(
                          `/blockchain/events/${record.event_id}/retry`,
                          json("POST"),
                        )
                          .then(() => {
                            message.success("Đã đưa vào hàng đợi thử lại");
                            query.refetch();
                          })
                          .catch((e) => message.error(e.message))
                      }
                    >
                      Thử lại sự kiện lỗi
                    </Button>
                  }
                />
              )}
              <Collapse
                style={{ marginTop: 20 }}
                items={[
                  {
                    key: "snapshot",
                    label: "Snapshot bất biến (lưu ngoài chain)",
                    children: (
                      <pre style={{ whiteSpace: "pre-wrap", fontSize: 11 }}>
                        {JSON.stringify(record.snapshot, null, 2)}
                      </pre>
                    ),
                  },
                ]}
              />
            </Card>
          ))}
        </>
      )}
    </>
  );
}
