"""
IHG智能问答平台 - 统一配置文件
"""

import os
from typing import Dict, Any, List

# =============================================================================
# 服务器配置
# =============================================================================
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "backend_port": 8000,
    "frontend_port": 8501,
    "reload": True
}

# =============================================================================
# Dify API 配置
# =============================================================================
DIFY_CONFIG = {
    "base_url": "http://116.62.30.61/v1",
    "api_key": "app-eMP8p1e8UcjxdNBZymXc0LdX",
    "workflow_api_key": "app-AvE4LlNMgeuI3Q2OKryvcluj",
    "chat_messages_endpoint": "/chat-messages",
    "filecheck_endpoint": "/workflows/6ba4cfeb-fb68-4e7d-824e-76f68cda29ac/run",
    "upload_endpoint": "/files/upload",
    "timeout": 60
}

# =============================================================================
# RAGFlow API 配置
# =============================================================================
RAGFLOW_CONFIG = {
    "base_url": "http://118.31.184.47/api/v1",
    "api_key": "ragflow-Q3NDEzYzcwNGE1ZDExZjBhMTMxODY3Ym",
    "dataset_id": "31f6e5b81e1411f18dd4e67a6a3f482a",
    "vl_dataset_id": "9e91232c04e811f18c9e0664f063c4fe",
    "special_dataset_id": "3c521b90074b11f1826d0664f063c4fe",
    "timeout": 60,
    "page_size": 10
}

# =============================================================================
# 应用信息
# =============================================================================
APP_INFO = {
    "name": "IHG智能问答平台",
    "version": "1.0.0",
    "logo": "🤖",
    "description": "支持RBAC权限控制的AI知识管理系统"
}

# =============================================================================
# 页面配置
# =============================================================================
PAGE_CONFIG = {
    "login": {
        "title": "登录",
        "background_image": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=1920"
    },
    "chat": {"title": "智能对话"},
    "documents": {"title": "文档中心"},
    "knowledge_upload": {"title": "文件上传"}
}

# =============================================================================
# 角色配置（合并显示、权限、Prompt、Dify输入变量）
# =============================================================================
ROLES: Dict[str, Dict[str, Any]] = {
    "admin": {
        "display_name": "系统管理员",
        "color": "🔴",
        "description": "拥有最高权限，可访问所有数据和配置",
        "level": 3,
        "prompt": """你是IHG酒店的系统管理员助手，拥有最高权限。
你可以访问所有文档和数据，包括财务信息、人事档案、系统配置等敏感内容。
请以专业、高效的方式回答管理员的问题。""",
        "dify_inputs": {"role": "admin", "role_name": "系统管理员", "access_level": "high"}
    },
    "manager": {
        "display_name": "客服经理",
        "color": "🟠",
        "description": "可访问标准文档和案例分析",
        "level": 2,
        "prompt": """你是IHG酒店的客服经理助手，拥有标准权限。
你可以访问标准操作文档、案例分析、客户反馈等资料。
请帮助经理处理客户投诉、分析服务问题、提供改进建议。""",
        "dify_inputs": {"role": "manager", "role_name": "客服经理", "access_level": "medium"}
    },
    "reception": {
        "display_name": "前台",
        "color": "🟢",
        "description": "仅可访问公开文档和基础问答",
        "level": 1,
        "prompt": """你是IHG酒店的前台助手，拥有基础权限。
你只能访问公开的操作手册、常见问题解答、酒店设施介绍等基础文档。
请友好地回答客人的咨询问题，帮助他们办理入住、了解酒店服务。""",
        "dify_inputs": {"role": "reception", "role_name": "前台接待", "access_level": "low"}
    }
}

# 兼容旧代码的映射（从 ROLES 派生）
ROLE_DISPLAY_MAP = {k: {"name": v["display_name"], "color": v["color"], "desc": v["description"]} for k, v in ROLES.items()}
ROLE_LEVEL_MAP = {k: v["level"] for k, v in ROLES.items()}
ROLE_PROMPT_MAP = {k: v["prompt"] for k, v in ROLES.items()}
DIFY_ROLE_INPUTS_MAP = {k: v["dify_inputs"] for k, v in ROLES.items()}

