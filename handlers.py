import asyncio
import logging

from aiogram import Router, Bot, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.enums.chat_type import ChatType
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import ADMINS, CHANNEL_ID, CHANNEL_URL, ADMIN_USERNAME
from db_connection import (
    insert_user, save_vacancy, get_user_vacancies, delete_vacancy_by_id
)

logger = logging.getLogger(__name__)
router = Router()

class VacancyForm(StatesGroup):
    all_info = State()

async def send_job_actions(message: Message, job_id: int):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Удалить вакансию", callback_data=f"action_delete_{job_id}")],
            [InlineKeyboardButton(text="🔄 Опубликовать ещё", callback_data=f"create_vacancy")],
            [InlineKeyboardButton(text="👤 Связаться с админом", callback_data="action_contact_admin")],
        ]
    )
    await message.answer("Выберите действие:", reply_markup=kb)

@router.message(
    F.chat.type != ChatType.PRIVATE,      # любые групповые/канальные чаты
    F.text & ~F.text.startswith("/")      # все тексты, не команды
)
async def block_non_admins(message: Message):
    if message.from_user.id not in ADMINS:
        await message.delete()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перейти к боту", url=CHANNEL_URL)]
        ])
        warn = await message.answer(
            "✉️ Писать здесь запрещено. Перейдите в личку бота:",
            reply_markup=kb
        )
        await asyncio.sleep(60)
        await warn.delete()
@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def start_handler(message: Message):
    await insert_user(message.from_user.id, message.from_user.username or "")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✉️ Выложить вакансию", callback_data="create_vacancy"
                ),
                InlineKeyboardButton(text="📋 Посмотреть вакансии", url=CHANNEL_URL
                )
            ]
        ]
    )

    await message.answer(
        "Привет!\n\nЯ помогу опубликовать вашу вакансию.\nВыберите действие:",
        reply_markup=kb,
    )

@router.callback_query(F.data == "create_vacancy")
async def show_template(call: CallbackQuery, state: FSMContext):
    await call.answer()
    template = (
        "Отправьте одним сообщением по шаблону:\n\n"
        "📍 <b>Адрес:</b> Москва, Сокольники\n"
        "📝 <b>Задача:</b> Требуется грузчик на 3 часа\n"
        "💵 <b>Оплата:</b> 1500 ₽\n"
        "☎️ <b>Контакт:</b> +7 999 123-45-67\n"
        "📌 <b>Примечание:</b> Нужен опыт работы\n\n\n"
        "<b>Скопируйте, замените поля и отправьте.</b>"
    )
    await call.message.answer(template, parse_mode=ParseMode.HTML)
    await state.set_state(VacancyForm.all_info)

@router.message(VacancyForm.all_info)
async def process_vacancy(message: Message, state: FSMContext, bot: Bot):
    # 1) Собираем данные из шаблона
    data: dict[str, str] = {}
    for line in message.text.splitlines():
        if ":" not in line:
            continue
        key, val = map(str.strip, line.split(":", 1))
        if key.startswith("📍"):
            data["address"] = val
        elif key.startswith("📝"):
            data["title"] = val
        elif key.startswith("💵"):
            data["payment"] = val
        elif key.startswith("☎️"):
            data["contact"] = val
        elif key.startswith("📌"):
            data["extra"] = val

    # 2) Формируем текст вакансии
    vac_text = (
        f"📍 <b>Адрес:</b> {data.get('address','—')}\n"
        f"📝 <b>Задача:</b> {data.get('title','—')}\n"
        f"💵 <b>Оплата:</b> {data.get('payment','—')}\n"
        f"☎️ <b>Контакт:</b> {data.get('contact','—')}\n"
    )
    if extra := data.get("extra"):
        vac_text += f"📌 <b>Примечание:</b> {extra}\n"

    # 3) Опубликовать в канале сразу с кнопкой-ссылкой
    publisher_id = message.from_user.id
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Откликнуться",
                    url=f"tg://user?id={publisher_id}"
                )
            ]
        ]
    )
    channel_msg = await bot.send_message(
        chat_id=CHANNEL_ID,
        text=vac_text,
        parse_mode=ParseMode.HTML,
        reply_markup=kb
    )

    # 4) Сохранить в БД и получить job_id
    job_id = await save_vacancy(
        user_id=publisher_id,
        message_id=channel_msg.message_id,
        data=data
    )

    # 5) Ответ автору + панель действий
    await message.answer(
        f"✅ Вакансия опубликована!\n\n"
        f"🆔 ID вакансии: <b>{job_id}</b>",
        parse_mode=ParseMode.HTML
    )
    await send_job_actions(message, job_id)
    await state.clear()


@router.callback_query(F.data.startswith("reply_"))
async def reply_publisher(call: CallbackQuery, bot: Bot):
    await call.answer()

    # callback_data = "reply_<job_id>_<publisher_tg>"
    _, _, publisher_tg_str = call.data.split("_", 2)
    publisher_id = int(publisher_tg_str)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📨 Написать работодателю",
                    url=f"tg://user?id={publisher_id}"
                )
            ]
        ]
    )

    # Обновляем именно то сообщение в канале, где была «Откликнуться»
    await bot.edit_message_reply_markup(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=kb
    )

@router.callback_query(F.data.startswith("action_delete_"))
async def action_delete(call: CallbackQuery, bot: Bot):
    await call.answer()
    job_id = int(call.data.rsplit("_", 1)[1])
    msg_id = await delete_vacancy_by_id(job_id)
    if msg_id:
        await bot.delete_message(CHANNEL_ID, msg_id)
        await call.message.edit_text(f"❌ Вакансия {job_id} удалена.")
    else:
        await call.message.edit_text(f"Вакансия {job_id} не найдена.")

from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

@router.callback_query(F.data == "action_contact_admin")
async def action_contact_admin(call: CallbackQuery):
    await call.answer()
    await call.message.answer(f"👤 Связаться с администратором: @{ADMIN_USERNAME}")

async def send_job_actions(message: Message, job_id: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❌ Удалить вакансию",
                callback_data=f"action_delete_{job_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="Опубликовать вакансию",
                callback_data="create_vacancy"
            )
        ],
        [
            InlineKeyboardButton(
                text="👤 Связаться с админом",
                callback_data="action_contact_admin"
            )
        ],
    ])
    await message.answer(
        "Выберите действие:",
        reply_markup=kb
    )

