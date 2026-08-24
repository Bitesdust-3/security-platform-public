<template>
  <el-container class="app-shell"
    ><el-aside width="240px" class="sidebar"
      ><BrandLogo />
      <el-menu router :default-active="$route.path" class="side-menu"
        ><el-menu-item index="/dashboard"><span class="menu-icon">⌂</span>风险总览</el-menu-item
        ><el-menu-item index="/assets"><span class="menu-icon">▣</span>资产管理</el-menu-item
        ><el-menu-item index="/scans"><span class="menu-icon">⌁</span>扫描任务</el-menu-item
        ><el-menu-item index="/scan-schedules"><span class="menu-icon">◫</span>自动化巡检</el-menu-item
        ><el-menu-item index="/vulnerabilities"><span class="menu-icon">!</span>漏洞管理</el-menu-item><el-menu-item index="/cve"><span class="menu-icon">◈</span>CVE 情报</el-menu-item><el-menu-item index="/reports"><span class="menu-icon">▤</span>安全报告</el-menu-item><el-menu-item index="/audit"><span class="menu-icon">◷</span>审计日志</el-menu-item></el-menu
      ><div class="sidebar-footer">授权资产 · 安全运营</div>
      </el-aside
    ><el-container
      ><el-header class="topbar"
        ><div class="topbar-context"><span class="topbar-dot" />生产安全控制台</div><span class="user-name">{{ auth.user?.display_name || auth.user?.username }}</span
        ><el-button link @click="signOut">退出</el-button></el-header
      ><el-main><router-view /></el-main></el-container
  ></el-container>
</template>
<script setup lang="ts">
import { useAuthStore } from "../stores/auth";
import { useRouter } from "vue-router";
import BrandLogo from "../components/BrandLogo.vue";

const auth = useAuthStore();
const router = useRouter();
const signOut = () => {
  auth.logout();
  router.push("/login");
};
</script>
