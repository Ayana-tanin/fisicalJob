import re
import asyncio
import logging

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.enums import ChatType, ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import update

from db_connection import (
    insert_user,
    save_vacancy,
    get_user_vacancies,
    delete_vacancy_by_id,
    get_session
)
from models import Job
from config import CHANNEL_ID, CHANNEL_URL, ADMINS

logger = logging.getLogger(__name__)
router = Router()

class VacancyForm(StatesGroup):
    all_info = State()

# Шаблоны полей и телефонный формат
TEMPLATE = {
    "address": r"^📍\s*Адрес:\s*(.+)$",
    "title":   r"^📝\s*Задача:\s*(.+)$",
    "payment": r"^💵\s*Оплата:\s*(.+)$",
    "contact": r"^☎️\s*Контакт:\s*(.+)$",
    "extra":   r"^📌\s*Примечание:\s*(.*)$",
}
PHONE_RE = re.compile(r"^\+?\d[\d\s\-]{7,}\d$")
kb_menu = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Выложить вакансию", callback_data="create")],
        [InlineKeyboardButton(text="📋 Мои вакансии", callback_data="list")],
        [InlineKeyboardButton(text="🌐 Канал", url=CHANNEL_URL)]
    ])

# /start — только в личных сообщениях
@router.message(
    CommandStart(),
    F.chat.type == ChatType.PRIVATE
)
async def cmd_start(msg: Message):
    await insert_user(msg.from_user.id, msg.from_user.username or "")
    await msg.answer(
        "👋 Привет! Я помогу опубликовать вашу вакансию. Выберите действие:",
        reply_markup=kb_menu
    )

# Подготовка шаблона вакансии
@router.callback_query(F.data == "create")
async def prepare_vacancy(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer(
        "📄 Отправьте вакансию по шаблону:\n\n"
        "📍 Адрес: Бишкек, ул. Ленина 1\n"
        "📝 Задача: Курьер на 2 часа\n"
        "💵 Оплата: 500 сом\n"
        "☎️ Контакт: +996501234567\n"
        "📌 Примечание: (необязательно)",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(VacancyForm.all_info)

# Обработка формы и публикация вакансии
@router.message(VacancyForm.all_info)
async def process_vacancy(msg: Message, state: FSMContext, bot: Bot):
    data = {}
    for line in msg.text.splitlines():
        for key, pat in TEMPLATE.items():
            m = re.match(pat, line.strip())
            if m:
                data[key] = m.group(1).strip()
    # Валидация
    for fld in ("address", "title", "payment", "contact"):
        if fld not in data:
            await msg.reply(f"❌ Поле '{fld}' не найдено. Повторите по шаблону.")
            return
    if not PHONE_RE.match(data["contact"]):
        await msg.reply("❌ Неверный формат номера. Пример: +996501234567")
        return
    # Сохранение
    job = await save_vacancy(msg.from_user.id, data)
    if job is None:
        await msg.reply("❌ У вас нет прав или внутренняя ошибка.")
        await state.clear()
        return
    if job == 0:
        await msg.reply("🔔 Дневной лимит вакансий исчерпан.")
        await state.clear()
        return
    # URL для отклика
    if msg.from_user.username:
        reply_url = f"https://t.me/{msg.from_user.username}"
    else:
        reply_url = f"tg://user?id={msg.from_user.id}"
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Откликнуться", url=reply_url)]
    ])
    posted = await bot.send_message(
        chat_id=CHANNEL_ID,
        text=(f"✨ <b>Вакансия: {data['title']}</b> ✨\n"
            f"📍Адрес: {data['address']}\n"
            f"💵Оплата: {data['payment']}\n"
            f"☎️Контакт: {data['contact']}"
            + (f"\n📌Примечание: {data['extra']}" if data.get("extra") else "")
        ),
        reply_markup=markup,
        parse_mode=ParseMode.HTML
    )
    # Сохраняем message_id для последующего удаления
    async with get_session() as session:
        await session.execute(
            update(Job).where(Job.id == job.id).values(message_id=posted.message_id)
        )
        await session.commit()
    await msg.answer("✅ Ваша вакансия опубликована. \n\n Для удаления вызовите мои вакансии",
                     reply_markup=kb_menu)
    await state.clear()

