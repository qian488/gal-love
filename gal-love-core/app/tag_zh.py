"""Built-in VNDB English tag -> Chinese mapping and alias lookup.

The canonical names are the English names used by VNDB.  Every entry also
carries a Chinese display name and a list of common aliases (English
synonyms, Chinese synonyms and short forms).  ``canonical_lookup`` resolves
any of those spellings to the same canonical tag.
"""

from __future__ import annotations

import sqlite3

from .normalize import json_dumps, json_loads, normalize_text, unique_preserving_order

# canonical English name -> (中文名, 别名列表)
TAG_ZH_MAP: dict[str, tuple[str, list[str]]] = {
    "romance": ("恋爱", ["love", "恋爱", "爱情", "romantic"]),
    "comedy": ("喜剧", ["搞笑", "喜剧", "comical", "humor"]),
    "school": ("校园", ["校园", "学园", "school life"]),
    "fantasy": ("奇幻", ["奇幻", "魔幻", "fantasy world"]),
    "drama": ("剧情", ["剧情", "dramatic"]),
    "mystery": ("推理", ["推理", "悬疑", "mystery novel"]),
    "horror": ("恐怖", ["恐怖", "horror novel"]),
    "ero": ("色情", ["色情", "成人", "erotic", "h内容"]),
    "visual novel": ("视觉小说", ["vn", "adv", "avg", "visualnovel"]),
    "kinetic novel": ("动态小说", ["动态小说", "kineticnovel"]),
    "sound novel": ("音响小说", ["音响小说", "soundnovel"]),
    "adventure": ("冒险", ["冒险", "adventure game"]),
    "action": ("动作", ["动作", "action game"]),
    "sci-fi": ("科幻", ["科幻", "scifi", "sf", "science fiction"]),
    "slice of life": ("日常", ["日常", "日常系", "生活片段", "sliceoflife"]),
    "psychological": ("心理", ["心理", "psychological thriller"]),
    "thriller": ("惊悚", ["惊悚", "thriller"]),
    "supernatural": ("超自然", ["超自然", "灵异"]),
    "magic": ("魔法", ["魔法体系", "法术", "magic system"]),
    "mecha": ("机甲", ["机甲", "mecha"]),
    "historical": ("历史", ["历史", "historical fiction"]),
    "war": ("战争", ["战争", "war story"]),
    "sports": ("运动", ["运动", "体育", "sports"]),
    "music": ("音乐", ["音乐", "musical"]),
    "idol": ("偶像", ["偶像", "idol"]),
    "cooking": ("料理", ["料理", "烹饪", "food"]),
    "dating sim": ("恋爱模拟", ["恋爱模拟", "模拟恋爱", "datingsim"]),
    "tragedy": ("悲剧", ["悲剧", "tragic"]),
    "tearjerker": ("催泪", ["催泪", "感人"]),
    "happy ending": ("圆满结局", ["圆满结局", "happyend", "he"]),
    "multiple endings": ("多结局", ["多结局", "multiend"]),
    "time travel": ("时空穿越", ["时空穿越", "穿越", "timetravel"]),
    "amnesia": ("失忆", ["失忆", "记忆丧失"]),
    "memory manipulation": ("记忆操纵", ["记忆操纵", "记忆修改"]),
    "artificial intelligence": ("人工智能", ["人工智能", "ai"]),
    "virtual reality": ("虚拟现实", ["虚拟现实", "vr"]),
    "robot": ("机器人", ["机器人", "robot"]),
    "android": ("仿生人", ["仿生人", "android"]),
    "yuri": ("百合", ["百合", "gl", "女同性恋", "shoujo ai"]),
    "yaoi": ("耽美", ["bl", "男同性恋", "shounen ai"]),
    "otome": ("乙女", ["乙女", "otome game"]),
    "bara": ("熊系", ["熊系", "bara", "肌肉男"]),
    "crossdressing": ("女装", ["女装", "伪娘", "crossdress"]),
    "gender bender": ("性别转换", ["性别转换", "性转", "genderbend"]),
    "cosplay": ("角色扮演", ["角色扮演", "cosplay"]),
    "maid": ("女仆", ["女仆", "maid"]),
    "nurse": ("护士", ["护士", "nurse"]),
    "teacher": ("教师", ["教师", "老师", "teacher"]),
    "student": ("学生", ["学生", "student"]),
    "siblings": ("兄弟姐妹", ["兄弟姐妹", "兄妹", "sibling"]),
    "parent child": ("亲子", ["亲子", "父母", "parentchild"]),
    "friendship": ("友情", ["友情", "友谊", "friendship"]),
    "family": ("家庭", ["家庭", "family"]),
    "gore": ("血腥", ["血腥", "暴力血腥", "gore"]),
    "violence": ("暴力", ["暴力", "violence"]),
    "philosophical": ("哲学", ["哲学", "philosophy"]),
    "religion": ("宗教", ["宗教", "religion"]),
    "mythology": ("神话", ["神话", "mythology"]),
    "folklore": ("民俗", ["民俗", "传说", "folklore"]),
    "urban": ("都市", ["都市", "urban"]),
    "rural": ("乡村", ["乡村", "田园", "rural"]),
    "summer": ("夏日", ["夏日", "summer"]),
    "winter": ("冬日", ["冬日", "winter"]),
    "festival": ("祭典", ["祭典", "夏日祭", "festival"]),
    "hot springs": ("温泉", ["温泉", "onsen", "hotspring"]),
    "travel": ("旅行", ["旅行", "travel"]),
    "seaside": ("海边", ["海边", "海滨", "seaside"]),
    "space": ("太空", ["太空", "宇宙", "space"]),
    "steampunk": ("蒸汽朋克", ["蒸汽朋克", "steampunk"]),
    "cyberpunk": ("赛博朋克", ["赛博朋克", "cyberpunk"]),
    "post-apocalyptic": ("末世", ["末世", "废土", "postapocalyptic"]),
    "zombie": ("丧尸", ["丧尸", "僵尸", "zombie"]),
    "vampire": ("吸血鬼", ["吸血鬼", "vampire"]),
    "ghost": ("幽灵", ["幽灵", "鬼", "ghost"]),
    "detective": ("侦探", ["侦探", "detective story"]),
    "courtroom": ("法庭", ["法庭", "律师", "courtroom"]),
    "medical": ("医疗", ["医疗", "医生", "medical"]),
    "painting": ("绘画", ["绘画", "美术", "painting"]),
    "photography": ("摄影", ["摄影", "photography"]),
    "writing": ("写作", ["写作", "小说家", "writing"]),
    "theater": ("戏剧", ["戏剧", "舞台剧", "theater"]),
    "dance": ("舞蹈", ["舞蹈", "dance"]),
    "cafe": ("咖啡厅", ["咖啡厅", "咖啡店", "cafe"]),
    "restaurant": ("餐厅", ["餐厅", "restaurant"]),
    "cats": ("猫", ["猫", "猫咪", "cat"]),
    "dogs": ("狗", ["狗", "狗狗", "dog"]),
    "animals": ("动物", ["动物", "animal"]),
    "nature": ("自然", ["自然", "nature"]),
    "nsfw": ("成人内容", ["成人内容", "r18", "nsfw"]),
    # ---- cont / tech: protagonist & heroine traits ----
    "male protagonist": ("男主视角", ["male protag", "男性主角", "男主角"]),
    "protagonist with a face": ("有脸主角", ["protagonist with face", "shown protagonist", "有脸男主"]),
    "heroine with big breasts": ("巨乳女主", ["big breasted heroine", "large breasted heroine", "大胸女主"]),
    "high school student heroine": ("女高中生", ["highschool student heroine", "high school girl", "高中女生"]),
    "other perspectives": ("多视角", ["other perspective", "alternate perspectives", "切换视角"]),
    "naked sprites": ("裸体立绘", ["nude sprites", "naked sprite", "裸立绘"]),
    "only virgin heroines": ("全员处女", ["virgin heroines only", "only virgin heroine", "仅处女女主"]),
    "student heroine": ("学生女主", ["schoolgirl heroine", "student girl", "学生女主角"]),
    "no sexual content": ("无性内容", ["no sex content", "no sexual scenes", "全年龄"]),
    "adult protagonist": ("成年主角", ["adult protag", "grown-up protagonist", "成年男主"]),
    "protagonist's childhood friend as a heroine": ("青梅竹马女主", ["childhood friend heroine", "osananajimi heroine", "幼驯染女主"]),
    "branching plot": ("分支剧情", ["branching story", "branching narrative", "分支故事"]),
    "adult heroine": ("成年女主", ["adult heroine", "grown-up heroine", "成熟女主"]),
    "female protagonist": ("女主视角", ["female protag", "woman protagonist", "女性主角"]),
    "high school student protagonist": ("高中生主角", ["highschool protagonist", "male high school protagonist", "高中男主"]),
    "heroine with sexual experience": ("非处女女主", ["sexually experienced heroine", "experienced heroine", "有经验女主"]),
    "music recollection": ("音乐鉴赏", ["music gallery", "sound test", "音乐回放"]),
    "under the same roof": ("同居", ["living together", "same roof", "同住"]),
    "twin tail heroine": ("双马尾女主", ["twintail heroine", "twin tails", "双马尾女孩"]),
    "loli heroine": ("萝莉女主", ["loli heroine", "lolita heroine", "萝莉系女主"]),
    "high school": ("高中", ["highschool", "high school setting", "高校"]),
    "bad ending(s)": ("坏结局", ["bad endings", "bad end", "badend"]),
    "more than seven endings": ("七结局以上", ["more than 7 endings", "many endings", "七种以上结局"]),
    "flashback": ("回忆杀", ["flashbacks", "reminiscence", "倒叙"]),
    "nameable protagonist": ("可命名主角", ["nameable protagonist", "customizable name", "可改名主角"]),
    "one true end": ("唯一真结局", ["one true ending", "true ending", "真结局"]),
    "side portraits": ("侧边立绘", ["side portrait", "side sprite", "侧边头像"]),
    "protagonist with a sprite": ("有立绘主角", ["protagonist with sprite", "visible protagonist", "主角立绘"]),
    "bad endings with story": ("剧情坏结局", ["story bad endings", "bad endings with story", "有剧情坏结局"]),
    "unlockable routes": ("解锁路线", ["unlockable route", "hidden routes", "可解锁路线"]),
    "kissing scene": ("接吻场景", ["kiss scene", "kissing scenes", "亲吻场景"]),
    "student protagonist": ("学生主角", ["schoolboy protagonist", "schoolboy hero", "学生男主"]),
    "perverted heroine": ("好色女主", ["perverted heroine", "lewd heroine", "好色女主角"]),
    "protagonist with voice acting": ("主角配音", ["voiced protagonist", "protagonist voice acting", "有配音主角"]),
    "super deformed cgs": ("Q版CG", ["sd cgs", "chibi cgs", "Q版立绘"]),
    "deredere heroine": ("黏人女主", ["deredere", "lovey-dovey heroine", "甜腻女主"]),
    "modern day japan": ("现代日本", ["modern japan", "contemporary japan", "现代日本背景"]),
    "only a single heroine": ("单女主", ["single heroine", "only one heroine", "唯一女主"]),
    "ojousama heroine": ("大小姐女主", ["ojou-sama heroine", "rich girl heroine", "千金女主"]),
    "few choices": ("选择稀少", ["fewer choices", "few choice", "少量选项"]),
    "only good endings": ("全好结局", ["good endings only", "only good ending", "仅好结局"]),
    "harem ending": ("后宫结局", ["harem end", "后宫end", "后宫线"]),
    "ponytail heroine": ("马尾女主", ["ponytail heroine", "马尾辫女主", "单马尾女主"]),
    "tsundere heroine": ("傲娇女主", ["tsundere heroine", "傲娇女孩", "傲娇系女主"]),
    "proactive protagonist": ("主动主角", ["proactive protagonist", "assertive protagonist", "积极主角"]),
    "heroine with glasses": ("眼镜女主", ["glasses heroine", "megane heroine", "眼镜娘"]),
    "linear plot": ("线性剧情", ["linear story", "linear narrative", "线性故事"]),
    "heroine with zettai ryouiki": ("绝对领域女主", ["zettai ryouiki heroine", "absolute territory", "绝对领域"]),
    "heroine with huge breasts": ("爆乳女主", ["huge breasted heroine", "huge breasts heroine", "爆乳女主角"]),
    "game over": ("游戏结束", ["gameover", "failure ending", "失败结局"]),
    "map movement": ("地图移动", ["map exploration", "map navigation", "地图探索"]),
    "life and death drama": ("生死剧情", ["life and death", "生死离别", "生死剧"]),
    "white haired heroine": ("白发女主", ["white-haired heroine", "silver haired heroine", "白发女孩"]),
    "enforced playing order": ("强制通关顺序", ["enforced order", "forced playing order", "强制路线顺序"]),
    "pregnancy": ("怀孕", ["pregnant", "gestation", "妊娠"]),
    "lots of choices": ("大量选项", ["many choices", "lots of choice", "选项众多"]),
    "marriage ending": ("结婚结局", ["marriage end", "wedding ending", "婚姻结局"]),
    "varied title screens": ("多标题画面", ["varied title screen", "multiple title screens", "多样标题画面"]),
    "protagonist's kouhai as a heroine": ("后辈女主", ["kouhai heroine", "junior heroine", "学妹女主"]),
    "love overcomes all": ("爱能战胜一切", ["love conquers all", "爱战胜一切", "爱情万能"]),
    "date display": ("日期显示", ["calendar display", "date indicator", "显示日期"]),
    "big breast sizes heroine": ("胸围尺寸女主", ["breast size heroine", "big breast size", "胸围尺寸"]),
    "unlockable choices": ("解锁选项", ["unlockable choice", "hidden choices", "可解锁选项"]),
    "single ending": ("单一结局", ["one ending", "only one ending", "唯一结局"]),
    "bonus side stories": ("附赠外传", ["bonus stories", "side stories", "追加外传"]),
    "tomboy heroine": ("假小子女主", ["tomboy heroine", "boyish heroine", "中性女主"]),
    "colored name-tags": ("彩色名牌", ["colored nametags", "colored name tags", "彩色名字标签"]),
    "episodic story": ("单元剧", ["episodic", "episodic narrative", "章节式剧情"]),
    "protagonist's senpai as a heroine": ("前辈女主", ["senpai heroine", "senior heroine", "学姐女主"]),
    "kuudere heroine": ("三无女主", ["kuudere", "cold heroine", "冰山女主"]),
    "protagonist's younger sister as a heroine": ("妹妹女主", ["younger sister heroine", "little sister heroine", "实妹女主"]),
    "brocon heroine": ("兄控女主", ["brocon", "brother complex heroine", "恋兄女主"]),
    "heroine with small breasts (non-loli)": ("贫乳女主", ["small breasted heroine", "flat chested heroine", "微乳女主"]),
    "backlog jump": ("回想跳转", ["log jump", "backlog navigation", "剧情回跳"]),
    "energetic heroine": ("元气女主", ["energetic heroine", "genki heroine", "活力女主"]),
    "brief nvl scenes": ("短NVL场景", ["brief nvl", "nvl scenes", "简短NVL"]),
    "bloody scenes": ("血腥场景", ["bloody scenes", "blood scenes", "流血场景"]),
    "unlockable gallery": ("解锁画廊", ["cg gallery", "unlockable cg gallery", "可解锁画廊"]),
    "heroine with ahoge": ("呆毛女主", ["ahoge heroine", "ahoge", "呆毛女孩"]),
    "meaningless choices": ("无意义选项", ["pointless choices", "meaningless choice", "无效选项"]),
    "food discussions": ("美食讨论", ["food talk", "food discussion", "料理话题"]),
    "multiple route mystery": ("多线悬疑", ["multi-route mystery", "multiple route mystery", "多路线推理"]),
    "donkan protagonist": ("迟钝主角", ["donkan protagonist", "oblivious protagonist", "木头主角"]),
    "teacher heroine": ("教师女主", ["female teacher", "teacher girl", "老师女主"]),
    "classic tsundere heroine": ("经典傲娇女主", ["classic tsundere", "traditional tsundere", "古典傲娇"]),
    "married heroine": ("已婚女主", ["wife heroine", "married woman heroine", "人妻女主"]),
    "infidelity": ("出轨", ["unfaithfulness", "extramarital affair", "不忠"]),
    "protagonist with sexual experience": ("非处男主", ["sexually experienced protagonist", "experienced protagonist", "有经验男主"]),
    "death of heroine": ("女主死亡", ["heroine death", "death of the heroine", "女主角之死"]),
    "fighting protagonist": ("战斗主角", ["combat protagonist", "combat male protagonist", "战斗男主"]),
    "fighting heroine": ("战斗女主", ["combat heroine", "fighting girl", "战斗女主角"]),
    "perverted protagonist": ("好色主角", ["perverted protagonist", "lewd protagonist", "好色男主"]),
    "shy heroine": ("害羞女主", ["bashful heroine", "shy girl", "内向女主"]),
    "read text marking": ("已读标记", ["read marker", "read text marker", "已读文本标记"]),
    "airhead heroine": ("天然呆女主", ["airhead heroine", "ditzy heroine", "呆萌女主"]),
    "only adult heroines": ("全员成年女主", ["adult heroines only", "only adult heroine", "仅成年女主"]),
    "genius heroine": ("天才女主", ["genius heroine", "smart heroine", "天才少女"]),
    "multiple protagonists": ("多主角", ["multiple protagonist", "multi protagonist", "多主角视角"]),
    "homicide": ("杀人", ["murder", "homicide case", "凶杀"]),
    "central heroine": ("核心女主", ["main heroine", "central heroine", "中心女主"]),
    "modern tsundere heroine": ("现代傲娇女主", ["modern tsundere", "modern tsundere heroine", "当代傲娇"]),
    "unlockable bonus content": ("解锁附赠内容", ["unlockable bonus content", "bonus content", "可解锁特典"]),
    "protagonist's full sister as a heroine": ("亲妹女主", ["full sister heroine", "blood sister heroine", "亲妹妹女主"]),
    "slice of life comedy": ("日常喜剧", ["sol comedy", "slice-of-life comedy", "日常搞笑"]),
    "sprite viewer": ("立绘鉴赏", ["sprite gallery", "sprite viewer", "立绘浏览"]),
    "breaking the fourth wall": ("打破第四面墙", ["breaking fourth wall", "fourth wall", "meta narrative"]),
    "lip sync": ("口型同步", ["lipsync", "lip synchronization", "嘴型同步"]),
    "early branching plot": ("早期分支", ["early branching", "early branch", "前期分支"]),
    "death of protagonist": ("主角死亡", ["protagonist death", "death of the protagonist", "男主角之死"]),
    "protagonist in relationship": ("主角恋爱中", ["protagonist in a relationship", "protagonist in relationship", "已交往主角"]),
    "naked heroine with apron": ("裸围裙女主", ["naked apron", "apron only heroine", "裸体围裙"]),
    "changeable font": ("可换字体", ["font change", "changeable fonts", "更换字体"]),
    "threesome ending": ("三人结局", ["three person ending", "threesome end", "三人行结局"]),
    "orphan protagonist": ("孤儿主角", ["orphan boy", "orphan male protagonist", "孤儿男主"]),
    "mother support character": ("母亲配角", ["mother support", "mother character", "母亲角色"]),
    "nakige": ("泣系", ["crying game", "tearjerking game", "催泪系"]),
    "maid heroine": ("女仆女主", ["maid girl", "maid heroine", "女仆女孩"]),
    "pregnancy good ending": ("怀孕好结局", ["pregnancy good ending", "pregnant good end", "怀孕圆满结局"]),
    "revenge": ("复仇", ["vengeance", "revenge story", "报仇"]),
    "normal scene recollection": ("通常场景回想", ["scene recollection", "normal scene gallery", "普通场景回放"]),
    "school life comedy": ("学园喜剧", ["school comedy", "school-life comedy", "校园喜剧"]),
    "group of friends": ("朋友圈", ["friend group", "group of friends", "伙伴团体"]),
    "foreigner heroine": ("外国人女主", ["foreign heroine", "foreigner girl", "外国女主"]),
    "pretending heroine": ("伪装女主", ["fake heroine", "pretending heroine", "假扮女主"]),
    "love hotel": ("爱情旅馆", ["lovehotel", "couple hotel", "情侣酒店"]),
    "descriptions of violence": ("暴力描写", ["violence descriptions", "descriptions of violence", "暴力描述"]),
    "bleep censor": ("消音审查", ["bleep censorship", "bleep censor", "哔声消音"]),
    "madness": ("疯狂", ["insanity", "craziness", "狂气"]),
    "highly animated sprites": ("动态立绘", ["animated sprites", "highly animated sprite", "live2d立绘"]),
    "betrayal": ("背叛", ["treachery", "betrayal", "叛变"]),
    "dark skinned heroine": ("黑皮女主", ["dark-skinned heroine", "tan skinned heroine", "深色皮肤女主"]),
    "imouto-type heroine": ("妹系女主", ["imouto type heroine", "imouto-type", "妹系角色"]),
    "more than seven heroines": ("七女主以上", ["many heroines", "more than 7 heroines", "七人以上女主"]),
    "high amount of bad endings": ("大量坏结局", ["many bad endings", "high amount of bad endings", "坏结局很多"]),
    "built-in encyclopedia": ("内置百科", ["in-game encyclopedia", "built-in encyclopedia", "游戏百科"]),
    "unlockable event": ("解锁事件", ["hidden event", "unlockable event", "可解锁事件"]),
    "secret identity": ("秘密身份", ["hidden identity", "secret identity", "隐藏身份"]),
    "fictional modern day japanese town": ("虚构现代日本小镇", ["fictional japanese town", "fictional modern town", "虚构日本小镇"]),
    "magic/esp combat": ("魔法超能战斗", ["magic esp combat", "esper combat", "超能力战斗"]),
    "orphan heroine": ("孤儿女主", ["orphan girl", "orphan heroine", "孤儿少女"]),
    "father support character": ("父亲配角", ["father support", "father character", "父亲角色"]),
    "colored texts": ("彩色文本", ["colored text", "coloured texts", "彩色文字"]),
    "protagonist's non-blood-related sister as a heroine": ("义妹女主", ["non-blood sister heroine", "step sister heroine", "义妹女主角"]),
    "university student protagonist": ("大学生主角", ["university student protagonist", "college student protagonist", "大学生男主"]),
    "modern day": ("现代", ["contemporary", "modern setting", "现代背景"]),
    "brother/sister romance": ("兄妹恋", ["brother sister romance", "sibling romance", "兄妹恋情"]),
    "suicide": ("自杀", ["self-killing", "suicide", "自尽"]),
    "unlockable hero(ine)": ("解锁隐藏女主", ["unlockable heroine", "unlockable hero", "隐藏女主"]),
    "has window transparency setting": ("窗口透明度设置", ["window transparency", "transparency setting", "窗口透明"]),
    "reunion": ("重逢", ["reuniting", "reunion", "再会"]),
    "bullying": ("霸凌", ["bully", "bullying", "欺凌"]),
    "oneesan-type heroine": ("御姐女主", ["oneesan type heroine", "older woman heroine", "大姐姐女主"]),
    "otaku heroine": ("宅女女主", ["otaku heroine", "geek girl heroine", "御宅女主"]),
    "mindbreak": ("精神崩溃", ["mind break", "mindbreak", "精神崩坏"]),
    "sword combat": ("剑术战斗", ["sword fighting", "swordplay", "刀剑战斗"]),
    "sword wielding heroine": ("持剑女主", ["swordswoman", "sword wielding heroine", "剑士女主"]),
    "confinement": ("监禁", ["imprisonment", "confinement", "囚禁"]),
    "wedding": ("婚礼", ["marriage ceremony", "wedding", "结婚典礼"]),
    "mind control": ("精神控制", ["brainwashing", "mind control", "洗脑"]),
    "heroine with swimsuits": ("泳装女主", ["swimsuit heroine", "bikini heroine", "泳衣女主"]),
    "alternate dimensions": ("异世界", ["alternate dimension", "another dimension", "平行世界"]),
    "achievements": ("成就", ["achievement", "steam achievements", "steam成就"]),
    "panchira": ("走光", ["panty shot", "panchira", "裙底走光"]),
    "student council president heroine": ("学生会长女主", ["student council heroine", "student council president heroine", "学生会长"]),
    "psychological trauma": ("心理创伤", ["trauma", "psychological trauma", "精神创伤"]),
    "lots of event cgs": ("大量事件CG", ["many event cgs", "lots of event cgs", "大量CG"]),
    "unlockable epilogue": ("解锁后日谈", ["hidden epilogue", "unlockable epilogue", "可解锁尾声"]),
    "girl x girl romance": ("百合恋爱", ["girls love", "girl x girl romance", "gl romance"]),
    "combat capable friends": ("战斗伙伴", ["fighting friends", "combat capable friends", "能战斗的伙伴"]),
    "mischievous heroine": ("调皮女主", ["naughty heroine", "mischievous heroine", "淘气女主"]),
    "heroine with tights": ("紧身裤女主", ["tights heroine", "pantyhose heroine", "连裤袜女主"]),
    "detective work": ("侦探工作", ["investigation", "detective work", "调查推理"]),
    "brief branches only": ("仅短分支", ["short branches only", "brief branches only", "只有短分支"]),
    "only non-virgin heroines": ("全员非处女", ["non-virgin heroines only", "only non-virgin heroines", "仅非处女女主"]),
    "villainous protagonist": ("反派主角", ["villain protagonist", "villainous protagonist", "恶役主角"]),
    "choices with 4 or more options": ("四项以上选项", ["four or more options", "choices with 4 or more options", "四个以上选项"]),
    "nympho heroine": ("淫荡女主", ["nymphomaniac heroine", "nympho heroine", "淫乱女主"]),
    "utsuge": ("致郁", ["depressing game", "utsuge", "郁系"]),
    "ending list": ("结局列表", ["endings list", "ending list", "结局一览"]),
    "no \"keep voice on click\" option": ("点击不中断语音", ["no keep voice on click", "voice on click option", "点击继续语音"]),
    "voiced thoughts": ("心声配音", ["thought voice", "voiced thoughts", "内心独白配音"]),
    "unlockable harem ending": ("解锁后宫结局", ["hidden harem ending", "unlockable harem ending", "可解锁后宫结局"]),
    "kidnapping": ("绑架", ["abduction", "kidnapping", "诱拐"]),
    "yandere heroine": ("病娇女主", ["yandere", "yandere heroine", "病娇女孩"]),
    "heroine with beauty mark": ("美人痣女主", ["beauty mark heroine", "heroine with beauty mark", "泪痣女主"]),
    "chosen choices marking": ("选项标记", ["choice marking", "chosen choices marking", "已选标记"]),
    "foolish friend": ("笨蛋朋友", ["stupid friend", "foolish friend", "笨蛋好友"]),
    "torture": ("拷问", ["torment", "torture", "酷刑"]),
    "murder mystery": ("杀人推理", ["whodunit", "murder mystery", "凶案推理"]),
    "jealousy": ("嫉妒", ["jealous", "jealousy", "吃醋"]),
    "female protagonist for a short time": ("短期女主视角", ["temporary female protagonist", "female protagonist for a short time", "短暂女主视角"]),
    "no romance plot": ("无恋爱剧情", ["no romance", "no romance plot", "无恋爱线"]),
    "pregnancy ending": ("怀孕结局", ["pregnant ending", "pregnancy ending", "妊娠结局"]),
    "nvl": ("NVL叙述", ["nvl mode", "nvl", "nvl模式"]),
    "photographic backgrounds": ("实景背景", ["photo backgrounds", "photographic backgrounds", "照片背景"]),
    "open ending(s)": ("开放式结局", ["open endings", "open ending", "开放结局"]),
    "infodumping": ("设定解说", ["info dump", "infodumping", "信息倾泻"]),
    "scenario selection": ("剧本选择", ["scenario select", "scenario selection", "章节选择"]),
    "big ass heroine": ("巨臀女主", ["large butt heroine", "big ass heroine", "美臀女主"]),
    "major antagonist": ("主要反派", ["main antagonist", "major antagonist", "主要敌人"]),
    "third-person narrative": ("第三人称叙事", ["third person narrative", "third-person narrative", "第三人称"]),
    "interactive adventure game": ("互动冒险游戏", ["interactive adventure", "interactive adventure game", "互动冒险"]),
    "past setting in a fictional world": ("虚构世界过去", ["fictional past setting", "past setting in a fictional world", "虚构古代世界"]),
    "hero(ine) selection": ("主角选择", ["heroine selection", "hero selection", "选择主角"]),
    "stockings": ("丝袜", ["pantyhose", "stockings", "长筒袜"]),
    "non-japanese voice acting": ("非日语配音", ["english voice acting", "non-japanese voice acting", "外语配音"]),
    "blackmail": ("勒索", ["extortion", "blackmail", "要挟"]),
    "western-style manor": ("西式洋馆", ["western manor", "western-style manor", "西洋宅邸"]),
    "pillow talk": ("枕边话", ["pillowtalk", "pillow talk", "枕边细语"]),
    "heroine with a fang": ("虎牙女主", ["fang heroine", "heroine with a fang", "小虎牙女主"]),
    "built-in walkthrough": ("内置攻略", ["in-game walkthrough", "built-in walkthrough", "游戏攻略"]),
    "protagonist with partial voice acting": ("主角部分配音", ["partial voiced protagonist", "protagonist with partial voice acting", "部分配音主角"]),
    "lesbian heroine": ("百合女主", ["lesbian girl", "lesbian heroine", "女同女主"]),
    "heroine with psychological problems": ("心理问题女主", ["psychologically troubled heroine", "heroine with psychological problems", "心理病女主"]),
    "no quick save/load": ("无快速存档", ["no quicksave", "no quick save/load", "无快速存读档"]),
    "sword wielding protagonist": ("持剑主角", ["swordsman protagonist", "sword wielding protagonist", "剑士主角"]),
    "sexual innuendo": ("性暗示", ["innuendo", "sexual innuendo", "情色暗示"]),
    "ejaculation forewarner": ("射精预告", ["ejaculation warning", "ejaculation forewarner", "发射预告"]),
    "superpowers": ("超能力", ["superpower", "superpowers", "异能"]),
    "adult hero": ("成年男角", ["adult hero", "grown-up hero", "成年男性主角"]),
    "graphic violence": ("露骨暴力", ["explicit violence", "graphic violence", "血腥暴力"]),
    "protagonist as the only male": ("唯一男性主角", ["only male protagonist", "protagonist as the only male", "唯一男主"]),
    "character profiles": ("角色资料", ["character profile", "character profiles", "角色介绍"]),
    "unique routes": ("独有路线", ["unique route", "unique routes", "专属路线"]),
    "slice of life drama": ("日常剧情", ["sol drama", "slice of life drama", "生活剧情"]),
    "promiscuous heroine": ("放荡女主", ["slutty heroine", "promiscuous heroine", "滥交女主"]),
    "half-japanese heroine": ("混血女主", ["half japanese", "half-japanese heroine", "混血女主角"]),
    "waitress heroine": ("女服务员女主", ["waitress girl", "waitress heroine", "服务员女主"]),
    "siscon protagonist": ("妹控主角", ["sister complex protagonist", "siscon protagonist", "恋妹主角"]),
    "princess heroine": ("公主女主", ["princess girl", "princess heroine", "王女女主"]),
    "jump to prior choices": ("跳回前选项", ["jump to previous choice", "jump to prior choices", "回跳选项"]),
    "protagonist's cousin as a heroine": ("堂表妹女主", ["cousin heroine", "cousin as a heroine", "表亲女主"]),
    "varying ending songs": ("不同片尾曲", ["different ending songs", "varying ending songs", "结局曲变化"]),
    "heroine with intake hairstyle": ("内扣发女主", ["intake hairstyle heroine", "inward curled hairstyle", "内扣发型女主"]),
    "twin sisters as heroines": ("双胞胎女主", ["twin sister heroines", "twin sisters as heroines", "双子女主"]),
    "transfer student heroine": ("转学生女主", ["transferee heroine", "transfer student heroine", "转校生女主"]),
    "university student heroine": ("大学生女主", ["college student heroine", "university student heroine", "女大学生"]),
    "completion status indicator": ("完成度指示", ["completion indicator", "completion status indicator", "完成度显示"]),
    "long common route": ("长共通线", ["long common path", "long common route", "共通线很长"]),
    "girl x girl romance only": ("纯百合", ["yuri only", "girl x girl romance only", "纯百合恋爱"]),
    "unarmed combat": ("徒手格斗", ["hand-to-hand combat", "unarmed combat", "空手战斗"]),
    "time loop": ("时间循环", ["timeloop", "time loop", "时空轮回"]),
    "miko heroine": ("巫女女主", ["shrine maiden heroine", "miko heroine", "神社巫女"]),
    "protagonist's sister as a support character": ("妹妹配角", ["sister support character", "protagonist's sister as a support character", "妹妹支援角色"]),
    "jump to next choice": ("跳到下一选项", ["next choice jump", "jump to next choice", "下一选项跳转"]),
    "late branching plot": ("后期分支", ["late branching", "late branching plot", "后期分歧"]),
    "heroine with kimono": ("和服女主", ["kimono heroine", "heroine with kimono", "穿和服女主"]),
    "yamato nadeshiko heroine": ("大和抚子女主", ["yamato nadeshiko", "yamato nadeshiko heroine", "抚子女主"]),
    "unrequited love": ("单恋", ["one-sided love", "unrequited love", "暗恋"]),
    "school dormitory": ("学校宿舍", ["dormitory life", "school dormitory", "宿舍生活"]),
    "hero with glasses": ("眼镜男主", ["glasses hero", "hero with glasses", "眼镜男"]),
    "protagonist with glasses": ("眼镜主角", ["glasses protagonist", "protagonist with glasses", "戴眼镜主角"]),
    "clothing damage": ("爆衣", ["clothes damage", "clothing damage", "服装破损"]),
    "unavoidable heroine death": ("女主必死", ["forced heroine death", "unavoidable heroine death", "不可避免女主死亡"]),
    "dream": ("梦境", ["dreams", "dream", "做梦"]),
}

