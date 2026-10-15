---
name: ai-game-dev
description: 用 AI 辅助做 3D 小游戏的通用生产线：ChatGPT(经 kimi-webbridge) 出概念图、Tripo3D 图生 3D、Blender 后处理、Godot 4 集成与玩法工程。当用户要做 3D 游戏（竞速/冒险/休闲等）、需要 AI 生成模型并落地成可玩成品时使用。核心原则：资产管线化、数值用公式反推、判定区域必审计、探针驱动调试、按功能提交可回退。
---

# AI 辅助 3D 游戏开发经验（ChatGPT × Tripo3D × Blender × Godot）

从完整卡丁车游戏项目沉淀的通用经验。照此流程可把一个玩法想法做成有完整闭环（菜单→对局→结算→持久化）的 3D 成品游戏。

## 一、总流程

1. **概念对齐**：先用 ChatGPT 出全套概念图（海报/角色/场景/道具）给用户检阅，风格确认后再动工——这是返工成本最低的一步。
2. **资产管线**：概念图 → Tripo3D 图生 3D → Blender 减面定型 → Godot 集成。
3. **玩法骨架**：先跑通最小闭环（能开始、能玩、能结束、能结算），再逐项加特色功能。
4. **验证驱动**：每个功能都有自动化验证（回归 + 截图），通过才提交。

## 二、AI 资产生成

### ChatGPT 概念图（kimi-webbridge 驱动真实浏览器）

- 固定 session 名；`list_tabs` 拿 tabId。**坑：navigate 不一定落在指定 tab**，之后必须 `list_tabs` 确认目标页在哪个 tabId 再继续。
- 填词：`#prompt-textarea` 填 innerHTML → dispatch `input` 事件 → 点 `#composer-submit-button`。发完截图确认进入生成态。
- 图像轮询：`[...document.querySelectorAll("img")].filter(i=>i.naturalWidth>200&&!i.src.includes("auth0"))`，约 40-90s 出图；下载用 chunked base64 脚本（如 `~/.cache/wb/dl.sh`）。
- Prompt 配方：「卡通/低多边形 3D 渲染风格 + 纯白背景 + 单体完整不裁切 + 四分之三视角 + 具体造型细节（配色/部件/材质/姿态）」。**一次只生成一个物件**——两格拼图裁切时易带邻物。
- 风格统一：所有资产沿用同一组风格词（如「类似马里奥赛车的卡通 3D 渲染」），否则拼在一起不像一个游戏。

### Tripo3D 图生 3D（studio.tripo3d.ai）

- 上传：图片转 `data:image/png;base64,...`，构造 File 注入 `input[type=file][accept*=image]` 并 dispatch `change`。页面上还有只收 .glb 的上传口，**必须用 accept 过滤选对 input**。
- Generate 按钮文本形如 `Generate\n\n55`，用 `/^Generate\d/` 匹配 innerText 后点击。生成约 4-5 分钟。Export → 对话框再 Export → GLB 到 `~/Downloads`。
- **浏览器关掉不丢资产**：任务在服务端，重开页面从 Assets 面板第一个缩略图进入即可导出（用「x>80% 屏宽且 y 最小的 img」定位资产卡）。
- Tripo 模型 100-190 万面，**必须后处理**（见下）。

### 模型后处理通用规范（Blender）

- 减面 DECIMATE ratio 0.02（道具/建筑）~0.03（主角/车辆），目标 2-4 万面；贴图压到 1024；按游戏内目标尺寸归一化（`scale=目标/max(dim)` 后 transform_apply）；底部对齐 `location.z -= bbox_min_z`。
- 给游戏用的小物件（道具图标类）可以更低（1-3 万面）；贴图 512-1024 足够。
- **Blender GUI+MCP 会因 `read_factory_settings` 死亡**：批量处理一律用 CLI 后台模式（`blender --background --factory-startup --python x.py`）。
- **导出丢物体**：对象会被莫名 hide（hide_set/hide_viewport/hide_render 三重），导出前全部置 False；导出日志确认 "Extracting primitive" 再信文件大小。
- 脚本自检：打印 IMPORT/EXPORT 对象数，不符就停；**覆盖大文件前先 `cp` 备份到 /tmp**。
- 恢复手段：Godot 导入缓存 `.godot/imported/*.scn` 可用 GLTFDocument（`append_from_scene` + `write_to_filesystem`）回导出 GLB 救回被覆盖的资产。

## 三、引擎集成纪律（Godot 4）

