import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.chat_action import ChatActionSender

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import init_db, add_or_update_user, mark_reached_end, export_to_excel, get_all_users

# --- Настройка логов ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),              # лог в консоль (для systemd)
        logging.FileHandler("bot.log")        # лог в файл (опционально)
    ]
)

# --- Конфигурация ---
API_TOKEN = os.getenv("BOT_TOKEN")  # безопаснее, чем писать токен прямо в код
ADMIN_ID = 7998228068                # твой Telegram ID

if not API_TOKEN:
    raise ValueError("❌ Не найден токен! Установи переменную окружения BOT_TOKEN.")

# --- Инициализация бота ---
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# --- FSM для рассылки ---
class PushStates(StatesGroup):
    waiting_for_content = State()

# --- Слайды ---
SLIDES = [
    {
        "photo": "photos/foto.jpg",
        "text": '''Guten Tag! Mein Name ist Christoph, und ich freue mich sehr, Sie kennenzulernen. 
Ich bin ein Trader mit umfangreicher Erfahrung 📊 und habe derzeit viele vielversprechende Projekte 🚀
Ich freue mich, dass gerade Sie hier auf meinem Kanal gelandet sind! 
Vielen Kunden, die finanzielle Probleme hatten, konnte ich bereits helfen 💪, sie zu lösen und so ihr Traumziel zu erreichen 🌟
Ich biete keine übernatürlichen Investitionen an ✋ – ich biete nur eine gute, solide Einkommensmöglichkeit 💼💰

Wenn Sie interessiert sind, freue ich mich sehr, Sie in meinem Telegram-Kanal zu begrüßen. 
Ich habe viele zufriedene Kunden und zahlreiche positive Bewertungen ⭐️
Sie können also ganz sicher sein – ich schätze jeden einzelnen meiner Kunden sehr.
Und wenn Sie mehr erfahren möchten, schreiben Sie mir einfach eine private Nachricht ✉️
Ich erzähle Ihnen gerne mehr über meine Arbeitsmethode 💼 und über die Perspektiven dieses Projekts 🚀

🔗Link zur Gruppe:  https://t.me/trading_germany

✉️Mir eine private Nachricht schreiben:  @christoph_crypto''',
        "button_text": "🔗 Weiter",
        "url": "https://t.me/trading_germany"
    }
]

# --- /start ---
@dp.message(Command("start"))
async def start(message: types.Message):
    logging.info(f"/start от пользователя {message.from_user.id} @{message.from_user.username}")
    add_or_update_user(message.from_user)
    await send_slide(message.chat.id)
    mark_reached_end(message.from_user.id)
    logging.info(f"Пользователь {message.from_user.id} дошёл до конца слайдов")

# --- Отправка слайда ---
async def send_slide(chat_id):
    slide = SLIDES[0]
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=slide["button_text"], url=slide["url"])]]
    )

    async with ChatActionSender.upload_photo(bot=bot, chat_id=chat_id):
        await bot.send_photo(
            chat_id,
            FSInputFile(slide["photo"]),
            caption=slide["text"],
            reply_markup=markup
        )
    logging.info(f"Отправлен слайд пользователю {chat_id}")

# --- /stats ---
@dp.message(Command("stats"))
async def send_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        logging.warning(f"Попытка доступа к /stats от пользователя {message.from_user.id}")
        return await message.answer("⛔ У тебя нет прав.")

    filename = export_to_excel()
    await message.answer_document(FSInputFile(filename), caption="📊 Статистика пользователей")
    os.remove(filename)
    logging.info(f"Статистика отправлена администратору {message.from_user.id}")

# --- /push (FSM) ---
@dp.message(Command("push"))
async def push_start(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ У тебя нет прав.")
    await message.answer("📢 Чтобы сделать рассылку, отправь текст и/или фото.")
    await state.set_state(PushStates.waiting_for_content)
    logging.info(f"Админ {message.from_user.id} начал рассылку")

@dp.message(PushStates.waiting_for_content)
async def push_send(message: types.Message, state: FSMContext):
    text = message.caption if message.caption else message.text or ""
    photo = message.photo[-1].file_id if message.photo else None

    if not text and not photo:
        return await message.answer("❌ Добавь текст или фото для рассылки.")

    users = get_all_users()
    sent = 0
    failed = 0

    logging.info(f"Начата рассылка. Всего пользователей: {len(users)}")

    for user in users:
        try:
            if photo:
                await bot.send_photo(chat_id=user["user_id"], photo=photo, caption=text)
            else:
                await bot.send_message(chat_id=user["user_id"], text=text)
            sent += 1
            await asyncio.sleep(0.05)  # защита от flood limit
        except Exception as e:
            failed += 1
            logging.error(f"Ошибка при отправке пользователю {user['user_id']}: {e}")

    await message.answer(f"✅ Рассылка завершена!\n📤 Отправлено: {sent}\n❌ Ошибок: {failed}")
    logging.info(f"Рассылка завершена. Отправлено: {sent}, Ошибок: {failed}")
    await state.clear()

# --- Запуск ---
async def main():
    init_db()
    logging.info("База данных инициализирована. Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
