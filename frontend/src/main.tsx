import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, App as AntApp } from "antd";
import viVN from "antd/locale/vi_VN";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./app/App";
import "./style.css";
const client = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={viVN}
      theme={{
        token: {
          colorPrimary: "#2d6553",
          colorInfo: "#2d6553",
          fontFamily:
            'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
          borderRadius: 8,
          colorBgLayout: "#f6f7f3",
          controlHeight: 38,
        },
        components: {
          Table: {
            headerBg: "#f6f7f3",
            headerColor: "#728078",
            headerSplitColor: "transparent",
            cellPaddingBlock: 18,
          },
          Menu: {
            darkItemBg: "#122f2a",
            darkItemSelectedBg: "#2d5145",
            darkItemSelectedColor: "#fff",
          },
          Layout: { siderBg: "#122f2a" },
        },
      }}
    >
      <AntApp>
        <QueryClientProvider client={client}>
          <App />
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>,
);
