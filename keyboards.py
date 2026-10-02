from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_reply():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⭐ Stars xizmati"), KeyboardButton(text="👑 Premium xizmati")],
        [KeyboardButton(text="🛒 Sotib olish"), KeyboardButton(text="👨‍💻 Admin bilan bog‘lanish")],
        [KeyboardButton(text="🧑‍💻 Dasturchi bilan bog‘lanish")],
    ], resize_keyboard=True)


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 Admin bilan bog‘lanish", callback_data="support")],
        [InlineKeyboardButton(text="🧑‍💻 Dasturchi bilan bog‘lanish", callback_data="developer")],
    ])


def admin_menu(owner=False):
    rows = [[InlineKeyboardButton(text="📊 Statistika", callback_data="adm:stats")],
            [InlineKeyboardButton(text="💰 Narxlarni boshqarish", callback_data="adm:prices")],
            [InlineKeyboardButton(text="⚙️ Bot ma’lumotlari", callback_data="adm:settings")],
            [InlineKeyboardButton(text="📣 Reklama yuborish", callback_data="adm:broadcast")],
            [InlineKeyboardButton(text="📢 Majburiy kanallar", callback_data="adm:channels")]]
    if owner:
        rows.append([InlineKeyboardButton(text="👥 Adminlar", callback_data="adm:admins")])
    rows.append([InlineKeyboardButton(text="◀️ Asosiy menyu", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_menu(callback="home"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Orqaga", callback_data=callback)]])
