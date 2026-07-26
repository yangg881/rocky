---
name: 职达简历
description: 忠于事实、专注岗位匹配的现代求职生产工具
colors:
  focused-blue: "oklch(49% 0.17 264)"
  focused-blue-hover: "oklch(43% 0.18 264)"
  focused-blue-soft: "oklch(94% 0.035 264)"
  graphite-ink: "oklch(24% 0.035 264)"
  graphite-soft: "oklch(45% 0.025 264)"
  quiet-muted: "oklch(57% 0.02 264)"
  working-surface: "oklch(98.5% 0.006 264)"
  raised-surface: "oklch(99.4% 0.004 264)"
  divider: "oklch(89% 0.012 264)"
  verified-green: "oklch(48% 0.12 154)"
  warning-amber: "oklch(58% 0.13 74)"
  danger-red: "oklch(51% 0.17 24)"
typography:
  headline:
    fontFamily: "Inter, Segoe UI, PingFang SC, Microsoft YaHei, system-ui, sans-serif"
    fontSize: "2rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Inter, Segoe UI, PingFang SC, Microsoft YaHei, system-ui, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "Inter, Segoe UI, PingFang SC, Microsoft YaHei, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Inter, Segoe UI, PingFang SC, Microsoft YaHei, system-ui, sans-serif"
    fontSize: "0.86rem"
    fontWeight: 700
    lineHeight: 1.4
rounded:
  sm: "8px"
  md: "12px"
  lg: "18px"
spacing:
  xs: "6px"
  sm: "12px"
  md: "18px"
  lg: "26px"
  xl: "34px"
components:
  button-primary:
    backgroundColor: "{colors.focused-blue}"
    textColor: "{colors.raised-surface}"
    rounded: "{rounded.sm}"
    padding: "9px 16px"
    height: "42px"
  button-primary-hover:
    backgroundColor: "{colors.focused-blue-hover}"
    textColor: "{colors.raised-surface}"
    rounded: "{rounded.sm}"
  input-default:
    backgroundColor: "{colors.raised-surface}"
    textColor: "{colors.graphite-ink}"
    rounded: "{rounded.sm}"
    padding: "9px 12px"
    height: "44px"
  card-standard:
    backgroundColor: "{colors.raised-surface}"
    textColor: "{colors.graphite-ink}"
    rounded: "{rounded.md}"
    padding: "26px"
---

# Design System: 职达简历

## Overview

**Creative North Star: "清醒的求职书桌"**

职达简历像一张在白天自然光下整理材料的书桌：内容完整、层次清楚、没有多余装饰。界面用克制的密度帮助求职者连续完成素材、岗位和导出任务；管理员端延续同一套组件语言，但通过独立入口和数据结构保持权限边界。

系统明确拒绝过度装饰、实验性交互和营销化夸张。状态变化快速而安静，重要动作有明确反馈，真实经历保护始终可见。

**Key Characteristics:**

- 浅色、冷调、低干扰的工作表面
- 单一蓝色强调关键动作和当前状态
- 熟悉的表单、导航、列表和数据表格
- 150 至 250 毫秒的状态动效，支持减少动态效果
- 桌面端高效，移动端保持完整任务路径

## Colors

冷调石墨中性色提供安静的阅读背景，聚焦蓝只在主动作、焦点和选中状态出现；绿色、琥珀色和红色严格承担语义状态。

### Primary

- **聚焦蓝**：用于主按钮、当前导航、焦点边框和关键词标签，是界面唯一的品牌强调色。

### Secondary

- **验证绿**：仅用于安全说明、成功状态和健康状态。
- **警示琥珀**：仅用于用量接近阈值或需要关注的状态。
- **风险红**：仅用于删除动作、错误和不可逆风险。

### Neutral

- **石墨正文**：承担标题、正文和深色侧栏。
- **静默灰**：承担辅助信息、时间和说明文案。
- **工作表面**：承担页面背景和次级区域。
- **抬升表面**：承担表单、数据区域和需要分组的容器。
- **分隔线**：只用于结构边界，不作为装饰。

**The One Focus Rule.** 聚焦蓝只标记当下最重要的动作或状态，不得同时装饰多个无关区域。

## Typography

