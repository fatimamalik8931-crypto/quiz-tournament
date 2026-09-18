"""Seeds the database with categories (EN + UR), sample questions, badges,
and a demo admin + demo player account. Safe to re-run: it wipes and
recreates content tables first (users are left alone if they already exist,
unless --fresh is passed).
"""
import json
import sys

from db import get_connection, init_db, new_id
from auth_utils import hash_password

# ---------------------------------------------------------------------------
# Categories: key, icon keyword, gradient, {lang: (name, description)}
# ---------------------------------------------------------------------------
CATEGORIES = [
    {
        "key": "education",
        "icon": "book",
        "colors": ("#4F46E5", "#7C3AED"),
        "i18n": {
            "en": ("Education", "General academic knowledge: math, language, history"),
            "ur": ("تعلیم", "عمومی علمی معلومات: ریاضی، زبان، تاریخ"),
        },
    },
    {
        "key": "technology",
        "icon": "cpu",
        "colors": ("#0EA5E9", "#22D3EE"),
        "i18n": {
            "en": ("Technology", "IT, gadgets, and programming basics"),
            "ur": ("ٹیکنالوجی", "آئی ٹی، گیجٹس اور پروگرامنگ کی بنیادی معلومات"),
        },
    },
    {
        "key": "general_knowledge",
        "icon": "globe",
        "colors": ("#059669", "#10B981"),
        "i18n": {
            "en": ("General Knowledge", "Capitals, geography, and everyday facts"),
            "ur": ("عمومی معلومات", "دارالحکومت، جغرافیہ اور روزمرہ معلومات"),
        },
    },
    {
        "key": "sports",
        "icon": "trophy",
        "colors": ("#F59E0B", "#F97316"),
        "i18n": {
            "en": ("Sports", "Football, cricket, Olympics, and more"),
            "ur": ("کھیل", "فٹبال، کرکٹ، اولمپکس اور دیگر"),
        },
    },
    {
        "key": "entertainment",
        "icon": "film",
        "colors": ("#DB2777", "#EC4899"),
        "i18n": {
            "en": ("Entertainment", "Movies, music, and pop culture"),
            "ur": ("تفریح", "فلمیں، موسیقی اور مقبول ثقافت"),
        },
    },
    {
        "key": "science_nature",
        "icon": "leaf",
        "colors": ("#16A34A", "#65A30D"),
        "i18n": {
            "en": ("Science & Nature", "Biology, physics, chemistry, and the natural world"),
            "ur": ("سائنس اور فطرت", "حیاتیات، طبیعیات، کیمسٹری اور قدرتی دنیا"),
        },
    },
]

