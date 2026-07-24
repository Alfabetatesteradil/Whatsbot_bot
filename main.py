from datetime import datetime, timedelta
import os
import random
import time
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# ==========================================
# 🔑 ДАННЫЕ ИЗ GREEN API:
ID_INSTANCE = "710722690715"
API_TOKEN = "38c0a3003c22469cad11461cd9f72335793bd5303fe8450baf"
# ==========================================

BOT_START_TIME = datetime.now()
users = {}

# Состояния активных игр
active_duels = {}  # chat_id: {initiator_id, initiator_name, bet}
active_quiz = {}  # chat_id: {question, answer}
active_tictactoe = (
    {}
)  # chat_id: {p1_id, p1_name, p2_id, p2_name, turn_id, board}

RANKS = [
    ("Дерево", 50),
    ("Уголь", 100),
    ("Железо", 150),
    ("Золото", 200),
    ("Алмаз", 500),
]

RUSSIAN_QUIZ = [
    {"q": "Что означает слово «ОКО»?", "a": "глаз"},
    {"q": "Что означает слово «ЧЕЛО»?", "a": "лоб"},
    {"q": "Что означает слово «ПЕРСТ»?", "a": "палец"},
    {"q": "Что означает слово «УСТА»?", "a": "губы"},
    {"q": "Что означает слово «ДЕСНИЦА»?", "a": "правая рука"},
    {"q": "Что означает слово «ШУЙЦА»?", "a": "левая рука"},
    {"q": "Что означает слово «ВЫЯ»?", "a": "шея"},
    {"q": "Что означает слово «ЛАНИТЫ»?", "a": "щеки"},
    {"q": "Что означает слово «РАМЕНА»?", "a": "плечи"},
    {"q": "Что означает слово «ЗДРАВИЕ»?", "a": "здоровье"},
    {"q": "Что означает слово «ОЧИ»?", "a": "глаза"},
    {"q": "Что означает слово «ЧАТА»?", "a": "монета"},
    {"q": "Что означает слово «ОДР»?", "a": "кровать"},
    {"q": "Что означает слово «ЗОДЧИЙ»?", "a": "архитектор"},
    {"q": "Что означает слово «КОЛОВРАТ»?", "a": "солнцеворот"},
    {"q": "Что означает слово «ИЗВАЯНИЕ»?", "a": "скульптура"},
    {"q": "Что означает слово «ПЕЧАЛЬ»?", "a": "грусть"},
    {"q": "Что означает слово «ВРАЧ»?", "a": "доктор"},
    {"q": "Что означает слово «ГЛАГОЛ»?", "a": "слово"},
    {"q": "Что означает слово «ПРИЗРАК»?", "a": "тень"},
]


def send_whatsapp_message(chat_id, text):
  url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"
  payload = {"chatId": chat_id, "message": text}
  headers = {"Content-Type": "application/json"}
  try:
    requests.post(url, json=payload, headers=headers, timeout=5)
  except Exception as e:
    print(f"Ошибка отправки: {e}", flush=True)


def get_uptime():
  delta = datetime.now() - BOT_START_TIME
  days = delta.days
  hours, rem = divmod(delta.seconds, 3600)
  mins, secs = divmod(rem, 60)
  res = ""
  if days > 0:
    res += f"{days} дн. "
  if hours > 0 or days > 0:
    res += f"{hours} ч. "
  return res + f"{mins} мин. {secs} сек."


def get_user(user_id):
  if user_id not in users:
    users[user_id] = {
        "xp": 0,
        "restarts": 0,
        "word1": "Слово1!",
        "word2": "Слово2!",
        "coins": {
            "bronze": 0,
            "copper": 0,
            "iron": 0,
            "gold": 0,
            "diamond": 0,
            "obsidian": 0,
        },
        "has_held_obsidian": False,
        "cool_until": None,
        "dobri_charges": 0,
        "ludoman_charges": 0,
    }
  return users[user_id]


def check_obsidian_announcement(user, user_name):
  if user["coins"]["obsidian"] > 0 and not user["has_held_obsidian"]:
    user["has_held_obsidian"] = True
    return f"@{user_name} *говорят легенды что @{user_name} выковал Обсидиан! Похволяйте его!*"
  return None


def add_xp(user, amount):
  if user["cool_until"] and datetime.now() < user["cool_until"]:
    amount *= 2
  user["xp"] += amount
  multiplier = user["restarts"] + 1
  total_max = sum(limit * multiplier for _, limit in RANKS)
  while user["xp"] >= total_max:
    user["xp"] -= total_max
    user["restarts"] += 1
    multiplier = user["restarts"] + 1
    total_max = sum(limit * multiplier for _, limit in RANKS)


