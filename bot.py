import asyncio
import json
import logging
import uuid
from collections import defaultdict
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ChatMemberUpdated
from aiogram.client.default import DefaultBotProperties
from typing import Union

# Константы
TOKEN="7754219638:AAHlCG9dLX-wJ4f6zuaPQDARkB-WtNshv8o"
CHANNEL_ID=-1002423189514
ADMIN_ID=5320545212

# Инициализация
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"), chat_member_updates=True)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

logging.basicConfig(level=logging.INFO)

# Хранилище
user_added_contacts = defaultdict(set)
jobs = {}
json_file = "data.json"

class JobPost(StatesGroup):
    title = State()
    payment = State()
    location = State()
    age = State()
    details = State()
    contact = State()

class AddMembersState(StatesGroup):
    waiting_to_check = State()

@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def delete_message(message: types.Message):
    await message.delete()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить 5 контактов", url="https://t.me/fisicalJob_bot")]
    ])
    msg = await message.answer("Чтобы разместить вакансию, перейдите к боту.", reply_markup=keyboard)
    await asyncio.sleep(60)
    await msg.delete()

@router.message(Command("start"))
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить 5 контактов", callback_data="add_contacts")],
        [InlineKeyboardButton(text="Получить реквизиты", callback_data="get_requisites")],
        [InlineKeyboardButton(text="Help", callback_data="help")]
    ])
    await message.answer("Добрый день! Для публикации вакансии добавьте 5 контактов и вызовите /add_job или оплатите 100 сом.", reply_markup=keyboard)

@router.callback_query(F.data == "add_contacts")
async def add_contacts(cb: types.CallbackQuery):
    await cb.message.answer(
        "Чтобы продолжить, добавьте 5 человек в нашу группу, затем вернитесь сюда.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="➕ Добавить в группу", url="https://t.me/tezJumush")
            ]]
        )
    )
    await cb.answer()

@router.callback_query(F.data == "get_requisites")
async def get_requisites(callback: types.CallbackQuery):
    await bot.send_message(ADMIN_ID, f"Пользователь @{callback.from_user.username} хочет получить реквизиты для оплаты.")
    await callback.message.answer("💳 MBank: 996 551 71 45 47\nПосле оплаты свяжитесь с @ant_anny. Также можем предоставить другие реквизиты.")
    await callback.answer()
    
@router.message(Command("my_jobs"))
async def my_jobs(message: types.Message):
    user_id = message.from_user.id
    user_jobs = [job_id for job_id, job in jobs.items() if job["employer"] == user_id]
    
    if not user_jobs:
        await message.answer("У вас нет опубликованных вакансий.")
        return
    
    job_list = ""
    for job_id in user_jobs:
        job = jobs[job_id]
        job_list += (
            f"📢 Вакансия: {job['title']}\n"
            f"💰 Оплата: {job['payment']}\n"
            f"📍 Местоположение: {job['location']}\n"
            f"👥 Возраст: {job['age']}\n"
            f"ℹ️ Условия: {job['details']}\n"
            f"☎️ Контакты: {job['contact']}\n\n" 
        )
        
    await message.answer(f"Ваши вакансии:\n\n{job_list}")


@router.message(Command("delete_job"))
async def delete_job(message: types.Message):
    user_id = message.from_user.id
    job_list = [job_id for job_id, job in jobs.items() if job["employer"] == user_id]

    if not job_list:
        await message.answer("У вас нет опубликованных вакансий для удаления.")
        return
    
    job_buttons = [
        [InlineKeyboardButton(text=f"Удалить {job_id}", callback_data=f"delete_{job_id}")]
        for job_id in job_list
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=job_buttons)
    
    await message.answer("Выберите вакансию для удаления:", reply_markup=keyboard)

@router.message(Command("delete_job"))
async def delete_job(message: types.Message):
    user_id = message.from_user.id
    job_list = [job_id for job_id, job in jobs.items() if job["employer"] == user_id]

    if not job_list:
        await message.answer("У вас нет опубликованных вакансий для удаления.")
        return
    
    job_buttons = [
        [InlineKeyboardButton(text=f"Удалить {job_id}", callback_data=f"delete_{job_id}")]
        for job_id in job_list
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=job_buttons)
    
    await message.answer("Выберите вакансию для удаления:", reply_markup=keyboard)

