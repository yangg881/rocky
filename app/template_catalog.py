"""Built-in resume templates with genuine layout differences.

These are first-class render recipes (not decorative swatches). Preview and final
Word/PDF all go through the same layout_variant + theme pipeline.
"""

from __future__ import annotations

from copy import deepcopy

# Eight industry-oriented templates. Each maps to a distinct layout_variant so
# choosing a different card produces a visibly different document structure.
_SYSTEM_TEMPLATES: tuple[dict, ...] = (
    {
        "id": "sys-tech-sidebar",
        "name": "互联网 · 左栏科技",
        "category": "互联网技术",
        "display_category": "互联网技术",
        "tags": ["研发", "产品", "双栏", "侧栏"],
        "accent": "#284C9B",
        "soft": "#EAF0FF",
        "ribbon": "#284C9B",
        "ink": "#1E293B",
        "base_theme": "tech_indigo",
        "layout_id": "timeline_focus",
        "layout_variant": "left_sidebar",
        "word_layout": "left_sidebar",
        "header_mode": "side",
        "section_style": "block",
        "avatar_mode": "square",
        "density": "compact",
        "sample_role": "高级后端工程师",
        "preview_note": "深色左栏放联系方式与技能，右侧放经历时间线。预览结构与最终生成一致。",
    },
    {
        "id": "sys-exec-minimal",
        "name": "商务 · 高管极简",
        "category": "商务管理",
        "display_category": "商务管理",
        "tags": ["高管", "咨询", "单栏", "极简"],
        "accent": "#263B59",
        "soft": "#EDF1F5",
        "ribbon": "#263B59",
        "ink": "#202B3B",
        "base_theme": "executive_navy",
        "layout_id": "accent_header",
        "layout_variant": "executive_minimal",
        "word_layout": "executive_minimal",
        "header_mode": "compact",
        "section_style": "line",
        "avatar_mode": "portrait",
        "density": "airy",
        "sample_role": "战略运营总监",
        "preview_note": "居中留白、标题字间距放大，强调管理履历层次。",
    },
    {
        "id": "sys-care-banner",
        "name": "教育医疗 · 顶栏关怀",
        "category": "教育医疗",
        "display_category": "教育医疗",
        "tags": ["教师", "医护", "顶栏", "时间线"],
        "accent": "#16756F",
        "soft": "#E7F5F1",
        "ribbon": "#16756F",
        "ink": "#1E3938",
        "base_theme": "care_teal",
        "layout_id": "timeline_focus",
        "layout_variant": "banner_timeline",
        "word_layout": "banner_timeline",
        "header_mode": "banner",
        "section_style": "numbered",
        "avatar_mode": "circle",
        "density": "balanced",
        "sample_role": "主治医师 / 学科教师",
        "preview_note": "顶部色带标题 + 左侧时间轴节点，适合教育/医疗履历。",
    },
    {
        "id": "sys-ops-timeline",
        "name": "工程运营 · 时间轴",
        "category": "工程运营",
        "display_category": "工程运营",
        "tags": ["工程", "制造", "物流", "时间轴"],
        "accent": "#1F6268",
        "soft": "#E7F2EF",
        "ribbon": "#1F6268",
        "ink": "#24383B",
        "base_theme": "operations_terra",
        "layout_id": "timeline_focus",
        "layout_variant": "banner_timeline",
        "word_layout": "banner_timeline",
        "header_mode": "banner",
        "section_style": "numbered",
        "avatar_mode": "square",
        "density": "compact",
        "sample_role": "生产运营主管",
        "preview_note": "强调项目周期与岗位时间，配工程绿配色。",
    },
    {
        "id": "sys-creative-asymm",
        "name": "市场创意 · 不对称",
        "category": "市场创意",
        "display_category": "市场创意",
        "tags": ["市场", "品牌", "设计", "创意"],
        "accent": "#75416F",
        "soft": "#F7EDF4",
        "ribbon": "#75416F",
        "ink": "#3B293C",
        "base_theme": "creative_plum",
        "layout_id": "timeline_focus",
        "layout_variant": "creative_asymmetry",
        "word_layout": "creative_asymmetry",
        "header_mode": "banner",
        "section_style": "block",
        "avatar_mode": "circle",
        "density": "balanced",
        "sample_role": "品牌营销经理",
        "preview_note": "顶部色块 + 标签式章节标题，视觉更活泼。",
    },
    {
        "id": "sys-campus-compact",
        "name": "应届校招 · 紧凑居中",
        "category": "应届校招",
        "display_category": "应届校招",
        "tags": ["校招", "实习", "紧凑", "居中"],
        "accent": "#4A69C6",
        "soft": "#F0F4FF",
        "ribbon": "#4A69C6",
        "ink": "#1E293B",
        "base_theme": "tech_indigo",
        "layout_id": "accent_header",
        "layout_variant": "campus_compact",
        "word_layout": "campus_compact",
        "header_mode": "top",
        "section_style": "numbered",
        "avatar_mode": "square",
        "density": "compact",
        "sample_role": "产品实习生",
        "preview_note": "居中头像与信息区，适合一页纸校招简历。",
    },
    {
        "id": "sys-sales-split",
        "name": "销售商务 · 双栏摘要",
        "category": "市场销售",
        "display_category": "市场销售",
        "tags": ["销售", "客户", "双栏", "成果"],
        "accent": "#9B5A69",
        "soft": "#FBEFF1",
        "ribbon": "#9B5A69",
        "ink": "#3B293C",
        "base_theme": "creative_plum",
        "layout_id": "accent_header",
        "layout_variant": "split_columns",
        "word_layout": "split_columns",
        "header_mode": "compact",
        "section_style": "block",
        "avatar_mode": "square",
        "density": "balanced",
        "sample_role": "大客户销售经理",
        "preview_note": "上半区分栏展示概述与教育/证书，下半部展开销售战绩。",
    },
    {
        "id": "sys-ats-mono",
        "name": "通用 · 打印友好",
        "category": "通用打印",
        "display_category": "通用打印",
        "tags": ["ATS", "打印", "单栏", "稳妥"],
        "accent": "#3D4654",
        "soft": "#F4F5F7",
        "ribbon": "#697484",
        "ink": "#28313F",
        "base_theme": "ats_mono",
        "layout_id": "accent_header",
        "layout_variant": "top_profile",
        "word_layout": "top_profile",
        "header_mode": "compact",
        "section_style": "line",
        "avatar_mode": "portrait",
        "density": "balanced",
        "sample_role": "综合岗候选人",
        "preview_note": "低装饰单栏结构，便于打印与 ATS 解析。",
    },
)


