import { useEffect, useState } from "react";
import {
  Alert,
  App,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Timeline,
  Typography,
} from "antd";
import {
  ArrowLeftOutlined,
  DeleteOutlined,
  PlusOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api, date, json } from "../lib/api";
import type { Equipment, Loan, LoanStatus, Page } from "../lib/types";
import { useAuth } from "./auth";
export const loanLabels: Record<LoanStatus, string> = {
  PENDING: "Chờ duyệt",
  APPROVED: "Đã duyệt · giữ chỗ",
  BORROWED: "Đang mượn",
  RETURNED: "Đã trả",
  REJECTED: "Từ chối",
  CANCELLED: "Đã hủy",
};
const colors: Record<LoanStatus, string> = {
  PENDING: "gold",
  APPROVED: "blue",
  BORROWED: "cyan",
  RETURNED: "green",
  REJECTED: "red",
  CANCELLED: "default",
};
export default function LoansPage() {
  const { user } = useAuth();
  const staff = user?.role !== "student";
  const { message, modal } = App.useApp();
  const client = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const isNew = location.pathname === "/loans/new";
  const id = location.pathname.match(/^\/loans\/(?!new$)([^/]+)$/)?.[1];
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string | undefined>();
  const [search, setSearch] = useState("");
  const [form] = Form.useForm();
  const [reason, setReason] = useState("");
  const [rejectOpen, setRejectOpen] = useState(false);
  const [approveOpen, setApproveOpen] = useState(false);
  const [due, setDue] = useState("");
  const [key, setKey] = useState(crypto.randomUUID());
  useEffect(() => {
    if (isNew) {
      form.resetFields();
      form.setFieldsValue({
        items: [{ quantity: 1 }],
        due_at: new Date(
          Date.now() + 3 * 86400000 - new Date().getTimezoneOffset() * 60000,
        )
          .toISOString()
          .slice(0, 16),
      });
      setKey(crypto.randomUUID());
    }
  }, [isNew]);
  const loans = useQuery({
    queryKey: ["loans", page, status],
    queryFn: () =>
      api<Page<Loan>>(
        `/loans?${new URLSearchParams({ page: String(page), ...(status ? { status } : {}) })}`,
      ),
    refetchInterval: 5000,
  });
  const detail = useQuery({
    queryKey: ["loan", id],
    queryFn: () => api<Loan>(`/loans/${id}`),
    enabled: !!id,
    refetchInterval: 5000,
  });
  const equipment = useQuery({
    queryKey: ["equipment-options", search],
    queryFn: () =>
      api<Page<Equipment>>(
        `/equipment?page_size=15&search=${encodeURIComponent(search)}`,
      ),
    enabled: isNew,
  });
  function invalidate() {
    for (const q of ["loans", "loan", "equipment", "summary", "verify"])
      client.invalidateQueries({ queryKey: [q] });
  }
  const create = useMutation({
    mutationFn: (values: {
      due_at: string;
      items: { equipment_id: string; quantity: number }[];
    }) =>
      api<Loan>("/loans", {
        ...json("POST", {
          ...values,
          due_at: new Date(values.due_at).toISOString(),
        }),
        headers: { "Idempotency-Key": key },
      }),
    onSuccess: (item) => {
      invalidate();
      navigate(`/loans/${item.id}`);
      message.success("Đã gửi yêu cầu mượn");
    },
    onError: (e) => message.error(e.message),
  });
  const transition = useMutation({
    mutationFn: ({ action, body }: { action: string; body?: unknown }) =>
      api<Loan>(`/loans/${id}/${action}`, json("POST", body)),
    onSuccess: () => {
      invalidate();
      setRejectOpen(false);
      setApproveOpen(false);
      message.success("Đã cập nhật phiếu mượn");
    },
    onError: (e) => message.error(e.message),
  });
  function command(action: string, label: string) {
    modal.confirm({
      title: label,
      content:
        action === "return"
          ? "Xác nhận đã nhận đủ toàn bộ thiết bị và hoàn tất kiểm tra?"
          : "Xác nhận thực hiện thao tác này?",
      okText: "Xác nhận",
      cancelText: "Hủy",
      onOk: () => transition.mutateAsync({ action }),
    });
  }
  const item = detail.data;
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">VẬN HÀNH PHÒNG LAB</span>
          <h1>{id ? "Chi tiết phiếu mượn" : "Mượn & trả thiết bị"}</h1>
          <p className="muted">
            {staff
              ? "Duyệt, bàn giao và tiếp nhận thiết bị."
              : "Theo dõi yêu cầu và lịch sử mượn của bạn."}
          </p>
        </div>
        {id ? (
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate("/loans")}
          >
            Danh sách phiếu
          </Button>
        ) : (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/loans/new")}
          >
            Tạo phiếu mượn
          </Button>
        )}
      </div>
      {id ? (
        <>
          {detail.error && <Alert type="error" title={detail.error.message} />}
          <Card loading={detail.isLoading}>
            {item && (
              <>
                <Space>
                  <Typography.Title level={4} style={{ margin: 0 }}>
                    {item.code}
                  </Typography.Title>
                  <Tag color={colors[item.status]}>
                    {loanLabels[item.status]}
                  </Tag>
                </Space>
                <Descriptions
                  style={{ marginTop: 20 }}
                  items={[
                    {
                      key: "requested",
                      label: "Ngày yêu cầu",
                      children: date(item.requested_at),
                    },
                    {
                      key: "due",
                      label: "Hạn trả",
                      children: date(item.due_at),
                    },
                    {
                      key: "id",
                      label: "Mã tham chiếu",
                      children: (
                        <Typography.Text copyable>{item.id}</Typography.Text>
                      ),
                    },
                  ]}
                />
                {item.rejection_reason && (
                  <Alert
                    type="warning"
                    title={`Lý do từ chối: ${item.rejection_reason}`}
                  />
                )}
                <Table
                  rowKey="equipment_id"
                  pagination={false}
                  dataSource={item.items}
                  columns={[
                    { title: "Thiết bị", dataIndex: "name" },
                    { title: "Mã", dataIndex: "code" },
                    { title: "Số lượng", dataIndex: "quantity" },
                    { title: "Đơn vị", dataIndex: "unit" },
                  ]}
                />
                <div className="loan-actions">
                  {staff && item.status === "PENDING" && (
                    <>
                      <Button
                        type="primary"
                        loading={transition.isPending}
                        onClick={() => {
                          setDue(
                            new Date(
                              new Date(item.due_at).getTime() -
                                new Date().getTimezoneOffset() * 60000,
                            )
                              .toISOString()
                              .slice(0, 16),
                          );
                          setApproveOpen(true);
                        }}
                      >
                        Duyệt phiếu
                      </Button>
                      <Button
                        danger
                        onClick={() => {
                          setReason("");
                          setRejectOpen(true);
                        }}
                      >
                        Từ chối
                      </Button>
                    </>
                  )}
                  {staff && item.status === "APPROVED" && (
                    <Button
                      type="primary"
                      onClick={() =>
                        command("handover", "Xác nhận bàn giao thiết bị")
                      }
                    >
                      Bàn giao thiết bị
                    </Button>
                  )}
                  {staff && item.status === "BORROWED" && (
                    <Button
                      type="primary"
                      onClick={() =>
                        command("return", "Xác nhận nhận trả toàn bộ")
                      }
                    >
                      Nhận trả toàn bộ
                    </Button>
                  )}
                  {(item.status === "PENDING" ||
                    (staff && item.status === "APPROVED")) && (
                    <Button
                      danger
                      onClick={() => command("cancel", "Hủy phiếu mượn")}
                    >
                      Hủy phiếu
                    </Button>
                  )}
                  <Link to={`/audit/verify?loan=${item.id}`}>
                    <Button icon={<SafetyCertificateOutlined />}>
                      Xác minh Blockchain
                    </Button>
                  </Link>
                </div>
                <Alert
                  type="info"
                  title="Trạng thái nghiệp vụ độc lập với Blockchain. Phiếu đã duyệt có thể bàn giao trong khi chờ giao dịch xác nhận."
                />
                <Typography.Title level={5}>
                  Giao dịch Blockchain
                </Typography.Title>
                <Table
                  rowKey="id"
                  dataSource={item.transactions}
                  pagination={false}
                  locale={{ emptyText: "Chưa phát sinh sự kiện duyệt/trả" }}
                  columns={[
                    { title: "Sự kiện", dataIndex: "event_type" },
                    {
                      title: "Trạng thái",
                      dataIndex: "status",
                      render: (v: string) => (
                        <Tag
                          color={
                            v === "CONFIRMED"
                              ? "green"
                              : v === "FAILED"
                                ? "red"
                                : "gold"
                          }
                        >
                          {v}
                        </Tag>
                      ),
                    },
                    {
                      title: "Transaction hash",
                      dataIndex: "tx_hash",
                      render: (v: string | null) =>
                        v ? (
                          <Typography.Text className="chain-hash" copyable>
                            {v}
                          </Typography.Text>
                        ) : (
                          "Chưa gửi"
                        ),
                    },
                    { title: "Lỗi", dataIndex: "error_message" },
                  ]}
                />
              </>
            )}
          </Card>
          {item && (
            <Card className="timeline-panel" title="Dòng thời gian">
              <Timeline
                items={item.timeline?.map((t) => ({
                  content: (
                    <>
                      <b>
                        {(
                          {
                            LoanRequested: "Gửi yêu cầu",
                            LoanApproved: "Duyệt phiếu",
                            LoanBorrowed: "Bàn giao",
                            LoanReturned: "Nhận trả",
                            LoanRejected: "Từ chối",
                            LoanCancelled: "Hủy phiếu",
                          } as Record<string, string>
                        )[t.action] || t.action}
                      </b>
                      <p className="muted">{date(t.created_at)}</p>
                    </>
                  ),
                }))}
              />
            </Card>
          )}
        </>
      ) : (
        <>
          <Space style={{ marginBottom: 20 }}>
            <Select
              allowClear
              placeholder="Tất cả trạng thái"
              value={status}
              style={{ width: 220 }}
              onChange={(v) => {
                setStatus(v);
                setPage(1);
              }}
              options={Object.entries(loanLabels).map(([value, label]) => ({
                value,
                label,
              }))}
            />
          </Space>
          {loans.error && <Alert type="error" title={loans.error.message} />}
          <Table
            className="table-panel"
            rowKey="id"
            loading={loans.isLoading}
            dataSource={loans.data?.items}
            pagination={{
              current: page,
              pageSize: 10,
              total: loans.data?.total,
              onChange: setPage,
            }}
            columns={[
              {
                title: "PHIẾU MƯỢN",
                dataIndex: "code",
                render: (v: string, item: Loan) => (
                  <Link to={`/loans/${item.id}`}>{v}</Link>
                ),
              },
              {
                title: "THIẾT BỊ",
                render: (_: unknown, item: Loan) =>
                  item.items.map((x) => `${x.name} × ${x.quantity}`).join(", "),
              },
              {
                title: "TRẠNG THÁI",
                dataIndex: "status",
                render: (v: LoanStatus) => (
                  <Tag color={colors[v]}>{loanLabels[v]}</Tag>
                ),
              },
              { title: "HẠN TRẢ", dataIndex: "due_at", render: date },
              {
                title: "BLOCKCHAIN",
                render: (_: unknown, item: Loan) =>
                  item.transactions.length
                    ? item.transactions.map((t) => (
                        <Tag
                          key={t.id}
                          color={t.status === "CONFIRMED" ? "green" : "gold"}
                        >
                          {t.status}
                        </Tag>
                      ))
                    : "Chưa phát sinh",
              },
            ]}
          />
        </>
      )}
      <Modal
        title="Tạo phiếu mượn thiết bị"
        open={isNew}
        width={750}
        onCancel={() => navigate("/loans")}
        onOk={() => form.submit()}
        okText="Gửi yêu cầu"
        confirmLoading={create.isPending}
      >
        <Alert
          type="info"
          title="Phiếu chờ duyệt chưa giữ chỗ thiết bị. Khả dụng được kiểm tra lại khi cán bộ duyệt."
        />
        <Form form={form} layout="vertical" onFinish={(v) => create.mutate(v)}>
          <Form.Item
            name="due_at"
            label="Hạn trả (giờ Việt Nam)"
            rules={[{ required: true, message: "Chọn hạn trả" }]}
          >
            <Input type="datetime-local" />
          </Form.Item>
          <Form.List
            name="items"
            rules={[
              {
                validator: async (_, values) => {
                  if (!values?.length)
                    throw new Error("Chọn ít nhất một thiết bị");
                },
              },
            ]}
          >
            {(fields, { add, remove }, { errors }) => (
              <>
                {fields.map(({ key, name, ...rest }) => (
                  <div className="loan-item-row" key={key}>
                    <Form.Item
                      {...rest}
                      name={[name, "equipment_id"]}
                      rules={[{ required: true, message: "Chọn thiết bị" }]}
                      style={{ flex: 1, margin: 0 }}
                    >
                      <Select
                        showSearch
                        placeholder="Tìm thiết bị theo tên hoặc mã"
                        filterOption={false}
                        onSearch={setSearch}
                        loading={equipment.isFetching}
                        options={equipment.data?.items.map((x) => ({
                          value: x.id,
                          label: `${x.name} · ${x.quantity_available} ${x.unit} khả dụng`,
                        }))}
                      />
                    </Form.Item>
                    <Form.Item
                      {...rest}
                      name={[name, "quantity"]}
                      rules={[{ required: true, message: "Nhập số lượng" }]}
                      style={{ margin: 0 }}
                    >
                      <InputNumber
                        aria-label="Số lượng mượn"
                        min={1}
                        max={1000000}
                        precision={0}
                      />
                    </Form.Item>
                    <Button
                      aria-label="Xóa dòng thiết bị"
                      icon={<DeleteOutlined />}
                      onClick={() => remove(name)}
                    />
                  </div>
                ))}
                <Form.ErrorList errors={errors} />
                <Button
                  type="dashed"
                  icon={<PlusOutlined />}
                  disabled={fields.length >= 50}
                  onClick={() => add({ quantity: 1 })}
                >
                  Thêm dòng thiết bị
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
      <Modal
        title="Từ chối phiếu"
        open={rejectOpen}
        onCancel={() => setRejectOpen(false)}
        onOk={() => {
          if (!reason.trim()) {
            message.error("Nhập lý do từ chối");
            return;
          }
          transition.mutate({ action: "reject", body: { reason } });
        }}
        confirmLoading={transition.isPending}
      >
        <Input.TextArea
          value={reason}
          maxLength={1000}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Lý do từ chối (bắt buộc)"
        />
      </Modal>
      <Modal
        title="Duyệt phiếu & giữ chỗ"
        open={approveOpen}
        onCancel={() => setApproveOpen(false)}
        onOk={() => {
          if (!due || new Date(due).getTime() <= Date.now()) {
            message.error("Hạn trả phải sau thời điểm hiện tại");
            return;
          }
          transition.mutate({
            action: "approve",
            body: { due_at: new Date(due).toISOString() },
          });
        }}
        confirmLoading={transition.isPending}
      >
        <p>Thiết bị được giữ chỗ nguyên lô khi đủ tồn kho.</p>
        <label>
          Hạn trả (giờ Việt Nam)
          <Input
            type="datetime-local"
            value={due}
            onChange={(e) => setDue(e.target.value)}
          />
        </label>
      </Modal>
    </>
  );
}