@router.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    text = (
        "Данный бот публикует ваши вакансии в чат и уведомляет о всех откликнувшихся.\n"
        "Для публикации необходимо добавить 5 контактов или оплатить 100 сом.\n"
        "Желаете оплатить — нажмите /get_requisites \n"
        "Для публикации вакансии — /add_job\n"
        "Для удаления вакансии — /delete_job\n"
        "Просмотр всех ваших опубликованных вакансий — /my_jobs"
    )
    await callback.message.answer(text)
    await callback.answer()

@router.chat_member()
async def track_invites(event: ChatMemberUpdated):
    if event.chat.id != CHANNEL_ID:
        print("fuck")
        return
    new_user = event.new_chat_member
    inviter = event.from_user
    print("fuck 2")
    if inviter and new_user and inviter.id != new_user.user.id:
        print("yess")
        user_added_contacts[inviter.id].add(new_user.user.id)
        print(user_added_contacts[inviter.id])  # print updated set
        logging.info(f"User {inviter.id} added {new_user.user.id} to the group.")

@router.message(Command("add_job"))
async def add_job(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    print("2", len(user_added_contacts.get(user_id, set())))
    # Проверяем количество добавленных контактов через словарь
    if len(user_added_contacts.get(user_id, set())) < 1:
        await message.answer(
            f"❗ Вы добавили {len(user_added_contacts.get(user_id, set()))} из 5 человек. Пожалуйста, добавьте ещё."
        )
        return
    await state.set_state(JobPost.title)
    await message.answer("Введите название вакансии:")

@router.message(StateFilter(JobPost.title))
async def job_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(JobPost.payment)
    await message.answer("Какая оплата?")

@router.message(StateFilter(JobPost.payment))
async def job_payment(message: types.Message, state: FSMContext):
    await state.update_data(payment=message.text)
    await state.set_state(JobPost.location)
    await message.answer("Где находится работа?")

@router.message(StateFilter(JobPost.location))
async def job_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    await state.set_state(JobPost.age)
    await message.answer("Возрастной диапазон?")

@router.message(StateFilter(JobPost.age))
async def job_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(JobPost.details)
    await message.answer("Дополнительные условия?")

@router.message(StateFilter(JobPost.details))
async def job_details(message: types.Message, state: FSMContext):
    await state.update_data(details=message.text)
    await state.set_state(JobPost.contact)
    await message.answer("Контакты работодателя?")

@router.message(StateFilter(JobPost.contact))
async def job_contact(message: types.Message, state: FSMContext):
    data = await state.get_data()
    data["contact"] = message.text
    job_id = str(uuid.uuid4())
    job_post = (
        f"📢 Вакансия: {data['title']}\n"
        f"💰 Оплата: {data['payment']}\n"
        f"📍 Местоположение: {data['location']}\n"
        f"👥 Возраст: {data['age']}\n"
        f"ℹ️ Условия: {data['details']}\n"
        f"☎️ Контакты: {data['contact']}"
    )
    employer_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Откликнуться", callback_data=f"apply_{job_id}")],
        [InlineKeyboardButton(text="Связаться с работодателем", url=f"tg://user?id={employer_id}")]
    ])
    msg = await bot.send_message(CHANNEL_ID, job_post, reply_markup=keyboard)
    jobs[job_id] = {"employer": employer_id, "applicants": [], "message_id": msg.message_id}
    await message.answer("✅ Вакансия опубликована!")
    await state.clear()

@router.callback_query(F.data.startswith("apply_"))
async def apply_job(callback: types.CallbackQuery):
    job_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    if job_id not in jobs or user_id in jobs[job_id]["applicants"]:
        await callback.answer("Вы уже откликнулись или вакансия не найдена.", show_alert=True)
        return
    jobs[job_id]["applicants"].append(user_id)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await bot.send_message(user_id, "Оставьте свой номер, чтобы работодатель мог с вами связаться.", reply_markup=keyboard)
    await callback.answer("✅ Отклик принят!")

@router.message(F.contact)
async def contact_share(message: types.Message):
    user_id = message.from_user.id
    for job_id, job in jobs.items():
        if user_id in job["applicants"]:
            contact = message.contact.phone_number
            employer_id = job["employer"]
            await bot.send_message(employer_id, f"📞 Новый отклик\nПользователь: @{message.from_user.username}\nНомер телефона: {contact}")
            break
    await message.answer("Спасибо! Контакт отправлен работодателю.", reply_markup=ReplyKeyboardRemove())

# --- Запуск бота ---
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
