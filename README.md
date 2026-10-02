# Parviz narxlar boti

Python 3.10+ va aiogram 3 asosidagi narxlar boti.

Botda foydalanuvchi Stars, Premium va PUBG Mobile UC narxlarini ko‘radi. Mahsulot tanlanganda sotib olish uchun admin profiliga o‘tadi. `/admin` orqali narxlar, admin username’i, reklama, adminlar va majburiy kanallar boshqariladi.

## Ishga tushirish

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` faylida:

- `BOT_TOKEN` — @BotFather bergan token;
- `OWNER_ID` — bot egasining Telegram ID raqami;
- `ADMIN_ID` — asosiy adminning Telegram ID raqami;
- `SUPPORT_USERNAME` — admin Telegram username’i (standart: `parviz_48_48`).

Keyin:

```bash
python bot.py
```

Operator foydalanuvchi yuborgan forward xabariga **Reply** qilsa, javob avtomatik foydalanuvchiga yuboriladi.

## Serverga joylash

Ubuntu/Debian serverda:

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin parviz
sudo mkdir -p /opt/parviz
sudo chown -R parviz:parviz /opt/parviz
cd /opt/parviz
git clone <REPOSITORY_URL> .
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
nano .env
chmod 600 .env
```

`.env` dagi `BOT_TOKEN`, `OWNER_ID`, `ADMIN_ID` va qolgan qiymatlarni to‘ldiring. Keyin servisni o‘rnating:

```bash
sudo cp parviz-bot.service.example /etc/systemd/system/parviz-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now parviz-bot
sudo systemctl status parviz-bot
```

Loglar: `sudo journalctl -u parviz-bot -f`.
