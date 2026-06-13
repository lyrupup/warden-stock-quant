import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "@/core/auth";
import { describeError } from "@/core/http";
import {
  Button,
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
import { registerSchema, type TRegisterForm } from "./schemas";
import { AuthShell } from "./login-page";

export function RegisterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const setSession = useAuthStore((s) => s.setSession);
  const setUser = useAuthStore((s) => s.setUser);
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<TRegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: "", username: "", password: "", confirmPassword: "" },
  });

  const onSubmit = async (values: TRegisterForm) => {
    setSubmitting(true);
    try {
      const tokens = await authApi.register({
        email: values.email,
        username: values.username || undefined,
        password: values.password,
      });
      setSession(tokens);
      try {
        const me = await authApi.me();
        setUser(me);
      } catch {
        /* 忽略，会话引导会重试 */
      }
      toast.success(t("auth.registerSuccess"));
      navigate("/", { replace: true });
    } catch (err) {
      toast.error(describeError(err) || t("auth.registerFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell title={t("auth.registerTitle")} description={import.meta.env.VITE_APP_NAME}>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("auth.email")}</FormLabel>
                <FormControl>
                  <Input type="email" autoComplete="email" placeholder="name@example.com" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="username"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("auth.username")}</FormLabel>
                <FormControl>
                  <Input autoComplete="nickname" {...field} />
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
                  <Input type="password" autoComplete="new-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="confirmPassword"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t("auth.confirmPassword")}</FormLabel>
                <FormControl>
                  <Input type="password" autoComplete="new-password" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
            {t("auth.register")}
          </Button>
        </form>
      </Form>
      <p className="mt-4 text-center text-sm text-muted-foreground">
        <Link to="/login" className="text-primary hover:underline">
          {t("auth.toLogin")}
        </Link>
      </p>
    </AuthShell>
  );
}
