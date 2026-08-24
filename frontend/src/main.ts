import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import App from "./App.vue";
import router from "./router";
import "./styles.css";
document.title = "企业安全运营平台 · Security Operations";

createApp(App).use(createPinia()).use(router).use(ElementPlus).mount("#app");
