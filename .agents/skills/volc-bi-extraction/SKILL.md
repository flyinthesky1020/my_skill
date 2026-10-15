---
name: volc-bi-extraction
description: 从火山引擎增长分析（DataFinder，console.volcengine.com/datafinder）和火山智能数据洞察（insight.msh.team，aeolus/DataWind）后台批量、可靠地取数：保存的分析结果直读、看板查询重放、漏斗参数窗口、明细报表全量拉取、UI 自动化改查询条件。当用户要给这类火山系 BI 后台的看板/事件分析做批量取数、转化率复盘、分日对比时使用。浏览器操作一律走 kimi-webbridge；写结果到飞书表格走 lark-sheets。
---

# 火山系 BI 后台取数经验

适用对象：
- **DataFinder（增长分析）**：`console.volcengine.com/datafinder/project/{pid}/event-analysis/result/{analysisId}`，事件分析（UV/新用户，按 user_is_new、$latest_referrer_host 等分组过滤）。
- **insight.msh.team BI（aeolus/DataWind）**：仪表盘 `#/dashboard/{id}`，图表（series）、漏斗（paramList 窗口）、明细表（raw_table/table）。

统一前提：用 kimi-webbridge 控浏览器（session 名固定一个）；网络抓包 `network start` 在页面操作前开；**重要 payload 落盘到工作目录而不是 /tmp（/tmp 会被系统清理）**。

## 一、DataFinder（事件分析）

### 1. 直读「已保存分析」的结果（首选，无需触发查询）

```
GET /datafinder/api/v1/analysis/{analysisId}/result?pack_dsl=1&normalize_version=...
Headers: x-csrf-token: <cookie csrfToken>, x-caller: portal, x-finder-app-id, x-finder-project-id
```
- 返回 `{data:[{date_index_list, data_item_list:[{group_by_key, data}]}], dsl}`，按天序列直接可用。
- 页面加载时必发此请求 → 先 `network start` 再 reload，`network detail` 拿 body 最快。
- POST 同路径改 DSL（如扩日期范围）必失败：`权限不足`/`操作失败`，不要浪费时间；PUT/POST /analysis/{id} 均 404。

### 2. 改查询条件（日期/过滤）→ 必须走 UI + 合成点击

应用跑在**无界微前端（shadow DOM）**里：
- 深度查询：`const deep=(sel)=>{let f=[];const walk=(r)=>{for(const e of r.querySelectorAll(sel)){f.push(e)}for(const e of r.querySelectorAll("*")){if(e.shadowRoot)walk(e.shadowRoot)}};walk(document);return f}`。
- **查询按钮对一切合成点击免疫**（el.click、React onClick 直调、CDP 鼠标/键盘都无效）。**解法：`location.reload()` 重建应用会话后，el.click() 立即可用**。点「查询」会 `POST /datafinder/api/v1/analysis`（新建临时分析）→ `GET .../result`，抓后者拿数据。
- 日期范围：点选择器开面板，快捷项（过去5/7/14/30/60/90/180天）直接点；自定义区间用 arco 日历（`.arco-picker-header-icon` 翻月、`.arco-picker-cell-in-view` 点日期、找「确 定」确认）。
- 属性过滤：点「+ 属性过滤」→「请选择属性」搜索 → 选属性（如 `最近一次站外域名`=$latest_referrer_host）→ 操作符下拉（≠（含null）= 保留空值）→ 属性值多选（框内搜索 → 点选项行；**已提交判定标准：筛选区标题变成 not(a, b…)**；浏览器自动填充下拉（x≈37 的小列表）是干扰，别点）。
- **验证 DSL**：读 `POST /analysis` 的 requestBody，看 `profile_filters[].expression.conditions[].property_values` 是否包含全部目标值；标题/ chip 显示不可信。
- 操作完把页面恢复默认（筛选/日期复位或 reload）。

## 二、insight BI（aeolus 仪表盘）

### 1. 先看懂结构（一次抓全）

- `POST /bi/aeolus/glue/api/v1/dashboard/dashboardAndSheet` → 组件树 + 每个报表的 `reqJson.schema`（dimensions/measures/whereList）+ 数据集定义（`metricsList[].expr`、`dimensionList`、`paramList`）。全部落盘。
- 图表数据：`POST /bi/aeolus/glue/api/v1/dashboard/query?reportId={rid}`，body 从抓包的同款请求改。
- **校验规则（schemaNotMatchInDB）**：只能改 `whereList` 里的**值**（日期窗口大小、国家筛选增删、paramList 值）；`groupByIdList/selectIdList/schema` 形状必须与报表一致。

### 2. 序列图（trend）：改 filter 值即重放

