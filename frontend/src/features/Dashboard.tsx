import { Alert, Button, Card, Col, Row, Statistic, Table, Tag } from "antd";
import {
  ArrowRightOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  SafetyCertificateOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, date } from "../lib/api";
import { useAuth } from "./auth";
interface Summary {
  equipment_count: number;
  available_units: number;
  active_loans: number;
  pending_loans: number;
  overdue_loans: number;
  confirmed_transactions: number;
  recent_loans: { id: string; code: string; status: string; due_at: string }[];
  popular_equipment: { name: string; quantity: number }[];
}
export default function Dashboard() {
  const { user } = useAuth();
  const query = useQuery({
    queryKey: ["summary"],
    queryFn: () => api<Summary>("/dashboard/summary"),
    refetchInterval: 15000,
  });
  const data = query.data;
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">PHÒNG LAB · TỔNG QUAN</span>
          <h1>
            Chào {user?.full_name.split(" ").at(-1)},<br />
            một ngày khám phá mới.
          </h1>
          <p className="muted">
            Mọi tài nguyên trong tầm tay. Mọi lượt mượn đều có dấu vết.
          </p>
        </div>
        <Link to="/loans/new">
          <Button type="primary" size="large">
            Tạo phiếu mượn <ArrowRightOutlined />
          </Button>
        </Link>
      </div>
      <div className="dashboard-banner">
        <div>
          <Tag color="green">LABCHAIN / WORKSPACE</Tag>
          <h2>
            Thực hành hôm nay.
            <br />
            Kiến tạo ngày mai.
          </h2>
          <p>Tra cứu thiết bị và bắt đầu buổi thực hành tiếp theo của bạn.</p>
          <Link to="/equipment">
            Khám phá danh mục <ArrowRightOutlined />
          </Link>
        </div>
        <div className="banner-art">
          <ExperimentOutlined />
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <span className="art-dot" />
        </div>
      </div>
      {query.error && (
        <Alert
          type="error"
          showIcon
          title={query.error.message}
          action={<Button onClick={() => query.refetch()}>Thử lại</Button>}
        />
      )}
      <Row gutter={[20, 20]} className="stats-row">
        {[
          {
            title: "Loại thiết bị",
            value: data?.equipment_count,
            icon: <ExperimentOutlined />,
            note: `${data?.available_units ?? "—"} đơn vị khả dụng`,
          },
          {
            title: "Phiếu đang mượn / giữ chỗ",
            value: data?.active_loans,
            icon: <SwapOutlined />,
            note: `${data?.pending_loans ?? "—"} phiếu chờ duyệt`,
          },
          {
            title: "Phiếu quá hạn",
            value: data?.overdue_loans,
            icon: <ClockCircleOutlined />,
            note: "Cần theo dõi và nhận trả",
          },
          {
            title: "Giao dịch đã xác nhận",
            value: data?.confirmed_transactions,
            icon: <SafetyCertificateOutlined />,
            note: "Hardhat · Local Blockchain",
          },
        ].map((x) => (
          <Col xs={24} sm={12} xl={6} key={x.title}>
            <Card loading={query.isLoading}>
              <div className="stat-label">
                {x.title}
                {x.icon}
              </div>
              <Statistic value={x.value ?? "—"} />
              <small className="muted">{x.note}</small>
            </Card>
          </Col>
        ))}
      </Row>
      <Row gutter={[20, 20]}>
        <Col xs={24} xl={16}>
          <Card
            title="Phiếu mượn gần đây"
            extra={
              <Link to="/loans">
                Xem tất cả <ArrowRightOutlined />
              </Link>
            }
          >
            <Table
              rowKey="id"
              dataSource={data?.recent_loans || []}
              pagination={false}
              columns={[
                {
                  title: "Phiếu mượn",
                  dataIndex: "code",
                  render: (v: string, item: { id: string }) => (
                    <Link to={`/loans/${item.id}`}>{v}</Link>
                  ),
                },
                {
                  title: "Trạng thái",
                  dataIndex: "status",
                  render: (v: string) => <Tag>{v}</Tag>,
                },
                { title: "Hạn trả", dataIndex: "due_at", render: date },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="Thiết bị được mượn nhiều">
            <div className="popular-list">
              {data?.popular_equipment.length ? (
                data.popular_equipment.map((item, i) => (
                  <div key={i}>
                    <span className="rank">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <strong>{item.name}</strong>
                    <Tag>{item.quantity} lượt đơn vị</Tag>
                  </div>
                ))
              ) : (
                <p className="muted">
                  Thống kê xuất hiện khi có phiếu được duyệt.
                </p>
              )}
            </div>
          </Card>
        </Col>
      </Row>
    </>
  );
}