def default_templates() -> list[dict]:
    result: list[dict] = []
    for order, item in enumerate(_SYSTEM_TEMPLATES, start=1):
        row = deepcopy(item)
        row.update(
            {
                "version": 3,
                "active": True,
                "sort_order": order,
                "generation_adapter": "system_layout_v3",
                "source_file": "",
                "source_folder": "system",
                "source_key": "",
                "builtin": True,
            }
        )
        result.append(row)
    return result


def public_template(template: dict) -> dict:
    allowed = {
        "id",
        "name",
        "category",
        "display_category",
        "tags",
        "accent",
        "soft",
        "ribbon",
        "ink",
        "base_theme",
        "layout_id",
        "layout_variant",
        "header_mode",
        "section_style",
        "avatar_mode",
        "word_layout",
        "density",
        "version",
        "active",
        "sort_order",
        "generation_adapter",
        "preview_note",
        "sample_role",
        "builtin",
    }
    return {key: deepcopy(value) for key, value in template.items() if key in allowed}


def catalog_key(template_id: str) -> str:
    return f"resume-templates/{template_id}.json"


def sample_resume_for_template(template: dict) -> dict:
    """Deterministic sample content so preview always matches render structure."""
    role = str(template.get("sample_role") or "目标岗位候选人")
    category = str(template.get("display_category") or "通用")
    return {
        "name": "示例候选人",
        "title": role,
        "contact": {
            "phone": "13800000000",
            "email": "demo@example.com",
            "location": "南宁",
            "age": "28",
        },
        "summary": f"具备{category}方向相关经验，擅长将真实业绩结构化表达，适配目标岗位关键词与业务场景。",
        "skills": ["沟通协作", "目标拆解", "数据分析", "项目推进"],
        "experience": [
            {
                "company": "示例科技有限公司",
                "role": role,
                "period": "2021.03 - 至今",
                "details": [
                    "负责核心业务模块规划与落地，协同跨部门推进关键里程碑。",
                    "基于真实数据复盘转化漏斗，优化流程并沉淀可复用方法。",
                    "带教新人并输出标准作业手册，提升团队交付稳定性。",
                ],
            },
            {
                "company": "成长型企业示例",
                "role": "业务专员",
                "period": "2018.07 - 2021.02",
                "details": [
                    "独立完成日常运营与客户对接，沉淀可量化过程指标。",
                    "参与重点项目交付，负责需求澄清与进度同步。",
                ],
            },
        ],
        "projects": [
            {
                "name": f"{category}示范项目",
                "role": "核心成员",
                "period": "2023.01 - 2023.12",
                "details": [
                    "从需求梳理到上线复盘全流程参与，保证交付质量。",
                    "沉淀模板与检查清单，降低重复沟通成本。",
                ],
            }
        ],
        "education": [
            {
                "school": "示例大学",
                "degree": "本科",
                "major": "相关专业",
                "period": "2014.09 - 2018.06",
                "details": ["主修课程与实践项目结合，完成毕业设计。"],
            }
        ],
        "certificates": ["相关职业资格证书（示例）", "英语能力证明（示例）"],
    }
