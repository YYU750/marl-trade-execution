# 第五轮交付核验

## 运行与结果

- `tests_round5/` 在隔离的第五轮实现和最终仓库克隆中均运行通过：35/35。
- 标准协议：300 train / 60 validation / 100 test seeds；训练、验证、测试互不重叠。测试成本 Q-learning 8.8491 bp、TWAP 7.5044 bp、价差紧迫度 7.7252 bp；配对 Q−TWAP 为 +1.3447 bp，95% 描述性 t 区间 `[+0.5334,+2.1560]`。
- 行为对账：3,000/3,000 条测试动作均满足最终成交 = 裁切后请求 + 环境补足。环境补足成交 9,015,269 / 10,000,000 股（90.15%）。
- 冻结策略压力协议：100 个全新 seed、5 个场景；Q 表保持冻结，epsilon=0，无测试更新。低流动性和宽价差下，所有测试状态均未出现在 Q 表中，成本明显高于规则基准。
- 标准结果的 Q 成本与动作序列逐项复现第四轮回执；选中候选第 1 episode 的终止更新通过独立重放。

## 文档与演示

- `deliverables/round5_course_report.md` 是正文来源；Word 版为 3 页 Letter 页面，通过 Microsoft Word 本机导出 PDF 后逐页检查，正文、两张比较表、页眉页脚均可读。
- `deliverables/round5_course_slides.pptx` 共 10 页。通过 PPTX 包结构、几何、字体和 Artifact Tool 重新导入检查，并逐页查看渲染图；未发现裁切、重叠或不可读内容。
- PPTX 使用 Microsoft YaHei。最终器确认字体名称及文本框几何；这不代表在其他电脑上已验证字体替换效果。

## GitHub 分支

目标仓库：`https://github.com/YYU750/marl-trade-execution`。本轮内容放入新分支 `codex/qlearning-course-round5`。分支不包含比赛数据、虚拟环境、密钥、完整历史实验目录或临时渲染文件。

## 限制

成本优势未通过：Q-learning 标准测试成本高于 TWAP。真实市场表现、Markov 状态充分性及双边学习均衡未验证。压力下状态覆盖不足；高完成率主要由硬约束保证。
