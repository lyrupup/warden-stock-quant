import { AppProviders } from "./providers";
import { AppRouter } from "./router";
import "@/core/i18n";

export function App() {
  return (
    <AppProviders>
      <AppRouter />
    </AppProviders>
  );
}
