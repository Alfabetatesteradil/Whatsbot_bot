from datetime import datetime, timedelta
import random
from flask import Flask, jsonify, request

app = Flask(__name__)

BOT_START_TIME = datetime.now()

users = {}

RANKS = [
    ("Дерево", 50),
    ("Уголь", 100),
    ("Железо", 150),
    ("Золото", 200),
    ("Алмаз", 500),
]


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
    return "🧀 КУСЬ! Внезапно кошка откусила кусочек от Золотой монеты! (Своих не едят, но тут не удержалась!)"

  if coins["diamond"] > 0:
    return "🦷 КРАК! Кошка попыталась грызть Алмаз, чуть не сломала зуб и удрала!"

  return "😾 Кошка цапнула вас! А монет-то нет, нищий!"


def process_command(user_id, user_name, msg):
  msg_clean = msg.strip()
  msg_lower = msg_clean.lower()
  user = get_user(user_id)

  if msg_lower == "!меню":
    return (
        "📜 *МЕНЮ КОМАНД* 📜\n"
        "!пинг — аптайм и задержка\n"
        "!ранг я — ваш профиль и монеты\n"
        "!трейд [XP] — обмен 5 XP на 1 Бронзу\n"
        "!кошка — погладить Золотую Кошку\n"
        "!лотерея [1/2/3] — испытать удачу"
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

    # Подготовка строк эффектов без ошибок синтаксиса
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
    if user["dobri_charges"] > 0:
      user["dobri_charges"] -= 1
      add_xp(user, 20)
      return (
          "😻 Кошка «Добри :3» не стала кусать вас! (+20 XP). Зарядов"
          f" осталось: {user['dobri_charges']}"
      )

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
        return "❌ Для Коней нужно 200 XP!"
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
        user["restarts"] += 1
        return (
            "💎 *АЛМАЗНЫЙ ВЫИГРЫШ!* Вы мгновенно получили *+1 ПЕРЕРОЖДЕНИЕ*! 🔥"
        )
      else:
        user["restarts"] += 2
        return (
            "🎰 💰 *MEGA JACKPOT!!!* Вы выиграли *+2 ПЕРЕРОЖДЕНИЯ ЗА РАЗ!* 💰🎰"
        )

  return None


@app.route("/webhook", methods=["POST"])
def webhook():
  data = request.json
  try:
    sender_id = data.get("sender_id")
    sender_name = data.get("sender_name", "Игрок")
    text = data.get("text", "")

    reply = process_command(sender_id, sender_name, text)
    if reply:
      return jsonify({"status": "success", "reply": reply})
  except Exception as e:
    return jsonify({"status": "error", "message": str(e)})

  return jsonify({"status": "ignored"})


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)
      