- 新 GLB 必须 `godot --headless --import` 生成 .import；新 `class_name` 脚本同样要跑一次 import 刷新全局类缓存。
- 模型落地：实例化后等一帧，递归 AABB 取底，`position.y = -aabb.position.y`。
- **GLB 贴图依赖链**：导入时内嵌贴图会被抽取成散装文件放在模型旁，`.godot/imported/*.scn` 按路径依赖它们。移动/删除散装贴图 = 模型加载失败（还连累引用它的脚本 parse error）。清理资产前先 grep `.import` 里的依赖路径，别只看 GLB"内嵌"假象。
- **场景互跳禁双向 preload**:`main.gd preload Race.tscn` + `race.gd preload Main.tscn` 循环引用，后加载方拿到的是半成品空场景（node count 0），切场景静默失败。互跳一律运行时 `change_scene_to_file()`。
- **首帧巨型 delta**：同步构建（网格+GLB 实例化）的耗时堆进场景切换后第一帧的 delta（可达数秒），补间/弹字/计时器被瞬吃——表现"卡一下+字体突变"。运镜/弹字前 `await get_tree().process_frame` 两次；切场景前先铺满加载页再切换。
- **每完成一个功能立即 git 提交**（明确基线，随时可回退）。`.gitignore`：`.godot/`、截图目录、未减面的原始大 GLB（动辄几百 MB）。
- 调试钩子做成环境变量开关（如 `XXX_DEBUG`），平时零成本，排查时直接可用。

## 四、玩法工程通用原则

### 数值用公式反推，不拍脑袋

- 弹道类（跳跃/投射物）：射程 = v·t，vy 由坡角或初速给出（vy=v·sinθ），落点差由高度差补偿。先算「最慢车/最低属性能不能过」，再定几何。
- 难度曲线：AI 强度给档位（如车速 ×0.92/1.0/1.08 + 橡皮筋强度），不要一个硬值。
- 经济/奖励：按名次/位置加权发放，领先给防守、落后给追赶。

### 判定/触发区域设计（事故重灾区）

- 任何 Area3D（拾取区/杀伤区/触发区）三问：**顶面多高压线吗？底面多低误伤吗？XZ 覆盖碰到合法区域吗？** 本项目三次连环卡死都是区域范围错：拾取区顶面罩住了正常滞空的单位（=空气墙）。
- 杀伤/救援区顶面 = `min(相邻合法面.y) - 安全余量`（我们用的 2m）。
- 沿走廊的判定区做**旋转薄盒**贴合走向；轴对齐大盒在对角线走廊上必误伤。
- 触发层要薄且贴边：大触发盒会在不该触发的地方提前触发。

### 碰撞与边界

- 防高速穿透用双层薄墙，不用单墙；防陷入地面的 snap 只做单向（只上抬不下吸，否则坡道卡死）。
- 角色碰撞体优先胶囊；盒体会在路肩/台阶卡死。
- 网格生成的边界（跳台口/断层口）要**精确截断**——粗网格会在边界形成幽灵坡/幽灵墙，把单位弹回。

### 手感

- 漂浮感的解法：着地持续下压（-4）+ 车身姿态（俯仰+侧倾）贴合地面法线（四元数 slerp，`Basis.slerp` 有归一化坑）+ 悬挂起伏/落地压缩。高速仍飘就加速度下压力（如 `-4 - 0.35*|v|`）。
- **撞击检测必须用滑移前速度**：`move_and_slide()` 会把法向速度分量吃掉，事后用 `velocity` 算撞击力度必然漏检（撞墙减速/反弹几乎不触发）。先存 `pre_vel := velocity` 再 slide，事后用 `get_slide_collision` + pre_vel 点乘墙面法线。贴墙行驶另加摩擦衰减。
- **跟车滞后公式**：位置插值平滑跟随的滞后量 ≈ `speed / stiffness`，全速时被甩开好几米（玩家会抱怨"镜头太远"）。刚度随车速线性提升可解，低速保持柔和。
- 反馈三层：视觉（粒子/车辙）、UI（仪表/消息）、镜头（trauma² 衰减的震屏）。自动触发的效果和按键触发的效果文案必须分开，否则玩家误以为按键失灵。
- **叠加轮罩住模型静态轮**：合并网格拆不出轮子，罩轮要"同心 + 略大"（胎面宽比半径更容易漏，轮毂盖会从胎面探出）。轮位用底部+外侧顶点四象限聚类实测，再用同几何标记渲染复核；放置高度用实测轮心，别用 radius 凑。
- **AI 要有人味（尤其录播）**：纯机器走线太稳没看头。给 AI 加：漂移阈值放宽（大弯必甩尾）、空手主动抢前方道具箱、氮气直道立刻喷、按技术分档的轻微走线晃动（偶尔蹭墙有火花）。注意跳台助跑区要豁免抢箱。

## 五、调试方法论（探针驱动，别猜）

