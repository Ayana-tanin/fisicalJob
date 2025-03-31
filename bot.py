import logging 
import asyncio
import os
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

user_added_contacts = defaultdict(set)
approved_users = {}
jobs = {}

class JobPost(StatesGroup):
    title = State()
    payment = State()
    location = State()
    age = State()
    details = State()
    contact = State()
    
STEPS = [
    ("title", JobPost.payment, "Какая зарплата?"),
    ("payment", JobPost.location, "Где находится работа?"),
    ("location", JobPost.age, "Возрастной диапазон?"),
    ("age", JobPost.details, "Дополнительные условия?"),
    ("details", JobPost.contact, "Контакты работодателя?"),
]

async def process_step(message: types.Message, state: FSMContext, key: str, next_state: State, question: str):
    await state.update_data(**{key: message.text})
    await state.set_state(next_state)
    await message.answer(question)

@router.message(StateFilter(None), F.text & ~F.text.startswith("/")) 
# Только для пользователей НЕ в анкете 
async def delete_and_notify(message: types.Message): 
    await message.delete() 
    keyboard = InlineKeyboardMarkup( inline_keyboard=[[InlineKeyboardButton(text="Написать боту", url="https://t.me/fisicalJob_bot")]] ) 
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
    username = callback.from_user.username
    user_mention = f"@{username}" if username else f"tg://user?id={callback.from_user.id}"
    
    await bot.send_message(ADMIN_ID, f"⚠️ Пользователь {user_mention} хочет оплатить размещение вакансии.")
    await callback.message.answer("📩 Свяжитесь с админом для оплаты: @ant_anny")
    await callback.answer()

@router.message(Command("add_job"))
async def add_job(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    contact_count = len(user_added_contacts.get(user_id, set()))
    if contact_count < -1:
        await message.answer(f"❌ Вы добавили {contact_count}/5 контактов. Добавьте ещё!")
        return
    await state.set_state(JobPost.title)
    await message.answer("Введите название вакансии:")

for key, next_state, question in STEPS:
    @router.message(StateFilter(getattr(JobPost, key)))
    async def handler(message: types.Message, state: FSMContext, key=key, next_state=next_state, question=question):
        await process_step(message, state, key, next_state, question)

@router.callback_query(F.data.startswith("apply_"))
async def process_application(callback: types.CallbackQuery):
    job_id = int(callback.data.split("_")[1])
    if job_id not in jobs:
        await callback.answer("❌ Вакансия уже удалена или не найдена.")
        return
    job = jobs[job_id]
    applicant_id = callback.from_user.id
    if applicant_id in job["applicants"]:
        await callback.answer("Вы уже откликнулись на эту вакансию.")
        return
    job["applicants"].append(applicant_id)
    await callback.answer("✅ Ваш отклик принят!")
    
    if len(job["applicants"]) >= 15:
        applicants_info = "\n".join([f"tg://user?id={app_id}" for app_id in job["applicants"]])
        await bot.send_message(job["employer"], f"🚨 Вакансия {job_id} достигла лимита откликов!\n{applicants_info}")
        if "message_id" in job:
            await bot.delete_message(CHANNEL_ID, job["message_id"])
        jobs.pop(job_id)

async def main():
    logging.basicConfig(level=logging.INFO)
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())