# ---------------------------------------------------------------------------
# Questions: category_key, difficulty, correct_index, {lang: (text, [opt0..3])}
# ---------------------------------------------------------------------------
QUESTIONS = [
    # ---------------- EDUCATION ----------------
    ("education", "easy", 1, {
        "en": ("What is 12 × 8?", ["86", "96", "108", "94"]),
        "ur": ("12 × 8 کا حاصل ضرب کیا ہے؟", ["86", "96", "108", "94"]),
    }),
    ("education", "medium", 1, {
        "en": ('Who wrote the play "Romeo and Juliet"?', ["Charles Dickens", "William Shakespeare", "Jane Austen", "Mark Twain"]),
        "ur": ("ڈرامہ 'رومیو اینڈ جولیٹ' کس نے لکھا؟", ["چارلس ڈکنز", "ولیم شیکسپیئر", "جین آسٹن", "مارک ٹوین"]),
    }),
    ("education", "easy", 0, {
        "en": ("What is the chemical symbol for water?", ["H2O", "O2", "CO2", "NaCl"]),
        "ur": ("پانی کی کیمیائی علامت کیا ہے؟", ["H2O", "O2", "CO2", "NaCl"]),
    }),
    ("education", "medium", 2, {
        "en": ("In which year did World War II end?", ["1943", "1944", "1945", "1946"]),
        "ur": ("دوسری جنگ عظیم کس سال ختم ہوئی؟", ["1943", "1944", "1945", "1946"]),
    }),
    ("education", "easy", 2, {
        "en": ('What is the plural of "child"?', ["Childs", "Childes", "Children", "Childrens"]),
        "ur": ("انگریزی لفظ 'Child' کی جمع کیا ہے؟", ["Childs", "Childes", "Children", "Childrens"]),
    }),
    ("education", "easy", 1, {
        "en": ("Which continent is the Sahara Desert located in?", ["Asia", "Africa", "Australia", "South America"]),
        "ur": ("صحرائے صحارا کس براعظم میں واقع ہے؟", ["ایشیا", "افریقہ", "آسٹریلیا", "جنوبی امریکہ"]),
    }),
    ("education", "medium", 2, {
        "en": ("What is the square root of 81?", ["7", "8", "9", "11"]),
        "ur": ("81 کا جذر (square root) کیا ہے؟", ["7", "8", "9", "11"]),
    }),
    ("education", "medium", 2, {
        "en": ('Who is known as the "Father of the Nation" in Pakistan?', ["Allama Iqbal", "Liaquat Ali Khan", "Muhammad Ali Jinnah", "Sir Syed Ahmed Khan"]),
        "ur": ("پاکستان میں 'بابائے قوم' کس کو کہا جاتا ہے؟", ["علامہ اقبال", "لیاقت علی خان", "محمد علی جناح", "سر سید احمد خان"]),
    }),

    # ---------------- TECHNOLOGY ----------------
    ("technology", "easy", 0, {
        "en": ('What does "CPU" stand for?', ["Central Processing Unit", "Computer Personal Unit", "Central Program Utility", "Control Processing Unit"]),
        "ur": ("'CPU' کا مطلب کیا ہے؟", ["سنٹرل پروسیسنگ یونٹ", "کمپیوٹر پرسنل یونٹ", "سنٹرل پروگرام یوٹیلیٹی", "کنٹرول پروسیسنگ یونٹ"]),
    }),
    ("technology", "easy", 2, {
        "en": ("Which company developed the Android operating system?", ["Apple", "Microsoft", "Google", "Samsung"]),
        "ur": ("اینڈرائیڈ آپریٹنگ سسٹم کس کمپنی نے بنایا؟", ["ایپل", "مائیکروسافٹ", "گوگل", "سام سنگ"]),
    }),
    ("technology", "medium", 0, {
        "en": ('What does "HTML" stand for?', ["HyperText Markup Language", "HighText Machine Language", "HyperTransfer Markup Language", "Home Tool Markup Language"]),
        "ur": ("'HTML' کا مطلب کیا ہے؟", ["ہائپر ٹیکسٹ مارک اپ لینگویج", "ہائی ٹیکسٹ مشین لینگویج", "ہائپر ٹرانسفر مارک اپ لینگویج", "ہوم ٹول مارک اپ لینگویج"]),
    }),
    ("technology", "easy", 1, {
        "en": ("Which of these is a programming language?", ["Photoshop", "Python", "Excel", "Windows"]),
        "ur": ("ان میں سے کون سی پروگرامنگ زبان ہے؟", ["فوٹوشاپ", "پائتھون", "ایکسل", "ونڈوز"]),
    }),
    ("technology", "easy", 0, {
        "en": ('What does "WWW" stand for?', ["World Wide Web", "World Wide Wire", "Web Wide World", "Wide World Web"]),
        "ur": ("'WWW' کا مطلب کیا ہے؟", ["ورلڈ وائیڈ ویب", "ورلڈ وائیڈ وائر", "ویب وائیڈ ورلڈ", "وائیڈ ورلڈ ویب"]),
    }),
    ("technology", "easy", 2, {
        "en": ("Which company makes the iPhone?", ["Samsung", "Google", "Apple", "Nokia"]),
        "ur": ("آئی فون کس کمپنی کی مصنوعات ہے؟", ["سام سنگ", "گوگل", "ایپل", "نوکیا"]),
    }),
    ("technology", "hard", 1, {
        "en": ("What is the binary representation of the decimal number 2?", ["01", "10", "11", "100"]),
        "ur": ("عدد 2 کی بائنری شکل کیا ہے؟", ["01", "10", "11", "100"]),
    }),
    ("technology", "medium", 2, {
        "en": ("Which of these is used to store data permanently on a computer?", ["RAM", "CPU", "Hard Disk", "Cache"]),
        "ur": ("کمپیوٹر میں ڈیٹا مستقل طور پر ذخیرہ کرنے کے لیے کیا استعمال ہوتا ہے؟", ["ریم (RAM)", "سی پی یو", "ہارڈ ڈسک", "کیش"]),
    }),

    # ---------------- GENERAL KNOWLEDGE ----------------
    ("general_knowledge", "easy", 2, {
        "en": ("What is the capital of Japan?", ["Seoul", "Beijing", "Tokyo", "Bangkok"]),
        "ur": ("جاپان کا دارالحکومت کیا ہے؟", ["سیول", "بیجنگ", "ٹوکیو", "بینکاک"]),
    }),
    ("general_knowledge", "medium", 3, {
        "en": ("Which is the largest ocean on Earth?", ["Atlantic", "Indian", "Arctic", "Pacific"]),
        "ur": ("دنیا کا سب سے بڑا سمندر کون سا ہے؟", ["بحر اوقیانوس", "بحر ہند", "بحر منجمد شمالی", "بحر الکاہل"]),
    }),
    ("general_knowledge", "easy", 2, {
        "en": ("How many continents are there on Earth?", ["5", "6", "7", "8"]),
        "ur": ("زمین پر کتنے براعظم ہیں؟", ["5", "6", "7", "8"]),
    }),
    ("general_knowledge", "easy", 0, {
        "en": ("What is the currency of Pakistan?", ["Rupee", "Dinar", "Dirham", "Taka"]),
        "ur": ("پاکستان کی کرنسی کیا ہے؟", ["روپیہ", "دینار", "درہم", "ٹکا"]),
    }),
    ("general_knowledge", "medium", 1, {
        "en": ("Which is the longest river in the world?", ["Amazon", "Nile", "Yangtze", "Mississippi"]),
        "ur": ("دنیا کا سب سے طویل دریا کون سا ہے؟", ["ایمیزون", "نیل", "یانگ زی", "مسیسیپی"]),
    }),
    ("general_knowledge", "medium", 2, {
        "en": ("How many days are there in a leap year?", ["364", "365", "366", "367"]),
        "ur": ("لیپ ایئر میں کتنے دن ہوتے ہیں؟", ["364", "365", "366", "367"]),
    }),
    ("general_knowledge", "easy", 2, {
        "en": ("What is the tallest mountain in the world?", ["K2", "Kangchenjunga", "Mount Everest", "Nanga Parbat"]),
        "ur": ("دنیا کی بلند ترین چوٹی کون سی ہے؟", ["کے ٹو", "کنچن جنگا", "ماؤنٹ ایورسٹ", "نانگا پربت"]),
    }),
    ("general_knowledge", "hard", 1, {
        "en": ("Which country gifted the Statue of Liberty to the USA?", ["England", "France", "Spain", "Italy"]),
        "ur": ("مجسمہ آزادی امریکہ کو کس ملک نے تحفے میں دیا؟", ["انگلینڈ", "فرانس", "اسپین", "اٹلی"]),
    }),

    # ---------------- SPORTS ----------------
    ("sports", "easy", 2, {
        "en": ("How many players are there in a football (soccer) team on the field?", ["9", "10", "11", "12"]),
        "ur": ("فٹبال کی ٹیم میں میدان میں کتنے کھلاڑی ہوتے ہیں؟", ["9", "10", "11", "12"]),
    }),
    ("sports", "easy", 1, {
        "en": ('In which sport would you perform a "slam dunk"?', ["Volleyball", "Basketball", "Tennis", "Cricket"]),
        "ur": ("'سلیم ڈنک' کس کھیل میں کیا جاتا ہے؟", ["والی بال", "باسکٹ بال", "ٹینس", "کرکٹ"]),
    }),
    ("sports", "easy", 2, {
        "en": ("How many players are on a cricket team?", ["9", "10", "11", "12"]),
        "ur": ("کرکٹ ٹیم میں کتنے کھلاڑی ہوتے ہیں؟", ["9", "10", "11", "12"]),
    }),
    ("sports", "medium", 2, {
        "en": ("The Olympic Games are held every how many years?", ["2", "3", "4", "5"]),
        "ur": ("اولمپک گیمز ہر کتنے سال بعد منعقد ہوتے ہیں؟", ["2", "3", "4", "5"]),
    }),
    ("sports", "hard", 2, {
        "en": ("Which country won the first Cricket World Cup in 1975?", ["Australia", "England", "West Indies", "India"]),
        "ur": ("1975 میں پہلا کرکٹ ورلڈ کپ کس ملک نے جیتا؟", ["آسٹریلیا", "انگلینڈ", "ویسٹ انڈیز", "بھارت"]),
    }),
    ("sports", "medium", 1, {
        "en": ("In tennis, what is a score of zero called?", ["Nil", "Love", "Zero", "Duck"]),
        "ur": ("ٹینس میں صفر اسکور کو کیا کہتے ہیں؟", ["نل", "لَو (Love)", "زیرو", "ڈک"]),
    }),
    ("sports", "easy", 1, {
        "en": ("Which sport uses a shuttlecock?", ["Tennis", "Badminton", "Squash", "Table Tennis"]),
        "ur": ("کس کھیل میں 'شٹل کاک' استعمال ہوتا ہے؟", ["ٹینس", "بیڈمنٹن", "اسکواش", "ٹیبل ٹینس"]),
    }),
    ("sports", "easy", 1, {
        "en": ("How many rings are there on the Olympic flag?", ["4", "5", "6", "7"]),
        "ur": ("اولمپک پرچم میں کتنے حلقے ہوتے ہیں؟", ["4", "5", "6", "7"]),
    }),

    # ---------------- ENTERTAINMENT ----------------
    ("entertainment", "easy", 1, {
        "en": ('Which movie franchise features a wizard named Harry Potter?', ["Lord of the Rings", "Harry Potter", "Narnia", "Twilight"]),
        "ur": ("کس فلمی سیریز میں 'ہیری پوٹر' نامی جادوگر شامل ہے؟", ["لارڈ آف دی رِنگز", "ہیری پوٹر", "نارنیا", "ٹوائی لائٹ"]),
    }),
    ("entertainment", "easy", 1, {
        "en": ('Who is known as the "King of Pop"?', ["Elvis Presley", "Michael Jackson", "Prince", "Justin Bieber"]),
        "ur": ("'کنگ آف پاپ' کس کو کہا جاتا ہے؟", ["ایلوس پریسلی", "مائیکل جیکسن", "پرنس", "جسٹن بیبر"]),
    }),
    ("entertainment", "medium", 2, {
        "en": ('Which streaming service produced the show "Stranger Things"?', ["Amazon Prime", "Disney+", "Netflix", "Hulu"]),
        "ur": ("شو 'اسٹرینجر تھنگز' کس اسٹریمنگ سروس نے پیش کیا؟", ["ایمیزون پرائم", "ڈزنی پلس", "نیٹ فلکس", "ہولو"]),
    }),
    ("entertainment", "easy", 2, {
        "en": ("Which animated movie features a snowman named Olaf?", ["Tangled", "Moana", "Frozen", "Encanto"]),
        "ur": ("کس اینیمیٹڈ فلم میں 'اولاف' نامی برفانی آدمی ہے؟", ["ٹینگلڈ", "موآنا", "فروزن", "اینکینٹو"]),
    }),
    ("entertainment", "medium", 1, {
        "en": ('Who played Iron Man in the Marvel Cinematic Universe?', ["Chris Evans", "Robert Downey Jr.", "Chris Hemsworth", "Mark Ruffalo"]),
        "ur": ("مارول سنیمیٹک یونیورس میں 'آئرن مین' کا کردار کس نے ادا کیا؟", ["کرس ایونز", "رابرٹ ڈاؤنی جونیئر", "کرس ہیمس ورتھ", "مارک رافیلو"]),
    }),
    ("entertainment", "hard", 1, {
        "en": ("Which of these films became the highest-grossing film of all time in the early 2020s?", ["Titanic", "Avatar", "Avengers: Endgame", "Star Wars"]),
        "ur": ("2020 کی دہائی کے آغاز تک سب سے زیادہ کمائی کرنے والی فلم کون سی تھی؟", ["ٹائی ٹینک", "اَوتار", "اینڈ گیم", "اسٹار وارز"]),
    }),
    ("entertainment", "easy", 2, {
        "en": ("Which instrument has 88 keys?", ["Guitar", "Violin", "Piano", "Flute"]),
        "ur": ("کس ساز میں 88 چابیاں ہوتی ہیں؟", ["گٹار", "وائلن", "پیانو", "بانسری"]),
    }),
    ("entertainment", "easy", 1, {
        "en": ('In which movie franchise would you find the character "Yoda"?', ["Star Trek", "Star Wars", "Transformers", "Marvel"]),
        "ur": ("کردار 'یوڈا' کس فلمی سیریز میں پایا جاتا ہے؟", ["اسٹار ٹریک", "اسٹار وارز", "ٹرانسفارمرز", "مارول"]),
    }),

    # ---------------- SCIENCE & NATURE ----------------
    ("science_nature", "easy", 1, {
        "en": ("Which planet is known as the Red Planet?", ["Venus", "Mars", "Jupiter", "Saturn"]),
        "ur": ("کس سیارے کو 'سرخ سیارہ' کہا جاتا ہے؟", ["زہرہ", "مریخ", "مشتری", "زحل"]),
    }),
    ("science_nature", "medium", 2, {
        "en": ("What gas do plants absorb from the atmosphere for photosynthesis?", ["Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"]),
        "ur": ("پودے فوٹو سنتھیسز کے لیے فضا سے کون سی گیس جذب کرتے ہیں؟", ["آکسیجن", "نائٹروجن", "کاربن ڈائی آکسائیڈ", "ہائیڈروجن"]),
    }),
    ("science_nature", "medium", 1, {
        "en": ("How many bones are there in the adult human body?", ["196", "206", "216", "226"]),
        "ur": ("بالغ انسانی جسم میں کتنی ہڈیاں ہوتی ہیں؟", ["196", "206", "216", "226"]),
    }),
    ("science_nature", "easy", 1, {
        "en": ("What is the largest mammal in the world?", ["African Elephant", "Blue Whale", "Giraffe", "Polar Bear"]),
        "ur": ("دنیا کا سب سے بڑا ممالیہ (mammal) کون سا ہے؟", ["افریقی ہاتھی", "نیلی وہیل", "زرافہ", "قطبی ریچھ"]),
    }),
    ("science_nature", "medium", 2, {
        "en": ("What is the chemical symbol for gold?", ["Go", "Gd", "Au", "Ag"]),
        "ur": ("سونے کی کیمیائی علامت کیا ہے؟", ["Go", "Gd", "Au", "Ag"]),
    }),
    ("science_nature", "easy", 2, {
        "en": ("Which planet is closest to the Sun?", ["Venus", "Earth", "Mercury", "Mars"]),
        "ur": ("سورج کے قریب ترین سیارہ کون سا ہے؟", ["زہرہ", "زمین", "عطارد", "مریخ"]),
    }),
    ("science_nature", "hard", 1, {
        "en": ('What is the "powerhouse of the cell"?', ["Nucleus", "Mitochondria", "Ribosome", "Golgi body"]),
        "ur": ("خلیے کا 'پاور ہاؤس' کسے کہا جاتا ہے؟", ["نیوکلیس", "مائٹوکونڈریا", "رائبوسوم", "گولگی باڈی"]),
    }),
    ("science_nature", "easy", 2, {
        "en": ("At what temperature does water boil at sea level (Celsius)?", ["90", "95", "100", "110"]),
        "ur": ("سطح سمندر پر پانی کس درجہ حرارت (سیلسیس) پر ابلتا ہے؟", ["90", "95", "100", "110"]),
    }),
]

