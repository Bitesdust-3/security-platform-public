<template>
  <div v-loading="loading" class="dashboard-page soc-dashboard">
    <div class="soc-orbit orbit-one" aria-hidden="true"></div><div class="soc-orbit orbit-two" aria-hidden="true"></div>
    <div class="soc-particles" aria-hidden="true"><i v-for="n in 18" :key="n" :style="{ '--i': n }"></i></div>
    <div class="dashboard-hero soc-command"><div><div class="eyebrow">SECUREOPS · SECURITY COMMAND CENTER</div><h2>安全运营指挥中心</h2><p>持续掌握组织资产与安全风险状态，聚焦需要优先处理的问题。</p></div><div class="security-score"><span>当前安全评分</span><strong>{{ securityScore }}</strong><el-tag type="success" effect="dark">系统运行正常</el-tag></div></div>
    <el-row :gutter="16"
      ><el-col v-for="(card, index) in cards" :key="card.label" :span="6" class="metric-col" :style="{ '--delay': `${index * 90}ms` }"
        ><el-card class="metric-card"
          ><div class="metric-top"><span class="metric-icon">{{ card.icon }}</span><span class="metric-label">{{ card.label }}</span></div>
          <div class="metric-value"><span>{{ animatedValues[index] }}</span><small v-if="index === 0">台</small></div></el-card
        ></el-col
      ></el-row
    ><el-row :gutter="16" class="section-card"
      ><el-col :span="12"
        ><el-card
          ><template #header>风险等级分布</template>
          <div v-if="hasLevels" ref="levelChart" class="chart chart-glow" /><el-empty v-else description="暂无风险等级数据" :image-size="80" /></el-card></el-col
      ><el-col :span="12"
        ><el-card
          ><template #header>风险趋势</template>
          <div v-if="trend.length" ref="trendChart" class="chart chart-glow" /><el-empty v-else description="暂无趋势数据" :image-size="80" /></el-card></el-col
    ></el-row><el-card class="section-card risk-table-card"><template #header><span>高风险资产排行</span><span class="live-indicator"><i/>实时数据</span></template><el-table v-if="topAssets.length" :data="topAssets"><el-table-column prop="ip_address" label="IP"/><el-table-column prop="hostname" label="主机名"/><el-table-column prop="vulnerability_count" label="漏洞数"/><el-table-column prop="highest_risk_level" label="最高等级"/><el-table-column prop="risk_score" label="风险分"><template #default="{row}"><span class="risk-score">{{ row.risk_score }}</span></template></el-table-column></el-table><el-empty v-else description="暂无高风险资产" :image-size="80"/></el-card>
  </div>
</template>
<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { PieChart, LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import client from "../api/client";
import type { RiskOverview, RiskLevels, RiskTrendPoint, TopRiskAsset, Scan, AssetList } from "../api/types";
use([CanvasRenderer, PieChart, LineChart, GridComponent, TooltipComponent]);
const levelChart = ref<HTMLElement>();
const trendChart = ref<HTMLElement>();
const loading = ref(true);
const levels = ref<RiskLevels>({ critical: 0, high: 0, medium: 0, low: 0 });
const trend = ref<RiskTrendPoint[]>([]);
const topAssets = ref<TopRiskAsset[]>([]);
const scanCount = ref(0);
const animatedValues = ref([0, 0, 0, 0, 0]);
const assetTypes = ref<Record<string, number>>({});
const securityScore = computed(() => Math.max(0, 100 - overview.value.critical_risk_count * 12 - overview.value.high_risk_count * 5));
const overview = ref<RiskOverview>({
  asset_count: 0,
  vulnerability_count: 0,
  open_vulnerability_count: 0,
  high_risk_count: 0,
  critical_risk_count: 0,
  risk_distribution: {},
});
const cards = computed(() => [
  { label: "资产总数", value: overview.value.asset_count, icon: "▣" },
  { label: "漏洞总数", value: overview.value.vulnerability_count, icon: "!" },
  { label: "开放漏洞", value: overview.value.open_vulnerability_count, icon: "◷" },
  { label: "高危及以上", value: overview.value.high_risk_count, icon: "▲" },
  { label: "扫描任务", value: scanCount.value, icon: "⌁" },
]);
const hasLevels = computed(() => Object.values(levels.value).some(Boolean));
const animateMetrics = () => { const target = cards.value.map((card) => Number(card.value) || 0); const started = performance.now(); const tick = (now: number) => { const progress = Math.min(1, (now - started) / 850); animatedValues.value = target.map((value) => Math.round(value * (1 - Math.pow(1 - progress, 3)))); if (progress < 1) requestAnimationFrame(tick); }; requestAnimationFrame(tick); };
onMounted(async () => {
  try {
    const [summary, levelsResponse, trendResponse, topResponse, scansResponse, assetsResponse] = await Promise.all([
      client.get("/risk/overview"),
      client.get<RiskLevels>("/risk/levels"),
      client.get<RiskTrendPoint[]>("/risk/trend"),
      client.get<TopRiskAsset[]>("/risk/top-assets"),
      client.get<Scan[]>("/scans"),
      client.get<AssetList>("/assets", { params: { page: 1, page_size: 100 } }),
    ]);
    overview.value = summary.data;
    levels.value = levelsResponse.data;
    trend.value = trendResponse.data;
    topAssets.value = topResponse.data;
    scanCount.value = scansResponse.data.length;
    assetTypes.value = assetsResponse.data.data.reduce<Record<string, number>>((result, asset) => { result[asset.asset_type] = (result[asset.asset_type] || 0) + 1; return result; }, {});
    animateMetrics();
    await nextTick();
    if (levelChart.value)
      echarts
        .init(levelChart.value)
        .setOption({
          tooltip: { trigger: "item" },
          color: ["#ff526d", "#ff9c45", "#ffd166", "#35e6d2"],
          animationDuration: 1100,
          series: [
            {
              type: "pie",
              radius: "65%",
          data: Object.entries(levels.value).map(([name, value]) => ({
                name,
                value,
              })),
            },
          ],
        });
    if (trendChart.value)
      echarts
        .init(trendChart.value)
        .setOption({
          tooltip: { trigger: "axis" },
          animationDuration: 1200,
          grid: { left: 36, right: 18, top: 20, bottom: 28 },
          xAxis: {
            type: "category",
            data: trend.value.map((item) => item.date),
          },
          yAxis: { type: "value" },
          series: [
            {
              type: "line",
              data: trend.value.map((item) => item.risk_score),
              smooth: true, symbol: "circle", symbolSize: 8, lineStyle: { width: 3, color: "#35e6d2" }, itemStyle: { color: "#35e6d2", shadowBlur: 12, shadowColor: "#35e6d2" }, areaStyle: { color: "rgba(53,230,210,.12)" },
            },
          ],
        });
  } catch { /* 保持空状态 */ } finally { loading.value = false; }
});
</script>
