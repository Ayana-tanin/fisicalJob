import asyncio
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8136864493:AAHVli5_gl0LCDrvCdsMhgXiq3irmBTZQ0Y"
CHANNEL_ID = -1002586848325
ADMIN_ID = 5320545212
ADMINS = [5320545212, 5402160054]

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def delete_message(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.delete()
        msg = await message.answer(
            "Чтобы разместить вакансию, перейдите к боту.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Перейти к боту", url="https://t.me/fisicalJob_bot")]
            ])
        )
        await asyncio.sleep(100)
        await msg.delete()

def start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Разместить задачу", callback_data="show_admin")],
        [InlineKeyboardButton(text="Найти подработку", url="https://t.me/tezJumush")]
    ])

@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Привет! Я — бот платформы Tez Jumush.", reply_markup=start_keyboard())


@router.callback_query(F.data == "show_admin")
async def show_admin(cb: types.CallbackQuery):
    await cb.message.answer(
        "Бот временно в ремонте. Свяжитесь с администратором:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Написать администратору", url=f"tg://user?id={ADMIN_ID}")]
        ])
    )
    print("Получен callback:", cb.data)
    await cb.answer()

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен вручную.")
