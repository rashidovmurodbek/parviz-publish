import asyncio
import html
import logging
from urllib.parse import quote

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import database as store
from config import OWNER_ID, OPERATORS, BOT_TOKEN, SUPPORT_USERNAME
from keyboards import admin_menu, back_menu, main_menu, main_reply

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
router = Router()
class AdminFlow(StatesGroup):
    broadcast = State()
    add_admin = State()
    remove_admin = State()
    add_channel = State()
    remove_channel = State()
    price_edit = State()
    product_add = State()
    referral_percent = State()
    product_edit = State()
    setting_edit = State()
    partial_amount = State()


def operator(user_id):
    return user_id in OPERATORS or store.is_admin(user_id)


def operator_ids():
    return set(OPERATORS) | {row["user_id"] for row in store.list_admins()}


def support_username():
    return store.get_setting("support_username", SUPPORT_USERNAME).strip().lstrip("@")


def admin_link(product=None):
    username = support_username()
    text = f"{product} olmoqchi edim" if product else "Sotib olmoqchi edim"
    return f"https://t.me/{username}?text={quote(text)}"


def purchase_markup(product=None):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Sotib olish", url=admin_link(product))],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="home")],
    ])


DEVELOPER_SETTINGS = {
    "developer_portfolio": ("💼 Portfolio", "Portfolio havolasini yuboring (https://...):"),
    "developer_telegram": ("✈️ Telegram", "Telegram havolasini yuboring (https://t.me/...):"),
    "developer_instagram": ("📸 Instagram", "Instagram havolasini yuboring (https://instagram.com/...):"),
    "developer_github": ("🐙 GitHub", "GitHub havolasini yuboring (https://github.com/...):"),
}


def developer_links_markup():
    rows = []
    for key, (label, _) in DEVELOPER_SETTINGS.items():
        url = store.get_setting(key)
        if url:
            rows.append([InlineKeyboardButton(text=label, url=url)])
    rows.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def developer_text():
    return "🧑‍💻 <b>Dasturchi bilan bog‘lanish</b>\n\nQuyidagi havolalar orqali bog‘lanishingiz mumkin:"


async def required_channels(bot: Bot, user_id: int):
    missing = []
    for channel in store.list_channels():
        try:
            member = await bot.get_chat_member(channel["chat_id"], user_id)
            if member.status in {"left", "kicked"}:
                missing.append(channel)
        except Exception:
            missing.append(channel)
    return missing


async def subscription_message(bot: Bot, user_id: int):
    missing = await required_channels(bot, user_id)
    if not missing:
        return None
    rows = []
    for channel in missing:
        label = channel["title"] or channel["username"] or str(channel["chat_id"])
        url = f"https://t.me/{channel['username'].lstrip('@')}" if channel["username"] else None
        if url:
            rows.append([InlineKeyboardButton(text=f"📢 {label}", url=url)])
    rows.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
    return "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", InlineKeyboardMarkup(inline_keyboard=rows)


async def ensure_access(message_or_callback, bot):
    user = message_or_callback.from_user
    result = await subscription_message(bot, user.id)
    if result:
        text, markup = result
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(text, reply_markup=markup)
            await message_or_callback.answer()
        else:
            await message_or_callback.answer(text, reply_markup=markup)
        return False
    return True


async def send_home(message: Message):
    await message.answer("🏠 <b>Parviz bot</b>ga xush kelibsiz!\n\nKerakli xizmatni tanlang va narxlarni ko‘ring.", reply_markup=main_reply())


@router.message(CommandStart())
async def start(message: Message, bot: Bot):
    store.ensure_user(message.from_user)
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 2 and parts[1].startswith("R"):
        try:
            store.set_referrer(message.from_user.id, int(parts[1][1:]))
        except ValueError:
            pass
    if not await ensure_access(message, bot):
        return
    await send_home(message)


@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery, bot: Bot):
    if await ensure_access(callback, bot):
        await callback.message.edit_text("✅ Obuna tasdiqlandi.", reply_markup=main_menu())


@router.callback_query(F.data == "home")
async def home(callback: CallbackQuery, bot: Bot):
    if not await ensure_access(callback, bot):
        return
    await callback.message.edit_text("🏠 Asosiy menyu:", reply_markup=main_menu())
    await callback.answer()


