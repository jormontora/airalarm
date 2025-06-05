import asyncio
from datetime import datetime, time as dtime_time
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import json
import os

# Токени та імена файлів
TELEGRAM_BOT_TOKEN = "7679275286:AAE5kZDo21Cp78Gmp3aZSo7MMRWLGXAUx-Y"
ALERTS_API_TOKEN = "e81339dd1aba257544385e1cb0aadf9d08e9223bab2203"
CHAT_IDS_FILE = "chat_ids.json"
ALERTS_DATA_FILE = "alerts_data.json"

# Список усіх областей України
OBLASTS = [
    "Вінницька область", "Волинська область", "Дніпропетровська область", "Донецька область",
    "Житомирська область", "Закарпатська область", "Запорізька область", "Івано-Франківська область",
    "Київська область", "Кіровоградська область", "Луганська область", "Львівська область",
    "Миколаївська область", "Одеська область", "Полтавська область", "Рівненська область",
    "Сумська область", "Тернопільська область", "Харківська область", "Херсонська область",
    "Хмельницька область", "Черкаська область", "Чернівецька область", "Чернігівська область"
]

# UID для всіх областей та міст зі спеціальним статусом
REGION_UIDS = {
    "Хмельницька область": 3,
    "Вінницька область": 4,
    "Рівненська область": 5,
    "Волинська область": 8,
    "Дніпропетровська область": 9,
    "Житомирська область": 10,
    "Закарпатська область": 11,
    "Запорізька область": 12,
    "Івано-Франківська область": 13,
    "Київська область": 14,
    "Кіровоградська область": 15,
    "Луганська область": 16,
    "Миколаївська область": 17,
    "Одеська область": 18,
    "Полтавська область": 19,
    "Сумська область": 20,
    "Тернопільська область": 21,
    "Харківська область": 22,
    "Херсонська область": 23,
    "Черкаська область": 24,
    "Чернігівська область": 25,
    "Чернівецька область": 26,
    "Львівська область": 27,
    "Донецька область": 28,
    "Автономна Республіка Крим": 29,
    "м. Севастополь": 30,
    "м. Київ": 31,
}

# ID адмінів для доступу до логів
ADMIN_IDS = {752113604}  # Вкажіть свій Telegram user_id

# Перевіряємо, чи зараз ніч
def is_night():
    now = datetime.now().time()
    # Використовуємо dtime_time замість time
    return now >= dtime_time(23, 0) or now <= dtime_time(6, 0)

# Отримуємо активні тривоги з API
def get_active_alerts():
    url = f"https://api.alerts.in.ua/v1/alerts/active.json?token={ALERTS_API_TOKEN}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"Не вдалося отримати дані з API: {exc}")
        return []

# Зберігаємо тривоги у файл
def save_alerts_data(alerts):
    try:
        with open(ALERTS_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"Не вдалося зберегти дані: {exc}")

# Перевіряємо, чи тривога по всій Україні
def check_alert_all_ukraine(alerts):
    oblasts = set(
        alert["location_title"]
        for alert in alerts
        if alert.get("alert_type") in ("air_raid", "artillery_shelling") and alert.get("location_type") == "oblast"
    )
    return set(OBLASTS).issubset(oblasts)