CanonicalInfo = tuple[str, str, list[str]]

_LOOKUP: dict[str, CanonicalInfo] = {}


def _build_index() -> None:
    for canonical, (name_zh, aliases) in TAG_ZH_MAP.items():
        info: CanonicalInfo = (
            canonical,
            name_zh,
            unique_preserving_order([name_zh, *aliases]),
        )
        for spelling in (canonical, name_zh, *aliases):
            key = normalize_text(spelling)
            if key:
                _LOOKUP[key] = info


_build_index()


def canonical_lookup(name: str | None) -> CanonicalInfo | None:
    """Resolve an English/Chinese name or alias to ``(canonical, zh, aliases)``.

    Returns ``None`` when the name is not part of the built-in mapping.
    """
    if not name:
        return None
    return _LOOKUP.get(normalize_text(name))


def canonical_lookup_keys(name: str | None) -> set[str]:
    """All normalized spellings that should resolve to the same tag."""
    info = canonical_lookup(name)
    if info is None:
        key = normalize_text(name)
        return {key} if key else set()
    canonical, name_zh, aliases = info
    keys = {normalize_text(value) for value in (canonical, name_zh, *aliases)}
    return {key for key in keys if key}


def backfill_tag_names(conn: sqlite3.Connection) -> dict[str, int]:
    """Fill translations and alias rows for tags created before the mapping existed.

    The importer applies ``canonical_lookup`` when a tag is first created, but an
    existing database keeps the old English-only rows.  This function is called
    idempotently by ``init_db`` so upgrading never needs a manual migration step.
    """
    updated = 0
    aliases_added = 0
    rows = conn.execute("SELECT id, name, aliases FROM tags").fetchall()
    for row in rows:
        info = canonical_lookup(row["name"])
        if info is None:
            continue
        canonical, name_zh, aliases = info
        current = json_loads(row["aliases"], []) or []
        merged = unique_preserving_order([*current, *aliases, name_zh])
        conn.execute(
            "UPDATE tags SET name_zh = COALESCE(NULLIF(name_zh, ''), ?), aliases = ? WHERE id = ?",
            (name_zh, json_dumps(merged), row["id"]),
        )
        updated += 1
        canonical_norm = normalize_text(canonical)
        spellings = {normalize_text(value) for value in (name_zh, *aliases)}
        spellings.discard("")
        spellings.discard(canonical_norm)
        for alias_norm in spellings:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO tag_aliases(alias_normalized, tag_id, lang, source)
                VALUES(?, ?, ?, 'builtin')
                """,
                (alias_norm, row["id"], "zh" if alias_norm == normalize_text(name_zh) else ""),
            )
            aliases_added += cur.rowcount
    return {"tags_updated": updated, "aliases_added": aliases_added}