@router.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    await callback.message.edit_text(f"👨‍💻 Admin: @{support_username()}", reply_markup=purchase_markup())
    await callback.answer()


@router.callback_query(F.data == "developer")
async def developer(callback: CallbackQuery):
    await callback.message.edit_text(developer_text(), reply_markup=developer_links_markup())
    await callback.answer()


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await send_home(message)


@router.message(F.text == "⭐ Stars xizmati")
async def stars(message: Message):
    rows = store.products("stars_")
    await send_catalog(message, rows, "⭐ Telegram Stars narxlari")


@router.message(F.text == "👑 Premium xizmati")
async def premium(message: Message):
    rows = store.products("premium_")
    await send_catalog(message, rows, "👑 Telegram Premium narxlari")


async def send_catalog(message: Message, rows, title: str):
    buttons = [[InlineKeyboardButton(text=f"{p['title']} — {p['price']:,.0f} so‘m".replace(',', ' '), callback_data=f"catalog:{p['code']}")] for p in rows]
    buttons.append([InlineKeyboardButton(text="👨‍💻 Admin bilan bog‘lanish", url=admin_link())])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="home")])
    await message.answer(f"<b>{title}</b>\n\nKerakli to‘plamni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("catalog:"))
async def catalog_selected(callback: CallbackQuery):
    product = store.get_product(callback.data.split(":", 1)[1])
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await callback.message.edit_text(
        f"<b>{html.escape(product['title'])}</b>\n\nNarxi: <b>{product['price']:,.0f} so‘m</b>\n\nBuyurtma berish uchun admin bilan bog‘laning.".replace(',', ' '),
        reply_markup=purchase_markup(product['title']),
    )
    await callback.answer()


@router.message(F.text == "🎮 UC sotib olish")
async def uc(message: Message):
    rows = store.products("uc_")
    buttons = [[InlineKeyboardButton(text=f"{p['title']} — {p['price']:,.0f} so‘m".replace(',', ' '), callback_data=f"uc:{p['code']}")] for p in rows]
    buttons.append([InlineKeyboardButton(text="👨‍💻 Admin bilan bog‘lanish", url=admin_link())])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="home")])
    await message.answer("🎮 <b>PUBG Mobile UC narxlari</b>\n\nKerakli UC miqdorini tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.message(F.text == "🎮 UC narxlari")
async def uc_prices(message: Message):
    await uc(message)


@router.callback_query(F.data == "uc_prices")
async def uc_prices_callback(callback: CallbackQuery):
    rows = store.products("uc_")
    buttons = [[InlineKeyboardButton(text=f"{p['title']} — {p['price']:,.0f} so‘m".replace(',', ' '), callback_data=f"uc:{p['code']}")] for p in rows]
    buttons.append([InlineKeyboardButton(text="👨‍💻 Admin bilan bog‘lanish", url=admin_link())])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="home")])
    await callback.message.edit_text("🎮 <b>PUBG Mobile UC narxlari</b>\n\nKerakli UC miqdorini tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("uc:"))
async def uc_selected(callback: CallbackQuery):
    product = store.get_product(callback.data.split(":", 1)[1])
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await callback.message.edit_text(
        f"🎮 <b>{html.escape(product['title'])}</b>\n\nNarxi: <b>{product['price']:,.0f} so‘m</b>\n\nBuyurtma berish uchun admin bilan bog‘laning.".replace(',', ' '),
        reply_markup=purchase_markup(product['title']),
    )
    await callback.answer()


@router.message(F.text.in_({"🛒 Sotib olish", "👨‍💻 Admin bilan bog‘lanish"}))
async def contact_admin(message: Message):
    await message.answer(f"🛒 Buyurtma berish uchun admin bilan bog‘laning: @{support_username()}", reply_markup=purchase_markup())


@router.message(F.text == "🧑‍💻 Dasturchi bilan bog‘lanish")
async def contact_developer(message: Message):
    await message.answer(developer_text(), reply_markup=developer_links_markup())


@router.message(F.text == "◀️ Orqaga")
async def back_reply(message: Message):
    await send_home(message)


@router.message(Command("admin"))
async def admin_command(message: Message):
    if not operator(message.from_user.id):
        return
    await message.answer("🛡 <b>Admin panel</b>", reply_markup=admin_menu(message.from_user.id == OWNER_ID))


@router.message(Command("owner"))
async def owner_command(message: Message):
    if message.from_user.id == OWNER_ID:
        await message.answer("👑 <b>Owner panel</b>", reply_markup=admin_menu(True))


@router.message(F.text.in_({"admin", "/admin", "owner", "/owner"}))
async def plain_panel_command(message: Message):
    if message.from_user.id == OWNER_ID and message.text.lstrip('/').lower() == 'owner':
        await message.answer("👑 <b>Owner panel</b>", reply_markup=admin_menu(True))
    elif operator(message.from_user.id) and message.text.lstrip('/').lower() == 'admin':
        await message.answer("🛡 <b>Admin panel</b>", reply_markup=admin_menu(message.from_user.id == OWNER_ID))
    else:
        await message.answer("⛔ Sizda panelga kirish huquqi yo‘q.")


@router.callback_query(F.data == "adm:stats")
async def admin_stats(callback: CallbackQuery):
    if not operator(callback.from_user.id): return
    s = store.get_stats()
    await callback.message.edit_text(f"📊 <b>Statistika</b>\n\n👥 Foydalanuvchilar: {s['users']}\n💰 Mahsulotlar: {len(store.products())}", reply_markup=admin_menu(callback.from_user.id == OWNER_ID))
    await callback.answer()


@router.callback_query(F.data == "adm:settings")
async def bot_settings_menu(callback: CallbackQuery):
    if not operator(callback.from_user.id): return
    rows = [
        [InlineKeyboardButton(text="👨‍💻 Admin username’ini o‘zgartirish", callback_data="setting:support_username")],
    ]
    text = f"⚙️ <b>Bot ma’lumotlari</b>\n\nAmaldagi admin: @{support_username()}"
    if callback.from_user.id == OWNER_ID:
        rows += [
            [InlineKeyboardButton(text="💼 Portfolio havolasini o‘zgartirish", callback_data="setting:developer_portfolio")],
            [InlineKeyboardButton(text="✈️ Telegram havolasini o‘zgartirish", callback_data="setting:developer_telegram")],
            [InlineKeyboardButton(text="📸 Instagram havolasini o‘zgartirish", callback_data="setting:developer_instagram")],
            [InlineKeyboardButton(text="🐙 GitHub havolasini o‘zgartirish", callback_data="setting:developer_github")],
        ]
        text += "\n\n🧑‍💻 Dasturchi havolalari faqat owner tomonidan boshqariladi."
    rows.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="owner_back")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)); await callback.answer()


