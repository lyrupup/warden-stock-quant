import { useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { Activity, Loader2 } from "lucide-react";
import { useAuthStore } from "@/core/auth";
import { describeError } from "@/core/http";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  Input,
  toast,
} from "@/core/ui";
import { authApi } from "./auth-api";
import { loginSchema, type TLoginForm } from "./schemas";

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const setSession = useAuthStore((s) => s.setSession);
  const setUser = useAuthStore((s) => s.setUser);
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<TLoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: { account: "", password: "" },
  });

  const onSubmit = async (values: TLoginForm) => {
    setSubmitting(true);
    try {
      const tokens = await authApi.login(values);
      setSession(tokens);
      try {
        const me = await authApi.me();
        setUser(me);
      } catch {
        /* /me 失败不阻断登录，后续会话引导会重试 */
      }
      toast.success(t("auth.loginSuccess"));
      const from = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(from, { replace: true });
    } catch (err) {
      toast.error(describeError(err) || t("auth.loginFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell title={t("auth.loginTitle")} description={import.meta.env.VITE_APP_NAME}>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <FormField
            control={form.control}
            name="account"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("auth.account")}</FormLabel>
                <FormControl>
                  <Input autoComplete="username" placeholder="name@example.com" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("auth.password")}</FormLabel>
                <FormControl>
                  <Input type="password" autoComplete="current-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {t("auth.login")}
          </Button>
        </form>
      </Form>
      <p className="mt-4 text-center text-sm text-muted-foreground">
        <Link to="/register" className="text-primary hover:underline">
          {t("auth.toRegister")}
        </Link>
      </p>
    </AuthShell>
  );
}

/** 鉴权页通用外壳（居中卡片），供登录/注册复用 */
export function AuthShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-2 text-center">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Activity className="h-5 w-5 text-primary" />
          </div>
          <CardTitle className="text-xl">{title}</CardTitle>
          {description ? <CardDescription>{description}</CardDescription> : null}
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </div>
  );
}