def render_board(board):
  symbols = {" ": "⬜", "X": "❌", "O": "⭕"}
  res = ""
  for i in range(0, 9, 3):
    res += "".join([symbols[board[j]] for j in range(i, i + 3)]) + "\n"
  return res


def check_win(board, symbol):
  wins = [
      [0, 1, 2],
      [3, 4, 5],
      [6, 7, 8],
      [0, 3, 6],
      [1, 4, 7],
      [2, 5, 8],
      [0, 4, 8],
      [2, 4, 6],
  ]
  return any(all(board[i] == symbol for i in combo) for combo in wins)


def process_command(chat_id, user_id, user_name, msg):
  msg_clean = msg.strip()
  msg_lower = msg_clean.lower()
  user = get_user(user_id)

  # ================= 📜 МЕНЮ =================
  if msg_lower == "!меню":
    return (
        "📜 *ПОЛНОЕ МЕНЮ КОМАНД* 📜\n\n"
        "⚙️ *ОСНОВНОЕ:*\n"
        "• `!пинг` — задержка и аптайм бота\n"
        "• `!ранг` — детальная карточка профиля\n"
        "• `!админ` — список администраторов\n"
        "• `!апельсин` — цитата про апельсины и яблоки\n"
        "• `!число` — случайное число (или `!число от X до Y`)\n\n"
        "🪙 *ЭКОНОМИКА:*\n"
        "• `!магазин` — каталог товаров\n"
        "• `!трейд [XP]` — обмен XP на Бронзовые монеты\n"
        "• `!межтрейд` — межсерверный рынок\n\n"
        "🐱 *ИНТЕРАКТИВ:*\n"
        "• `!кошка` — погладить кошку\n\n"
        "🎮 *МИНИ-ИГРЫ:*\n"
        "• `!дуэль [ставка]` — вызов на дуэль\n"
        "• `!рулетка [ставка]` — русская рулетка (1/6 шанс x5)\n"
        "• `!викторина` — вопрос по русскому языку (`!ответ [слово]`)\n"
        "• `!крестики` — сыграть в крестики-нолики (`!ход 1-9`)"
    )

  # ================= 🤫 СЕКРЕТНЫЕ И АДМИН КОМАНДЫ =================
  elif msg_lower == "!альтик":
    return "*АЛЬТИК ЛУЧШИЙ, АЛЬТИК ЛУЧШИЙ В МИРЕ АДМИН НА СВЕТЕ*"

  elif msg_lower == "!админ":
    return (
        "👑 *СПИСОК АДМИНИСТРАТОРОВ:* 👑\n\n"
        f"1. @{user_name} — Главный Создатель / Владелец\n"
        "2. Бот-Помощник — Модератор"
    )

  elif msg_lower == "!апельсин":
    return "ХАХАХАХ АПЕЛЬСИН🍊, ЯБЛОКО ЛУЧШЕ🍎🍎🍏🍏"

  # ================= ⚡ ПИНГ =================
  elif msg_lower == "!пинг":
    start_time = time.time()
    try:
      url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/getStateInstance/{API_TOKEN}"
      requests.get(url, timeout=3)
      ping_ms = int((time.time() - start_time) * 1000)
    except Exception:
      ping_ms = "N/A"
    return (
        f"🏓 *Понг!*\n⚡ *Задержка:* {ping_ms} мс\n⏱ *Время работы:*"
        f" {get_uptime()}"
    )

  # ================= 🎲 ЧИСЛО =================
  elif msg_lower.startswith("!число"):
    clean_msg = (
        msg_lower.replace("!число", "").replace("от", "").replace("до", "")
    )
    parts = clean_msg.split()
    min_val, max_val = 1, 100
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
      v1, v2 = int(parts[0]), int(parts[1])
      min_val, max_val = min(v1, v2), max(v1, v2)
    elif len(parts) == 1 and parts[0].isdigit():
      v = int(parts[0])
      min_val, max_val = min(1, v), max(1, v)
    return (
        f"🎲 *Случайное число* [{min_val} – {max_val}]:\n👉"
        f" *{random.randint(min_val, max_val)}*"
    )

  # ================= 📊 РАНГ =================
  elif msg_lower.startswith("!ранг"):
    xp, restarts = user["xp"], user["restarts"]
    multiplier = restarts + 1
    rank_str, curr = "", xp

    for r_name, limit in RANKS:
      max_xp = limit * multiplier
      if curr < max_xp:
        rank_str = f"{r_name} : {curr}/{max_xp}"
        break
      curr -= max_xp
    if not rank_str:
      rank_str = f"Алмаз : {limit * multiplier}/{limit * multiplier}"

    effects = []
    if user["cool_until"] and datetime.now() < user["cool_until"]:
      effects.append("Крутой Крутой (x2 XP)")
    if user["dobri_charges"] > 0:
      effects.append(f"Добри :3 ({user['dobri_charges']} защ.)")
    if user["ludoman_charges"] > 0:
      effects.append(f"Лудоман ({user['ludoman_charges']} зар.)")

    effects_str = ", ".join(effects) if effects else "*нет эффектов*"

    c = user["coins"]
    coins_str = (
        f"Бронза-{c['bronze']} Медь-{c['copper']} Железо-{c['iron']}"
        f" Золото-{c['gold']} Алмаз-{c['diamond']}"
    )

    if user["has_held_obsidian"] or c["obsidian"] > 0:
      coins_str += f" Обсидиан-{c['obsidian']}"

    return (
        f"@{user_name}\n"
        f"{rank_str}\n"
        f"{user['word1']}\n"
        f"Перерождений : {restarts}\n"
        f"{user['word2']}\n"
        f"Эффекты : {effects_str}\n"
        f"Денежки : {coins_str}"
    )

  # ================= 🛒 МАГАЗИН И ТРЕЙД =================
  elif msg_lower == "!магазин":
    return (
        "🛒 *МАГАЗИН ПРЕДМЕТОВ* 🛒\n\n"
        "1. Эффект «Добри :3» — 3 Железные монеты\n"
        "2. Эффект «Крутой Крутой» — 1 Золотая монета\n"
        "3. Эффект «Лудоман» — 5 Медных монет\n\n"
        "💡 Покупка: `!купить [номер]`"
    )

  elif msg_lower.startswith("!трейд"):
    parts = msg_lower.split()
    if len(parts) == 2 and parts[1].isdigit():
      val = int(parts[1])
      if val % 5 != 0 or user["xp"] < val:
        return "❌ Число должно быть кратно 5 и хватать XP!"
      user["xp"] -= val
      user["coins"]["bronze"] += val // 5

      obs_msg = check_obsidian_announcement(user, user_name)
      res = f"✅ Обменяно {val} XP на {val // 5} Бронзовых монет!"
      return f"{res}\n\n{obs_msg}" if obs_msg else res
    return "🎟 Используйте: `!трейд [число_кратное_5]`"

  elif msg_lower == "!межтрейд":
    return (
        "🌐 *МЕЖСЕРВЕРНЫЙ ТРЕЙД* 🌐\nСоздать лот:"
        " `!межтрейд создать [монета] [кол-во] [цена]`"
    )

  # ================= 🐱 КОШКА =================
  elif msg_lower in ["!кошка", "!погладь"]:
    if user["dobri_charges"] > 0:
      user["dobri_charges"] -= 1
      add_xp(user, 480)
      return f"😻 «Добри :3» подарила *+480 XP*! Осталось зарядов: {user['dobri_charges']}"
    add_xp(user, 10)
    return "😾 Кошка помурчала и дала +10 XP!"

  # ================= ⚔️ ДУЭЛИ =================
  elif msg_lower.startswith("!дуэль"):
    parts = msg_lower.split()
    bet = 0
    if len(parts) >= 2 and parts[-1].isdigit():
      bet = int(parts[-1])

    if user["xp"] < bet:
      return f"❌ У вас недостаточно XP! Баланс: {user['xp']} XP."

    active_duels[chat_id] = {
        "initiator_id": user_id,
        "initiator_name": user_name,
        "bet": bet,
    }
    return (
        f"⚔️ {user_name} вызывает любого на дуэль на *{bet} XP*!\nКому-нибудь"
        " написать: `!принять` или `!отказ`"
    )

  elif msg_lower == "!принять":
    if chat_id not in active_duels:
      return "❌ В этом чате нет активных вызовов на дуэль!"

    d = active_duels.pop(chat_id)
    if user_id == d["initiator_id"]:
      return "❌ Нельзя принять дуэль у самого себя!"

    bet = d["bet"]
    init_user = get_user(d["initiator_id"])

    if user["xp"] < bet or init_user["xp"] < bet:
      return "❌ У одного из участников больше нет нужного количества XP!"

    if random.choice([True, False]):
      winner_id, winner_name = user_id, user_name
      loser_id, loser_name = d["initiator_id"], d["initiator_name"]
    else:
      winner_id, winner_name = d["initiator_id"], d["initiator_name"]
      loser_id, loser_name = user_id, user_name

    get_user(winner_id)["xp"] += bet
    get_user(loser_id)["xp"] -= bet
    return (
        f"💥 ДУЭЛЬ СОСТОЯЛАСЬ!\nПобедил *{winner_name}* и забрал *+{bet}"
        f" XP* у {loser_name}!"
    )

  elif msg_lower == "!отказ":
    if chat_id in active_duels:
      del active_duels[chat_id]
      return "🛡 Дуэль отклонена!"

  # ================= 💥 РУЛЕТКА =================
  elif msg_lower.startswith("!рулетка"):
    parts = msg_lower.split()
    if len(parts) == 2 and parts[1].isdigit():
      bet = int(parts[1])
      if user["xp"] < bet or bet <= 0:
        return "❌ Недостаточно XP!"
      user["xp"] -= bet
      if random.randint(1, 6) == 1:
        win = bet * 5
        add_xp(user, win)
        return f"💥 БАХ! Вы выжили и забираете x5 куш: *+{win} XP*!"
      else:
        return f"🪹 *Щёлк...* Барабан пуст. Вы потеряли {bet} XP."

  # ================= 📚 ВИКТОРИНА =================
  elif msg_lower == "!викторина":
    q_data = random.choice(RUSSIAN_QUIZ)
    active_quiz[chat_id] = q_data
    return f"📚 *Вопрос:* {q_data['q']}\n\nОтвет командой: `!ответ [слово]`"

  elif msg_lower.startswith("!ответ"):
    if chat_id in active_quiz:
      ans = msg_lower.replace("!ответ", "").strip()
      correct = active_quiz[chat_id]["a"].lower()
      if ans == correct:
        del active_quiz[chat_id]
        add_xp(user, 150)
        return f"🎉 Правильно, {user_name}! Это «{correct}». *+150 XP*!"
      else:
        return "❌ Неверно!"

  # ================= ❌⭕ КРЕСТИКИ-НОЛИКИ =================
  elif msg_lower == "!крестики":
    active_tictactoe[chat_id] = {
        "p1_id": user_id,
        "p1_name": user_name,
        "p2_id": None,
        "p2_name": None,
        "turn_id": user_id,
        "board": [" "] * 9,
    }
    return (
        f"🎮 Игра создана!\nИгрок 1 (❌): *{user_name}*\n\nХодит"
        f" *{user_name}*: напишите `!ход [1-9]`.\nВторой игрок подключится"
        " автоматически при своем ходу!"
    )

  elif msg_lower.startswith("!ход"):
    if chat_id not in active_tictactoe:
      return "❌ Игра не начата! Напишите `!крестики`."

    game = active_tictactoe[chat_id]

    if game["p2_id"] is None and user_id != game["p1_id"]:
      game["p2_id"] = user_id
      game["p2_name"] = user_name

    if user_id != game["turn_id"]:
      curr_turn_name = (
          game["p1_name"] if game["turn_id"] == game["p1_id"] else game["p2_name"]
      )
      return f"⏳ Сейчас не ваш ход! Ходит: *{curr_turn_name}*"

    parts = msg_lower.split()
    if len(parts) == 2 and parts[1].isdigit():
      pos = int(parts[1]) - 1
      if 0 <= pos <= 8 and game["board"][pos] == " ":
        symbol = "X" if user_id == game["p1_id"] else "O"
        game["board"][pos] = symbol

        if check_win(game["board"], symbol):
          b_img = render_board(game["board"])
          del active_tictactoe[chat_id]
          add_xp(user, 200)
          return (
              f"🎉 ПОБЕДА! *{user_name}* выиграл!\n\n{b_img}\nПолучено *+200"
              " XP*!"
          )

        if " " not in game["board"]:
          b_img = render_board(game["board"])
          del active_tictactoe[chat_id]
          return f"🤝 НИЧЬЯ!\n\n{b_img}"

        if game["p2_id"] is None:
          game["turn_id"] = "WAITING"
          next_name = "Второй игрок"
        else:
          game["turn_id"] = (
              game["p2_id"] if user_id == game["p1_id"] else game["p1_id"]
          )
          next_name = (
              game["p2_name"] if user_id == game["p1_id"] else game["p1_name"]
          )

        return (
            f"Ход сделан!\n\n{render_board(game['board'])}\nСледующий ход:"
            f" *{next_name}*"
        )

  return None


@app.route("/webhook", methods=["POST"])
def webhook():
  data = request.get_json(silent=True) or {}
  if data.get("typeWebhook") in [
      "incomingMessageReceived",
      "outgoingMessageReceived",
      "outgoingAPIMessageReceived",
  ]:
    message_data = data.get("messageData", {})
    type_message = message_data.get("typeMessage")
    text = ""
    if type_message == "textMessage":
      text = message_data.get("textMessageData", {}).get("textMessage", "")
    elif type_message in ["extendedTextMessage", "quotedMessage"]:
      text = message_data.get("extendedTextMessageData", {}).get("text", "")

    sender_data = data.get("senderData", {})
    sender_id = sender_data.get("sender") or data.get("chatId", "unknown")
    sender_name = sender_data.get("senderName", "Игрок")
    chat_id = (
        data.get("chatId")
        or sender_data.get("chatId")
        or data.get("keyRemoteJid")
    )

    if text and chat_id:
      reply = process_command(chat_id, sender_id, sender_name, text)
      if reply:
        send_whatsapp_message(chat_id, reply)

  return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
  return "Бот активен!", 200


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
      