@router.callback_query(F.data.startswith("setting:"))
async def setting_edit_start(callback: CallbackQuery, state: FSMContext):
    if not operator(callback.from_user.id): return
    key = callback.data.split(":", 1)[1]
    if key in DEVELOPER_SETTINGS and callback.from_user.id != OWNER_ID:
        await callback.answer("Faqat owner o‘zgartira oladi.", show_alert=True)
        return
    await state.update_data(key=key); await state.set_state(AdminFlow.setting_edit)
    prompts = {"support_username": "Admin username’ini yuboring (@ bilan yoki @siz)."}
    prompts.update({key: prompt for key, (_, prompt) in DEVELOPER_SETTINGS.items()})
    await callback.message.answer(prompts.get(key, "Yangi qiymatni yuboring:")); await callback.answer()


@router.message(AdminFlow.setting_edit)
async def setting_edit(message: Message, state: FSMContext):
    if not operator(message.from_user.id): return
    key = (await state.get_data())["key"]
    if key in DEVELOPER_SETTINGS and message.from_user.id != OWNER_ID:
        await state.clear()
        await message.answer("⛔ Faqat owner o‘zgartira oladi.")
        return
    value = (message.text or '').strip()
    if key == "support_username":
        value = value.lstrip('@')
        if not value or any(char.isspace() for char in value):
            await message.answer("Username bo‘sh bo‘lmasligi va probelsiz bo‘lishi kerak. Qayta yuboring:")
            return
    elif key in DEVELOPER_SETTINGS:
        if value in {"-", "o‘chirish", "ochirish"}:
            value = ""
        elif not value.startswith(("http://", "https://")):
            await message.answer("Havola http:// yoki https:// bilan boshlanishi kerak. Qayta yuboring:")
            return
    store.set_setting(key, value)
    await state.clear(); await message.answer("✅ Ma’lumot saqlandi.", reply_markup=admin_menu(message.from_user.id == OWNER_ID))


