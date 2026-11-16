import { createContext, useContext, useEffect, useState } from "react";
import { App, Button, Form, Input, Typography } from "antd";
import {
  ArrowRightOutlined,
  SafetyCertificateOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { api, json, setToken } from "../lib/api";
import type { User } from "../lib/types";

const AuthContext = createContext<{
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}>(null!);
export const useAuth = () => useContext(AuthContext);
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const queryClient = useQueryClient();
  const logout = () => {
    setUser(null);
    setToken(null);
    queryClient.clear();
  };
  useEffect(() => {
    const expired = () => logout();
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);
  async function login(email: string, password: string) {
    const response = await api<{ access_token: string; user: User }>(
      "/auth/login",
      json("POST", { email, password }),
    );
    queryClient.clear();
    setToken(response.access_token);
    setUser(response.user);
  }
  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
export function LoginPage() {
  const { login } = useAuth();
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  async function submit(values: { email: string; password: string }) {
    setLoading(true);
    try {
      await login(values.email, values.password);
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="login">
      <section className="login-story">
        <div className="brand">
          <span className="brand-mark">
            <ExperimentOutlined />
          </span>
          LabChain<span className="version">LAB MANAGEMENT</span>
        </div>
        <div>
          <span className="eyebrow">KẾT NỐI TRI THỨC · CHIA SẺ THIẾT BỊ</span>
          <h1>
            Mỗi thiết bị.
            <br />
            Một cơ hội
            <br />
            <em>khám phá.</em>
          </h1>
          <p>
            Quản lý thiết bị, theo dõi mượn trả và xác minh lịch sử trong một
            không gian làm việc.
          </p>
        </div>
        <span className="login-foot">
          <SafetyCertificateOutlined /> Lịch sử minh bạch với Blockchain
        </span>
      </section>
      <section className="login-form">
        <div>
          <span className="eyebrow">CHÀO MỪNG TRỞ LẠI</span>
          <Typography.Title level={2}>Đăng nhập LabChain</Typography.Title>
          <p className="muted">Sử dụng tài khoản được cấp bởi phòng Lab.</p>
          <Form layout="vertical" onFinish={submit} requiredMark={false}>
            <Form.Item
              name="email"
              label="Email"
              rules={[
                {
                  required: true,
                  type: "email",
                  message: "Nhập địa chỉ email hợp lệ",
                },
              ]}
            >
              <Input
                size="large"
                autoComplete="username"
                placeholder="staff@labchain.local"
              />
            </Form.Item>
            <Form.Item
              name="password"
              label="Mật khẩu"
              rules={[{ required: true, message: "Nhập mật khẩu" }]}
            >
              <Input.Password size="large" autoComplete="current-password" />
            </Form.Item>
            <Button
              block
              type="primary"
              size="large"
              htmlType="submit"
              loading={loading}
            >
              Đăng nhập <ArrowRightOutlined />
            </Button>
          </Form>
          <p className="login-note">
            Tài khoản demo: admin, staff hoặc student @labchain.local.
            <br />
            Mật khẩu được sinh trong tệp .env khi thiết lập.
          </p>
        </div>
        <span className="muted">
          LabChain · Không gian thực hành, vận hành thông minh.
        </span>
      </section>
    </div>
  );
}
