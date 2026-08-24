import { defineStore } from "pinia";
import client from "../api/client";
import type { User } from "../api/types";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("access_token") || "",
    user: null as User | null,
  }),
  getters: { isAuthenticated: (state) => Boolean(state.token) },
  actions: {
    async login(username: string, password: string) {
      const { data } = await client.post("/auth/login", { username, password });
      this.token = data.access_token;
      localStorage.setItem("access_token", this.token);
      await this.fetchMe();
    },
    async fetchMe() {
      const { data } = await client.get<User>("/auth/me");
      this.user = data;
    },
    logout() {
      this.token = "";
      this.user = null;
      localStorage.removeItem("access_token");
    },
  },
});
