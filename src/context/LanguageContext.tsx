"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

export type Language = "en-US" | "en-GB" | "es-ES" | "fr-FR" | "de-DE" | "ja-JP" | "zh-CN";

const translations: Record<Language, Record<string, string>> = {
  "en-US": {
    manage: "MANAGE",
    comply: "COMPLY",
    audit: "AUDIT",
    dashboard: "Dashboard",
    organization: "Organization",
    assets: "Assets",
    riskRegister: "Risks",
    controls: "Controls",
    tickets: "Tickets",
    iso27001: "ISO 27001",
    gapAnalysis: "Gap Analysis",
    evidence: "Evidence",
    auditPrep: "Audit Prep",
    docAnalysis: "Doc Analysis",
    auditLog: "Audit Log",
    reports: "Reports",
    users: "Users",
    settings: "Settings",
    language: "Language",
    preferences: "Preferences",
    profile: "Profile",
    security: "Security",
    notifications: "Notifications",
    frameworks: "Frameworks",
    saveChanges: "Save Changes",
    active: "Active",
    download: "Download",
    preview: "Preview",
    search: "Search...",
    logout: "Log out",
  },
  "en-GB": {
    manage: "MANAGE",
    comply: "COMPLY",
    audit: "AUDIT",
    dashboard: "Dashboard",
    organization: "Organisation",
    assets: "Assets",
    riskRegister: "Risks",
    controls: "Controls",
    tickets: "Tickets",
    iso27001: "ISO 27001",
    gapAnalysis: "Gap Analysis",
    evidence: "Evidence",
    auditPrep: "Audit Prep",
    docAnalysis: "Doc Analysis",
    auditLog: "Audit Log",
    reports: "Reports",
    users: "Users",
    settings: "Settings",
    language: "Language",
    preferences: "Preferences",
    profile: "Profile",
    security: "Security",
    notifications: "Notifications",
    frameworks: "Frameworks",
    saveChanges: "Save Changes",
    active: "Active",
    download: "Download",
    preview: "Preview",
    search: "Search...",
    logout: "Log out",
  },
  "es-ES": {
    manage: "GESTIONAR",
    comply: "CUMPLIR",
    audit: "AUDITORÍA",
    dashboard: "Panel Principal",
    organization: "Organización",
    assets: "Activos",
    riskRegister: "Riesgos",
    controls: "Controles",
    tickets: "Tickets",
    iso27001: "ISO 27001",
    gapAnalysis: "Análisis de Brechas",
    evidence: "Evidencia",
    auditPrep: "Prep. Auditoría",
    docAnalysis: "Análisis Doc.",
    auditLog: "Reg. Auditoría",
    reports: "Informes",
    users: "Usuarios",
    settings: "Configuración",
    language: "Idioma",
    preferences: "Preferencias",
    profile: "Perfil",
    security: "Seguridad",
    notifications: "Notificaciones",
    frameworks: "Marcos",
    saveChanges: "Guardar Cambios",
    active: "Activo",
    download: "Descargar",
    preview: "Vista Previa",
    search: "Buscar...",
    logout: "Cerrar sesión",
  },
  "fr-FR": {
    manage: "GÉRER",
    comply: "CONFORMITÉ",
    audit: "AUDIT",
    dashboard: "Tableau de Bord",
    organization: "Organisation",
    assets: "Actifs",
    riskRegister: "Risques",
    controls: "Contrôles",
    tickets: "Tickets",
    iso27001: "ISO 27001",
    gapAnalysis: "Analyse d'Écart",
    evidence: "Preuves",
    auditPrep: "Prép. Audit",
    docAnalysis: "Analyse Doc.",
    auditLog: "Journal d'Audit",
    reports: "Rapports",
    users: "Utilisateurs",
    settings: "Paramètres",
    language: "Langue",
    preferences: "Préférences",
    profile: "Profil",
    security: "Sécurité",
    notifications: "Notifications",
    frameworks: "Cadres",
    saveChanges: "Enregistrer les modifications",
    active: "Actif",
    download: "Télécharger",
    preview: "Aperçu",
    search: "Rechercher...",
    logout: "Déconnexion",
  },
  "de-DE": {
    manage: "VERWALTEN",
    comply: "COMPLIANCE",
    audit: "AUDIT",
    dashboard: "Dashboard",
    organization: "Organisation",
    assets: "Assets",
    riskRegister: "Risiken",
    controls: "Kontrollen",
    tickets: "Tickets",
    iso27001: "ISO 27001",
    gapAnalysis: "Gap-Analyse",
    evidence: "Nachweise",
    auditPrep: "Audit-Vorbereitung",
    docAnalysis: "Dokumenten-Analyse",
    auditLog: "Audit-Protokoll",
    reports: "Berichte",
    users: "Benutzer",
    settings: "Einstellungen",
    language: "Sprache",
    preferences: "Einstellungen",
    profile: "Profil",
    security: "Sicherheit",
    notifications: "Benachrichtigungen",
    frameworks: "Frameworks",
    saveChanges: "Änderungen speichern",
    active: "Aktiv",
    download: "Herunterladen",
    preview: "Vorschau",
    search: "Suchen...",
    logout: "Abmelden",
  },
  "ja-JP": {
    manage: "管理",
    comply: "コンプライアンス",
    audit: "監査",
    dashboard: "ダッシュボード",
    organization: "組織",
    assets: "資産",
    riskRegister: "リスク",
    controls: "管理策",
    tickets: "チケット",
    iso27001: "ISO 27001",
    gapAnalysis: "ギャップ分析",
    evidence: "証拠資料",
    auditPrep: "監査準備",
    docAnalysis: "文書分析",
    auditLog: "監査ログ",
    reports: "レポート",
    users: "ユーザー",
    settings: "設定",
    language: "言語",
    preferences: "環境設定",
    profile: "プロフィール",
    security: "セキュリティ",
    notifications: "通知",
    frameworks: "フレームワーク",
    saveChanges: "変更を保存",
    active: "アクティブ",
    download: "ダウンロード",
    preview: "プレビュー",
    search: "検索...",
    logout: "ログアウト",
  },
  "zh-CN": {
    manage: "管理",
    comply: "合规",
    audit: "审计",
    dashboard: "仪表板",
    organization: "组织机构",
    assets: "资产管理",
    riskRegister: "风险项",
    controls: "控制措施",
    tickets: "工单",
    iso27001: "ISO 27001",
    gapAnalysis: "差距分析",
    evidence: "证据档案",
    auditPrep: "审计准备",
    docAnalysis: "文档分析",
    auditLog: "审计日志",
    reports: "报告",
    users: "用户管理",
    settings: "设置",
    language: "语言",
    preferences: "偏好设置",
    profile: "个人资料",
    security: "安全",
    notifications: "通知",
    frameworks: "合规框架",
    saveChanges: "保存更改",
    active: "已启用",
    download: "下载",
    preview: "预览",
    search: "搜索...",
    logout: "退出登录",
  },
};

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>("en-US");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("app_language") as Language;
      if (saved && translations[saved]) {
        setLanguageState(saved);
      }
    }
  }, []);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    if (typeof window !== "undefined") {
      localStorage.setItem("app_language", lang);
    }
  };

  const t = (key: string): string => {
    return translations[language]?.[key] || translations["en-US"]?.[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