- 环境变量全家桶：`DEBUG`（逐帧轨迹/事件原因）、`AUTO`（AI 代驾跑回归）、`SHOT`（定点截图）、`DUMP`（导出关键数据）、强制配置项（角色/氛围）。
- 回归标准：无头跑整场，要求 0 SCRIPT ERROR、对局正常结束、无非预期重置、进度单调前进。
- 卡死排查三步：①全量事件打印（谁、在哪、为什么被重置/传送）②逐帧轨迹探针（位置/速度/接地/碰撞法线）③空间探针证伪（`intersect_shape` 记得 `collide_with_areas=true`）。
- 视觉 QA：关键点位固定机位截图；改任何视觉后必拍。窗口模式比实时快，截图时间点会漂，quit-after 要给足。
- 稳定性：多角色/多配置连跑（如三车型各一场全场），确认无脚本错误、无卡死。
- **几何穿盖审计三件套**（地形盖路面/物体穿模类）:①面级检查——顶点级审计会漏（稀疏网格的面比顶点高）;②中心线 DUMP 成 JSON 当基准（pos/tangent/side，注意同步控制点改动）;③纯 Python 解析 GLB 复核（struct+json 读 node/mesh/accessor，绕开 Blender 导入器命名漂移，文件里的 node name 才是 Godot 契约）。
- **Blender ↔ Godot 坐标坑**:glTF 文件是 Godot 同款 Y-up；导入 Blender 后 Z-up，且 Blender.y = -Godot.z。修复脚本里写错映射 = 修到镜像位置"修不到点上"，先打两个已知点验证坐标再批量。
- 贴地/压高修复用**局部反距离加权（IDW)**：以路面顶点 6m 局部加权插值出贴合 bank 弯道的参考面，比按 prog 分桶或中心线高度可靠（分桶有采样量化空洞）。
- 自动跑图/录屏钩子：自动退出要用 `set_meta("fresh_finish")` 标记"本次会话刚完赛"再触发；别拿持久化数据（如 last_results）当条件，陈旧数据会误触发早退。录屏先确认游戏窗口真的上了被录那块屏（会议/多屏会抢）。

## 六、GDScript / 场景高频坑

- `var x := abs(...)`、数组元素、`or` 连接表达式 → 类型推断失败，显式标类型。
- `Transform3D(...)` 无 12-float 构造（用 Basis+origin 或 rotation_euler）。
- `global_position` 必须在 `add_child` 之后设置（否则 "!is_inside_tree()"）。
- 手写 `.tscn`：`load_steps` 数错即 Parse Error；sub_resource id 别重复。
- GPUParticles3D：拖尾/烟用 `local_coords=false` 留在世界坐标；TorusMesh 属性是 inner/outer_radius。
- HUD 动态加节点后等两帧再读 `get_global_rect()`。
- 窗口无头模式下 `-s` 脚本不加载 autoload，别用它跑依赖单例的场景。
- **tscn 里自定义 `class_name` 节点不能光写 `type="类名"`**（会成 placeholder 报 cannot be created），要 `type="Control"` + `script = ExtResource("id")` 显式挂脚本。
- **Blender 5.x 导入→修改→导出 GLB 后，再导入时对象命名规则可能变**（有时按 mesh 数据块命名）。资产修复脚本别只按导入后对象名匹配；glTF 文件里的 node name 才是 Godot 侧 find_children 的稳定契约，不放心就用包围盒位置认物体。

## 七、Web 发布（HTML 导出）

- 导出链路：装 export_templates → 建 Web preset(`export_presets.cfg`)→ `godot --headless --export-release "Web" build/web/index.html`（目标目录要先手动建）。
- 渲染器用平台覆盖 `rendering/renderer/rendering_method.web="gl_compatibility"`，桌面端保持 Forward+ 不动。
- **nothreads 变体省心**：任意静态托管可跑，不要 COOP/COEP 响应头；要性能再考虑 threads 变体。
- **瘦身三板斧**:① Tripo 原始大 GLB 移进带 `.gdignore` 的隔离目录（不删文件），并清掉 `.godot/imported/` 里对应 `.scn` 缓存（残留缓存照样进包，pck 能从 390MB 砍到 78MB);② 贴图抽取件 `sips -Z 1024` 统一压边长（2048~4096 的 ctex 是大头）;③ 导出后 strings 抽查 pck 确认无 `_raw`。
- 单文件超 100MB 用 `split -b 90m` 分卷 + `cat` 合并（别用 zip 自带分卷格式，macOS 自带 unzip 解不了）。
- **file:// 打不开**：必须起 HTTP 服务（`python3 -m http.server`）再测；本地起服务前先 `lsof -i :port` 查端口被谁占了（撞端口会开到别人的项目）。
- 浏览器实测别只看能加载：点进选车/比赛确认 GLB 贴图在（之前出现过"包能跑但车辆无贴图"，根因是导出时散装贴图缺失）。

## 附：卡丁车参考数值（本项目实测可用）

街机车：grip 7-8.5、drift_grip 2.6-2.9、GRAVITY 42、着地下压 -4、双层护栏 ±4.6/±5.6。漂移：Shift 手动 + 80% 极速满舵 0.14s 自动。跳台：12m 坑、落差 2m、24m/s 车速 → 唇口 20° 上翘。起步蓄力：按 W +0.45/s、松开 -0.26/s、完美区 0.55-0.78。
