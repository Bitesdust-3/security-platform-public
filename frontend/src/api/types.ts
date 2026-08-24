export interface User {
  id: number;
  username: string;
  display_name: string | null;
  is_active: boolean;
  roles: string[];
}
export interface TokenResponse {
  access_token: string;
  token_type: string;
}
export interface RiskOverview {
  asset_count: number;
  vulnerability_count: number;
  open_vulnerability_count: number;
  high_risk_count: number;
  critical_risk_count: number;
  risk_distribution: Record<string, number>;
}
export interface RiskLevels {
  critical: number;
  high: number;
  medium: number;
  low: number;
}
export interface RiskTrendPoint {
  date: string;
  vulnerability_count: number;
  risk_score: number;
}
export interface TopRiskAsset { asset_id?: number; ip_address: string | null; hostname: string | null; vulnerability_count: number; highest_risk_level: string; risk_score: number; }
export interface Asset {
  id: number;
  asset_name: string;
  asset_type: string;
  ip_address: string | null;
  hostname: string | null;
  environment: string | null;
  importance: number;
  owner: string | null;
  status: string;
  os_info?: string | null;
  description: string | null;
  services?: AssetService[];
}
export interface AssetService { id: number; port: number; protocol: string; service_name: string | null; service_version: string | null; }
export interface AssetList {
  data: Asset[];
  total: number;
  page: number;
  page_size: number;
}
export interface Scan {
  id: number;
  task_name: string;
  scan_type: string;
  target: string;
  status: string;
  created_at?: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  result_summary?: string | null;
}
export interface ScanResult { id: number; scan_task_id: number; asset_id: number | null; result_type: string; raw_summary: string | null; normalized_data: string | null; created_at: string; }
export interface ScanSchedule { id: number; task_name: string; target: string; asset_id: number | null; scan_type: string; schedule_type: string; execute_at: string | null; cron_expression: string | null; status: string; created_by: number | null; last_run_at: string | null; next_run_at: string | null; error_message: string | null; created_at: string; updated_at: string; }
export interface Vulnerability {
  id: number;
  title: string;
  cve_id: string | null;
  severity: string;
  cvss_score?: number | null;
  status: string;
  asset_id?: number | null;
  source: string | null;
  remediation: string | null;
  description?: string | null;
  created_at?: string;
}
export interface VulnerabilityList {
  data: Vulnerability[];
  total: number;
  page: number;
  page_size: number;
}
export interface CveIntelligence { id:number; cve_id:string; title:string|null; description:string|null; cvss_score:number|null; severity:string; affected_products:string[]; references:string[]; published_at:string|null; last_modified_at:string|null; source:string; synced_at:string; }
export interface CveList { data:CveIntelligence[]; total:number; page:number; page_size:number; }
export interface SecurityReport { id:number; report_name:string; period_start:string; period_end:string; generated_at:string; asset_count:number; online_asset_count:number; high_risk_asset_count:number; vulnerability_count:number; cve_count:number; high_risk_vulnerability_count:number; risk_distribution:Record<string,number>; scan_statistics:Record<string,number>; vulnerability_trend:any[]; top_risk_assets:any[]; recommendations:string[]; created_by:number|null; }