BADGES = [
    ("first_quiz", "First Steps", "Complete your first quiz", "flag"),
    ("perfect_score", "Perfectionist", "Score 100% on a quiz", "star"),
    ("ten_quizzes", "Quiz Enthusiast", "Complete 10 quizzes", "medal"),
    ("tournament_winner", "Champion", "Finish first in a tournament", "crown"),
    ("speed_demon", "Speed Demon", "Answer correctly in under 3 seconds", "bolt"),
]


def run(fresh=False):
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    if fresh:
        for table in [
            "tournament_answers", "tournament_participants", "tournament_questions",
            "tournaments", "quiz_answers", "quiz_attempts", "user_badges", "badges",
            "question_translations", "questions", "category_translations", "categories",
        ]:
            cur.execute(f"DELETE FROM {table}")

    # Categories + translations (idempotent: skip existing keys)
    cat_ids = {}
    for cat in CATEGORIES:
        existing = cur.execute("SELECT id FROM categories WHERE key = ?", (cat["key"],)).fetchone()
        if existing:
            cat_ids[cat["key"]] = existing["id"]
            continue
        cid = new_id()
        cat_ids[cat["key"]] = cid
        cur.execute(
            "INSERT INTO categories (id, key, icon, color_from, color_to) VALUES (?,?,?,?,?)",
            (cid, cat["key"], cat["icon"], cat["colors"][0], cat["colors"][1]),
        )
        for lang, (name, desc) in cat["i18n"].items():
            cur.execute(
                "INSERT INTO category_translations (id, category_id, language, name, description) VALUES (?,?,?,?,?)",
                (new_id(), cid, lang, name, desc),
            )

    # Questions + translations (only seed if this category currently has none)
    for cat_key, difficulty, correct_index, i18n in QUESTIONS:
        cat_id = cat_ids[cat_key]
        qid = new_id()
        cur.execute(
            "INSERT INTO questions (id, category_id, difficulty, points, time_limit_seconds, correct_index) VALUES (?,?,?,?,?,?)",
            (qid, cat_id, difficulty, {"easy": 10, "medium": 15, "hard": 20}[difficulty], 20, correct_index),
        )
        for lang, (text, options) in i18n.items():
            cur.execute(
                "INSERT INTO question_translations (id, question_id, language, text, options_json) VALUES (?,?,?,?,?)",
                (new_id(), qid, lang, text, json.dumps(options, ensure_ascii=False)),
            )

    # Badges
    for key, name, desc, icon in BADGES:
        existing = cur.execute("SELECT id FROM badges WHERE key = ?", (key,)).fetchone()
        if existing:
            continue
        cur.execute(
            "INSERT INTO badges (id, key, name, description, icon) VALUES (?,?,?,?,?)",
            (new_id(), key, name, desc, icon),
        )

    # Demo accounts
    def ensure_user(name, email, password, role):
        existing = cur.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            return existing["id"]
        uid = new_id()
        cur.execute(
            "INSERT INTO users (id, name, email, password_hash, role) VALUES (?,?,?,?,?)",
            (uid, name, email, hash_password(password), role),
        )
        return uid

    ensure_user("Admin", "admin@quiz.local", "admin123", "ADMIN")
    ensure_user("Demo Player", "demo@quiz.local", "demo1234", "USER")

    conn.commit()
    conn.close()
    print("Database seeded: 6 categories, {} questions, {} badges.".format(len(QUESTIONS), len(BADGES)))
    print("Admin login:  admin@quiz.local / admin123")
    print("Demo login:   demo@quiz.local / demo1234")


if __name__ == "__main__":
    run(fresh="--fresh" in sys.argv)
