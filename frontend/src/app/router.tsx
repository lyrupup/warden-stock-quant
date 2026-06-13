import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/app/layout";
import { RequireAuth, RequireRole } from "@/app/guards";
import { SessionBootstrap } from "@/app/session-bootstrap";
import { ERole } from "@/types";
import { LoginPage, RegisterPage } from "@/features/auth";
import { DashboardPage } from "@/features/dashboard";
import { AccountPage } from "@/features/account";
import { DatasetsPage } from "@/features/datasets";
import { StrategiesPage } from "@/features/strategies";
import { BacktestsPage, BacktestComparePage, OptimizationsPage } from "@/features/backtests";
import { FactorsPage } from "@/features/factors";
import { PortfoliosPage } from "@/features/portfolios";
import { TradingPage } from "@/features/trading";
import { RiskPage } from "@/features/risk";
import { AlertsPage } from "@/features/alerts";
import { AdminPage } from "@/features/admin";
import { ForbiddenPage, NotFoundPage } from "@/features/errors";

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 公开路由 */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        {/* 受保护路由（统一布局） */}
        <Route
          element={
            <RequireAuth>
              <SessionBootstrap>
                <AppLayout />
              </SessionBootstrap>
            </RequireAuth>
          }
        >
          <Route path="/" element={<DashboardPage />} />
          <Route path="/datasets" element={<DatasetsPage />} />
          <Route path="/strategies" element={<StrategiesPage />} />
          <Route path="/strategies/:id" element={<StrategiesPage />} />
          <Route path="/backtests" element={<BacktestsPage />} />
          <Route path="/backtests/compare" element={<BacktestComparePage />} />
          <Route path="/backtests/:id" element={<BacktestsPage />} />
          <Route path="/optimizations" element={<OptimizationsPage />} />
          <Route path="/optimizations/:id" element={<OptimizationsPage />} />
          <Route path="/factors" element={<FactorsPage />} />
          <Route path="/factors/:id" element={<FactorsPage />} />
          <Route path="/portfolios" element={<PortfoliosPage />} />
          <Route path="/portfolios/:id" element={<PortfoliosPage />} />
          <Route path="/trading" element={<TradingPage />} />
          <Route path="/risk" element={<RiskPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/account" element={<AccountPage />} />

          {/* 管理员路由 */}
          <Route
            path="/admin/*"
            element={
              <RequireRole role={ERole.Admin}>
                <AdminPage />
              </RequireRole>
            }
          />

          <Route path="/403" element={<ForbiddenPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
