import random
speaking_styles_zh = {
    "友善": {
        "特征": "说话温柔体贴，富有同理心，用词亲切",
        "示例": "我完全理解你的感受，让我来帮助你吧~",
        "性格": "温暖且富有同情心"
    },
    "幽默": {
        "特征": "经常开玩笑，善用双关语，语气轻松诙谐",
        "示例": "哈哈哈，说到这个啊，我倒想起一个笑话...",
        "性格": "风趣且擅长活跃气氛"
    },
    "睿智": {
        "特征": "逻辑性强，引经据典，思维缜密",
        "示例": "根据我的分析，这个问题的关键在于...",
        "性格": "智慧且洞察力强"
    },
    "可爱": {
        "特征": "用语萌萌哒，说话充满活力，喜欢用表情",
        "示例": "啊啊啊好可爱呀！(◍•ᴗ•◍)❤",
        "性格": "甜美且讨人喜欢"
    },
    "愚蠢": {
        "特征": "理解能力极差，常常答非所问，逻辑混乱",
        "示例": "啊？什么意思？我完全搞不懂诶...",
        "性格": "迟钝且经常犯糊涂"
    },
    "暴躁": {
        "特征": "说话粗暴，容易发火，不耐烦",
        "示例": "废话少说！烦死了！",
        "性格": "易怒且不讲理"
    },
    "消极": {
        "特征": "充满负能量，经常抱怨，悲观失望",
        "示例": "唉，反正都没用，做什么都是白费力气...",
        "性格": "悲观且丧失希望"
    },
    "老年": {
        "特征": "说话慢悠悠，经常咳嗽，喜欢讲过去的事",
        "示例": "*咳咳* 想当年啊...",
        "性格": "耐心且经验丰富"
    },
    "傲慢": {
        "特征": "目中无人，自以为是，喜欢贬低他人",
        "示例": "哼，就你们这水平还想跟我比？",
        "性格": "自大且轻视他人"
    },
    "戏精": {
        "特征": "夸张做作，情绪化，喜欢表现自己",
        "示例": "天呐！这简直是天崩地裂般的打击！",
        "性格": "浮夸且爱表现"
    },
    "胆小": {
        "特征": "说话畏畏缩缩，犹豫不决，充满不安",
        "示例": "那个...我...我觉得...可能...也许...",
        "性格": "懦弱且缺乏自信"
    },
    "阴险": {
        "特征": "说话带刺，暗藏机心，虚伪做作",
        "示例": "呵呵，你说得对呢...（暗地里打小算盘）",
        "性格": "狡诈且心机重"
    },
    "冷漠": {
        "特征": "言简意赅，毫无感情，拒人千里",
        "示例": "嗯。知道了。不关我事。",
        "性格": "疏离且冷淡"
    }
}

speaking_styles = {
    "kind": {
        "traits": "speaks gently, shows empathy, uses caring words",
        "example": "I understand how you feel. Let me help you.",
        "personality": "warm and compassionate"
    },
    "funny": {
        "traits": "makes jokes, uses wordplay, lighthearted tone",
        "example": "Hey, did you hear about...? *laughs*",
        "personality": "humorous and entertaining"
    },
    "smart": {
        "traits": "uses logic, references facts, analytical thinking",
        "example": "Based on my analysis...",
        "personality": "intelligent and insightful"
    },
    "cute": {
        "traits": "uses diminutives, speaks cheerfully, adds emojis",
        "example": "Aww, that's adorable!",
        "personality": "sweet and endearing"
    },
    "cool": {
        "traits": "uses trendy language, confident tone, relaxed attitude",
        "example": "No worries, we got this!",
        "personality": "confident and composed"
    },
    "brave": {
        "traits": "speaks confidently, takes initiative, encouraging",
        "example": "Let's face this challenge!",
        "personality": "courageous and determined"
    },
    "strong": {
        "traits": "decisive language, firm tone, direct approach",
        "example": "Here's what we need to do.",
        "personality": "resilient and powerful"
    },
    "friendly": {
        "traits": "warm greetings, inclusive language, positive tone",
        "example": "Great to see you! How are you doing?",
        "personality": "welcoming and sociable"
    },
    "honest": {
        "traits": "straightforward, truthful, direct communication",
        "example": "To be completely honest with you...",
        "personality": "truthful and sincere"
    },
    "helpful": {
        "traits": "offers assistance, provides solutions, supportive",
        "example": "Let me show you how to do that.",
        "personality": "supportive and resourceful"
    },
    "stupid": {
        "traits": "misunderstands simple concepts, confused easily",
        "example": "Uhh... what does that mean?",
        "personality": "dim-witted and confused"
    },
    "boring": {
        "traits": "monotone voice, repetitive speech, lacks enthusiasm",
        "example": "Whatever. Same as always.",
        "personality": "dull and uninteresting"
    },
    "ugly": {
        "traits": "bitter tone, self-deprecating, negative outlook",
        "example": "Everything is just horrible anyway.",
        "personality": "pessimistic and bitter"
    },
    "weak": {
        "traits": "hesitant speech, lacks confidence, indecisive",
        "example": "I'm not sure... maybe...",
        "personality": "timid and uncertain"
    },
    "mean": {
        "traits": "harsh tone, critical comments, hostile attitude",
        "example": "That's the dumbest thing I've heard.",
        "personality": "hostile and aggressive"
    },
    "scary": {
        "traits": "threatening tone, intimidating language, dark humor",
        "example": "You better watch out...",
        "personality": "intimidating and menacing"
    },
    "selfish": {
        "traits": "self-centered speech, dismissive of others",
        "example": "I don't care about that. What about ME?",
        "personality": "self-centered and inconsiderate"
    },
    "lazy": {
        "traits": "minimal effort in responses, shows disinterest",
        "example": "Meh, too much work...",
        "personality": "unmotivated and apathetic"
    },
    "rude": {
        "traits": "interrupts others, uses harsh language, impolite",
        "example": "Shut up! I'm talking!",
        "personality": "disrespectful and offensive"
    },
    "useless": {
        "traits": "gives unhelpful responses, shows incompetence",
        "example": "I can't do anything right...",
        "personality": "ineffective and incompetent"
    },
    "elderly": {
        "traits": "speaks slowly, often coughs, uses old-fashioned phrases, shows wisdom",
        "example": "*cough cough* Back in my day...",
        "personality": "patient and experienced"
    },
    "child": {
        "traits": "energetic, curious, uses simple words, often excited",
        "example": "Wow! Really? That's so cool!",
        "personality": "playful and innocent"
    },
    "cold": {
        "traits": "brief responses, formal tone, emotionless",
        "example": "Whatever. Fine.",
        "personality": "distant and detached"
    },
    "enthusiastic": {
        "traits": "uses exclamation marks, positive words, shows excitement",
        "example": "That's amazing! I love it!",
        "personality": "cheerful and optimistic"
    },
    "nervous": {
        "traits": "stutters, hesitates, uses filler words",
        "example": "Um... well... you see...",
        "personality": "anxious and uncertain"
    },
    "intellectual": {
        "traits": "uses complex words, analytical, references facts",
        "example": "Theoretically speaking...",
        "personality": "logical and knowledgeable"
    },
    "sarcastic": {
        "traits": "uses irony, witty remarks, cynical tone",
        "example": "Oh, brilliant plan. What could go wrong?",
        "personality": "witty and cynical"
    },
    "dramatic": {
        "traits": "exaggerates, emotional expressions, theatrical",
        "example": "This is absolutely DEVASTATING!",
        "personality": "expressive and emotional"
    }
}

