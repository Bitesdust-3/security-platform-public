<template>
  <div class="login-page">
    <div class="login-intro">
      <div class="intro-kicker">SECUREOPS · SECURITY OPERATIONS CENTER</div>
      <h1>让风险可见，<br /><span>让运营更有序。</span></h1>
      <p>面向企业授权资产的安全运营工作台，集中管理资产、扫描、漏洞与风险。</p>
      <div class="intro-points"><span>● 资产可视化</span><span>● 风险可解释</span><span>● 全程可审计</span></div>
    </div>
    <el-card class="login-card"
      ><LogoMark compact /><h2>SecureOps 登录</h2><p class="login-subtitle">企业级安全运营控制台</p>
      <el-form @submit.prevent="submit"
        ><el-form-item
          ><el-input
            v-model="form.username"
            placeholder="用户名" /></el-form-item
        ><el-form-item
          ><el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="密码" /></el-form-item
        ><el-button
          type="primary"
          native-type="submit"
          :loading="loading"
          class="full-width"
          >登录</el-button
        ></el-form
      ></el-card
    >
  </div>
</template>
<script setup lang="ts">
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { useAuthStore } from "../stores/auth";
import { useRouter } from "vue-router";
import LogoMark from "../components/LogoMark.vue";
const auth = useAuthStore();
const router = useRouter();
const loading = ref(false);
const form = reactive({ username: "", password: "" });
const submit = async () => {
  if (!form.username || !form.password)
    return ElMessage.warning("请输入用户名和密码");
  loading.value = true;
  try {
    await auth.login(form.username, form.password);
    router.push("/dashboard");
  } catch {
    ElMessage.error("登录失败，请检查账号或服务状态");
  } finally {
    loading.value = false;
  }
};
</script>