@router.callback_query(F.data == "adm:prices")
async def prices_menu(callback: CallbackQuery):
    if not operator(callback.from_user.id): return
    rows = []
    for product in store.products():
        rows.append([InlineKeyboardButton(text=f"✏️ {product['title'][:22]}: {product['price']:,.0f}".replace(',', ' '), callback_data=f"editproduct:{product['code']}"), InlineKeyboardButton(text="🗑", callback_data=f"delprice:{product['code']}")])
    rows += [[InlineKeyboardButton(text="➕ Mahsulot qo‘shish", callback_data="adm:add_product")], [InlineKeyboardButton(text="◀️ Orqaga", callback_data="owner_back")]]
    await callback.message.edit_text("💰 <b>Narxlarni boshqarish</b>\nMahsulotni tanlab narxini o‘zgartiring:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)); await callback.answer()


@router.callback_query(F.data.startswith("price:"))
async def price_edit_start(callback: CallbackQuery, state: FSMContext):
    if not operator(callback.from_user.id): return
    code = callback.data.split(":", 1)[1]
    product = store.get_product(code)
    await state.update_data(code=code); await state.set_state(AdminFlow.price_edit)
    await callback.message.answer(f"{product['title']}\nHozirgi narx: {product['price']}\n\nYangi narxni so‘mda yuboring:")
    await callback.answer()


@router.callback_query(F.data.startswith("editproduct:"))
async def product_edit_start(callback: CallbackQuery, state: FSMContext):
    if not operator(callback.from_user.id): return
    code = callback.data.split(":", 1)[1]
    product = store.get_product(code)
    await state.update_data(code=code); await state.set_state(AdminFlow.product_edit)
    await callback.message.answer(f"<b>{product['title']}</b>\nHozirgi narx: {product['price']}\n\nYangi ma’lumotni yuboring:\n<code>nomi | narxi | tavsifi</code>")
    await callback.answer()


@router.message(AdminFlow.product_edit)
async def product_edit(message: Message, state: FSMContext):
    if not operator(message.from_user.id): return
    parts = [x.strip() for x in (message.text or '').split('|')]
    try:
        if len(parts) < 2 or not parts[0]: raise ValueError
        price = float(parts[1].replace(' ', '').replace(',', '.'))
        if price < 0: raise ValueError
        code = (await state.get_data())["code"]
        if not store.update_product(code, title=parts[0], price=price, description=parts[2] if len(parts) > 2 else ''):
            raise ValueError
        await message.answer("✅ Mahsulot ma’lumotlari yangilandi.", reply_markup=admin_menu(message.from_user.id == OWNER_ID)); await state.clear()
    except ValueError:
        await message.answer("Format noto‘g‘ri: <code>nomi | narxi | tavsifi</code>")


@router.message(AdminFlow.price_edit)
async def price_edit(message: Message, state: FSMContext):
    if not operator(message.from_user.id): return
    try:
        price = float(message.text.replace(' ', '').replace(',', '.'))
        if price < 0: raise ValueError
        code = (await state.get_data())["code"]
        store.set_product_price(code, price)
        await message.answer(f"✅ Narx yangilandi: {price:,.0f} so'm".replace(',', ' '), reply_markup=admin_menu(message.from_user.id == OWNER_ID))
        await state.clear()
    except ValueError:
        await message.answer("Narx faqat son bo‘lishi kerak.")


@router.callback_query(F.data.startswith("delprice:"))
async def price_delete(callback: CallbackQuery):
    if not operator(callback.from_user.id): return
    store.delete_product(callback.data.split(":", 1)[1])
    await callback.answer("Mahsulot o‘chirildi")
    await prices_menu(callback)


@router.callback_query(F.data == "adm:add_product")
async def product_add_start(callback: CallbackQuery, state: FSMContext):
    if not operator(callback.from_user.id): return
    await state.set_state(AdminFlow.product_add)
    await callback.message.answer("Yangi mahsulotni quyidagi formatda yuboring:\n<code>code | nomi | narxi | tavsif</code>")
    await callback.answer()


@router.message(AdminFlow.product_add)
async def product_add(message: Message, state: FSMContext):
    if not operator(message.from_user.id): return
    parts = [x.strip() for x in (message.text or '').split('|')]
    try:
        if len(parts) < 3 or not parts[0] or not parts[1]: raise ValueError
        price = float(parts[2].replace(' ', '').replace(',', '.'))
        if price < 0: raise ValueError
        store.add_product(parts[0], parts[1], price, parts[3] if len(parts) > 3 else '')
        await message.answer("✅ Mahsulot qo‘shildi.", reply_markup=admin_menu(message.from_user.id == OWNER_ID)); await state.clear()
    except ValueError:
        await message.answer("Format noto‘g‘ri. Masalan: <code>stars_500 | ⭐ 500 Stars | 150000</code>")


@router.callback_query(F.data == "adm:referral")
async def referral_edit_start(callback: CallbackQuery, state: FSMContext):
    if not operator(callback.from_user.id): return
    await state.set_state(AdminFlow.referral_percent)
    await callback.message.answer(f"Hozirgi referral foizi: {store.get_setting('referral_percent', '1')}%\nYangi foizni yuboring:"); await callback.answer()


@router.message(AdminFlow.referral_percent)
async def referral_edit(message: Message, state: FSMContext):
    if not operator(message.from_user.id): return
    try:
        value = float(message.text.replace(',', '.'))
        if value < 0 or value > 100: raise ValueError
        store.set_setting('referral_percent', value)
        await message.answer(f"✅ Referral foizi {value}% qilib saqlandi.", reply_markup=admin_menu(message.from_user.id == OWNER_ID)); await state.clear()
    except ValueError:
        await message.answer("0 dan 100 gacha son yuboring.")


@router.callback_query(F.data == "adm:broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not operator(callback.from_user.id): return
    await state.set_state(AdminFlow.broadcast)
    await callback.message.answer("📣 Reklama xabarini yuboring. Matn, rasm, video yoki fayl bo‘lishi mumkin. /cancel — bekor qilish.")
    await callback.answer()


@router.message(AdminFlow.broadcast)
async def broadcast(message: Message, state: FSMContext, bot: Bot):
    if not operator(message.from_user.id): return
    ok = failed = 0
    for user in store.list_users():
        try:
            await message.copy_to(user["id"])
            ok += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.04)
    await state.clear()
    await message.answer(f"✅ Reklama yuborildi.\nYetkazildi: {ok}\nXato: {failed}", reply_markup=admin_menu(message.from_user.id == OWNER_ID))


@router.callback_query(F.data == "adm:admins")
async def admins_menu(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID: return
    rows = [[InlineKeyboardButton(text="➕ Admin qo‘shish", callback_data="adm:add_admin")], [InlineKeyboardButton(text="➖ Admin o‘chirish", callback_data="adm:remove_admin")], [InlineKeyboardButton(text="📋 Adminlarni ko‘rish", callback_data="adm:list_admins")], [InlineKeyboardButton(text="◀️ Orqaga", callback_data="owner_back")]]
    await callback.message.edit_text("👥 Admin boshqaruvi:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data == "adm:add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID: return
    await state.set_state(AdminFlow.add_admin)
    await callback.message.answer("Yangi adminning Telegram ID raqamini yuboring:")
    await callback.answer()


@router.message(AdminFlow.add_admin)
async def add_admin(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID: return
    try:
        user_id = int(message.text)
        store.add_admin(user_id)
        await message.answer(f"✅ Admin qo‘shildi: <code>{user_id}</code>")
    except ValueError:
        await message.answer("ID faqat raqam bo‘lishi kerak.")
    await state.clear()


@router.callback_query(F.data == "adm:remove_admin")
async def remove_admin_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID: return
    await state.set_state(AdminFlow.remove_admin)
    await callback.message.answer("O‘chiriladigan admin ID’sini yuboring:")
    await callback.answer()


@router.message(AdminFlow.remove_admin)
async def remove_admin(message: Message, state: FSMContext):
    if message.from_user.id == OWNER_ID:
        try:
            user_id = int(message.text); store.remove_admin(user_id)
            await message.answer(f"✅ Admin o‘chirildi: <code>{user_id}</code>")
        except ValueError: await message.answer("ID noto‘g‘ri.")
    await state.clear()


@router.callback_query(F.data == "adm:list_admins")
async def list_admins(callback: CallbackQuery):
    if callback.from_user.id != OWNER_ID: return
    admins = store.list_admins()
    text = "📋 Adminlar:\n" + ("\n".join(f"• <code>{a['user_id']}</code>" for a in admins) if admins else "Hali admin qo‘shilmagan.")
    await callback.message.edit_text(text, reply_markup=back_menu("adm:admins")); await callback.answer()


@router.callback_query(F.data == "adm:channels")
async def channels_menu(callback: CallbackQuery):
    if not operator(callback.from_user.id): return
    rows = [[InlineKeyboardButton(text="➕ Kanal qo‘shish", callback_data="adm:add_channel")], [InlineKeyboardButton(text="➖ Kanal o‘chirish", callback_data="adm:remove_channel")], [InlineKeyboardButton(text="📋 Kanallarni ko‘rish", callback_data="adm:list_channels")], [InlineKeyboardButton(text="◀️ Orqaga", callback_data="owner_back")]]
    await callback.message.edit_text("📢 Majburiy obuna kanallari:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)); await callback.answer()


@router.callback_query(F.data == "adm:add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    if not operator(callback.from_user.id): return
    await state.set_state(AdminFlow.add_channel); await callback.message.answer("Kanal username’ini yuboring, masalan: @kanal. Bot kanalga admin bo‘lishi kerak."); await callback.answer()


@router.message(AdminFlow.add_channel)
async def add_channel(message: Message, state: FSMContext, bot: Bot):
    if not operator(message.from_user.id): return
    try:
        chat = await bot.get_chat(message.text.strip())
        store.add_channel(str(chat.id), chat.title or "Kanal", chat.username)
        await message.answer(f"✅ Kanal qo‘shildi: {chat.title}")
    except Exception:
        await message.answer("Kanal topilmadi. Username’ni @ bilan yuboring va botni kanalga admin qiling.")
    await state.clear()


@router.callback_query(F.data == "adm:remove_channel")
async def remove_channel_start(callback: CallbackQuery, state: FSMContext):
    if not operator(callback.from_user.id): return
    await state.set_state(AdminFlow.remove_channel); await callback.message.answer("O‘chiriladigan kanal username yoki ID’sini yuboring:"); await callback.answer()


@router.message(AdminFlow.remove_channel)
async def remove_channel(message: Message, state: FSMContext):
    if operator(message.from_user.id):
        chat_id = message.text.strip()
        if chat_id.startswith("@"): chat_id = chat_id
        store.remove_channel(chat_id); await message.answer("✅ Kanal o‘chirildi.")
    await state.clear()


@router.callback_query(F.data == "adm:list_channels")
async def list_channels(callback: CallbackQuery):
    if not operator(callback.from_user.id): return
    channels = store.list_channels()
    text = "📢 Kanallar:\n" + ("\n".join(f"• {c['title']} — <code>{c['chat_id']}</code>" for c in channels) if channels else "Kanal qo‘shilmagan.")
    await callback.message.edit_text(text, reply_markup=back_menu("adm:channels")); await callback.answer()


@router.callback_query(F.data == "owner_back")
async def owner_back(callback: CallbackQuery):
    if operator(callback.from_user.id):
        await callback.message.edit_text("🛡 Admin panel", reply_markup=admin_menu(callback.from_user.id == OWNER_ID)); await callback.answer()


@router.message()
async def fallback(message: Message, bot: Bot):
    store.ensure_user(message.from_user)
    if operator(message.from_user.id):
        reply = message.reply_to_message
        origin = getattr(reply, "forward_origin", None) if reply else None
        target = getattr(getattr(origin, "sender_user", None), "id", None)
        if target:
            try:
                await message.copy_to(target)
                await message.answer("✅ Javob foydalanuvchiga yuborildi.")
            except Exception:
                await message.answer("❌ Javobni yuborib bo‘lmadi.")
            return
        await message.answer("❌ Noma’lum buyruq. /admin yoki /owner dan foydalaning.")
        return

    delivered = 0
    for operator_id in operator_ids():
        try:
            await message.forward(operator_id)
            delivered += 1
        except Exception:
            continue
    if delivered:
        await message.answer("✅ Xabaringiz adminlarga yuborildi.")
    else:
        await message.answer("❌ Xato ma’lumot.\n/start yozing.")


async def main():
    store.init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(); dp.include_router(router)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
