import { useState } from "react";
import {
  App,
  Button,
  Form,
  Input,
  Modal,
  Select,
  Switch,
  Table,
  Tag,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, date, json } from "../lib/api";
import type { Page, User } from "../lib/types";
import { useAuth } from "./auth";
export default function UsersPage() {
  const { user } = useAuth();
  const { message } = App.useApp();
  const client = useQueryClient();
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const [editing, setEditing] = useState<User | null>(null);
  const query = useQuery({
    queryKey: ["users", page],
    queryFn: () => api<Page<User>>(`/users?page=${page}`),
  });
  const save = useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      api(
        editing ? `/users/${editing.id}` : "/users",
        json(
          editing ? "PATCH" : "POST",
          Object.fromEntries(
            Object.entries(values).filter(
              ([, v]) => v !== "" && v !== undefined,
            ),
          ),
        ),
      ),
    onSuccess: () => {
      setOpen(false);
      client.invalidateQueries({ queryKey: ["users"] });
      message.success("Đã lưu tài khoản");
    },
    onError: (e) => message.error(e.message),
  });
  function show(item: User | null) {
    setEditing(item);
    form.resetFields();
    form.setFieldsValue(item || { role: "student" });
    setOpen(true);
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">QUẢN TRỊ HỆ THỐNG</span>
          <h1>Tài khoản</h1>
          <p className="muted">
            Cấp tài khoản và quản lý quyền truy cập phòng Lab.
          </p>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => show(null)}
        >
          Thêm tài khoản
        </Button>
      </div>
      <Table
        rowKey="id"
        loading={query.isFetching}
        dataSource={query.data?.items}
        columns={[
          { title: "Họ tên", dataIndex: "full_name" },
          { title: "Email", dataIndex: "email" },
          {
            title: "Vai trò",
            dataIndex: "role",
            render: (v: string) => <Tag>{v}</Tag>,
          },
          {
            title: "Hoạt động",
            dataIndex: "is_active",
            render: (v: boolean) => (v ? "Đang hoạt động" : "Đã khóa"),
          },
          { title: "Ngày tạo", dataIndex: "created_at", render: date },
          {
            title: "Thao tác",
            render: (_: unknown, item: User) => (
              <Button onClick={() => show(item)}>Chỉnh sửa</Button>
            ),
          },
        ]}
        pagination={{
          current: page,
          pageSize: 15,
          total: query.data?.total,
          onChange: setPage,
        }}
      />
      {query.error && <p className="error-text">{query.error.message}</p>}
      <Modal
        title={editing ? "Chỉnh sửa tài khoản" : "Thêm tài khoản"}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={save.isPending}
      >
        <Form form={form} layout="vertical" onFinish={(v) => save.mutate(v)}>
          {!editing && (
            <Form.Item
              name="email"
              label="Email"
              rules={[{ required: true, type: "email" }]}
            >
              <Input />
            </Form.Item>
          )}
          <Form.Item
            name="full_name"
            label="Họ tên"
            rules={[{ required: true, max: 200 }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="password"
            label={
              editing ? "Mật khẩu mới (để trống để giữ nguyên)" : "Mật khẩu"
            }
            rules={[{ required: !editing, min: 12, max: 128 }]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item name="role" label="Vai trò">
            <Select
              disabled={editing?.id === user?.id}
              options={["student", "staff", "admin"].map((v) => ({
                value: v,
                label: v,
              }))}
            />
          </Form.Item>
          {editing && (
            <Form.Item
              name="is_active"
              label="Đang hoạt động"
              valuePropName="checked"
            >
              <Switch disabled={editing.id === user?.id} />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </>
  );
}
