from datetime import datetime, timedelta
import os
import random
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# ==========================================
# 🔑 ДАННЫЕ ИЗ GREEN API:
ID_INSTANCE = "71072260715"
API_TOKEN = "38c0a3003c22469cad11461cd9f72335793bd5303fe8450baf"
# ==========================================

BOT_START_TIME = datetime.now()
users = {}

RANKS = [
    ("Дерево", 50),
    ("Уголь", 100),
    ("Железо", 150),
    ("Золото", 200),
    ("Алмаз", 500),
]


def send_whatsapp_message(chat_id, text):
  """Функция отправки сообщения в WhatsApp чат/группу"""
  url = f"https://api.green-api.com/waInstance{ID_INSTANCE}/sendMessage/{API_TOKEN}"
  payload = {"chatId": chat_id, "message": text}
  headers = {"Content-Type": "application/json"}

  try:
    res = requests.post(url, json=payload, headers=headers, timeout=5)
    print("Ответ от Green API:", res.status_code, res.text, flush=True)
  except Exception as e:
    print(f"Ошибка при отправке в WhatsApp: {e}", flush=True)


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


def bite_coins(user):
  coins = user["coins"]

  if coins["obsidian"] > 0:
    return "😱 Кошка увидела Обсидиан, испугалась и отскочила! Вы в безопасности!"

  for c_type, c_name in [
      ("bronze", "Бронзовую"),
      ("copper", "Медную"),
      ("iron", "Железную"),
  ]:
    if coins[c_type] > 0:
      coins[c_type] -= 1
      return f"😾 КУСЬ! Кошка с хрустом съела вашу {c_name} монету! 🪙"

  if coins["gold"] > 0 and random.random() < 0.01:
    coins["gold"] -= 1
    return "🧀 КУСЬ! Внезапно кошка откусила кусочек от Золотой монеты!"

  if coins["diamond"] > 0:
    return "🦷 КРАК! Кошка попыталась грызть Алмаз, чуть не сломала зуб и удрала!"

  return "😾 Кошка цапнула вас! А монет-то нет, нищий!"


