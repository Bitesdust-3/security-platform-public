<template>
  <span class="logo-mark" :class="{ compact }" aria-label="SecureOps Logo">
    <img :src="logo" alt="SecureOps" />
    <span class="logo-radar" aria-hidden="true" />
  </span>
</template>

<script setup lang="ts">
import logo from "../assets/secureops-logo.png";
defineProps<{ compact?: boolean }>();
</script>