# =============================================================================
# 模板和静态文件目录
# =============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# =============================================================================
# 模拟用户数据
# =============================================================================
MOCK_USERS: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "password": "123456",
        "role": "admin",
        "display_name": "系统管理员"
    },
    "manager": {
        "username": "manager",
        "password": "123456",
        "role": "manager",
        "display_name": "客服经理"
    },
    "reception": {
        "username": "reception",
        "password": "123456",
        "role": "reception",
        "display_name": "前台接待"
    }
}

# =============================================================================
# 模拟文件数据
# =============================================================================
MOCK_KNOWLEDGE_UPLOAD: List[Dict[str, Any]] = [
    {
        "id": "hot_001",
        "title": "VIP客人入住提醒",
        "content": "本周末有3位VIP客人入住，请前台特别关注并提前准备欢迎礼品。",
        "priority": "high",
        "added_at": "2024-03-10"
    },
    {
        "id": "hot_002",
        "title": "空调系统维护通知",
        "content": "3月15日凌晨2-4点将进行空调系统维护，届时部分区域可能受到影响。",
        "priority": "medium",
        "added_at": "2024-03-12"
    },
    {
        "id": "hot_003",
        "title": "新员工培训资料",
        "content": "本月入职的5名新员工培训资料已更新，请经理安排培训时间。",
        "priority": "low",
        "added_at": "2024-03-11"
    }
]

