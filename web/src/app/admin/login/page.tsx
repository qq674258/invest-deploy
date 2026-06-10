"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { adminApi } from "@/lib/admin-api";
import { setAdminToken, setAdminPermissions } from "@/lib/admin-auth";
import { SectionCard } from "@/components/ui/section-card";
import { BtnPrimary, controlInputClass, FormLabel } from "@/components/ui/form-field";

export default function AdminLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await adminApi.login(username, password);
      setAdminToken(res.token);
      const me = await adminApi.me();
      setAdminPermissions(me.permissions, me.is_superuser);
      router.replace("/admin/funds");
    } catch {
      setError("登录失败，请检查用户名与密码（默认见 .env ADMIN_*）");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <SectionCard variant="primary" className="w-full max-w-md space-y-5">
        <div>
          <h1 className="text-xl font-semibold">管理后台登录</h1>
          <p className="mt-1 text-xs text-muted">
            请在项目根目录 <code className="text-foreground">.env</code> 配置 ADMIN_USERNAME / ADMIN_PASSWORD，并
            <code className="text-foreground"> docker compose restart api</code>
          </p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <FormLabel>用户名</FormLabel>
            <input
              className={controlInputClass}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </div>
          <div>
            <FormLabel>密码</FormLabel>
            <input
              type="password"
              className={controlInputClass}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>
          {error && <p className="text-sm text-danger">{error}</p>}
          <BtnPrimary type="submit" disabled={loading}>
            {loading ? "登录中…" : "登录"}
          </BtnPrimary>
        </form>
      </SectionCard>
    </div>
  );
}
