"""
意图分类模块 - Intent Classifier
基于规则的客服意图识别，可扩展为ML模型
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json
import pickle
from pathlib import Path


class IntentType(Enum):
    """意图类型枚举"""
    # 订单相关
    ORDER_STATUS = "查询订单状态"
    ORDER_CANCEL = "取消订单"
    ORDER_MODIFY = "修改订单"
    ORDER_TRACKING = "物流查询"
    
    # 售后相关
    REFUND_REQUEST = "申请退款"
    RETURN_REQUEST = "申请退货"
    EXCHANGE_REQUEST = "申请换货"
    
    # 产品相关
    PRODUCT_INQUIRY = "产品咨询"
    PRICE_INQUIRY = "价格咨询"
    STOCK_INQUIRY = "库存查询"
    
    # 账户相关
    ACCOUNT_ISSUE = "账户问题"
    PASSWORD_RESET = "密码重置"
    
    # 支付相关
    PAYMENT_ISSUE = "支付问题"
    PAYMENT_METHOD = "支付方式"
    
    # 投诉建议
    COMPLAINT = "投诉"
    SUGGESTION = "建议"
    
    # 其他
    GREETING = "问候"
    GOODBYE = "结束对话"
    THANKS = "感谢"
    UNKNOWN = "未知意图"
    HUMAN_AGENT = "转人工"


@dataclass
class Intent:
    """意图识别结果"""
    intent_type: IntentType
    confidence: float
    entities: Dict[str, List[str]] = field(default_factory=dict)
    matched_keywords: List[str] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class IntentRule:
    """意图规则"""
    intent_type: IntentType
    keywords: List[str]
    patterns: List[str] = field(default_factory=list)
    priority: int = 1  # 优先级，数字越大优先级越高
    required_entities: List[str] = field(default_factory=list)


class IntentClassifier:
    """
    意图分类器
    
    支持：
    1. 基于关键词的规则匹配
    2. 正则表达式模式匹配
    3. 实体提取
    4. 可扩展为ML模型
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.rules: List[IntentRule] = []
        self.entity_patterns: Dict[str, str] = {}
        self.intent_stats: Dict[IntentType, int] = defaultdict(int)
        self.confidence_threshold = 0.6
        
        # 初始化默认规则
        self._init_default_rules()
        self._init_entity_patterns()
        
        if model_path and Path(model_path).exists():
            self.load(model_path)
    
    def _init_default_rules(self) -> None:
        """初始化默认意图规则"""
        default_rules = [
            # 订单相关
            IntentRule(
                intent_type=IntentType.ORDER_STATUS,
                keywords=["订单", "状态", "到哪了", "进度", "发货", "情况"],
                patterns=[r"订单[号ID]?[是为]?([\d]+)", r"查[询看]?订单"],
                priority=3
            ),
            IntentRule(
                intent_type=IntentType.ORDER_CANCEL,
                keywords=["取消", "撤销", "不要了", "退掉", "删掉"],
                patterns=[r"取消订单", r"不要[了啦]"],
                priority=4
            ),
            IntentRule(
                intent_type=IntentType.ORDER_MODIFY,
                keywords=["修改", "改", "换", "更改", "变更"],
                patterns=[r"改地址", r"改[换]?商品", r"修改订单"],
                priority=3
            ),
            IntentRule(
                intent_type=IntentType.ORDER_TRACKING,
                keywords=["物流", "快递", "到哪了", "运送", "配送", "发货"],
                patterns=[r"物流[信息]?", r"快递[号]?([\d]+)"],
                priority=3
            ),
            
            # 售后相关
            IntentRule(
                intent_type=IntentType.REFUND_REQUEST,
                keywords=["退款", "退钱", "返还", "钱退"],
                patterns=[r"申请退款", r"[我要]?退款"],
                priority=4
            ),
            IntentRule(
                intent_type=IntentType.RETURN_REQUEST,
                keywords=["退货", "退回去", "寄回", "退回"],
                patterns=[r"申请退货", r"[我要]?退货"],
                priority=4
            ),
            IntentRule(
                intent_type=IntentType.EXCHANGE_REQUEST,
                keywords=["换货", "更换", "换一个", "换尺码", "换颜色"],
                patterns=[r"申请换货", r"[我要]?换货"],
                priority=4
            ),
            
            # 产品相关
            IntentRule(
                intent_type=IntentType.PRODUCT_INQUIRY,
                keywords=["产品", "商品", "东西", "这个", "怎么样", "好用吗"],
                patterns=[r"[这那]?个[商品产品]?", r"介绍[一下]?"],
                priority=2
            ),
            IntentRule(
                intent_type=IntentType.PRICE_INQUIRY,
                keywords=["价格", "多少钱", "怎么卖", "优惠", "打折", "便宜"],
                patterns=[r"多少[钱块]?", r"[有没]?优惠"],
                priority=2
            ),
            IntentRule(
                intent_type=IntentType.STOCK_INQUIRY,
                keywords=["库存", "有货", "还有吗", "缺货", "现货"],
                patterns=[r"[有没]?货", r"库存[多少]?"],
                priority=2
            ),
            
            # 账户相关
            IntentRule(
                intent_type=IntentType.ACCOUNT_ISSUE,
                keywords=["账户", "账号", "登录", "注册", "上不去"],
                patterns=[r"登[录不]?上", r"账号[问题]?"],
                priority=3
            ),
            IntentRule(
                intent_type=IntentType.PASSWORD_RESET,
                keywords=["密码", "忘记", "重置", "找回", "修改密码"],
                patterns=[r"忘记密码", r"重置密码", r"改密码"],
                priority=3
            ),
            
            # 支付相关
            IntentRule(
                intent_type=IntentType.PAYMENT_ISSUE,
                keywords=["支付", "付款", "付不了", "失败", "扣款"],
                patterns=[r"支付失败", r"付不了[钱款]?"],
                priority=3
            ),
            IntentRule(
                intent_type=IntentType.PAYMENT_METHOD,
                keywords=["支付方式", "微信", "支付宝", "银行卡", "分期"],
                patterns=[r"[支持]?什么支付", r"怎么付款"],
                priority=2
            ),
            
            # 投诉建议
            IntentRule(
                intent_type=IntentType.COMPLAINT,
                keywords=["投诉", "举报", "不满", "差评", "态度差", "欺骗"],
                patterns=[r"我要投诉", r"[太很]?差[劲]?"],
                priority=5
            ),
            IntentRule(
                intent_type=IntentType.SUGGESTION,
                keywords=["建议", "意见", "希望", "能不能", "建议你们"],
                patterns=[r"[有个]?建议", r"希望[你们]?"],
                priority=2
            ),
            
            # 转人工
            IntentRule(
                intent_type=IntentType.HUMAN_AGENT,
                keywords=["人工", "客服", "找人工", "转人工", "真人", "经理", "主管"],
                patterns=[r"转人工", r"找[真人]?客服", r"人工[客服服务]?"],
                priority=5
            ),
            
            # 社交
            IntentRule(
                intent_type=IntentType.GREETING,
                keywords=["你好", "您好", "在吗", "有人吗", "hi", "hello", "在不在"],
                patterns=[r"^你好", r"^您好", r"^[在嗨]"],
                priority=1
            ),
            IntentRule(
                intent_type=IntentType.GOODBYE,
                keywords=["再见", "拜拜", "bye", "结束", "挂了", "走了"],
                patterns=[r"^再见", r"^拜拜"],
                priority=1
            ),
            IntentRule(
                intent_type=IntentType.THANKS,
                keywords=["谢谢", "感谢", "多谢", "谢了", "thank"],
                patterns=[r"^谢谢", r"^感谢"],
                priority=1
            ),
        ]
        
        self.rules = default_rules
    
    def _init_entity_patterns(self) -> None:
        """初始化实体提取模式"""
        self.entity_patterns = {
            "order_id": r"订单[号ID]?[是为]?\s*[:：]?\s*([A-Z0-9]{6,20})",
            "phone": r"1[3-9]\d{9}",
            "email": r"[\w.-]+@[\w.-]+\.\w+",
            "product_name": r"[《【]([^《》【】]+)[》】]",
            "amount": r"(\d+[\.,]?\d*)\s*[元块]?",
            "date": r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)",
        }
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """提取实体"""
        entities = defaultdict(list)
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                entities[entity_type] = matches
        
        return dict(entities)
    
    def classify(self, text: str) -> Intent:
        """
        分类意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            意图识别结果
        """
        text = text.strip().lower()
        
        # 提取实体
        entities = self._extract_entities(text)
        
        # 计算每个意图的匹配分数
        intent_scores: Dict[IntentType, Tuple[float, List[str]]] = {}
        
        for rule in self.rules:
            score = 0.0
            matched_keywords = []
            
            # 关键词匹配
            for keyword in rule.keywords:
                if keyword in text:
                    score += 1.0
                    matched_keywords.append(keyword)
            
            # 正则模式匹配
            for pattern in rule.patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 2.0  # 模式匹配权重更高
                    matched_keywords.append(f"pattern:{pattern[:20]}")
            
            # 优先级加权
            score *= rule.priority
            
            if score > 0:
                intent_scores[rule.intent_type] = (score, matched_keywords)
        
        # 选择最佳意图
        if not intent_scores:
            return Intent(
                intent_type=IntentType.UNKNOWN,
                confidence=0.0,
                entities=entities,
                matched_keywords=[],
                raw_text=text
            )
        
        # 按分数排序
        best_intent = max(intent_scores.items(), key=lambda x: x[1][0])
        intent_type, (score, matched_keywords) = best_intent
        
        # 计算置信度 (归一化)
        total_score = sum(s for s, _ in intent_scores.values())
        confidence = score / total_score if total_score > 0 else 0
        
        # 更新统计
        self.intent_stats[intent_type] += 1
        
        return Intent(
            intent_type=intent_type,
            confidence=round(min(confidence, 1.0), 3),
            entities=entities,
            matched_keywords=matched_keywords,
            raw_text=text
        )
    
    def classify_batch(self, texts: List[str]) -> List[Intent]:
        """批量分类"""
        return [self.classify(text) for text in texts]
    
    def add_rule(self, rule: IntentRule) -> None:
        """添加自定义规则"""
        self.rules.append(rule)
    
    def remove_rule(self, intent_type: IntentType) -> None:
        """移除规则"""
        self.rules = [r for r in self.rules if r.intent_type != intent_type]
    
    def update_keywords(
        self, 
        intent_type: IntentType, 
        keywords: List[str],
        mode: str = "append"
    ) -> None:
        """
        更新关键词 (热更新支持)
        
        Args:
            intent_type: 意图类型
            keywords: 关键词列表
            mode: "append" 追加, "replace" 替换
        """
        for rule in self.rules:
            if rule.intent_type == intent_type:
                if mode == "replace":
                    rule.keywords = keywords
                else:
                    rule.keywords = list(set(rule.keywords + keywords))
                return
        
        # 如果不存在该规则，创建新规则
        if mode == "replace" or mode == "append":
            self.rules.append(IntentRule(
                intent_type=intent_type,
                keywords=keywords,
                priority=2
            ))
    
    def get_intent_distribution(self) -> Dict[str, int]:
        """获取意图分布统计"""
        return {k.value: v for k, v in self.intent_stats.items()}
    
    def get_suggested_response(self, intent: Intent) -> str:
        """
        根据意图获取建议回复
        
        Args:
            intent: 意图识别结果
            
        Returns:
            建议回复文本
        """
        responses = {
            IntentType.ORDER_STATUS: "我来帮您查询订单状态，请提供订单号。",
            IntentType.ORDER_CANCEL: "我理解您想取消订单，请提供订单号，我帮您处理。",
            IntentType.ORDER_MODIFY: "好的，请告诉我您需要修改什么信息。",
            IntentType.ORDER_TRACKING: "我来帮您查询物流信息，请提供订单号或快递单号。",
            IntentType.REFUND_REQUEST: "我来帮您处理退款申请，请提供订单号和退款原因。",
            IntentType.RETURN_REQUEST: "我来帮您处理退货申请，请提供订单号和退货原因。",
            IntentType.EXCHANGE_REQUEST: "我来帮您处理换货申请，请提供订单号和需要更换的规格。",
            IntentType.PRODUCT_INQUIRY: "请问您对哪款产品感兴趣？我可以为您详细介绍。",
            IntentType.PRICE_INQUIRY: "这款产品的价格是XXX元，目前有优惠活动。",
            IntentType.STOCK_INQUIRY: "我来帮您查询库存情况。",
            IntentType.ACCOUNT_ISSUE: "我来帮您解决账户问题，请描述具体情况。",
            IntentType.PASSWORD_RESET: "我来帮您重置密码，请提供注册手机号。",
            IntentType.PAYMENT_ISSUE: "支付遇到问题了吗？请告诉我具体情况。",
            IntentType.PAYMENT_METHOD: "我们支持微信支付、支付宝、银行卡等多种支付方式。",
            IntentType.COMPLAINT: "非常抱歉给您带来不好的体验，我会认真对待您的反馈。",
            IntentType.SUGGESTION: "感谢您的宝贵建议，我们会认真考虑。",
            IntentType.HUMAN_AGENT: "好的，我为您转接人工客服，请稍等。",
            IntentType.GREETING: "您好！很高兴为您服务，请问有什么可以帮您？",
            IntentType.GOODBYE: "感谢您的咨询，祝您生活愉快，再见！",
            IntentType.THANKS: "不客气，很高兴能帮到您！",
            IntentType.UNKNOWN: "抱歉，我没有完全理解您的意思，能否换一种说法？",
        }
        
        return responses.get(intent.intent_type, "请问有什么可以帮您？")
    
    def save(self, path: str) -> None:
        """保存模型"""
        # 将规则转换为可序列化格式
        serializable_rules = []
        for rule in self.rules:
            serializable_rules.append({
                'intent_type': rule.intent_type.name,
                'keywords': rule.keywords,
                'patterns': rule.patterns,
                'priority': rule.priority,
                'required_entities': rule.required_entities
            })
        
        data = {
            'rules': serializable_rules,
            'entity_patterns': self.entity_patterns,
            'intent_stats': {k.name: v for k, v in self.intent_stats.items()},
            'confidence_threshold': self.confidence_threshold,
            'saved_at': datetime.now().isoformat()
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, path: str) -> 'IntentClassifier':
        """加载模型 (热更新支持)"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 恢复规则
        self.rules = []
        for rule_data in data['rules']:
            self.rules.append(IntentRule(
                intent_type=IntentType[rule_data['intent_type']],
                keywords=rule_data['keywords'],
                patterns=rule_data['patterns'],
                priority=rule_data['priority'],
                required_entities=rule_data['required_entities']
            ))
        
        self.entity_patterns = data['entity_patterns']
        self.confidence_threshold = data['confidence_threshold']
        
        # 恢复统计
        self.intent_stats = defaultdict(int)
        for k, v in data.get('intent_stats', {}).items():
            try:
                self.intent_stats[IntentType[k]] = v
            except KeyError:
                pass
        
        return self
    
    def export_rules(self, output_path: str) -> None:
        """导出规则到文件"""
        rules_data = []
        for rule in self.rules:
            rules_data.append({
                'intent_type': rule.intent_type.value,
                'keywords': rule.keywords,
                'patterns': rule.patterns,
                'priority': rule.priority
            })
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(rules_data, f, ensure_ascii=False, indent=2)


# 便捷函数
def quick_classify(text: str) -> Dict:
    """快速分类接口"""
    classifier = IntentClassifier()
    intent = classifier.classify(text)
    
    return {
        "intent": intent.intent_type.value,
        "confidence": intent.confidence,
        "entities": intent.entities,
        "suggested_response": classifier.get_suggested_response(intent)
    }


def batch_classify(texts: List[str]) -> List[Dict]:
    """批量分类接口"""
    classifier = IntentClassifier()
    intents = classifier.classify_batch(texts)
    
    return [
        {
            "text": text,
            "intent": intent.intent_type.value,
            "confidence": intent.confidence
        }
        for text, intent in zip(texts, intents)
    ]


if __name__ == "__main__":
    # 示例用法
    classifier = IntentClassifier()
    
    test_messages = [
        "你好，我想查询我的订单",
        "订单号123456到哪里了？",
        "我要退款",
        "这个产品多少钱？",
        "怎么联系人工客服？",
        "谢谢你的帮助",
        "我要投诉你们的服务",
        "忘记密码了怎么办",
    ]
    
    print("=" * 70)
    print("意图分类测试")
    print("=" * 70)
    
    for msg in test_messages:
        intent = classifier.classify(msg)
        response = classifier.get_suggested_response(intent)
        
        print(f"\n用户: {msg}")
        print(f"意图: {intent.intent_type.value} (置信度: {intent.confidence})")
        print(f"匹配关键词: {intent.matched_keywords}")
        print(f"提取实体: {intent.entities}")
        print(f"建议回复: {response}")
    
    # 测试热更新
    print("\n" + "=" * 70)
    print("热更新测试 - 添加新关键词")
    print("=" * 70)
    
    classifier.update_keywords(
        IntentType.PRICE_INQUIRY, 
        ["价位", "贵不贵", "值不值"],
        mode="append"
    )
    
    test_msg = "这个价位贵不贵？"
    intent = classifier.classify(test_msg)
    print(f"\n用户: {test_msg}")
    print(f"意图: {intent.intent_type.value} (置信度: {intent.confidence})")
    print(f"匹配关键词: {intent.matched_keywords}")
