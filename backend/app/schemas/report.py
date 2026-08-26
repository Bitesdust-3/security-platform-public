from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
class ReportCreate(BaseModel):
    report_name: str = Field(default="企业安全运营报告", min_length=1, max_length=160)
    period_start: datetime
    period_end: datetime
class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:int; report_name:str; period_start:datetime; period_end:datetime; generated_at:datetime; asset_count:int; online_asset_count:int; high_risk_asset_count:int; vulnerability_count:int; cve_count:int; high_risk_vulnerability_count:int; risk_distribution:dict; scan_statistics:dict; vulnerability_trend:list; top_risk_assets:list; top_vulnerabilities:list; recommendations:list; created_by:int|None; status:str; archived_at:datetime|None
