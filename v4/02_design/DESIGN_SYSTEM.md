# 统一像素设计系统

## 层级与技术落点
沿用 `mobile/lib/core/design/tokens_v2/ → theme/ → context.colors/typo/space/radius/motion`。先盘点现存语义，再增加极少数字段（pixelStep、cornerCut、accentInk、stateMotion）。不引入第三套品牌色/第二套字阶。包内JSON只是设计输入；产品编译期转换到既有令牌，随后由唯一源生成Web/原生示例。

## 视觉语法
主卡：一条深墨轮廓+1个4/8dp阶梯角；次卡：单线或轻底色；列表：用留白与分割，不每行镶框。单视口最多一个强主CTA。阴影只表层级，不对每张卡加高光；像素图形统一2dp概念网格，外观可在最终设备像素取整，不对文字画布整数缩放。

DPR处理：stroke中心与填充边缘各自对齐物理像素；DPR=1/1.25/1.5/2/3覆盖。小sprite用nearest-neighbor、整数纹理倍数或离散尺寸资产；布局保持逻辑dp连续，不用Transform缩整个App来“对齐像素”。大面积叠透明噪声/BackdropFilter禁止成为默认。不能为了少量像素图形把Flutter全部变成CustomPainter。

## 字体与阅读
中文正文系统sans，16sp/1.6；标签14sp；最小辅助13sp，不塞10px英文装饰。长文可调整字号；代码等宽但不8bit；公式与屏幕阅读器描述保持。像素短标题为可替换品牌资产，不承担错误、帮助或长文本。包不分发字体。使用字体前记录许可证与中文覆盖范围，缺字回退不改变行高。

## 主题和状态
paper_day/dusk/quiet 是同一语义映射，不是不同产品。quiet 是显式选择或系统减少动态偏好的保守呈现，不由AI从“情绪低落”偷偷推断并改变主题。高对比/色觉辅助维持既有可访问配置并逐色测试。不要用红绿/亮暗单独表达未掌握与掌握。

## 核心组件合同
| 组件 | 内容/事件 | 状态与边界 |
|---|---|---|
| PixelFrame | 轮廓与surface | 仅装饰；Semantics由child提供；不能吞手势 |
| PrimaryAction | 文本+可选图标 | loading不改宽度；重复点击禁写；focus ring在切角外仍可见 |
| GoalAnchor | 目标、期限、有效期 | 过期/暂停明确；不显示不存在的7天连续 |
| NextStepCard | 产物标准、执行人、估时 | 单主CTA、卡住入口、编辑；少字段渐进展开 |
| AuroraReceipt | 为什么/用了哪条经验 | 只对实际选用ref有说明；纠正/仅本次/删除始终可达 |
| ActionDiffSheet | old→new/变化理由 | proposed/approved/applying/committed/unknown/conflict；不能合并 |
| RunCard | plan、阶段、handoff | 离开后恢复；长任务不以假进度百分比填空 |
| EvidenceStamp | outcome→来源与方法 | persisted≠validated≠mastery；可撤回和重算 |
| PathNode | 轨迹节点与详情 | 有列表替代；不靠亮度表示能力 |
| MemoryItem | 事实/偏好/推断分层 | scope用人话；来源缺失不伪造；并发版本冲突可见 |
| FeedbackToast | 短反馈 | 成功须真实回执；关键错误持久内联，不2秒消失 |
| QuietControls | 声/触/动独立偏好 | 不可因页面初始化重开声音 |

## 布局
宽<600：单列、16dp边距；600–1023：主要区+可收起上下文；≥1024：导航侧栏+中列动作/对话+右侧来源，正文max宽约720dp。真实断点需与既有Shell兼容，保持route ID。文本200%时允许更少列、更高卡片，不截断主按钮标签。键盘弹出后输入栏和错误仍可见，bottomSafeArea单一消费。

## 迁移办法
先适配组件故事页和主旅程，保留旧主题fallback；每个页面家族逐个替换并截图对照；最后收旧样式桥。迁移令牌只触design目录，不混业务逻辑。优先删除重复装饰与重复组件，不机械把2万次DS调用改名。全端行为测试复用，golden差异须独立解释每类变化。

## 验收
实现按R01/R05/R06等来源原则及项目阈值，见METRICS。相同状态在任意页面有相同语义；错误、撤回和未知不能用庆祝视觉。滚动/点击/正文60Hz目标不受像素动画12fps限制；frame统计在profile/release测，不在debug截图里估帧率。