# Просмотр вакансий с заголовками
@router.callback_query(F.data == "list")
async def list_vacancies(call: CallbackQuery):
    await call.answer()
    vacs = await get_user_vacancies(call.from_user.id)
    if not vacs:
        return await call.message.answer("У вас пока нет вакансий.")

    buttons = []
    import json
    for job in vacs:
        # показываем только активные
        if not job.message_id:
            continue
        info = job.all_info
        # извлекаем заголовок
        if isinstance(info, dict):
            title = info.get('title', f"#{job.id}")
        else:
            try:
                info_dict = json.loads(info)
                title = info_dict.get('title', f"#{job.id}")
            except:
                title = f"#{job.id}"
        buttons.append([
            InlineKeyboardButton(
                text=f"❌ Удалить: {title}",
                callback_data=f"del:{job.id}"
            )
        ])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await call.message.answer("Ваши вакансии:", reply_markup=kb)

# Удаление вакансии из канала и БД
@router.callback_query(lambda c: c.data and c.data.startswith("del:"))
async def delete_vacancy_handler(call: CallbackQuery, bot: Bot):
    await call.answer()
    vid = int(call.data.split(":",1)[1])
    # получаем и проверяем права на удаление
    vacs = await get_user_vacancies(call.from_user.id)
    job = next((j for j in vacs if j.id == vid), None)
    if not job:
        return await call.answer("Вакансия не найдена или вы не автор.", show_alert=True)
    # удаляем из канала
    if job.message_id:
        try:
            await bot.delete_message(chat_id=CHANNEL_ID, message_id=job.message_id)
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение в канале #{vid}: {e}")
    # удаляем из БД
    ok = await delete_vacancy_by_id(vid)
    if ok:
        await call.answer("✅ Вакансия удалена.", show_alert=True)
        # обновляем клавиатуру, убираем кнопку
        new_buttons = [row for row in call.message.reply_markup.inline_keyboard if row[0].callback_data != f"del:{vid}"]
        await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=new_buttons))
    else:
        await call.answer("❌ Ошибка при удалении.", show_alert=True)

# Следующий хэндлер... вакансии из канала и из базы
@router.callback_query(lambda c: c.data and c.data.startswith("del:"))
async def delete_vacancy_handler(call: CallbackQuery, bot: Bot):
    await call.answer()
    vid = int(call.data.split(":",1)[1])
    # получаем вакансию
    job = await get_user_vacancies(call.from_user.id)
    job = next((j for j in job if j.id == vid), None)
    if not job:
        return await call.answer("Вакансия не найдена.", show_alert=True)
    # удаляем из канала
    if job.message_id:
        try:
            await bot.delete_message(chat_id=CHANNEL_ID, message_id=job.message_id)
        except Exception as e:
            logger.error(f"Не удалось удалить сообщение в канале #{vid}: {e}")
    # удаляем из базы
    ok = await delete_vacancy_by_id(vid)
    if ok:
        await call.answer("✅ Вакансия удалена.", show_alert=True)
        # обновляем клавиатуру — убираем кнопку удалённой вакансии
        new_buttons = [row for row in call.message.reply_markup.inline_keyboard if not row[0].callback_data == f"del:{vid}"]
        await call.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=new_buttons))
    else:
        await call.answer("❌ Ошибка при удалении.", show_alert=True)

# Блокировка сообщений в группах
@router.message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
async def block_non_admins(message: Message):
    try:
        user_id = message.from_user.id if message.from_user else None
        if user_id not in ADMINS:
            logger.info(f"Удаляем сообщение от {user_id} в чате {message.chat.id}")
            await message.delete()
            bot_user = await message.bot.get_me()
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📝 Опубликовать вакансию",
                    url=f"https://t.me/{bot_user.username}"                )]
            ])
            warn = await message.answer(
                "<b>Сообщения в группе не от бота запрещены!</b>\n\n"
                "Чтобы опубликовать вакансию, перейдите в личку бота.",
                reply_markup=kb,
                parse_mode=ParseMode.HTML
            )
            await asyncio.sleep(120)
            try:
                await warn.delete()
            except Exception as e:
                logger.error(f"Не удалось удалить предупреждение: {e}")
    except Exception as e:
        logger.error(f"Ошибка в block_non_admins: {e}")