**Display Font:** Inter（回退到 Segoe UI、苹方、微软雅黑和系统无衬线）
**Body Font:** Inter（使用相同回退）

**Character:** 单一无衬线字体保证中文与英文界面稳定、熟悉、可快速扫描。层级由字号、字重和留白形成，不依赖装饰字体。

### Hierarchy

- **Headline**（700，2rem，1.2）：页面主标题，使用轻微负字距形成紧凑而专业的轮廓。
- **Title**（700，1.15rem，1.3）：区域标题和主要列表标题。
- **Body**（400，15px，1.55）：表单说明、结果内容和工作流正文，连续说明限制在 65 至 75 个字符宽度。
- **Label**（700，0.86rem，1.4）：表单标签、按钮和操作名称。

**The Native Clarity Rule.** 所有操作标签使用熟悉的系统无衬线字形，禁止为求新而牺牲可读性。

## Elevation

系统以色调分层和细边框为主，阴影只用于登录面板、浮动提示和需要脱离页面层级的反馈。普通内容容器保持平面，不使用层层嵌套阴影。

### Shadow Vocabulary

- **环境抬升**（`0 16px 50px oklch(24% 0.035 264 / 0.09)`）：仅用于登录面板和浮动提示。
- **焦点环**（`0 0 0 3px oklch(49% 0.17 264 / 0.22)`）：用于键盘焦点和表单输入焦点。

**The Flat Work Rule.** 工作区默认平面化，只有跨越当前内容层级的元素才能获得环境阴影。

## Components

### Buttons

- **Shape:** 轻柔圆角（8px），最小高度 42px。
- **Primary:** 聚焦蓝背景、抬升表面文字、9px 16px 内边距，只用于页面主动作。
- **Hover / Focus:** 悬停加深蓝色并上移 1px；键盘焦点使用 3px 聚焦蓝透明环。
- **Secondary / Danger:** 次要按钮使用白色表面和结构边框；危险按钮使用浅红背景与风险红文字，并要求二次点击确认。

### Chips

- **Style:** 浅蓝背景、聚焦蓝文字、999px 圆角，适用于默认标记和计数。
- **State:** 状态芯片根据成功、警告和等待语义切换颜色，永远同时显示文字。

### Cards / Containers

- **Corner Style:** 标准容器 12px，登录面板 18px。
- **Background:** 抬升表面放在工作表面之上。
- **Shadow Strategy:** 工作容器无阴影，遵循平面工作规则。
- **Border:** 1px 分隔线，禁止彩色侧边条。
- **Internal Padding:** 标准桌面 26px，窄屏 19px。

### Inputs / Fields

- **Style:** 抬升表面、1px 结构边框、8px 圆角，最小高度 44px。
- **Focus:** 边框切换为聚焦蓝并显示 3px 焦点环。
- **Error / Disabled:** 错误使用风险红文字；禁用态使用工作表面和静默灰文字，保持标签可读。

### Navigation

深石墨侧栏承载桌面导航，当前项以完整聚焦蓝底色标记；移动端变为固定顶栏和可收起侧栏。所有导航项最小高度 44px，文字与图形共同传达状态。

### 真实经历保护提示

使用验证绿浅色表面和完整文字说明，固定出现在工作台核心流程之前。它不是装饰徽章，而是模型行为边界的持续承诺。

## Do's and Don'ts

### Do:

- **Do** 将聚焦蓝留给主动作、当前导航和焦点状态。
- **Do** 为按钮、输入、导航和表格提供默认、悬停、焦点、禁用、加载和错误状态。
- **Do** 使用 12px 标准容器圆角、1px 结构边框和有节奏的 12/18/26/34px 间距。
- **Do** 保持普通用户端与管理后台入口、导航和权限完全分离。
- **Do** 使用文字配合颜色表达成功、警告和错误，保证色盲用户可辨。

### Don't:

- **Don't** 使用过度装饰、渐变文字、玻璃拟态或无意义动效。
- **Don't** 构建重复卡片墙或在容器中继续嵌套同形卡片。
- **Don't** 使用营销化夸张措辞，或让用户难以判断当前步骤和数据状态的实验性交互。
- **Don't** 使用大于 1px 的彩色左侧或右侧条纹作为强调。
- **Don't** 以纯黑或纯白替代带品牌色相的石墨中性色。

