import { useEffect, useRef, useState } from "react";
import {
  Alert,
  App,
  Button,
  Checkbox,
  Descriptions,
  Drawer,
  Dropdown,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import type { InputRef, TableColumnsType } from "antd";
import {
  CopyOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FilterOutlined,
  InboxOutlined,
  PlusOutlined,
  SearchOutlined,
  SettingOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";
import { api, date, download, json, money, request } from "../lib/api";
import type {
  Equipment,
  EquipmentInput,
  ImportResult,
  Page,
} from "../lib/types";
import { readColumns, useShortcuts } from "../lib/shortcuts";
import { useAuth } from "./auth";
import OcrAssistant from "./OcrAssistant";

function PrivateImage({ item }: { item: Equipment }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    let current = "";
    let mounted = true;
    if (item.image_path)
      request(`/equipment/${item.id}/image`)
        .then((r) => r.blob())
        .then((blob) => {
          current = URL.createObjectURL(blob);
          if (mounted) setUrl(current);
          else URL.revokeObjectURL(current);
        })
        .catch(() => {});
    return () => {
      mounted = false;
      if (current) URL.revokeObjectURL(current);
    };
  }, [item.id, item.image_path]);
  return url ? (
    <img className="detail-image" src={url} alt={item.name} />
  ) : null;
}
export default function EquipmentPage() {
  const { user } = useAuth();
  const canEdit = user?.role !== "student";
  const { message, modal } = App.useApp();
  const client = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [sort, setSort] = useState("-created_at");
  const [selected, setSelected] = useState<React.Key[]>([]);
  const [columns, setColumns] = useState(readColumns);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Equipment | null>(null);
  const [detail, setDetail] = useState<Equipment | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [format, setFormat] = useState("xlsx");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportResult | null>(null);
  const [importing, setImporting] = useState(false);
  const searchRef = useRef<InputRef>(null);
  const [form] = Form.useForm<EquipmentInput>();
  useEffect(() => {
    if (search === debounced) return;
    const timer = setTimeout(() => {
      setDebounced(search);
      setPage(1);
      setSelected([]);
    }, 300);
    return () => clearTimeout(timer);
  }, [search, debounced]);
  useEffect(() => {
    localStorage.setItem("labchain-columns", JSON.stringify(columns));
  }, [columns]);
  useEffect(() => {
    if (!imageFile) {
      setImagePreview("");
      return;
    }
    const url = URL.createObjectURL(imageFile);
    setImagePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [imageFile]);
  function showForm(item: Equipment | null = null) {
    if (!canEdit) return;
    setEditing(item);
    form.resetFields();
    if (item) form.setFieldsValue(item);
    else form.setFieldsValue({ quantity_total: 1, price: "0", unit: "cái" });
    setImageFile(null);
    setOpen(true);
  }
  useEffect(() => {
    if (location.pathname === "/equipment/new") showForm();
    else {
      const id = location.pathname.match(/^\/equipment\/([^/]+)$/)?.[1];
      if (id)
        api<Equipment>(`/equipment/${id}`)
          .then(setDetail)
          .catch((e) => message.error(e.message));
    }
  }, [location.pathname]);
  const query = useQuery({
    queryKey: ["equipment", page, pageSize, debounced, sort],
    queryFn: () =>
      api<Page<Equipment>>(
        `/equipment?${new URLSearchParams({ page: String(page), page_size: String(pageSize), search: debounced, sort })}`,
      ),
  });
  function invalidate() {
    client.invalidateQueries({ queryKey: ["equipment"] });
    client.invalidateQueries({ queryKey: ["summary"] });
    setSelected([]);
  }
  const save = useMutation({
    mutationFn: async (values: EquipmentInput) => {
      const saved = await api<Equipment>(
        editing ? `/equipment/${editing.id}` : "/equipment",
        json(editing ? "PATCH" : "POST", values),
      );
      setEditing(saved);
      if (imageFile) {
        const data = new FormData();
        data.append("file", imageFile);
        return api<Equipment>(`/equipment/${saved.id}/image`, {
          method: "POST",
          body: data,
        });
      }
      return saved;
    },
    onSuccess: () => {
      setOpen(false);
      invalidate();
      message.success("Đã lưu thiết bị");
      if (location.pathname !== "/equipment") navigate("/equipment");
    },
    onError: (e) => {
      invalidate();
      message.error(e.message);
    },
  });
  const action = useMutation({
    mutationFn: ({
      path,
      body,
      method = "POST",
    }: {
      path: string;
      body?: unknown;
      method?: string;
    }) => api(path, json(method, body)),
    onSuccess: () => {
      invalidate();
      message.success("Thao tác thành công");
    },
    onError: (e) => message.error(e.message),
  });
  const busy = save.isPending || action.isPending;
  function remove(ids: React.Key[]) {
    modal.confirm({
      title: `Lưu trữ ${ids.length} thiết bị?`,
      content:
        "Thiết bị có lịch sử được giữ lại trong cơ sở dữ liệu. Thiết bị đang giữ chỗ sẽ không được xóa. Cả lô chỉ thực hiện khi mọi thiết bị hợp lệ.",
      okText: "Lưu trữ",
      cancelText: "Hủy",
      okButtonProps: { danger: true },
      onOk: async () => {
        await action.mutateAsync({
          path: "/equipment/bulk-delete",
          body: { ids },
        });
      },
    });
  }
  useShortcuts({
    create: canEdit && !open && !importOpen ? () => showForm() : undefined,
    save: open && !save.isPending ? () => form.submit() : undefined,
    search: !open && !importOpen ? () => searchRef.current?.focus() : undefined,
  });
  const columnNames = {
    code: "Mã thiết bị",
    product_type: "Phân loại",
    stock: "Số lượng",
    price: "Đơn giá",
    updated_at: "Cập nhật",
  };
  const tableColumns: TableColumnsType<Equipment> = [
    {
      title: "THIẾT BỊ",
      dataIndex: "name",
      key: "name",
      sorter: true,
      width: 280,
      render: (_, item) => (
        <button className="equipment-cell" onClick={() => setDetail(item)}>
          <span
            className={`equipment-icon tone-${item.product_type.length % 4}`}
          >
            <InboxOutlined />
          </span>
          <span>
            <strong>{item.name}</strong>
            <small>{item.description || item.code}</small>
          </span>
        </button>
      ),
    },
    ...(
      [
        {
          title: "MÃ THIẾT BỊ",
          dataIndex: "code",
          key: "code",
          sorter: true,
          render: (v: string) => <span className="mono">{v}</span>,
        },
        {
          title: "PHÂN LOẠI",
          dataIndex: "product_type",
          key: "product_type",
          render: (v: string) => <Tag variant="filled">{v}</Tag>,
        },
        {
          title: "KHẢ DỤNG / TỔNG",
          key: "stock",
          render: (_: unknown, item: Equipment) => (
            <span className={item.quantity_available ? "stock" : "stock empty"}>
              <b>{item.quantity_available}</b> / {item.quantity_total}{" "}
              <small>{item.unit}</small>
            </span>
          ),
        },
        {
          title: "ĐƠN GIÁ",
          dataIndex: "price",
          key: "price",
          sorter: true,
          render: (v: string) => money(v),
        },
        {
          title: "CẬP NHẬT",
          dataIndex: "updated_at",
          key: "updated_at",
          render: (v: string) => date(v),
        },
      ] as TableColumnsType<Equipment>
    ).filter((c) => columns.includes(String(c.key))),
    {
      title: "THAO TÁC",
      key: "actions",
      fixed: "right",
      width: 140,
      render: (_, item) => (
        <Space size={0}>
          <Tooltip title="Chi tiết">
            <Button
              type="text"
              icon={<EyeOutlined />}
              aria-label={`Chi tiết ${item.code}`}
              onClick={() => setDetail(item)}
            />
          </Tooltip>
          {canEdit && (
            <>
              <Tooltip title="Sửa">
                <Button
                  type="text"
                  icon={<EditOutlined />}
                  aria-label={`Sửa ${item.code}`}
                  onClick={() => showForm(item)}
                />
              </Tooltip>
              <Dropdown
                menu={{
                  items: [
                    {
                      key: "copy",
                      label: "Nhân bản",
                      icon: <CopyOutlined />,
                      onClick: () =>
                        action.mutate({
                          path: `/equipment/${item.id}/duplicate`,
                        }),
                    },
                    {
                      key: "delete",
                      label: "Lưu trữ",
                      danger: true,
                      icon: <DeleteOutlined />,
                      onClick: () => remove([item.id]),
                    },
                  ],
                }}
              >
                <Button type="text" aria-label={`Thao tác ${item.code}`}>
                  •••
                </Button>
              </Dropdown>
            </>
          )}
        </Space>
      ),
    },
  ];
  async function runImport(commit = false) {
    if (!file) return;
    setImporting(true);
    try {
      const body = new FormData();
      body.append("file", file);
      const result = await api<ImportResult>(
        `/equipment/import?format=${format}&dry_run=${!commit}`,
        { method: "POST", body },
      );
      setPreview(result);
      if (commit) {
        message.success(`Đã nhập ${result.imported} thiết bị`);
        setImportOpen(false);
        invalidate();
      }
    } catch (e) {
      setPreview(null);
      message.error((e as Error).message);
    } finally {
      setImporting(false);
    }
  }
  function fileChange(value: File | null) {
    setFile(value);
    setPreview(null);
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">KHÔNG GIAN THIẾT BỊ</span>
          <h1>
            Danh mục thiết bị{" "}
            <span className="count-pill">{query.data?.total ?? "—"}</span>
          </h1>
          <p className="muted">
            Theo dõi, sắp xếp và quản lý tài nguyên phòng Lab.
          </p>
        </div>
        {canEdit && (
          <Button
            type="primary"
            size="large"
            icon={<PlusOutlined />}
            onClick={() => showForm()}
          >
            Thêm thiết bị <kbd>Alt N</kbd>
          </Button>
        )}
      </div>
      <div className="inventory-note">
        <span className="live-dot" />
        <span>Dữ liệu tồn kho được cập nhật theo mỗi lượt mượn trả.</span>
        <span className="note-right">PHÒNG LAB / DANH MỤC</span>
      </div>
      <section className="table-panel">
        <div className="table-toolbar">
          <Input
            ref={searchRef}
            prefix={<SearchOutlined />}
            placeholder="Tìm theo tên, mã hoặc mô tả…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            allowClear
            className="search-input"
            aria-label="Tìm thiết bị"
          />
          <div className="toolbar-actions">
            <Dropdown
              trigger={["click"]}
              popupRender={() => (
                <div className="column-menu">
                  <b>Hiển thị cột</b>
                  {Object.entries(columnNames).map(([key, label]) => (
                    <Checkbox
                      key={key}
                      checked={columns.includes(key)}
                      onChange={(e) =>
                        setColumns(
                          e.target.checked
                            ? [...columns, key]
                            : columns.filter((x) => x !== key),
                        )
                      }
                    >
                      {label}
                    </Checkbox>
                  ))}
                </div>
              )}
            >
              <Button aria-label="Cột hiển thị" icon={<SettingOutlined />}>
                Cột hiển thị
              </Button>
            </Dropdown>
            {canEdit && (
              <>
                <Button
                  icon={<UploadOutlined />}
                  onClick={() => {
                    setImportOpen(true);
                    setPreview(null);
                    setFile(null);
                  }}
                >
                  Nhập dữ liệu
                </Button>
                <Dropdown
                  menu={{
                    items: ["xlsx", "json", "xml"].map((f) => ({
                      key: f,
                      label: `Xuất ${f.toUpperCase()} (kết quả tìm kiếm)`,
                      onClick: () =>
                        download(
                          `/equipment/export?format=${f}&search=${encodeURIComponent(debounced)}`,
                          `equipment.${f}`,
                        ).catch((e) => message.error(e.message)),
                    })),
                  }}
                >
                  <Button icon={<DownloadOutlined />}>Xuất dữ liệu</Button>
                </Dropdown>
              </>
            )}
          </div>
        </div>
        {selected.length > 0 && (
          <div className="selection-bar">
            <b>Đã chọn {selected.length} thiết bị</b>
            <Button
              size="small"
              icon={<CopyOutlined />}
              disabled={busy}
              onClick={() =>
                action.mutate({
                  path: "/equipment/bulk-duplicate",
                  body: { ids: selected },
                })
              }
            >
              Nhân bản các mục
            </Button>
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              disabled={busy}
              onClick={() => remove(selected)}
            >
              Lưu trữ các mục
            </Button>
            <Button type="text" size="small" onClick={() => setSelected([])}>
              Bỏ chọn
            </Button>
          </div>
        )}
        {query.error && (
          <Alert
            showIcon
            type="error"
            title={query.error.message}
            action={<Button onClick={() => query.refetch()}>Thử lại</Button>}
          />
        )}
        <Table
          rowKey="id"
          columns={tableColumns}
          dataSource={query.data?.items}
          loading={query.isFetching}
          scroll={{ x: 1100 }}
          rowSelection={
            canEdit
              ? { selectedRowKeys: selected, onChange: setSelected }
              : undefined
          }
          pagination={{
            current: page,
            pageSize,
            total: query.data?.total,
            showSizeChanger: true,
            pageSizeOptions: [10, 15],
            showTotal: (total) => `${total} thiết bị`,
            onChange: (p, s) => {
              setPage(p);
              setPageSize(s);
              setSelected([]);
            },
          }}
          onChange={(_, __, s) => {
            const value = Array.isArray(s) ? s[0] : s;
            if (value?.field) {
              setSort(
                (value.order === "descend" ? "-" : "") + String(value.field),
              );
              setSelected([]);
            }
          }}
          locale={{
            emptyText: (
              <Empty
                description={
                  search
                    ? "Không tìm thấy thiết bị phù hợp"
                    : "Chưa có thiết bị"
                }
              />
            ),
          }}
        />
      </section>
      <div className="table-foot">
        <FilterOutlined /> Phím tắt: <kbd>Alt N</kbd> thêm mới ·{" "}
        <kbd>Alt S</kbd> lưu biểu mẫu · <kbd>Alt F</kbd> tìm kiếm. Có thể sử
        dụng các nút tương ứng.
      </div>
      <Drawer
        open={open}
        onClose={() => {
          setOpen(false);
          if (location.pathname === "/equipment/new") navigate("/equipment");
        }}
        title={editing ? "Chỉnh sửa thiết bị" : "Thêm thiết bị"}
        size="large"
        extra={
          <Button
            type="primary"
            onClick={() => form.submit()}
            loading={save.isPending}
          >
            Lưu thiết bị <kbd>Alt S</kbd>
          </Button>
        }
      >
        <OcrAssistant apply={(values) => form.setFieldsValue(values)} />
        <Form
          form={form}
          layout="vertical"
          requiredMark={false}
          onFinish={(values) => save.mutate(values)}
        >
          <div className="form-pair">
            <Form.Item
              name="code"
              label="Mã thiết bị"
              rules={[
                {
                  required: true,
                  pattern: /^[A-Za-z0-9][A-Za-z0-9._-]*$/,
                  message: "Nhập mã: chữ, số, dấu . _ -",
                },
                { max: 80 },
              ]}
            >
              <Input placeholder="EQ-0031" />
            </Form.Item>
            <Form.Item
              name="product_type"
              label="Phân loại"
              rules={[
                { required: true, message: "Nhập phân loại" },
                { max: 100 },
              ]}
            >
              <Input placeholder="Vi điều khiển" />
            </Form.Item>
          </div>
          <Form.Item
            name="name"
            label="Tên thiết bị"
            rules={[
              {
                required: true,
                whitespace: true,
                message: "Nhập tên thiết bị",
              },
              { max: 200 },
            ]}
          >
            <Input placeholder="Tên thiết bị" />
          </Form.Item>
          <div className="form-pair">
            <Form.Item
              name="quantity_total"
              label="Tổng số lượng"
              rules={[{ required: true, message: "Nhập số lượng" }]}
            >
              <InputNumber
                min={editing?.quantity_reserved || 0}
                max={1000000}
                precision={0}
                style={{ width: "100%" }}
              />
            </Form.Item>
            <Form.Item
              name="unit"
              label="Đơn vị"
              rules={[{ required: true, message: "Nhập đơn vị" }, { max: 30 }]}
            >
              <Input />
            </Form.Item>
          </div>
          <Form.Item
            name="price"
            label="Đơn giá (VND)"
            rules={[{ required: true, message: "Nhập đơn giá" }]}
          >
            <InputNumber
              min={0}
              max={9999999999.99}
              precision={2}
              stringMode
              style={{ width: "100%" }}
            />
          </Form.Item>
          <Form.Item name="description" label="Mô tả" rules={[{ max: 10000 }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item label="Ảnh thiết bị · PNG, JPEG, WebP (tối đa 5 MB)">
            <input
              type="file"
              aria-label="Ảnh thiết bị"
              accept="image/png,image/jpeg,image/webp"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f && f.size > 5242880) {
                  message.error("Ảnh vượt quá 5 MB");
                  return;
                }
                setImageFile(f || null);
              }}
            />
            {imagePreview && (
              <img
                className="detail-image"
                src={imagePreview}
                alt="Ảnh xem trước"
              />
            )}
          </Form.Item>
        </Form>
      </Drawer>
      <Modal
        open={!!detail}
        onCancel={() => {
          setDetail(null);
          if (location.pathname !== "/equipment") navigate("/equipment");
        }}
        footer={<Button onClick={() => setDetail(null)}>Đóng</Button>}
        title="Chi tiết thiết bị"
        width={700}
      >
        {detail && (
          <>
            <PrivateImage item={detail} />
            <Descriptions
              column={2}
              bordered
              items={[
                {
                  key: "name",
                  label: "Tên thiết bị",
                  children: detail.name,
                  span: 2,
                },
                { key: "code", label: "Mã", children: detail.code },
                {
                  key: "type",
                  label: "Phân loại",
                  children: detail.product_type,
                },
                {
                  key: "quantity",
                  label: "Tổng / Giữ chỗ / Khả dụng",
                  children: `${detail.quantity_total} / ${detail.quantity_reserved} / ${detail.quantity_available}`,
                },
                { key: "unit", label: "Đơn vị", children: detail.unit },
                {
                  key: "price",
                  label: "Đơn giá",
                  children: money(detail.price),
                  span: 2,
                },
                {
                  key: "description",
                  label: "Mô tả",
                  children: detail.description || "—",
                  span: 2,
                },
                {
                  key: "created",
                  label: "Ngày tạo",
                  children: date(detail.created_at),
                },
                {
                  key: "updated",
                  label: "Cập nhật",
                  children: date(detail.updated_at),
                },
                {
                  key: "id",
                  label: "ProductID",
                  children: (
                    <Typography.Text copyable>{detail.id}</Typography.Text>
                  ),
                  span: 2,
                },
              ]}
            />
          </>
        )}
      </Modal>
      <Modal
        title="Nhập thiết bị"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        width={800}
        footer={
          <Space>
            <Button onClick={() => setImportOpen(false)}>Hủy</Button>
            <Button
              disabled={!file}
              loading={importing}
              onClick={() => runImport()}
            >
              Kiểm tra & xem trước
            </Button>
            <Button
              type="primary"
              disabled={!preview?.valid || importing}
              loading={importing}
              onClick={() => runImport(true)}
            >
              Xác nhận nhập {preview?.total || 0} thiết bị
            </Button>
          </Space>
        }
      >
        <Alert
          type="info"
          showIcon
          title="Tối đa 5 MB / 1.000 dòng. Nhập nguyên lô: có lỗi sẽ không lưu dòng nào."
        />
        <Space style={{ margin: "20px 0" }}>
          <Select
            value={format}
            onChange={(v) => {
              setFormat(v);
              fileChange(null);
            }}
            options={["xlsx", "json", "xml"].map((v) => ({
              value: v,
              label: v.toUpperCase(),
            }))}
          />
          <Button
            icon={<DownloadOutlined />}
            onClick={() =>
              download(
                `/equipment/import-template?format=${format}`,
                `template.${format}`,
              ).catch((e) => message.error(e.message))
            }
          >
            Tải tệp mẫu
          </Button>
          <input
            key={format}
            type="file"
            accept={`.${format}`}
            aria-label="Tệp nhập thiết bị"
            onChange={(e) => fileChange(e.target.files?.[0] || null)}
          />
        </Space>
        {preview && (
          <>
            <Alert
              type={preview.valid ? "success" : "error"}
              showIcon
              title={
                preview.valid
                  ? `${preview.total} dòng hợp lệ. Xác nhận để lưu.`
                  : `Có ${preview.errors.length} lỗi. Dữ liệu chưa được lưu.`
              }
            />
            {preview.errors.map((e, i) => (
              <p key={i} className="error-text">
                Dòng {e.row}: {e.message}
              </p>
            ))}
            <Table
              size="small"
              rowKey="code"
              pagination={false}
              dataSource={preview.preview}
              columns={[
                { title: "Mã", dataIndex: "code" },
                { title: "Tên thiết bị", dataIndex: "name" },
                { title: "Số lượng", dataIndex: "quantity_total" },
              ]}
            />
            <p className="muted">Xem trước tối đa 20 dòng.</p>
          </>
        )}
      </Modal>
    </>
  );
}
