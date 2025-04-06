import logging 
import asyncio
import os
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from aiogram.fsm.state import StatesGroup, State
from collections import defaultdict
import uuid
from aiogram.client.default import DefaultBotProperties

TOKEN="7754219638:AAFv67IZiIxHCLwQ-W0nDsp1Aws3MZhCio8"
CHANNEL_ID = -1002423189514
ADMIN_ID = 5320545212

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
    chat_member_updates=True
)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Логирование
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Хранилища
user_added_contacts = defaultdict(set)
approved_users = {}
jobs = {}

# Определение состояний анкеты
class JobPost(StatesGroup):
    title = State()
    payment = State()
    location = State()
    age = State()
    details = State()
    contact = State()

@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def delete_and_notify(message: types.Message):
    await message.delete()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Написать боту", url="https://t.me/fisisalJob_bot")]]
    )
    msg = await message.answer("Чтобы начать публикацию, перейдите к боту", reply_markup=keyboard)
    await asyncio.sleep(300)
    await msg.delete()

@router.message(Command("start"))
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить 5 контактов", callback_data="add_contacts")],
            [InlineKeyboardButton(text="Получить реквизиты", callback_data="get_requisites")]
        ]
    )
    await message.answer("Привет! Чтобы разместить вакансию, добавьте 5 контактов или оплатите 100 сом. После этого используйте /add_job.", reply_markup=keyboard)

@router.callback_query(F.data == "add_contacts")
async def add_contacts(callback: types.CallbackQuery):
    await callback.message.answer("Добавьте 5 контактов в группу https://t.me/fisisalJob")
    await callback.answer()

@router.callback_query(F.data == "get_requisites")
async def get_requisites(callback: types.CallbackQuery):
    await bot.send_message(ADMIN_ID, f"⚠️ Пользователь @{callback.from_user.username} хочет оплатить размещение вакансии.")
    await callback.message.answer("📩 Свяжитесь с админом для оплаты: @ant_anny")
    await callback.answer()

    
@router.chat_member()
async def track_new_members(event: ChatMemberUpdated):
    try:
        # Проверка только на нужный канал
        if event.chat.id != CHANNEL_ID:
            return

        new_user = event.new_chat_member
        inviter = event.from_user

        # Только если пользователь был добавлен вручную (а не сам вступил)
        if inviter and new_user and inviter.id != new_user.user.id:
            user_added_contacts[inviter.id].add(new_user.user.id)
            logging.info(f"[+] User {new_user.user.id} был добавлен пользователем {inviter.id}")
    except Exception as e:
        logging.error(f"Ошибка в track_new_members: {e}")

@router.message(Command("add_job"))
async def add_job(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    contact_count = len(user_added_contacts.get(user_id, set()))
    logging.info(f"👤 User {user_id} добавил {contact_count} контактов")

    if contact_count <= 5:
        await message.answer(f"❌ Вы добавили {contact_count}/5 контактов. Добавьте ещё!")
        return

    await state.set_state(JobPost.title)
    await message.answer("Введите название вакансии:")

@router.message(StateFilter(JobPost.title))
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(JobPost.payment)
    await message.answer("Какая зарплата?")

@router.message(StateFilter(JobPost.payment))
async def process_payment(message: types.Message, state: FSMContext):
    await state.update_data(payment=message.text)
    await state.set_state(JobPost.location)
    await message.answer("Где находится работа?")

@router.message(StateFilter(JobPost.location))
async def process_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    await state.set_state(JobPost.age)
    await message.answer("Возрастной диапазон?")

@router.message(StateFilter(JobPost.age))
async def process_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(JobPost.details)
    await message.answer("Дополнительные условия?")

@router.message(StateFilter(JobPost.details))
async def process_details(message: types.Message, state: FSMContext):
    await state.update_data(details=message.text)
    await state.set_state(JobPost.contact)
    await message.answer("Контакты работодателя?")
    
@router.message(StateFilter(JobPost.contact))
async def process_contact(message: types.Message, state: FSMContext):
    data = await state.get_data()
    data["contact"] = message.text

    job_id = str(uuid.uuid4())      
    job_post = (f"📢 Вакансия: {data['title']}\n💰 Оплата: {data['payment']}\n📍 Местоположение: {data['location']}\n👥 Возраст: {data['age']}\nℹ️ Условия: {data['details']}\n☎️ Контакты: {data['contact']}")

    employer_id = message.chat.id  # ID работодателя

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Откликнуться", callback_data=f"apply_{job_id}")],
        [InlineKeyboardButton(text="Связаться с работодателем", url=f"tg://user?id={employer_id}")]
    ])
    
    msg = await bot.send_message(CHANNEL_ID, job_post, reply_markup=keyboard)
    
    jobs[job_id] = {
        "count": 0,
        "employer": employer_id,
        "applicants": [],
        "contact": data["contact"],
        "message_id": msg.message_id  # ID сообщения для удаления
    }
    
    await message.answer("✅ Вакансия опубликована!")
    await state.clear()

@router.callback_query(F.data.startswith("apply_"))
async def apply(callback_query: types.CallbackQuery):
    job_id = callback_query.data.split("_")[1]
    
    user_id = callback_query.from_user.id
    username = f"@{callback_query.from_user.username}" if callback_query.from_user.username else f"[{callback_query.from_user.first_name}](tg://user?id={user_id})"

    if job_id in jobs:
    
        if user_id in jobs[job_id]["applicants"]:
            await callback_query.answer("Вы уже откликнулись на эту вакансию.", show_alert=True)
            return

        jobs[job_id]["applicants"].append(user_id)
        jobs[job_id]["count"] += 1
        employer_id = jobs[job_id]["employer"]

        await bot.send_message(employer_id, f"🔔 Новый отклик на вашу вакансию!\n👤 Кандидат: {username}\n📩 Свяжитесь с ним напрямую.")

        if jobs[job_id]["count"] >= 15:
            applicants_info = "\n".join(
                [f"@{callback_query.from_user.username}" if callback_query.from_user.username else f"[{callback_query.from_user.first_name}](tg://user?id={user_id})"
                 for user_id in jobs[job_id]["applicants"]]
            )
            await bot.send_message(employer_id, f"🚨 Вакансия {job_id} закрыта!\nСписок откликнувшихся:\n{applicants_info}")
            
            await bot.delete_message(CHANNEL_ID, jobs[job_id]["message_id"])  
            del jobs[job_id] 

    await callback_query.answer("✅ Ваш отклик отправлен работодателю!")  

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())