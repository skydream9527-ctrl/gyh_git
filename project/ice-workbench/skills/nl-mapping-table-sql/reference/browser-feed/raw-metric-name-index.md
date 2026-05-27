# Browser Feed - 底表/宽表指标名称索引

> **数据层级**：底表/宽表（dwm/dwd 层）

## Browser Main App (浏览器主端) - 底表/宽表指标

| Metric ID | Metric Name (CN) | Metric Name (EN) | Category |
|-----------|------------------|------------------|----------|
| BM001 | 浏览器主启DAU | browser_main_launch_dau | User Scale |
| BM002 | 浏览器有效DAU | browser_valid_dau | User Scale |
| BM003 | 浏览器消费UV | browser_consumption_uv | Consumption |

## Browser Feed (浏览器信息流) - 底表/宽表指标

| Metric ID | Metric Name (CN) | Metric Name (EN) | Category |
|-----------|------------------|------------------|----------|
| BF001 | 浏览器一级页VV | browser_level1_page_vv | Page View |
| BF002 | 浏览器短会话UV | browser_short_session_uv | Session |
| BF003 | 浏览器长会话UV | browser_long_session_uv | Session |
| BF004 | 浏览器二级页VV | browser_level2_page_vv | Page View |
| BF005 | 图文详情页VV/时长 | news_detail_vv_duration | Content |
| BF006 | 视频详情页VV/时长 | video_detail_vv_duration | Content |
| BF007 | 浏览器搜索SUG页UV | browser_search_sug_uv | Search |
| BF008 | 浏览器开屏UV | browser_splash_uv | Ad |

---

## Usage

When user mentions a metric, map it to the corresponding Metric ID and look up the SQL template in the raw-* reference files.

### Example Mapping

| User Input | Mapped Metric | Reference File |
|------------|---------------|----------------|
| "主启DAU" | BM001 | raw-core-metrics-reference.md |
| "消费UV" | BM003 | raw-core-metrics-reference.md |
| "一级页浏览量" | BF001 | raw-core-metrics-reference.md |
| "搜索SUG页" | BF007 | raw-event-metrics-reference.md |