# Читаємо chat_id з файлу
def load_chat_ids():
    if os.path.exists(CHAT_IDS_FILE):
        try:
            with open(CHAT_IDS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

# Зберігаємо chat_id у файл
def save_chat_ids(chat_ids):
    try:
        with open(CHAT_IDS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(chat_ids), f)
    except Exception as exc:
        print(f"Не вдалося зберегти chat_ids: {exc}")

# Додаємо chat_id у підписку
async def register_chat(chat_id):
    ids = load_chat_ids()
    ids.add(chat_id)
    save_chat_ids(ids)

# Видаляємо chat_id з підписки
async def unregister_chat(chat_id):
    ids = load_chat_ids()
    if chat_id in ids:
        ids.remove(chat_id)
        save_chat_ids(ids)

# Розсилаємо повідомлення всім підписаним
async def notify_all(bot, text):
    ids = load_chat_ids()
    for chat_id in ids:
        try:
            await bot.send_message(chat_id, text)
        except Exception as exc:
            print(f"Не вдалося надіслати повідомлення {chat_id}: {exc}")

# Основний цикл перевірки тривог і розсилки
async def alert_watcher(bot):
    notified = False
    while True:
        try:
            alerts = get_active_alerts()
            save_alerts_data(alerts)
            if is_night() and check_alert_all_ukraine(alerts):
                if not notified:
                    alert = next(
                        (a for a in alerts if a.get("alert_type") in ("air_raid", "artillery_shelling") and a.get("location_type") == "oblast"),
                        None
                    )
                    if alert:
                        alert_type = alert.get("alert_type", "невідомо")
                        notes = alert.get("notes", "")
                        msg = (
                            "УВАГА! Тривога по всій Україні!\n"
                            f"Тип тривоги: {alert_type}\n"
                            f"Нотатки: {notes}"
                        )
                    else:
                        msg = "УВАГА! Тривога по всій Україні!"
                    await notify_all(bot, msg)
                    notified = True
            else:
                notified = False
        except Exception as exc:
            print(f"Помилка в alert_watcher: {exc}")
        await asyncio.sleep(60)

# Обробка /start — підписка на сповіщення
async def on_start(message: types.Message):
    await register_chat(message.chat.id)
    await message.reply("Ви підписані на сповіщення про тривоги по всій Україні вночі.")

# Обробка /stop — відписка від сповіщень
async def on_stop(message: types.Message):
    await unregister_chat(message.chat.id)
    await message.reply("Ви відписані від сповіщень.")

# Додаємо групу у підписку, якщо додали бота
async def on_new_chat_member(message: types.Message):
    await register_chat(message.chat.id)
    await message.reply("Групу підписано на сповіщення про тривоги по всій Україні вночі.")

# Адмін-команда /log — показати останні 3 тривоги з історії API (через прямий запит)
async def on_log(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("Недостатньо прав.")
        return

    KYIV_UID = 31
    url = f"https://api.alerts.in.ua/v1/regions/{KYIV_UID}/alerts/month_ago.json?token={ALERTS_API_TOKEN}"
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        alerts = data.get("alerts", [])
    except Exception as exc:
        await message.reply(f"Не вдалося отримати історію тривог: {exc}")
        return

    # Повертаємо всі типи тривог (без фільтрації)
    last3 = sorted(alerts, key=lambda a: a.get("started_at", ""), reverse=True)[:3]
    if not last3:
        await message.reply("Немає тривог по Києву.")
        return

    msg = "Три останні тривоги:"
    for a in last3:
        started = a.get("started_at", "невідомо")
        finished = a.get("finished_at", "ще триває")
        alert_type = a.get("alert_type", "невідомо")
        notes = a.get("notes", "")
        try:
            if finished and finished != "ще триває" and started != "невідомо":
                dt_start = datetime.fromisoformat(started.replace("Z", "+00:00"))
                dt_finish = datetime.fromisoformat(finished.replace("Z", "+00:00"))
                duration = str(dt_finish - dt_start)
            else:
                duration = "ще триває"
        except Exception:
            duration = "невідомо"
        msg += (
            f"\n\nПочаток: {started}"
            f"\nКінець: {finished}"
            f"\nТривалість: {duration}"
            f"\nТип: {alert_type}"
            f"\nНотатки: {notes}"
        )
    await message.reply(msg)

# Реєструємо всі хендлери для бота
def setup_handlers(dp: Dispatcher):
    dp.message.register(on_start, Command("start"))
    dp.message.register(on_stop, Command("stop"))
    dp.message.register(on_log, Command("log"))
    dp.message.register(on_new_chat_member, lambda msg: msg.new_chat_members is not None)

# Запускаємо бота
async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    setup_handlers(dp)
    asyncio.create_task(alert_watcher(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())