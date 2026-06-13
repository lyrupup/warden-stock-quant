/* Vite/React 框架入口：此处按框架约定允许 default 导入与 createRoot 渲染。 */
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "@/app/app";
import "@/index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