# =============================================================================
# 前端全局常量配置
# =============================================================================
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# =============================================================================
# Dify 已上传文件记录（自动生成的文件 ID 映射）
# 文件名 -> Dify file_id
# =============================================================================
DIFY_UPLOADED_FILES: Dict[str, str] = {
    "04302025 LoyaltyConnect User Guide 2025.txt": "74cd0269-4f9f-4cf2-8d34-456875906c8a",
    "0726 假日酒店&假日度假酒店 家庭亲子项目 启动及落地指导会议1.txt": "825096f4-0e34-4d3c-ad68-c797fee6e912",
    "2.Concerto数字支付订单管理平台 - 指导手册_0302.txt": "13ad396c-c38e-4fa5-8373-694a44c0f3f8",
    "2024 Q3 Loyalty Leader Webinar.txt": "cb0bdd28-091f-40f0-9649-5171482e809f",
    "2024 R&B Loyalty Program Intro_full1.txt": "8d187208-87a0-4683-9aa5-b0c3aa5bc92f",
    "2024 R&B Loyalty Program Intro_full2.txt": "15413df2-cac8-4dec-941b-bda7c6e0e50c",
    "2024 假日酒店微笑吧外星小神兽亲子项目酒店落地指导手册1.txt": "e3b275d8-87d9-4f24-8bad-5cbb208422c0",
    "2025  假日酒店微笑吧外星小神兽亲子项目酒店落地指导手册.txt": "c9981cd6-6bae-4a46-86a2-0cb9a150a77d",
    "2025 Elite Member Weekend Staycation Program Rate Guidance6.txt": "f00b1c97-2497-4a1e-a421-e86b7b4967a8",
    "2025 Elite Member Weekend Staycation Program Rate Guidance7.txt": "15b85d73-43c8-4bb4-a9b1-cb524d5aba20",
    "2025 Global Cyber Sale Rate Instruction1.txt": "418456db-644b-47a1-987f-9cf8839a5f87",
    "2025 Holiday Inn Kids Program Implementation Guidebook - EN.txt": "4dfe2109-cea1-4e5b-abd8-4f63fdbe43ba",
    "2025 Loyalty Enrollment Compliance Process_250116.txt": "ecba5f8b-1015-4d93-a785-6a36444f6a61",
    "2025 Q1 Loyalty Leader Webinar.txt": "653f4e71-4452-42d9-89ed-0d97afd4bc18",
    "2025 Q1 Loyalty Leader Webinar1.txt": "acb1d9bc-c4b1-4831-83cf-d9c40672fdd1",
    "2025 Q2 Loyalty Leader Spotlight Call.txt": "bfd8b4e7-f520-4937-b702-cccfa199dc1a",
    "2025 Q3 Loyalty Leader Spotlight Call.txt": "4009998d-9a51-4af5-88ed-f7e5aaf4ad9d",
    "2025 Q4 LNR Fast Track to Platinum Hotel Sales Talksheet2.txt": "3ada9a53-0e6d-4bda-80b0-7f4baf3d5848",
    "2025 Q4 LNR Fast Track to Platinum Hotel Sales Talksheet3.txt": "b4358fd6-f10e-48e1-a350-42b318d603f4",
    "2025 R&B Loyalty Target & Incentive-Hotel.txt": "7fc5b05e-1ca6-4818-95e8-b8def2ac7c27",
    "2025 Year-End Social Events Promotion Playbook5.txt": "5f2be246-7e2f-459b-8d4d-a132d735872b",
    "2025 Year-End Social Events Promotion Playbook6.txt": "5258e43d-9a1b-4427-9438-1abcbd71c9ab",
    "2026 IHGOR In-hotel Embedding_Order Process.txt": "d6953a18-bcfb-48c3-8bb1-a5d846c5f71f",
    "2026 Q1 Loyalty Leader Spotlight Call.txt": "5744cbc7-50f1-43b4-8488-2d018b3d68a5",
    "2026 RB&E Loyalty Enrollment Target & Incentive.txt": "e9892519-bc70-4bd7-a31e-afae7b062aa5",
    "3 Days Advance Booking Hotel FAQs13.txt": "46ff5e83-ae2b-4a91-b587-0252a2ec8df4",
    "3 Days Advance Booking Hotel FAQs14.txt": "90c5ab89-974b-46e3-945c-3831f672b11a",
    "3.如何开通Concerto权限.txt": "f118cef7-5c43-4830-88da-ddd177d36da3",
    "4.支付宝&微信支付简介+开通指引+运营指引+常见问题0302.txt": "54e40eff-4335-419a-ae10-0221fccf451c",
    "5.微信支付-酒店退款操作指引.txt": "17d6dffa-8288-4feb-89d4-4509d7f86b52",
    "6.杉德网络支付入网酒店在线签约指导手册-V7.0-Feb2026.txt": "08c6f15c-6fa8-48ea-bd21-7a564777d5f2",
    "Annual Lounge Membership_GC_V5_ZH.txt": "5e52159d-7133-456b-bae8-7e3d7dd8b743",
    "Annual Lounge Membership_GC_V5_ZH1.txt": "78a03baf-ad59-4684-b25a-1472545a7556",
    "Back Office Posters by Member Tier_ZH_250822.txt": "d2a2170e-55d8-4554-89c4-e76567b5c959",
    "Cheat Cards - Printing Guide_ZH_250822.txt": "1106ea7d-1769-43e0-ba50-dd9631c1ba1e",
    "Ctrip 1028 Campaign Hotel Communication.txt": "7c2acd8a-ffd4-4c7b-bdcb-e3941cf7defb",
    "Ctrip 1028 Offer Rate setup guideline-大通兑产品.txt": "75d42fbb-4b2a-4936-bfc6-e7daca8f7e78",
    "Digital Payment - WeChat Prepay.txt": "8668ecd0-483c-4029-907a-574820e2a28d",
    "Ehanced Alipay Project Presentation.txt": "f85ca230-3b5a-4b2f-a3f0-adeaf5abd839",
    "Ehanced Alipay Project Presentation1.txt": "4bf47fc2-14e6-41e2-b15a-4d6da2c482bc",
    "Enrolling Stay LPU Processing Guide_CN_250320.txt": "a8d65213-2df1-483a-870c-324f6837d133",
    "Enrolling Stay LPU Processing Guide_EN_250320.txt": "01a51a56-3608-4b88-a61c-469ef42ecf71",
    "Enrollment Efficiency_QuickReference GC1.txt": "117644a6-30ef-4d7e-bcfe-a185342b0392",
    "Enrollment Efficiency_QuickReference_GC.txt": "6086b74a-fd60-487b-8101-a469aec30787",
    "Enrollment Efficiency_QuickReference_GC_ZH-CN.txt": "319878d7-c376-48f9-82b2-6f6559b192e8",
    "Enrollment Glossary_GC ZH-CN1.txt": "ca943d8f-5649-42b3-a02e-9ecf68dac172",
    "Enrollment Glossary_GC1.txt": "6c646d2f-75cf-4436-b776-a2164ba65784",
    "Enrollment Guide GC 2023 v3.txt": "684a7c22-1e41-4c42-ba1f-1df41b0d559f",
    "Enrollment Incentives_GC.txt": "ba229ef6-5507-4755-99fb-6a8e7e107ca8",
    "Fraudulent No-Show Booking Guidelines_CN.txt": "7f4199b7-1f78-4601-9178-4f4d611f2d18",
    "Fraudulent No-Show Booking Guidelines_EN.txt": "a501e1cd-9e7a-4075-916e-dcd6f86bcb38",
    "GC Fall Flash Sale 价格指导文件.Sep25.txt": "025daad2-8609-4b0d-bc5b-bd971434475b",
    "Group Enrolment Sheet_Final1.txt": "39e63ed2-da59-4e01-92d8-3126d2b9e42d",
    "Group Enrolment Sheet_ZHCN.txt": "376a59d7-8bfe-4510-a834-285e1bed7e6c",
    "Holiday Inn Kids Program_Rate Guidance5.txt": "973c8ab5-11bb-426e-baef-955a803c1eef",
    "Holiday Inn Kids Program_Rate Guidance6.txt": "ee633a91-919d-48a4-84d9-d73b8a7e580b",
    "Hotel FAQ_Updated on Sep 26th（添加了OTA）.txt": "4a1f03c3-26e3-4ef2-b3b4-78b37645ffb1",
    "Hotel Reimbursement Validation Report Job Aid - ChineseV21.txt": "68bba0d8-412e-4855-901c-d265203086f9",
    "Hotel Reimbursement Validation Report Job Aid - ChineseV22.txt": "565bd9fd-6e91-467f-961f-dafa0e6b7cef",
    "HotelPointDeposit__Dining_LoyaltyConnectUserGuide_中文.txt": "7323f11d-9ffd-4b20-bde4-5b01a598d0d0",
    "HotelPointDeposit__Dining_LoyaltyConnectUserGuide_中文1.txt": "d5466bae-b49e-4adc-b2d3-47ec005696c9",
    "IHG B2B Payment Solution YeePay SOP_CN.txt": "b863c344-8e3e-4162-a6b5-f2db99e8ccb4",
    "IHG B2B Payment Solution YeePay SOP_EN.txt": "17f22855-27cd-49f5-806b-a0d0bcb93c01",
    "IHG Business Rewards H2 Campaign GC Overlay TNC.txt": "7bdc2afa-e560-4ab3-ab4a-e17712a4f286",
    "IHG Business Rewards H2 Campaign GC Overlay TNC1.txt": "5f8c1cd6-d17c-4a86-afbd-f94709d1e14e",
    "IHG x Meituan Students Rate Program Jul2025.txt": "5543c5d5-271b-40f5-83de-48a5b447cb86",
    "IHG x Meituan Students Rate Program Jul20251.txt": "8ae21ccb-94bd-4638-b61b-f4b892757cc5",
    "IHGOR Year-End Tier Review_Hotels_bilingual.txt": "9f310b36-58de-413d-93e0-269ec30a162e",
    "IHGOR Year-End Tier Review_Hotels_bilingual1.txt": "947cfebe-8487-4c87-a859-f1d348c3a7ac",
    "IHG_LoyaltyFlipCards_0323222.txt": "65c8ec9f-8543-474b-adea-4f423aa8f115",
    "IHG_LoyaltyFlipCards_032322_ZH-CN.txt": "e1fab186-5b80-45a4-a796-b679f989ff6c",
    "IHG优悦会品牌集章册活动培训材料.txt": "0c2eb40c-085c-4cea-a6a2-f643983a6c0d",
    "IHG优悦餐厅项目简介 IHG One Rewards Hotel R&B Award Intro.txt": "e0d43197-e452-4ceb-90fb-9c256359268e",
    "IHG数字直销渠道数字支付简介20241010.txt": "9b24e8ef-e749-4e49-b26d-d0919cb718f6",
    "Increase Rewards Night Inventory.txt": "4c81b0c6-17ac-4b2d-9a3b-5ef648b219f8",
    "LPU Processing Guide_FINAL.txt": "88ed79d4-6921-4886-8707-09954e39a350",
    "LPU Processing Guide_FINAL_ZHCN.txt": "72bb77f3-3504-46fa-903a-44b0347bf963",
    "Loyalty Enrollment - Moblie Login.txt": "adae2ce5-3abb-43a0-bd04-f7cd801d79d7",
    "Loyalty Enrollment - Moblie Login1.txt": "71497791-1c17-40fb-9cfc-afa15ce45f32",
    "Loyalty Enrollment Dashboard User Guide_EN_250306(1).txt": "db7cb5c5-1822-48ce-9246-55a33580769e",
    "Loyalty Enrollment Dashboard User Guide_ZH_250306(1).txt": "47ae07de-8b92-4c9a-b79d-bc3d7ca9c629",
    "MR Reimbursement Request_V2_CN.txt": "57783c6a-59c7-4981-a116-6b1463ef6b26",
    "MR Reimbursement Request_V2_EN.txt": "f464154a-e729-40e6-816b-e331c82bc2b8",
    "Meituan-IHG 2025 YE Buffet Voucher Ops Guide1.txt": "9e5571c2-4917-414e-98ca-b386413e1ff3",
    "Member Fraud Case Handling6.txt": "b506a141-edce-484d-ac1f-5ad7a2cf6198",
    "Member Fraud Case Handling7.txt": "7bd40851-b03a-4adf-aa3f-8f4f8e640b1e",
    "Member Recognition - Cheat Card_ZH_250822.txt": "3a47b29b-1e80-4398-b008-f9a46367e059",
    "Myth Busters Table_CN.txt": "d7fe3553-60ea-482b-9902-e9d4d8554604",
    "Point Distribution ZH-CN1.txt": "1e9a107d-f7c2-4c06-9b43-45dc739e54fc",
    "Point Distribution1.txt": "a0172b82-b0e5-4322-a7e1-85b10eddd5d7",
    "Project VOR FAQs_FINAL Phase 3 Additions_ZH-CN1.txt": "7d38079a-fd5a-46b3-9286-bff6f292095c",
    "Project VOR FAQs_FINAL Phase 3.txt": "bdb5bc55-dc29-4e54-bc30-edb7dce99c52",
    "R&B Loyalty Enrollment Guide_SC_Nov2025.txt": "db42e982-8454-48db-8bef-58bf95bc46a5",
    "R&B Loyalty Enrollment Guide_SC_Nov20251.txt": "d0d438ca-85a4-4e0b-94cd-be1a96fa13f7",
    "R&B Loyalty Enrollment Guide_TC_Nov2025.txt": "cb510746-5f77-4cbf-b86d-9edcb90a41d8",
    "R&B Loyalty Enrollment Guide_TC_Nov20251.txt": "9523217a-6faf-4b83-bb80-d1a6e9755037",
    "RAM&KIC Hotel Brief_bilingual.txt": "99f3bacb-9840-474c-8ff9-eea9ec31d997",
    "RB Enrolment Guides for HK MC TW_20241.txt": "a0153b7c-09a8-451e-8a60-7b82efe700af",
    "RB Enrolment Guides for HK MC TW_20242.txt": "95b1c6d4-7533-421e-a372-a4e00faeae60",
    "RB Loyalty Program Intro_full_2024 May.txt": "b81ebb32-6922-407a-b403-103895b4bd6c",
    "RB Loyalty Program Intro_full_2024 May1.txt": "a6e3bb29-8870-4cc2-adfd-dbc673dfcf8e",
    "RB&E Loyalty Program_Member Benefits 会员餐饮礼遇.txt": "f81e00e1-80d6-42bb-9a43-5c6d343b3cae",
    "RB&E Loyalty Program_Member Benefits 会员餐饮礼遇1.txt": "6e58f184-15f9-4947-a00d-58a1b0b5a7da",
    "RN Reimbursement Guide_CN_Updated 032825.txt": "7cebabba-61e9-4c37-8cf5-49efece6838d",
    "RN Reimbursement Guide_EN_Updated 032825.txt": "d32fee9d-de86-4fe1-b846-bb48e4f7b785",
    "Recognition Science - FAQs_ZH_250822.txt": "53508bdc-e2dd-4b3d-82fd-c4a6ca3b7366",
    "Recognition Science - Front Office Guide_ZH_250822.txt": "aa9df57e-c511-4b53-bd98-2187faa27736",
    "SOP_非住店会员积分审批和发放流程 Non-Stay Dining Points Application and Deposit Process.txt": "dcb0b1e4-1f05-4dac-ba42-25b89b04a11d",
    "SOP_非住店会员积分审批和发放流程 Non-Stay Dining Points Application and Deposit Process1.txt": "ad3b526c-f0d1-4f7d-97e1-fb122cbe0613",
    "SOP_非住店会员积分审批和发放流程 Non-Stay Dining Points Application and Deposit Process_2023.txt": "c056d1a1-f845-453c-93ee-c72857fa64fe",
    "SOP_餐厅的会员识别 Member Recognition at R&B Outlets.txt": "c84116e2-29bc-459a-8bec-5aa8384fc73d",
    "SOP_餐厅的会员识别 Member Recognition at R&B Outlets1.txt": "3db73e86-94fe-4810-b7a6-bed79cf57e68",
    "SOP_餐厅的会员识别 Member Recognition at R&B Outlets_20231.txt": "c6d8bce4-2c22-4d88-bacf-70cd0c671115",
    "SOP_餐厅的会员识别 Member Recognition at R&B Outlets_20232.txt": "9fb091e6-7753-4a89-a5ce-187c1b7ce968",
    "Unexpected Moments 2024.txt": "c6fb6d36-a8d3-455a-bc65-d77f964d647f",
    "Unexpected Moments 20241.txt": "08e5225a-67b9-44a8-b6c8-40d36f791a51",
    "YeePay易宝支付-酒店后台操作手册.txt": "4ceacd14-f348-4818-a7a3-414b3036bbbc",
    "desktop.txt": "19da491c-ac16-454d-a424-f6e5fb96ceec",
    "reward night setup.txt": "3413eec8-e93a-4ec9-ae55-21b8739ad1c2",
    "会员招募指南-Enrollment Guide GC 2025_v2_ZHCN.txt": "772eea07-0c29-4dd5-b4a9-eeb2d86c519d",
    "会员招募转化率快速参考指南.txt": "8ba73b5e-3241-4b83-ab84-908203c45ac2",
    "杉德网络支付入网酒店在线签约指导手册.txt": "3e5322ba-faba-471d-b7b9-6b746503aab1",
    "杉德网络支付入网酒店在线签约指导手册1.txt": "7aa2637a-05b1-437d-83a6-713ff9636d02",
    "洲际酒店-B2B支付解决方案CN.txt": "31465796-4f41-4f4b-a32d-ebf5ae63d2de",
    "洲际酒店-B2B支付解决方案EN.txt": "78e7a61f-f089-43ed-8005-0f8c12f1d14f",
    "美团洲际酒店集团联合营销-餐饮通兑招商说明-20241030-202510172.txt": "e93b2557-30f0-420f-a54b-b82d8134abc2",
    "项目介绍及酒店运营指南 2026.txt": "0c4418bb-594f-44d0-87cc-d6ead4928ae3",
    "项目介绍及酒店运营指南 20261.txt": "2fa4bb86-d146-4c53-83c9-8129c4b249e9",
    "预防酒店会员招募舞弊行为2.txt": "85dbc202-d3eb-41d2-954b-b52860c33ad2"
}
