#!/usr/bin/env python3
"""Generate neutral, non-sensitive mock corpus segments for Mock My AI.

Produces >=1000 JSONL segments per language under data/corpus/<lang>/.
Languages: en, zh, ja, es, fr. Content is synthetic and topic-safe.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "data" / "corpus"
TARGET = 1100
RNG = random.Random(42)

# ---------------------------------------------------------------------------
# Building blocks per language (neutral topics: weather, cooking, travel,
# science facts, programming tips, nature, daily life, learning)
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, dict] = {
    "en": {
        "short": [
            "Hello! How can I help you today?",
            "Sure, I can explain that briefly.",
            "That is a great question.",
            "Let me summarize the key points.",
            "Here is a short answer.",
            "Understood. Proceeding with the request.",
            "Thanks for clarifying.",
            "I agree with that approach.",
            "Here is a simple example.",
            "Feel free to ask a follow-up.",
        ],
        "topics": [
            ("weather", [
                "The forecast looks clear with mild temperatures.",
                "A light breeze is expected through the afternoon.",
                "Humidity may rise near the coast this evening.",
                "Morning fog often clears by mid-day.",
                "Pack a light jacket if you are heading outdoors.",
            ]),
            ("cooking", [
                "Simmer the sauce on low heat until it thickens.",
                "Fresh herbs add brightness without much effort.",
                "Rest the dough for twenty minutes before baking.",
                "Taste and adjust salt near the end of cooking.",
                "A cast-iron pan holds heat evenly for searing.",
            ]),
            ("travel", [
                "Arrive early to avoid long security lines.",
                "Carry a reusable water bottle on long trips.",
                "Local markets are good places to try regional snacks.",
                "Offline maps help when mobile signal is weak.",
                "Keep copies of important documents in cloud storage.",
            ]),
            ("science", [
                "Water expands when it freezes into ice.",
                "Photosynthesis converts light into chemical energy.",
                "The speed of light in vacuum is about 300,000 km/s.",
                "DNA stores genetic instructions in living cells.",
                "Magnets attract iron and some other metals.",
            ]),
            ("programming", [
                "Write small functions that do one thing well.",
                "Name variables clearly so future readers understand intent.",
                "Automated tests catch regressions early.",
                "Prefer immutable data when concurrency is involved.",
                "Log meaningful errors with enough context to debug.",
            ]),
            ("nature", [
                "Oak trees can live for several centuries.",
                "Bees pollinate many flowering plants.",
                "Coral reefs support rich marine biodiversity.",
                "Migratory birds follow seasonal food patterns.",
                "Soil microbes recycle nutrients for plants.",
            ]),
            ("learning", [
                "Spaced repetition strengthens long-term memory.",
                "Teaching a topic to someone else reveals gaps.",
                "Short daily practice beats rare long sessions.",
                "Ask clarifying questions before deep work.",
                "Take notes in your own words after reading.",
            ]),
            ("daily", [
                "A short walk after lunch can improve focus.",
                "Keep a tidy desk to reduce visual distraction.",
                "Drink water regularly throughout the day.",
                "Set a timer for focused work blocks.",
                "Stretch your shoulders if you sit for hours.",
            ]),
        ],
        "connectors": [
            "Additionally,", "Also,", "In practice,", "For example,",
            "On the other hand,", "Meanwhile,", "As a tip,", "Notably,",
            "In short,", "Overall,",
        ],
        "closers": [
            "Hope that helps!",
            "Let me know if you need more detail.",
            "Happy to expand on any part.",
            "That covers the basics.",
            "Feel free to ask for examples.",
        ],
    },
    "zh": {
        "short": [
            "你好，有什么可以帮你的？",
            "好的，我简单说明一下。",
            "这是个不错的问题。",
            "我来概括几个要点。",
            "下面是简短回答。",
            "明白了，继续处理。",
            "谢谢补充说明。",
            "这个思路可以。",
            "这里有个简单例子。",
            "有后续问题随时问。",
        ],
        "topics": [
            ("天气", [
                "今天气温适中，适合户外活动。",
                "午后可能有轻微阵雨。",
                "沿海地区傍晚湿度会升高。",
                "晨雾通常在中午前散去。",
                "出门建议带一件薄外套。",
            ]),
            ("烹饪", [
                "小火慢炖，汤汁会更浓郁。",
                "新鲜香草能提亮味道。",
                "面团醒二十分钟再烘烤。",
                "出锅前再调盐更稳妥。",
                "铸铁锅受热均匀，适合煎制。",
            ]),
            ("旅行", [
                "提前到机场可以避开安检高峰。",
                "长途旅行带可重复使用的水杯。",
                "当地市集适合品尝特色小吃。",
                "信号弱时离线地图很有用。",
                "重要证件备份到云端更安心。",
            ]),
            ("科学", [
                "水结成冰时体积会膨胀。",
                "光合作用把光能转化为化学能。",
                "真空中光速约为每秒三十万公里。",
                "DNA 保存细胞的遗传指令。",
                "磁铁能吸引铁等部分金属。",
            ]),
            ("编程", [
                "函数尽量短小，只做一件事。",
                "变量命名要清楚表达意图。",
                "自动化测试能尽早发现回归。",
                "并发时优先使用不可变数据。",
                "错误日志要带足够上下文。",
            ]),
            ("自然", [
                "橡树可以存活数百年。",
                "蜜蜂帮助许多开花植物授粉。",
                "珊瑚礁支撑丰富的海洋生物多样性。",
                "候鸟随季节追逐食物资源。",
                "土壤微生物为植物循环养分。",
            ]),
            ("学习", [
                "间隔重复有助于长期记忆。",
                "把知识点讲给别人能暴露漏洞。",
                "每天短时练习胜过偶尔长时间突击。",
                "深入工作前先把问题问清楚。",
                "读完后用自己的话记笔记。",
            ]),
            ("日常", [
                "午饭后散步有助于恢复专注。",
                "桌面整洁能减少视觉干扰。",
                "白天要记得少量多次喝水。",
                "用计时器切分专注工作块。",
                "久坐时记得活动肩膀。",
            ]),
        ],
        "connectors": [
            "另外，", "同时，", "实际使用中，", "比如，",
            "另一方面，", "与此同时，", "小提示：", "值得注意的是，",
            "简言之，", "总的来说，",
        ],
        "closers": [
            "希望对你有帮助！",
            "需要更详细说明可以再问。",
            "哪一部分想展开都可以说。",
            "以上是基础要点。",
            "需要例子随时告诉我。",
        ],
    },
    "ja": {
        "short": [
            "こんにちは。何かお手伝いできますか？",
            "はい、簡単に説明します。",
            "良い質問ですね。",
            "要点をまとめます。",
            "短い回答はこちらです。",
            "承知しました。進めます。",
            "補足ありがとうございます。",
            "その方針で大丈夫です。",
            "簡単な例を示します。",
            "追加の質問もどうぞ。",
        ],
        "topics": [
            ("天気", [
                "気温は穏やかで外出に適しています。",
                "午後は弱い雨の可能性があります。",
                "沿岸部では夕方に湿度が上がります。",
                "朝霧は昼前に晴れることが多いです。",
                "薄手の上着を持っていくと安心です。",
            ]),
            ("料理", [
                "弱火で煮込むとソースがとろみます。",
                "新鮮なハーブで風味が明るくなります。",
                "生地は二十分休ませてから焼きます。",
                "塩味は仕上げ直前に調整します。",
                "鋳鉄鍋は熱が均一で焼き目がきれいです。",
            ]),
            ("旅行", [
                "早めに到着すると保安検査がスムーズです。",
                "長距離では再利用ボトルが便利です。",
                "地元の市場で郷土料理を楽しめます。",
                "電波が弱い場所ではオフライン地図が役立ちます。",
                "重要書類はクラウドに控えを残しましょう。",
            ]),
            ("科学", [
                "水は凍ると体積が増えます。",
                "光合成は光を化学エネルギーに変えます。",
                "真空中の光速はおよそ毎秒三十万キロです。",
                "DNAは細胞の遺伝情報を保持します。",
                "磁石は鉄などの金属を引きつけます。",
            ]),
            ("プログラミング", [
                "関数は小さく一つの役割に絞ります。",
                "変数名は意図が伝わるように付けます。",
                "自動テストは退行を早期に見つけます。",
                "並行処理では不変データを優先します。",
                "エラーログには十分な文脈を残します。",
            ]),
            ("自然", [
                "オークの木は何百年も生きることがあります。",
                "ミツバチは多くの花の受粉を助けます。",
                "サンゴ礁は豊かな海洋生物を支えます。",
                "渡り鳥は季節ごとに食料を追います。",
                "土壌微生物は植物の養分を循環させます。",
            ]),
            ("学習", [
                "間隔反復は長期記憶を強化します。",
                "人に教えると理解の穴が見えます。",
                "短い毎日の練習がまれな長時間より効きます。",
                "深い作業の前に疑問を整理します。",
                "読んだら自分の言葉でメモします。",
            ]),
            ("日常", [
                "食後の短い散歩は集中を助けます。",
                "机を整えると視覚的な気が散りが減ります。",
                "日中はこまめに水分を取ります。",
                "タイマーで集中ブロックを区切ります。",
                "長時間座るときは肩を伸ばします。",
            ]),
        ],
        "connectors": [
            "また、", "加えて、", "実際には、", "例えば、",
            "一方で、", "その間に、", "ヒントとして、", "注目すべきは、",
            "要するに、", "全体として、",
        ],
        "closers": [
            "参考になれば幸いです！",
            "詳細が必要なら教えてください。",
            "どの部分でも詳しく説明できます。",
            "基本はこのくらいです。",
            "例が必要なら言ってください。",
        ],
    },
    "es": {
        "short": [
            "¡Hola! ¿En qué puedo ayudarte?",
            "Claro, te lo explico brevemente.",
            "Es una muy buena pregunta.",
            "Resumo los puntos clave.",
            "Aquí va una respuesta corta.",
            "Entendido. Continúo con la solicitud.",
            "Gracias por aclarar.",
            "Estoy de acuerdo con ese enfoque.",
            "Aquí tienes un ejemplo sencillo.",
            "Puedes hacer más preguntas si quieres.",
        ],
        "topics": [
            ("clima", [
                "El pronóstico es despejado con temperaturas suaves.",
                "Se espera una brisa ligera por la tarde.",
                "La humedad puede subir cerca de la costa.",
                "La niebla matinal suele despejarse al mediodía.",
                "Lleva una chaqueta ligera si sales.",
            ]),
            ("cocina", [
                "Cocina la salsa a fuego lento hasta que espese.",
                "Las hierbas frescas aportan frescura sin esfuerzo.",
                "Deja reposar la masa veinte minutos antes de hornear.",
                "Ajusta la sal cerca del final.",
                "Una sartén de hierro fundido reparte bien el calor.",
            ]),
            ("viaje", [
                "Llega temprano para evitar colas de seguridad.",
                "Lleva una botella reutilizable en viajes largos.",
                "Los mercados locales son buenos para probar snacks.",
                "Los mapas sin conexión ayudan con poca señal.",
                "Guarda copias de documentos importantes en la nube.",
            ]),
            ("ciencia", [
                "El agua se expande al congelarse.",
                "La fotosíntesis convierte luz en energía química.",
                "La velocidad de la luz en el vacío es unos 300.000 km/s.",
                "El ADN guarda instrucciones genéticas en las células.",
                "Los imanes atraen hierro y algunos otros metales.",
            ]),
            ("programacion", [
                "Escribe funciones pequeñas que hagan una sola cosa.",
                "Nombra variables con claridad para futuros lectores.",
                "Las pruebas automáticas detectan regresiones pronto.",
                "Prefiere datos inmutables con concurrencia.",
                "Registra errores con contexto suficiente para depurar.",
            ]),
            ("naturaleza", [
                "Los robles pueden vivir varios siglos.",
                "Las abejas polinizan muchas plantas con flores.",
                "Los arrecifes de coral sostienen gran biodiversidad.",
                "Las aves migratorias siguen patrones de alimento.",
                "Los microbios del suelo reciclan nutrientes.",
            ]),
            ("aprendizaje", [
                "La repetición espaciada fortalece la memoria.",
                "Enseñar un tema revela lagunas de comprensión.",
                "Práctica breve diaria supera sesiones raras y largas.",
                "Aclara dudas antes del trabajo profundo.",
                "Toma notas con tus propias palabras.",
            ]),
            ("diario", [
                "Un paseo corto tras el almuerzo mejora el foco.",
                "Un escritorio ordenado reduce distracciones.",
                "Bebe agua con regularidad durante el día.",
                "Usa un temporizador para bloques de concentración.",
                "Estira los hombros si estás sentado muchas horas.",
            ]),
        ],
        "connectors": [
            "Además,", "También,", "En la práctica,", "Por ejemplo,",
            "Por otro lado,", "Mientras tanto,", "Como consejo,", "Cabe destacar,",
            "En resumen,", "En general,",
        ],
        "closers": [
            "¡Espero que te sirva!",
            "Dime si necesitas más detalle.",
            "Puedo ampliar cualquier parte.",
            "Eso cubre lo básico.",
            "Pide ejemplos cuando quieras.",
        ],
    },
    "fr": {
        "short": [
            "Bonjour ! Comment puis-je vous aider ?",
            "Bien sûr, je vais expliquer brièvement.",
            "C'est une très bonne question.",
            "Voici les points clés.",
            "Voici une réponse courte.",
            "Compris. Je continue.",
            "Merci pour la précision.",
            "Je suis d'accord avec cette approche.",
            "Voici un exemple simple.",
            "N'hésitez pas à poser une suite.",
        ],
        "topics": [
            ("meteo", [
                "Les prévisions sont claires avec des températures douces.",
                "Une légère brise est attendue cet après-midi.",
                "L'humidité peut monter près de la côte le soir.",
                "Le brouillard du matin se dissipe souvent avant midi.",
                "Emportez une veste légère si vous sortez.",
            ]),
            ("cuisine", [
                "Faites mijoter la sauce à feu doux jusqu'à épaississement.",
                "Les herbes fraîches apportent de la fraîcheur facilement.",
                "Laissez reposer la pâte vingt minutes avant cuisson.",
                "Ajustez le sel vers la fin.",
                "Une poêle en fonte répartit bien la chaleur.",
            ]),
            ("voyage", [
                "Arrivez tôt pour éviter les files de sécurité.",
                "Emportez une bouteille réutilisable en long trajet.",
                "Les marchés locaux sont idéaux pour goûter des spécialités.",
                "Les cartes hors ligne aident quand le réseau est faible.",
                "Gardez des copies de documents importants dans le cloud.",
            ]),
            ("science", [
                "L'eau se dilate lorsqu'elle gèle.",
                "La photosynthèse convertit la lumière en énergie chimique.",
                "La vitesse de la lumière dans le vide est d'environ 300 000 km/s.",
                "L'ADN stocke les instructions génétiques des cellules.",
                "Les aimants attirent le fer et certains métaux.",
            ]),
            ("programmation", [
                "Écrivez de petites fonctions qui font une seule chose.",
                "Nommez clairement les variables pour les lecteurs futurs.",
                "Les tests automatisés détectent tôt les régressions.",
                "Préférez des données immuables en concurrence.",
                "Journalisez les erreurs avec assez de contexte.",
            ]),
            ("nature", [
                "Les chênes peuvent vivre plusieurs siècles.",
                "Les abeilles pollinisent de nombreuses plantes à fleurs.",
                "Les récifs coralliens soutiennent une riche biodiversité.",
                "Les oiseaux migrateurs suivent les ressources alimentaires.",
                "Les microbes du sol recyclent les nutriments.",
            ]),
            ("apprentissage", [
                "La répétition espacée renforce la mémoire à long terme.",
                "Enseigner un sujet révèle les lacunes.",
                "Une courte pratique quotidienne bat les longues sessions rares.",
                "Clarifiez les questions avant le travail profond.",
                "Prenez des notes avec vos propres mots.",
            ]),
            ("quotidien", [
                "Une courte marche après le déjeuner aide la concentration.",
                "Un bureau rangé réduit les distractions visuelles.",
                "Buvez de l'eau régulièrement dans la journée.",
                "Utilisez un minuteur pour des blocs de focus.",
                "Étirez les épaules si vous restez assis longtemps.",
            ]),
        ],
        "connectors": [
            "De plus,", "Aussi,", "En pratique,", "Par exemple,",
            "D'un autre côté,", "Pendant ce temps,", "En conseil,", "Notamment,",
            "En bref,", "Dans l'ensemble,",
        ],
        "closers": [
            "J'espère que cela aide !",
            "Dites-moi si vous voulez plus de détail.",
            "Je peux développer n'importe quelle partie.",
            "Cela couvre l'essentiel.",
            "Demandez des exemples quand vous voulez.",
        ],
    },
}


def build_segment(lang: str, length: str, idx: int) -> str:
    data = TEMPLATES[lang]
    if length == "short":
        return RNG.choice(data["short"])

    topic_name, sentences = RNG.choice(data["topics"])
    n = {"medium": RNG.randint(2, 4), "long": RNG.randint(5, 9)}[length]
    parts: list[str] = []
    for i in range(n):
        s = sentences[i % len(sentences)]
        if i == 0:
            parts.append(s)
        else:
            parts.append(f"{RNG.choice(data['connectors'])} {s}")
    # spice with a short opener sometimes
    if RNG.random() < 0.4:
        parts.insert(0, RNG.choice(data["short"]))
    if RNG.random() < 0.7:
        parts.append(RNG.choice(data["closers"]))
    # uniqueness salt (neutral)
    salt = {
        "en": f" (note #{idx})",
        "zh": f"（备注 #{idx}）",
        "ja": f"（メモ #{idx}）",
        "es": f" (nota #{idx})",
        "fr": f" (note #{idx})",
    }[lang]
    if RNG.random() < 0.3:
        parts.append(salt.strip())
    return " ".join(parts) if lang != "zh" else "".join(
        p if p.endswith(("。", "？", "！", "：", "，")) or p.startswith(("另外", "同时", "实际", "比如", "另一", "与此", "小提", "值得", "简言", "总的", "（"))
        else (p + (" " if lang != "zh" else ""))
        for p in parts
    ) if False else (" ".join(parts) if lang in ("en", "es", "fr", "ja") else "".join(
        # Chinese: join carefully — connectors already include punctuation-ish commas
        p for p in parts
    ).replace("。另外", "。另外").replace("  ", ""))


def generate_lang(lang: str) -> list[dict]:
    segments: list[dict] = []
    # distribution: short / medium / long
    counts = {"short": 250, "medium": 500, "long": TARGET - 750}
    i = 0
    for length, count in counts.items():
        for _ in range(count):
            i += 1
            text = build_segment(lang, length, i)
            # ensure Chinese join is readable
            if lang == "zh":
                text = build_zh_segment(length, i)
            tokens_approx = max(1, len(text) // (1 if lang in ("zh", "ja") else 4))
            segments.append({
                "id": f"{lang}-{i:04d}",
                "lang": lang,
                "length": length,
                "text": text,
                "approx_chars": len(text),
                "approx_tokens": tokens_approx,
            })
    RNG.shuffle(segments)
    return segments


def build_zh_segment(length: str, idx: int) -> str:
    data = TEMPLATES["zh"]
    if length == "short":
        return RNG.choice(data["short"])
    topic_name, sentences = RNG.choice(data["topics"])
    n = {"medium": RNG.randint(2, 4), "long": RNG.randint(5, 9)}[length]
    parts: list[str] = []
    if RNG.random() < 0.4:
        parts.append(RNG.choice(data["short"]))
    for i in range(n):
        s = sentences[i % len(sentences)]
        if i == 0 and not parts:
            parts.append(s)
        else:
            parts.append(RNG.choice(data["connectors"]) + s)
    if RNG.random() < 0.7:
        parts.append(RNG.choice(data["closers"]))
    if RNG.random() < 0.3:
        parts.append(f"（备注 #{idx}）")
    return "".join(parts)


def write_custom_qa() -> None:
    qa = [
        {
            "pattern": r"(?i)\bping\b",
            "match": "regex",
            "reply": "pong",
            "langs": ["*"],
        },
        {
            "pattern": "你好 mock",
            "match": "contains",
            "reply": "你好！我是 Mock My AI，这是一条自定义语料回复。",
            "langs": ["zh"],
        },
        {
            "pattern": "hello mock",
            "match": "contains",
            "reply": "Hello! This is a custom Q&A override from Mock My AI.",
            "langs": ["en"],
        },
        {
            "pattern": r"(?i)what is mock my ai",
            "match": "regex",
            "reply": "Mock My AI is an open-source server that mocks OpenAI, Anthropic, and Gemini style APIs with fake but schema-correct responses.",
            "langs": ["*"],
        },
    ]
    path = CORPUS_DIR / "custom_qa.json"
    path.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    for lang in TEMPLATES:
        segs = generate_lang(lang)
        out = CORPUS_DIR / lang / "segments.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for s in segs:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        print(f"{lang}: {len(segs)} segments → {out}")
    write_custom_qa()
    print("Done.")


if __name__ == "__main__":
    main()