def process_command(user_id, user_name, msg):
  msg_clean = msg.strip()
  msg_lower = msg_clean.lower()
  user = get_user(user_id)

  if msg_lower == "!меню":
    return (
        "📜 *МЕНЮ КОМАНД* 📜\n!пинг — аптайм и задержка\n!ранг — ваш профиль и"
        " монеты\n!трейд [XP] — обмен 5 XP на 1 Бронзу\n!кошка — погладить"
        " Золотую Кошку\n!лотерея [1/2/3] — испытать удачу"
    )

  elif msg_lower == "!пинг":
    return (
        f"🏓 *Понг!*\n⚡ Задержка: 42 мс\n⏱ *Время работы:* {get_uptime()}"
    )

  elif msg_lower.startswith("!ранг"):
    xp = user["xp"]
    restarts = user["restarts"]
    multiplier = restarts + 1

    rank_str = ""
    curr = xp
    for r_name, limit in RANKS:
      max_xp = limit * multiplier
      if curr < max_xp:
        rank_str = f"{r_name} {curr}/{max_xp}"
        break
      curr -= max_xp

    if not rank_str:
      rank_str = f"Алмаз {limit * multiplier}/{limit * multiplier}"

    ludoman_str = (
        f"{user['ludoman_charges']} шт."
        if user["ludoman_charges"] > 0
        else "Не имеется"
    )

    cool_str = "Не имеется"
    if user["cool_until"] and datetime.now() < user["cool_until"]:
      rem = user["cool_until"] - datetime.now()
      hrs, r = divmod(rem.seconds, 3600)
      mins, _ = divmod(r, 60)
      cool_str = f"{hrs:02d}:{mins:02d} осталось"

    dobri_str = "Имеется" if user["dobri_charges"] > 0 else "Не имеется"
    lucky_str = (
        "Имеется"
        if (user["lucky_until"] and datetime.now() < user["lucky_until"])
        else "Не имеется"
    )

    c = user["coins"]
    coins_str = (
        f"Бронза : {c['bronze']}, Медь : {c['copper']}, Железо : {c['iron']},"
        f" Золото : {c['gold']}, Алмаз : {c['diamond']}"
    )
    if user["has_held_obsidian"] or c["obsidian"] > 0 or c["diamond"] >= 64:
      user["has_held_obsidian"] = True
      coins_str += f", Обсидиан : {c['obsidian']}"

    return (
        f"/// @{user_name}, {rank_str} ///\n"
        f"{user['word1']} ; {user['word2']}\n"
        f"\\\\\\ Перерождения : {restarts} \\\\\\\n"
        f"Эффекты:\n"
        f'"Лудоман" : {ludoman_str}\n'
        f'"Крутой Крутой" : {cool_str}\n'
        f'"Добри :3" : {dobri_str}\n'
        f'"Везучий случай" : {lucky_str}\n'
        f"Монеты : {coins_str}"
    )

  elif msg_lower.startswith("!трейд"):
    parts = msg_lower.split()
    if len(parts) == 2 and parts[1].isdigit():
      val = int(parts[1])
      if val % 5 != 0:
        return "❌ Ваше количество очков не делится на 5!"
      if user["xp"] < val:
        return "❌ Недостаточно очков!"
      user["xp"] -= val
      gained = val // 5
      user["coins"]["bronze"] += gained
      return f"✅ Обменяно {val} XP на {gained} Бронзовых монет!"
    return "🎟 Используйте: `!трейд [число_кратное_5]`"

  elif msg_lower in ["!кошка", "!погладь"]:
    # При наличии заряда "Добри :3" даём ровно 480 XP (заменяет спавн монет)
    if user["dobri_charges"] > 0:
      user["dobri_charges"] -= 1
      add_xp(user, 480)
      return (
          "😻 Кошка «Добри :3» не стала кусать вас и подарила *+480 XP*!"
          f" Зарядов осталось: {user['dobri_charges']}"
      )

    # Обычное поглаживание
    if random.random() < 0.01:
      old_xp = user["xp"]
      add_xp(user, old_xp)
      return (
          "😻 ✨ МУРРР! Золотая кошка удвоила ваши очки! Теперь XP:"
          f" {user['xp']}!"
      )
    else:
      return bite_coins(user)

  elif msg_lower.startswith("!лотерея"):
    parts = msg_lower.split()
    if len(parts) < 2 or parts[1] not in ["1", "2", "3"]:
      return "🎟 Укажите билет: `!лотерея 1`, `!лотерея 2` или `!лотерея 3`"

    ticket = parts[1]
    if ticket == "1":
      if user["xp"] < 15:
        return "❌ Недостаточно XP (нужно 15 XP)!"
      user["xp"] -= 15
      chance = random.randint(1, 100)
      if chance <= 75:
        return "💨 Пусто! Ничего не выпало."
      elif chance <= 97:
        add_xp(user, 100)
        return "🟡 ЗОЛОТО! Вы выиграли +100 XP!"
      else:
        add_xp(user, 200)
        return "💎 АЛМАЗ! Вы выиграли +200 XP!"

    elif ticket == "3":
      if user["xp"] < 200:
        return "❌ Для билета 3 нужно 200 XP!"
      user["xp"] -= 200
      chance = random.randint(1, 100)
      if chance <= 50:
        return "💨 Пусто... Вы потеряли 200 XP!"
      elif chance <= 75:
        add_xp(user, 200)
        return "🔄 Возврат! Ваши 200 XP вернулись."
      elif chance <= 90:
        add_xp(user, 500)
        return "🟡 Золотой выигрыш! +500 XP!"
      elif chance <= 98:
        add_xp(user, 1000)
        return (
            "💎 *АЛМАЗНЫЙ ВЫИГРЫШ!* Вы выиграли крупный куш и получили *+1000"
            " XP*! 🔥"
        )
      else:
        add_xp(user, 3000)
        return (
            "🎰 💰 *MEGA JACKPOT!!!* Вы сорвали мега-куш и получили *+3000 XP*!"
            " 💰🎰"
        )

  return None


@app.route("/webhook", methods=["POST"])
def webhook():
  data = request.get_json(silent=True) or {}

  type_webhook = data.get("typeWebhook")

  allowed_types = [
      "incomingMessageReceived",
      "outgoingMessageReceived",
      "outgoingAPIMessageReceived",
  ]

  if type_webhook in allowed_types:
    message_data = data.get("messageData", {})
    type_message = message_data.get("typeMessage")

    text = ""

    if type_message == "textMessage":
      text = message_data.get("textMessageData", {}).get("textMessage", "")

    elif type_message in ["extendedTextMessage", "quotedMessage"]:
      ext_data = message_data.get("extendedTextMessageData", {})
      text = ext_data.get("text", "")
      if not text:
        text = (
            message_data.get("quotedMessage", {})
            .get("textMessageData", {})
            .get("textMessage", "")
        )

    sender_data = data.get("senderData", {})
    sender_id = sender_data.get("sender") or data.get("chatId", "unknown")
    sender_name = sender_data.get("senderName", "Игрок")

    chat_id = (
        data.get("chatId")
        or sender_data.get("chatId")
        or data.get("keyRemoteJid")
    )

    print(
        f"Распознанный текст: '{text}' от {sender_name} в чате {chat_id}",
        flush=True,
    )

    if text and chat_id:
      reply = process_command(sender_id, sender_name, text)
      if reply:
        send_whatsapp_message(chat_id, reply)

  return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def home():
  return "Бот активен!", 200


if __name__ == "__main__":
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
        