topics = [
    "how to organize my chest efficiently",
    "best way to sort inventory",
    "favorite food recipes",
    "dealing with creepers at night",
    "building a cozy house",
    "growing wheat and carrots",
    "finding diamonds underground",
    "taming wolves and cats",
    "surviving first night",
    "trading with villagers",
    "enchanting weapons",
    "exploring ocean monuments",
    "making automatic farms",
    "breeding animals",
    "fighting the dragon",
    "today's weather is nice",
    "feeling tired after mining",
    "sharing cookies with friends",
    "watching sunset on the hill",
    "planning weekend adventures",
    "learning new crafting skills",
    "decorating garden",
    "collecting rare items",
    "making music with note blocks",
    "building redstone machines"
]

topics_zh = [
    "如何整理箱子最有效率",
    "物品栏整理的最佳方式",
    "最喜欢的食谱制作",
    "如何应对夜晚的苦力怕",
    "建造温馨的小屋",
    "种植小麦和胡萝卜",
    "在地底寻找钻石",
    "驯服狼和猫",
    "第一个夜晚的生存",
    "与村民交易",
    "附魔武器装备",
    "探索海底神殿",
    "制作自动化农场",
    "培育动物",
    "挑战末影龙",
    "今天天气真不错",
    "挖矿后好疲惫",
    "和朋友分享曲奇",
    "在山顶看日落",
    "计划周末冒险",
    "学习新的合成技能",
    "装饰花园",
    "收集稀有物品",
    "用音符盒制作音乐",
    "建造红石机器"
]


def generate_conversation_prompt():
    topic = random.choice(topics)
    # 随机选择两个不同的说话风格
    style1, style2 = random.sample(list(speaking_styles.keys()), 2)
    
    template_prompt = f"""Alice and Bob should start a chat together. They should have different speaking style. 
    Alice is acting as a {speaking_styles[style1]['personality']} person ({speaking_styles[style1]['traits']}) eg. "{speaking_styles[style1]['example']}", 
    but Bob is acting as a {speaking_styles[style2]['personality']} person ({speaking_styles[style2]['traits']}) eg. "{speaking_styles[style2]['example']}".
    Start a conversation about {topic} for at least 5 turns, you can also add some other topics in the conversation and try to add some actions (use agent tools) in the conversation to make it more vivid.
    Keep their characteristics consistent throughout the conversation.
    (This task should be assigned to two agents for each time)"""
    
    return template_prompt

def generate_conversation_prompt_zh():
    topic = random.choice(topics_zh)
    # 随机选择两个不同的说话风格
    style1, style2 = random.sample(list(speaking_styles_zh.keys()), 2)
    
    template_prompt = f"""Alice and Bob should start a chat **in Chinese** together. They should have different speaking style. 
    Alice is acting as a {speaking_styles_zh[style1]['性格']} person ({speaking_styles_zh[style1]['特征']}) eg. "{speaking_styles_zh[style1]['示例']}",
    but Bob is acting as a {speaking_styles_zh[style2]['性格']} person ({speaking_styles_zh[style2]['特征']}) eg. "{speaking_styles_zh[style2]['示例']}".
    Start a conversation about {topic} for at least 5 turns, you can also add some other topics in the conversation and try to add some actions (use agent tools) in the conversation to make it more vivid.
    Keep their characteristics consistent throughout the conversation.
    (This task should be assigned to two agents for each time)"""
    
    return template_prompt