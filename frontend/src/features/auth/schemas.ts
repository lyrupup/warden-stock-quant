import { z } from "zod";

export const loginSchema = z.object({
  account: z.string().min(1, "请输入邮箱或用户名"),
  password: z.string().min(8, "密码至少 8 位"),
});
export type TLoginForm = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    email: z.string().email("邮箱格式不正确"),
    username: z.string().optional(),
    password: z.string().min(8, "密码至少 8 位"),
    confirmPassword: z.string().min(8, "密码至少 8 位"),
  })
  .refine((d) => d.password === d.confirmPassword, {
    message: "两次输入的密码不一致",
    path: ["confirmPassword"],
  });
export type TRegisterForm = z.infer<typeof registerSchema>;
