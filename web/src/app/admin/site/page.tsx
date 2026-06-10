"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { adminApi, type SiteUser } from "@/lib/admin-api";
import { getAdminToken } from "@/lib/admin-auth";
import { SectionCard, SectionCardHeader } from "@/components/ui/section-card";
import {
  BtnPrimary,
  controlInputClass,
  FormLabel,
} from "@/components/ui/form-field";

export default function AdminSitePage() {
  const qc = useQueryClient();
  const [msg, setMsg] = useState("");
  const [title, setTitle] = useState("投资回撤提醒-定投计算器工具");
  const [newPhone, setNewPhone] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newName, setNewName] = useState("");
  const [editing, setEditing] = useState<SiteUser | null>(null);
  const [editPhone, setEditPhone] = useState("");
  const [editPassword, setEditPassword] = useState("");
  const [editName, setEditName] = useState("");
  const [editEnabled, setEditEnabled] = useState(true);

  const authed = !!getAdminToken();
  const siteQ = useQuery({
    queryKey: ["admin-site-config"],
    queryFn: adminApi.getSiteConfig,
    enabled: authed,
  });
  const usersQ = useQuery({
    queryKey: ["admin-site-users"],
    queryFn: adminApi.listSiteUsers,
    enabled: authed,
  });
  const logsQ = useQuery({
    queryKey: ["admin-login-logs"],
    queryFn: () => adminApi.listLoginLogs({ limit: 100 }),
    enabled: authed,
  });

  useEffect(() => {
    const site = siteQ.data?.config?.site;
    if (site) {
      setTitle(site.title ?? "投资回撤提醒-定投计算器工具");
    }
  }, [siteQ.data]);

  const saveSiteMut = useMutation({
    mutationFn: () => {
      const base = siteQ.data?.config ?? {};
      return adminApi.saveSiteConfig({
        ...base,
        site: {
          ...(base.site ?? {}),
          title: title.trim() || "投资回撤提醒-定投计算器工具",
          frontend_login_enabled: false,
        },
      });
    },
    onSuccess: () => {
      setMsg("站点配置已保存");
      qc.invalidateQueries({ queryKey: ["admin-site-config"] });
      qc.invalidateQueries({ queryKey: ["site-config"] });
    },
    onError: (e: Error) => setMsg(e.message),
  });

  const createUserMut = useMutation({
    mutationFn: () =>
      adminApi.createSiteUser({
        phone: newPhone.trim(),
        password: newPassword,
        display_name: newName.trim() || undefined,
      }),
    onSuccess: () => {
      setMsg("用户已创建");
      setNewPhone("");
      setNewPassword("");
      setNewName("");
      qc.invalidateQueries({ queryKey: ["admin-site-users"] });
    },
    onError: (e: Error) => setMsg(e.message),
  });

  const updateUserMut = useMutation({
    mutationFn: () => {
      if (!editing) throw new Error("未选择用户");
      return adminApi.updateSiteUser(editing.id, {
        phone: editPhone.trim(),
        password: editPassword || undefined,
        display_name: editName.trim() || undefined,
        enabled: editEnabled,
      });
    },
    onSuccess: () => {
      setMsg("用户已更新");
      setEditing(null);
      setEditPassword("");
      qc.invalidateQueries({ queryKey: ["admin-site-users"] });
    },
    onError: (e: Error) => setMsg(e.message),
  });

  const deleteUserMut = useMutation({
    mutationFn: (id: number) => adminApi.deleteSiteUser(id),
    onSuccess: () => {
      setMsg("用户已删除");
      qc.invalidateQueries({ queryKey: ["admin-site-users"] });
    },
    onError: (e: Error) => setMsg(e.message),
  });

  const deleteLogMut = useMutation({
    mutationFn: (id: number) => adminApi.deleteLoginLog(id),
    onSuccess: () => {
      setMsg("日志已删除");
      qc.invalidateQueries({ queryKey: ["admin-login-logs"] });
    },
    onError: (e: Error) => setMsg(e.message),
  });

  function startEdit(user: SiteUser) {
    setEditing(user);
    setEditPhone(user.phone);
    setEditPassword("");
    setEditName(user.display_name ?? "");
    setEditEnabled(user.enabled);
  }

  return (
    <div className="space-y-6">
      {msg && <div className="alert-banner alert-banner--info text-xs">{msg}</div>}

      <SectionCard className="space-y-4">
        <SectionCardHeader
          title="站点设置"
          subtitle="网站标题；指数首页与计算器公开访问，登录用户使用「我的基金」与「回撤提醒」"
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <FormLabel>网站标题</FormLabel>
            <input
              className={controlInputClass}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
        </div>
        <p className="text-xs text-muted">
          首页纳斯达克100等指数、复利/All in 计算器无需登录；「我的基金」与「回撤提醒」需登录后使用。
        </p>
        <BtnPrimary
          className="!w-auto px-6"
          disabled={saveSiteMut.isPending}
          onClick={() => saveSiteMut.mutate()}
        >
          {saveSiteMut.isPending ? "保存中…" : "保存站点设置"}
        </BtnPrimary>
      </SectionCard>

      <SectionCard className="space-y-4">
        <SectionCardHeader title="前台用户" subtitle="手机号登录账号管理" />
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <FormLabel>手机号</FormLabel>
            <input
              className={controlInputClass}
              value={newPhone}
              onChange={(e) => setNewPhone(e.target.value)}
              placeholder="13800138000"
            />
          </div>
          <div>
            <FormLabel>密码</FormLabel>
            <input
              type="password"
              className={controlInputClass}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <div>
            <FormLabel>昵称（可选）</FormLabel>
            <input
              className={controlInputClass}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
          </div>
        </div>
        <button
          type="button"
          className="rounded-lg border border-border px-4 py-2 text-xs hover:bg-card"
          disabled={createUserMut.isPending}
          onClick={() => createUserMut.mutate()}
        >
          {createUserMut.isPending ? "创建中…" : "新增用户"}
        </button>

        <div className="overflow-x-auto rounded-lg border border-border/50">
          <table className="w-full min-w-[560px] text-left text-xs">
            <thead className="bg-background/40 text-muted">
              <tr>
                <th className="px-3 py-2">手机号</th>
                <th className="px-3 py-2">昵称</th>
                <th className="px-3 py-2">状态</th>
                <th className="px-3 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {(usersQ.data?.items ?? []).map((user) => (
                <tr key={user.id} className="border-t border-border/40">
                  <td className="px-3 py-2 font-mono">{user.phone}</td>
                  <td className="px-3 py-2">{user.display_name ?? "—"}</td>
                  <td className="px-3 py-2">
                    {user.enabled ? (
                      <span className="text-emerald-400">启用</span>
                    ) : (
                      <span className="text-amber-400">禁用</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      className="mr-2 text-primary hover:underline"
                      onClick={() => startEdit(user)}
                    >
                      编辑
                    </button>
                    <button
                      type="button"
                      className="text-danger hover:underline"
                      onClick={() => {
                        if (confirm(`删除用户 ${user.phone}？`)) {
                          deleteUserMut.mutate(user.id);
                        }
                      }}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {editing && (
          <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 space-y-3">
            <p className="text-sm font-medium">编辑用户 #{editing.id}</p>
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <FormLabel>手机号</FormLabel>
                <input
                  className={controlInputClass}
                  value={editPhone}
                  onChange={(e) => setEditPhone(e.target.value)}
                />
              </div>
              <div>
                <FormLabel>新密码（留空不改）</FormLabel>
                <input
                  type="password"
                  className={controlInputClass}
                  value={editPassword}
                  onChange={(e) => setEditPassword(e.target.value)}
                />
              </div>
              <div>
                <FormLabel>昵称</FormLabel>
                <input
                  className={controlInputClass}
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={editEnabled}
                onChange={(e) => setEditEnabled(e.target.checked)}
              />
              启用
            </label>
            <div className="flex gap-2">
              <BtnPrimary
                className="!w-auto px-6"
                disabled={updateUserMut.isPending}
                onClick={() => updateUserMut.mutate()}
              >
                保存用户
              </BtnPrimary>
              <button
                type="button"
                className="rounded-lg border border-border px-4 py-2 text-xs"
                onClick={() => setEditing(null)}
              >
                取消
              </button>
            </div>
          </div>
        )}
      </SectionCard>

      <SectionCard className="space-y-4">
        <SectionCardHeader title="登录日志" subtitle="前台与管理后台登录记录" />
        <div className="overflow-x-auto rounded-lg border border-border/50">
          <table className="w-full min-w-[720px] text-left text-xs">
            <thead className="bg-background/40 text-muted">
              <tr>
                <th className="px-3 py-2">时间</th>
                <th className="px-3 py-2">账号</th>
                <th className="px-3 py-2">类型</th>
                <th className="px-3 py-2">结果</th>
                <th className="px-3 py-2">IP</th>
                <th className="px-3 py-2">说明</th>
                <th className="px-3 py-2">操作</th>
              </tr>
            </thead>
            <tbody>
              {(logsQ.data?.items ?? []).map((log) => (
                <tr key={log.id} className="border-t border-border/40">
                  <td className="px-3 py-2 whitespace-nowrap">
                    {log.created_at?.replace("T", " ").slice(0, 19) ?? "—"}
                  </td>
                  <td className="px-3 py-2 font-mono">{log.phone}</td>
                  <td className="px-3 py-2">{log.login_type}</td>
                  <td className="px-3 py-2">
                    {log.success ? (
                      <span className="text-emerald-400">成功</span>
                    ) : (
                      <span className="text-danger">失败</span>
                    )}
                  </td>
                  <td className="px-3 py-2">{log.ip ?? "—"}</td>
                  <td className="px-3 py-2 text-muted">
                    {log.failure_reason ?? log.user_agent?.slice(0, 40) ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      className="text-danger hover:underline"
                      onClick={() => deleteLogMut.mutate(log.id)}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionCard>
    </div>
  );
}
