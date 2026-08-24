import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: () => import("../views/LoginView.vue") },
    {
      path: "/",
      component: () => import("../layouts/AppLayout.vue"),
      meta: { requiresAuth: true },
      children: [
        { path: "", redirect: "/dashboard" },
        {
          path: "dashboard",
          component: () => import("../views/DashboardView.vue"),
        },
        { path: "assets", component: () => import("../views/AssetsView.vue") },
        { path: "scans", component: () => import("../views/ScansView.vue") },
        { path: "scan-schedules", component: () => import("../views/ScanSchedulesView.vue") },
        {
          path: "vulnerabilities",
          component: () => import("../views/VulnerabilitiesView.vue"),
        },
        { path: "cve", component: () => import("../views/CveView.vue") },
        { path: "reports", component: () => import("../views/ReportsView.vue") },
        { path: "audit", component: () => import("../views/AuditView.vue") },
      ],
    },
  ],
});
router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.meta.requiresAuth && !auth.isAuthenticated) return "/login";
  if (to.path === "/login" && auth.isAuthenticated) return "/dashboard";
});
export default router;
