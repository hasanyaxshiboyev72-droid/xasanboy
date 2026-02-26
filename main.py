import asyncio
import random
import time
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# BOT TOKENINGIZNI KIRITING
TOKEN = "8255989814:AAHpKYY9Deu0Gg3eo_YoqfD_n-45doMMRWs"
bot = Bot(token=TOKEN)
dp = Dispatcher()

user_games = {}
# Foydalanuvchi rekordlarini saqlash uchun (Vaqtincha xotirada)
user_records = {}

EMOJIS = ['🍎', '🍌', '🍇', '🍉', '🍓', '🍒', '🍑', '🥭', '🍍', '🥥', '🥝', '🍅', '🥑', '🍆', '🥕']


def create_board(rows, cols):
    pairs_needed = (rows * cols) // 2
    selected = EMOJIS[:pairs_needed] * 2
    random.shuffle(selected)
    board = []
    idx = 0
    for r in range(rows):
        row = []
        for c in range(cols):
            row.append(selected[idx])
            idx += 1
        board.append(row)
    return board


def get_game_keyboard(user_id):
    game = user_games[user_id]
    builder = InlineKeyboardBuilder()
    for r in range(game['rows']):
        for c in range(game['cols']):
            text = game['board'][r][c] if game['revealed'][r][c] else "❓"
            builder.add(InlineKeyboardButton(text=text, callback_data=f"click_{r}_{c}"))
    builder.adjust(game['cols'])
    return builder.as_markup()


def format_time(seconds):
    """Vaqtni chiroyli ko'rinishga keltirish"""
    m = seconds // 60
    s = seconds % 60
    return f"{m} daqiqa {s} soniya" if m > 0 else f"{s} soniya"


@dp.message(CommandStart())
async def cmd_start(message: Message):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🟢 Oson (4x4)"))
    builder.add(KeyboardButton(text="🟡 O'rtacha (5x4)"))
    builder.add(KeyboardButton(text="🔴 Qiyin (6x5)"))
    builder.add(KeyboardButton(text="🏆 Mening Rekordim"))  # Rekord tugmasi
    builder.adjust(3,1)

    await message.answer(
        "🧠 Brain Game botiga xush kelibsiz!\nQiyinchilik darajasini tanlang yoki rekordingizni ko'ring:",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )


@dp.message(F.text == "🏆 Mening Rekordim")
async def show_record(message: Message):
    user_id = message.from_user.id
    record = user_records.get(user_id)
    if record:
        await message.answer(f"🥇 Sizning eng yaxshi natijangiz: {format_time(record)}")
    else:
        await message.answer("Sizda hali rekord yo'q. O'yinni boshlang!")


@dp.message(F.text.in_(["🟢 Oson (4x4)", "🟡 O'rtacha (5x4)", "🔴 Qiyin (6x5)"]))
async def start_game(message: Message):
    user_id = message.from_user.id
    if "Oson" in message.text:
        rows, cols = 4, 4
    elif "O'rtacha" in message.text:
        rows, cols = 5, 4
    else:
        rows, cols = 6, 5

    user_games[user_id] = {
        'board': create_board(rows, cols),
        'revealed': [[False] * cols for _ in range(rows)],
        'rows': rows,
        'cols': cols,
        'first_click': None,
        'locked': False,
        'matches': 0,
        'start_time': time.time()
    }

    await message.answer("O'yin tayyorlanmoqda... ⏳", reply_markup=ReplyKeyboardRemove())
    markup = get_game_keyboard(user_id)
    await message.answer("O'yin boshlandi! Bir xil emojilarni toping 👇", reply_markup=markup)


@dp.callback_query(F.data.startswith("click_"))
async def process_click(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_games:
        await callback.answer("O'yin eskirgan, boshqatdan boshlang!", show_alert=True)
        return

    game = user_games[user_id]
    if game['locked']:
        await callback.answer()
        return

    _, r, c = callback.data.split('_')
    r, c = int(r), int(c)

    if game['revealed'][r][c]:
        await callback.answer()
        return

    game['revealed'][r][c] = True

    if game['first_click'] is None:
        game['first_click'] = (r, c)
        await callback.message.edit_reply_markup(reply_markup=get_game_keyboard(user_id))
        await callback.answer()
    else:
        game['locked'] = True
        await callback.message.edit_reply_markup(reply_markup=get_game_keyboard(user_id))
        r1, c1 = game['first_click']

        if game['board'][r1][c1] == game['board'][r][c]:
            game['matches'] += 1
            game['first_click'] = None
            game['locked'] = False
            await callback.answer()

            total_pairs = (game['rows'] * game['cols']) // 2
            if game['matches'] == total_pairs:
                end_time = time.time()
                duration = int(end_time - game['start_time'])

                # REKORDNI TEKSHIRISH VA SAQLASH
                current_record = user_records.get(user_id)
                is_new_record = False
                if current_record is None or duration < current_record:
                    user_records[user_id] = duration
                    is_new_record = True

                record_msg = "\n🔥 YANGI REKORD!" if is_new_record else f"\nSizning eng yaxshi natijangiz: {format_time(user_records[user_id])}"

                await callback.message.answer(
                    f"🎉 Qoyilmaqom! Barcha juftliklarni topdingiz!\n⏱️ Vaqt: {format_time(duration)}{record_msg}"
                )

                # Menyuni qaytarish
                builder = ReplyKeyboardBuilder()
                builder.add(KeyboardButton(text="🟢 Oson (4x4)"), KeyboardButton(text="🟡 O'rtacha (5x4)"),
                            KeyboardButton(text="🔴 Qiyin (6x5)"), KeyboardButton(text="🏆 Mening Rekordim"))
                builder.adjust(1)
                await callback.message.answer("Yana o'ynaysizmi?", reply_markup=builder.as_markup(resize_keyboard=True))

                del user_games[user_id]
        else:
            await callback.answer()
            await asyncio.sleep(0.4)
            game['revealed'][r1][c1] = False
            game['revealed'][r][c] = False
            game['first_click'] = None
            game['locked'] = False
            try:
                await callback.message.edit_reply_markup(reply_markup=get_game_keyboard(user_id))
            except Exception:
                pass


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())