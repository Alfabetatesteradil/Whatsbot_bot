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

# Хранилища состояний игр и дуэлей
active_duels = {}
active_quiz = {}
active_tictactoe = {}

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
    {"q": "Что означает слово «ДЕСНИЦА»?", "a": "рука"},
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
        "word1": "Слово 1",
        "word2": "Слово 2",
        "coins": {
            "bronze": 0,
            "copper": 0,
            "iron": 0,
            "gold": 0,
            "diamond": 0,
            "obsidian": 0,
        },
        "has_held_obsidian": False,
        "ludoman_charges": 0,
        "cool_until": None,
        "dobri_charges": 0,
        "lucky_until": None,
    }
  return users[user_id]


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
        "• `!ранг` — ваш профиль, монеты и уровень\n\n"
        "🪙 *ЭКОНОМИКА И ТОРГОВЛЯ:*\n"
        "• `!магазин` — виртуальный магазин предметов\n"
        "• `!трейд [XP]` — обмен XP на Бронзовые монеты\n"
        "• `!межтрейд` — межсерверный обмен ресурсами\n\n"
        "🐱 *ИНТЕРАКТИВ:*\n"
        "• `!кошка` — погладить Золотую Кошку\n\n"
        "🎮 *МИНИ-ИГРЫ:*\n"
        "• `!лотерея [1/2/3]` — испытать удачу в билетах\n"
        "• `!дуэль @игрок [ставка]` — вызов на дуэль на XP\n"
        "• `!рулетка [ставка]` — русская рулетка (1/6 шанс x5)\n"
        "• `!викторина` — викторина по русскому языку (`!ответ [слово]`)\n"
        "• `!крестики @игрок` — игра в крестики-нолики (`!ход [1-9]`)"
    )

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

  elif msg_lower.startswith("!ранг"):
    xp, restarts = user["xp"], user["restarts"]
    multiplier = restarts + 1
    rank_str, curr = "", xp
    for r_name, limit in RANKS:
      max_xp = limit * multiplier
      if curr < max_xp:
        rank_str = f"{r_name} {curr}/{max_xp}"
        break
      curr -= max_xp
    if not rank_str:
      rank_str = f"Алмаз {limit * multiplier}/{limit * multiplier}"

    c = user["coins"]
    coins_str = (
        f"Бронза:{c['bronze']}, Медь:{c['copper']}, Железо:{c['iron']},"
        f" Золото:{c['gold']}, Алмаз:{c['diamond']}"
    )
    return (
        f"/// @{user_name}, {rank_str} ///\n\\\\\\ Перерождения : {restarts}"
        f" \\\\\\\nМонеты : {coins_str}"
    )

  # ================= 🛒 МАГАЗИН И ТРЕЙДЫ =================
  elif msg_lower == "!магазин":
    return (
        "🛒 *МАГАЗИН ПРЕДМЕТОВ* 🛒\n\n"
        "1. Эффект «Добри :3» — 3 Железные монеты (защита от кошки + 480 XP)\n"
        "2. Эффект «Крутой Крутой» — 1 Золотая монета (удвоение XP на 1 час)\n"
        "3. Эффект «Лудоман» — 5 Медных монет (+удача в лотерее)\n\n"
        "💡 Для покупки напишите: `!купить [номер_товара]`"
    )

  elif msg_lower.startswith("!трейд"):
    parts = msg_lower.split()
    if len(parts) == 2 and parts[1].isdigit():
      val = int(parts[1])
      if val % 5 != 0 or user["xp"] < val:
        return "❌ Ошибка! Число должно быть кратно 5 и хватать XP."
      user["xp"] -= val
      user["coins"]["bronze"] += val // 5
      return f"✅ Обменяно {val} XP на {val // 5} Бронзовых монет!"
    return "🎟 Используйте: `!трейд [число_кратное_5]`"

  elif msg_lower == "!межтрейд":
    return (
        "🌐 *МЕЖСЕРВЕРНЫЙ ТРЕЙД* 🌐\n"
        "Система межсерверного обмена активна!\n"
        "Чтобы выставить лот или принять предложение с другого сервера, используйте:"
        " `!межтрейд создать [монета] [количество] [цена]`"
    )

  # ================= 🐱 КОШКА =================
  elif msg_lower in ["!кошка", "!погладь"]:
    if user["dobri_charges"] > 0:
      user["dobri_charges"] -= 1
      add_xp(user, 480)
      return f"😻 «Добри :3» подарила вам *+480 XP*! Осталось зарядов: {user['dobri_charges']}"
    add_xp(user, 10)
    return "😾 Кошка слегка помурчала и дала +10 XP!"

  # ================= ⚔️ ДУЭЛИ =================
  elif msg_lower.startswith("!дуэль"):
    parts = msg_lower.split()
    if len(parts) >= 3 and parts[2].isdigit():
      bet = int(parts[2])
      target_tag = parts[1]
      if user["xp"] < bet:
        return "❌ У вас недостаточно XP для такой ставки!"
      active_duels[target_tag] = {
          "initiator_id": user_id,
          "initiator_name": user_name,
          "target_tag": target_tag,
          "bet": bet,
      }
      return (
          f"⚔️ @{user_name} вызывает {target_tag} на дуэль на *{bet} XP*!\n"
          f"Напишите `!принять` или `!отказ`."
      )

  elif msg_lower == "!принять":
    found_key = None
    for tag, d in active_duels.items():
      if tag in msg_lower or tag.replace("@", "") in user_id:
        found_key = tag
        break
    if not found_key and active_duels:
      found_key = list(active_duels.keys())[0]

    if found_key:
      d = active_duels.pop(found_key)
      bet = d["bet"]
      init_user = get_user(d["initiator_id"])

      if user["xp"] < bet or init_user["xp"] < bet:
        return "❌ У одного из участников не хватает XP!"

      winner = random.choice([user_id, d["initiator_id"]])
      loser = d["initiator_id"] if winner == user_id else user_id
      get_user(winner)["xp"] += bet
      get_user(loser)["xp"] -= bet
      win_name = user_name if winner == user_id else d["initiator_name"]
      return f"💥 ДУЭЛЬ СОСТОЯЛАСЬ! Победил @{win_name} и забирает *+{bet} XP*!"

  elif msg_lower == "!отказ" and active_duels:
    active_duels.clear()
    return "🛡 Дуэль была отклонена!"

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

  # ================= 📜 ВИКТОРИНА (20 СЛОВ) =================
  elif msg_lower == "!викторина":
    q_data = random.choice(RUSSIAN_QUIZ)
    active_quiz[chat_id] = q_data
    return f"📚 *Викторина по русскому языку:*\n{q_data['q']}\n\nОтветьте с помощью: `!ответ [слово]`"

  elif msg_lower.startswith("!ответ"):
    if chat_id in active_quiz:
      ans = msg_lower.replace("!ответ", "").strip()
      correct = active_quiz[chat_id]["a"].lower()
      if ans == correct:
        del active_quiz[chat_id]
        add_xp(user, 150)
        return (
            f"🎉 Правильно, @{user_name}! Это действительно «{correct}»."
            " Получено *+150 XP*!"
        )
      else:
        return "❌ Неверно, попробуйте ещё раз!"

  # ================= ❌⭕ КРЕСТИКИ-НОЛИКИ =================
  elif msg_lower.startswith("!крестики"):
    parts = msg_lower.split()
    if len(parts) >= 2:
      opponent = parts[1]
      active_tictactoe[chat_id] = {
          "p1": user_id,
          "p2": opponent,
          "p1_name": user_name,
          "p2_name": opponent,
          "turn": user_id,
          "board": [" "] * 9,
      }
      return (
          f"🎮 Игра начинается! @{user_name} (❌) против {opponent} (⭕)!\n"
          f"{render_board([' '] * 9)}\nХодит @{user_name}: напишите `!ход"
          " [1-9]`"
      )

  elif msg_lower.startswith("!ход"):
    if chat_id in active_tictactoe:
      game = active_tictactoe[chat_id]
      if user_id != game["turn"]:
        return "⏳ Сейчас не ваш ход!"
      parts = msg_lower.split()
      if len(parts) == 2 and parts[1].isdigit():
        pos = int(parts[1]) - 1
        if 0 <= pos <= 8 and game["board"][pos] == " ":
          symbol = "X" if user_id == game["p1"] else "O"
          game["board"][pos] = symbol

          if check_win(game["board"], symbol):
            board_img = render_board(game["board"])
            del active_tictactoe[chat_id]
            add_xp(user, 200)
            return (
                f"🎉 ПОБЕДА! @{user_name} выиграл!\n{board_img}\nПолучено *+200"
                " XP*!"
            )

          if " " not in game["board"]:
            board_img = render_board(game["board"])
            del active_tictactoe[chat_id]
            return f"🤝 НИЧЬЯ!\n{board_img}"

          game["turn"] = game["p2"] if user_id == game["p1"] else game["p1"]
          next_name = (
              game["p2_name"] if user_id == game["p1"] else game["p1_name"]
          )
          return (
              f"Ход сделан!\n{render_board(game['board'])}\nСледующий ход:"
              f" {next_name}"
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
            
