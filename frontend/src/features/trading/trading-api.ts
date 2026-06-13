import { api, unwrap } from "@/core/http";
import type { TPageData } from "@/types";

export type TOrder = {
  id: number;
  code: string;
  side: string;
  order_type: string;
  price?: string;
  qty: number;
  filled_qty: number;
  status: string;
  gateway: string;
  reason?: string;
  trade_date?: string;
  created_at: string;
};

export type TTrade = {
  id: number;
  order_id: number;
  code: string;
  side: string;
  price?: string;
  qty: number;
  amount?: string;
  commission?: string;
  tax?: string;
  trade_time: string;
};

export type TSignal = {
  code: string;
  side: string;
  qty: number;
  price: number;
  reason: string;
};

export const tradingApi = {
  listOrders: (portfolioId: number, page = 1, size = 20) =>
    unwrap<TPageData<TOrder>>(
      api.get(`portfolios/${portfolioId}/orders`, { searchParams: { page, size } }),
    ),

  listTrades: (portfolioId: number, page = 1, size = 20) =>
    unwrap<TPageData<TTrade>>(
      api.get(`portfolios/${portfolioId}/trades`, { searchParams: { page, size } }),
    ),

  listSignals: (portfolioId: number) =>
    unwrap<TSignal[]>(api.get(`portfolios/${portfolioId}/signals`)),

  submitOrder: (
    portfolioId: number,
    payload: {
      code: string;
      side: "buy" | "sell";
      qty: number;
      order_type?: "limit" | "market";
      price?: number;
    },
  ) => unwrap<TOrder>(api.post(`portfolios/${portfolioId}/orders`, { json: payload })),

  cancelOrder: (orderId: number) => unwrap<TOrder>(api.post(`orders/${orderId}/cancel`)),
};
