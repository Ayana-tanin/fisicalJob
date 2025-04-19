import asyncio
import logging
from collections import defaultdict
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.client.default import DefaultBotProperties

# Константы
TOKEN="7754219638:AAHlCG9dLX-wJ4f6zuaPQDARkB-WtNshv8o"
CHANNEL_ID=-1002423189514
ADMIN_ID=5320545212
DATA_FILE = 'user_data.json'
ADMINS = [5320545212, 5402160054 ]

def start_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Разместить задачу", callback_data="show_admin")],
        [InlineKeyboardButton(text="Найти подработку", url="https://t.me/tezJumush")]
    ])

# /start
@router.message(Command("start"))
async def start(message: types.Message):
    await message.answer("👋 Привет! Я — бот платформы Tez Jumush. Хочешь найти помощника или подработку?", reply_markup=start_keyboard())

# Проверка публикации
@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def delete_message(message: types.Message):
    if message.from_user.id not in ADMINS:
        await message.delete()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перейдите к боту", url="https://t.me/fisicalJob_bot")]
        ])
        msg = await message.answer("Чтобы разместить вакансию, перейдите к боту.", reply_markup=keyboard)
        await asyncio.sleep(100)
        await msg.delete()

# Добавление контактов
@router.callback_query(F.data == "show_admin")
async def show_admin(cb: types.CallbackQuery):
    admin_id = ADMIN_ID  # Admin's Telegram ID
    await cb.message.answer(
        "Бот временно в ремонте, для того чтобы выложить вакансию свяжитесь с администратором. И мы все выложим",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Написать администратору", url=f"tg://user?id={admin_id}")]
        ])
    )
    await cb.answer()

@router.callback_query(F.data == "add_contacts")
async def add_contacts(cb: types.CallbackQuery):
    await cb.message.answer(
        "Чтобы продолжить, добавьте 1 человека в нашу группу, затем вернитесь сюда.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить в группу", url="https://t.me/tezJumush")],
            [InlineKeyboardButton(text="Все готово добавил", callback_data="track_invites")]
        ])
    )
    await cb.answer()