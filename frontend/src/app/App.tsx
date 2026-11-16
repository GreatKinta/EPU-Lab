import { lazy, Suspense } from "react";
import { Avatar, Button, Layout, Menu, Spin, Tag } from "antd";
import {
  AppstoreOutlined,
  AuditOutlined,
  ExperimentOutlined,
  LogoutOutlined,
  NodeIndexOutlined,
  SwapOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { AuthProvider, LoginPage, useAuth } from "../features/auth";
const EquipmentPage = lazy(() => import("../features/EquipmentPage"));
const Dashboard = lazy(() => import("../features/Dashboard"));
const UsersPage = lazy(() => import("../features/UsersPage"));
const LoansPage = lazy(() => import("../features/LoansPage"));
const VerifyPage = lazy(() => import("../features/VerifyPage"));
const labels: Record<string, string> = {
  dashboard: "Tổng quan",
  equipment: "Thiết bị",
  loans: "Mượn & trả",
  audit: "Xác minh Blockchain",
  users: "Tài khoản",
};
const roles = {
  admin: "Quản trị viên",
  staff: "Cán bộ phòng Lab",
  student: "Sinh viên",
};
function Shell() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  if (!user) return <LoginPage />;
  const key = location.pathname.split("/")[1] || "dashboard";
  const items = [
    { key: "dashboard", icon: <AppstoreOutlined />, label: "Tổng quan" },
    { key: "equipment", icon: <ExperimentOutlined />, label: "Thiết bị" },
    { key: "loans", icon: <SwapOutlined />, label: "Mượn & trả" },
    { key: "audit", icon: <AuditOutlined />, label: "Xác minh Blockchain" },
    ...(user.role === "admin"
      ? [{ key: "users", icon: <TeamOutlined />, label: "Tài khoản" }]
      : []),
  ];
  return (
    <Layout className="app-shell">
      <Layout.Sider
        width={246}
        breakpoint="lg"
        collapsedWidth={72}
        className="sidebar"
      >
        <div className="brand" onClick={() => navigate("/dashboard")}>
          <span className="brand-mark">
            <ExperimentOutlined />
          </span>
          <span className="brand-name">
            LabChain<small>LAB MANAGEMENT</small>
          </span>
        </div>
        <div className="sidebar-caption">KHÔNG GIAN LÀM VIỆC</div>
        <Menu
          mode="inline"
          theme="dark"
          selectedKeys={[key]}
          items={items}
          onClick={(e) =>
            navigate(e.key === "audit" ? "/audit/verify" : `/${e.key}`)
          }
        />
        <div className="sidebar-bottom">
          <NodeIndexOutlined />
          <strong>Ghi nhận. Xác minh.</strong>
          <p>
            Quản lý tập trung.
            <br />
            Lịch sử có thể đối chiếu.
          </p>
          <Tag color="green">Hardhat · Local EVM</Tag>
        </div>
      </Layout.Sider>
      <Layout>
        <Layout.Header className="topbar">
          <span>
            Không gian phòng Lab <span className="breadcrumb-slash">/</span>{" "}
            <b>{labels[key]}</b>
          </span>
          <SpaceUser />
          <Button
            type="text"
            aria-label="Đăng xuất"
            icon={<LogoutOutlined />}
            onClick={logout}
          />
        </Layout.Header>
        <Layout.Content className="main-content">
          <Suspense
            fallback={
              <div className="page-loading">
                <Spin size="large" />
              </div>
            }
          >
            <Routes>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/equipment/*" element={<EquipmentPage />} />
              <Route path="/loans/*" element={<LoansPage />} />
              <Route path="/audit/verify" element={<VerifyPage />} />
              <Route
                path="/users"
                element={
                  user.role === "admin" ? (
                    <UsersPage />
                  ) : (
                    <Navigate to="/dashboard" />
                  )
                }
              />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </Suspense>
          <footer className="app-footer">
            <span>LabChain · Hệ thống quản lý thiết bị phòng Lab</span>
            <span>Thiết kế cho học tập & khám phá</span>
          </footer>
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
function SpaceUser() {
  const { user } = useAuth();
  return (
    <div className="user-block">
      <Avatar style={{ background: "#e9eee5", color: "#2c5142" }}>
        {user?.full_name.split(" ").at(-1)?.slice(0, 1)}
      </Avatar>
      <span>
        <b>{user?.full_name}</b>
        <small>{user && roles[user.role]}</small>
      </span>
    </div>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </BrowserRouter>
  );
}