- 改 `whereList[]` 的 `val`（如 `创建日期 op:last val:[60]→[100]`）扩窗口；删掉 `所在国家` 过滤得全球，val `['cn']`/`['overseas']` 拆区。
- 返回 `vizData.datasets[0][0][0]`：记录含 `10001`=指标名、`10002`=值、以及日期键（取 `dimMetId2AliasMap`/`fieldMap` 对列名）。

### 3. 漏斗/参数化数据集：paramList 传窗口

```
query.paramList = [
  {"id":80,"name":"end_date","val":{"op":"fixed","val":"YYYY-MM-DD"}},
  {"id":81,"name":"start_date","val":{"op":"fixed","val":"YYYY-MM-DD"}}
]
```
- start=end=当日 → 单日 cohort（当日注册当日转化）；start=D-6,end=D → 7 日窗口 cohort。
- param 的 id/name 从数据集 `paramList` 定义来；改 param 值不算形状变化，校验通过。
- 逐日循环用页面内 `fetch` 跑（每批 15 天左右，evaluate 串行 await）。

### 4. 明细表（raw_table/table）全量拉取（以「用户账户明细查询」为例）

真实请求走 `POST /bi/aeolus/vqs/api/v2/vizQuery/query`：
- **新增 where 必须同时加进 `query.whereList` 和 `schema.whereList`**（镜像字段，`option.isReportFilter:true`），否则 schemaNotMatchInDB。利用这点可做等值技巧：`创建日期=D` + `最早充值日期=D`（query+schema 双写）→ 精确筛出「当日注册且当日首充」的用户（人数与漏斗「新用户充值人数」完全一致，可互相验证）。
- **viz 层只返回 50 行**；翻页参数不在 query 里——设 `schema.pagination={"frontOnlyOffset":50,"size":30000}`（offset>0 即返回全量行，实测 612/5258 行全回）。
- 列是 uniqueId 键：用响应 `data.columns[]`（`unique_id`→`name`）映射。
- 金额类指标单位在数据集 SQL 里已缩放（如 `total_recharge_amount*1.0/100000`，即元）。

### 5. 页面渲染常识

- 后台 tab 不渲染图表 → `cdp Emulation.setFocusEmulationEnabled {enabled:true}`（用完设回 false）；最后手段 `Page.bringToFront`。
- 懒加载：滚动**内容区最大 scrollHeight 的容器**触发下方图表查询；`network list` 里按 `reportId` 找请求。

## 三、数字核验（每次必做）

- 用用户给的锚点值核对单日（如 9/25 注册=5217、10/7 新用户 UV=18703）。
- 口径三角验证：全球 = 中国区 + 海外（应逐日精确相等）；漏斗注册数 ≈ 趋势注册数（差 1–2% 正常）。
- 聚合自洽：窗口 cohort ≥ 同日 cohort（窗口允许跨日转化）；明细行数 == total（防 50 行截断）。
- 金额数据警惕大额离群（单日 2000 万级企业充值会主导均值，必要时同时给人均/中位数口径）。

## 四、落飞书表格（lark-sheets 要点）

- 写入：`+cells-set --writes`（stdin 传 JSON；每批 ≤50 行）；比率列**写公式**（=C4/B4）而非静态值，收尾必跑 `+formula-verify` 到 success。
- 样式：`+styles-put` 一次交付（表头 #DDEBF7 加粗居中、汇总行 #D6E4F0 加粗 + 上边框 medium、高亮行 #FFF2CC、数值 #,##0 / 0.00%、冻结表头）。
- 图表：`+chart-create --print-example line` 拿模板；refs 含表头行、dim2.series.index 按 refs 内列序；**`--sheet-name` 绝不能为空**（空名会把图建到错的子表；bash 关联数组在 macOS bash3 不可用）；改图用 `+chart-list` 取全量 snapshot 后 `+chart-update` 整体回写。
- 高风险操作（chart-delete 等）必须 `--dry-run` → 用户确认 → `--yes`。

## 五、排障速查

| 症状 | 原因 | 解法 |
|---|---|---|
| POST /analysis/…/result 权限不足 | 计算接口锁死，只能 GET 已保存结果 | 走 UI 改条件+查询（reload 后 el.click 有效） |
| 点「查询」无任何请求 | 应用会话过期/合成事件被忽略 | reload 页面再点 |
| schemaNotMatchInDB | 改了查询形状（groupBy/select）或 where 未双写 | 只改 filter 值；新 where 同时写 query+schema |
| viz 只回 50 行 | viz 展示层截断 | schema.pagination.frontOnlyOffset>0 |
| 页面空白/图表不出数 | 后台 tab 不渲染 | 焦点模拟 + 滚动最大容器 |
| 抓不到 datafinder 请求 | 条件未变更，前端用缓存 | 必须真改条件触发新查询 |
