import io
import random
import cv2
import numpy as np
from PIL import Image
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

# --- CONFIG ---
BOT_TOKEN = "8635625101:AAENL_CKh30rP6aHQXlPMVeKSvLwILXunX4"
ADMIN_ID = 8520025523

# Veri Depoları
user_balances = {}
user_vips = {}
user_spins = {}
user_discounts = {}
user_stats = {}
user_last_photo = {}
user_ai_mode = {}
user_lang = {}

SHOP_PACKAGES = {
    "star_5k": {"title": "5.000 FS", "fs": 5000, "stars": 280},
    "star_37k": {"title": "37.028 FS", "fs": 37028, "stars": 1836},
    "star_63k": {"title": "63.951 FS", "fs": 63951, "stars": 4386},
    "star_103k": {"title": "103.926 FS", "fs": 103926, "stars": 6937},
    "star_289k": {"title": "289.959 FS", "fs": 289959, "stars": 12855},
    "star_vip": {
        "title": "982 Gün Sınırsız VIP",
        "fs": 0,
        "vip": True,
        "stars": 19496,
    },
}

# OpenCV Yüz Algılama ve Bıyık/Sakal Çizim Motoru
def apply_facial_effect(photo_bytes, effect_code):
    np_arr = np.frombuffer(photo_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(gray, 1.1, 5)

    code = effect_code.upper().strip()

    for x, y, w, h in faces:
        mustache_y1 = int(y + h * 0.62)
        mustache_y2 = int(y + h * 0.74)
        mustache_x1 = int(x + w * 0.28)
        mustache_x2 = int(x + w * 0.72)

        if "BYK-01" in code:  # İnce / Pala Bıyık
            pts = np.array(
                [
                    [mustache_x1, mustache_y1 + 5],
                    [int(x + w * 0.5), mustache_y1 - 5],
                    [mustache_x2, mustache_y1 + 5],
                    [int(x + w * 0.5), mustache_y2 - 8],
                ],
                np.int32,
            )
            cv2.fillPoly(img, [pts], (15, 15, 15))

        elif "BYK-02" in code:  # Kalın Koyu Bıyık
            cv2.ellipse(
                img,
                (int(x + w * 0.5), int(mustache_y1)),
                (int(w * 0.22), int(h * 0.08)),
                0,
                0,
                180,
                (10, 10, 10),
                -1,
            )

        elif "BYK-03" in code:  # Top Sakal & Bıyık
            cv2.ellipse(
                img,
                (int(x + w * 0.5), int(mustache_y1)),
                (int(w * 0.22), int(h * 0.07)),
                0,
                0,
                180,
                (10, 10, 10),
                -1,
            )
            cv2.ellipse(
                img,
                (int(x + w * 0.5), int(y + h * 0.85)),
                (int(w * 0.16), int(h * 0.1)),
                0,
                0,
                360,
                (10, 10, 10),
                -1,
            )

        elif "SKL-01" in code:  # Kirli Sakal
            for _ in range(400):
                rx = random.randint(int(x + w * 0.2), int(x + w * 0.8))
                ry = random.randint(int(y + h * 0.62), int(y + h * 0.92))
                cv2.line(
                    img, (rx, ry), (rx + 2, ry + 4), (20, 20, 20), 1
                )

    _, encoded_img = cv2.imencode(".jpg", img)
    return io.BytesIO(encoded_img.tobytes())

def get_main_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎨 Saç Rengi (10 FS)", callback_data="cat_hair_color"
                ),
                InlineKeyboardButton(
                    "🧔 Bıyık & Sakal (10 FS)", callback_data="cat_beard"
                ),
            ],
            [
                InlineKeyboardButton(
                    "👶👴 Yaş Değiştir (10 FS)", callback_data="cat_age"
                ),
                InlineKeyboardButton(
                    "😄 Gülme/Mimik (10 FS)", callback_data="cat_smile"
                ),
            ],
            [
                InlineKeyboardButton("🎡 Çark Çevir", callback_data="wheel"),
                InlineKeyboardButton("🤖 AİOR-Aİ Sor", callback_data="ai_chat"),
            ],
            [
                InlineKeyboardButton("👤 Profilim", callback_data="profile"),
                InlineKeyboardButton("⭐ Yıldız Mağazası", callback_data="shop"),
            ],
        ]
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_balances.setdefault(user_id, 0)
    user_spins.setdefault(user_id, 8)
    user_stats.setdefault(user_id, 0)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
                InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
            ],
            [
                InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
                InlineKeyboardButton("🇦🇿 Azərbaycanca", callback_data="lang_az"),
            ],
            [
                InlineKeyboardButton("☀️ Kurdî", callback_data="lang_ku"),
            ],
        ]
    )
    await update.message.reply_text(
        "🔥 **FACEİSTOKİS AI Botuna Hoşgeldiniz! / Welcome!**\n\nLütfen bir dil seçin / Choose language:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("lang_"):
        user_lang[user_id] = data.replace("lang_", "")
        await query.message.reply_text(
            "✅ **Dil Seçildi!**\n📸 İşlenmesini istediğiniz fotoğrafı gönderin.",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown",
        )
        return

    if data == "shop":
        buttons = []
        is_admin = user_id == ADMIN_ID

        for key, pkg in SHOP_PACKAGES.items():
            if is_admin:
                btn_text = f"🎁 {pkg['title']} (ÜCRETSİZ - Admin)"
            else:
                btn_text = f"⭐ {pkg['title']} ({pkg['stars']} Yıldız)"
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"buy_{key}")])

        await query.message.reply_text(
            "⭐ **FACEİSTOKİS YILDIZ MAĞAZASI**\n\nPaket seçiniz:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
        )
        return

    if data.startswith("buy_"):
        pkg_key = data.replace("buy_", "")
        pkg = SHOP_PACKAGES.get(pkg_key)

        if pkg:
            # ADMIN ÖZEL: Bedava yükleme
            if user_id == ADMIN_ID:
                if pkg.get("vip"):
                    user_vips[user_id] = True
                    await query.message.reply_text("👑 **Admin VIP Hesaba Tanımlandı!**")
                else:
                    user_balances[user_id] = user_balances.get(user_id, 0) + pkg["fs"]
                    await query.message.reply_text(
                        f"⚡ **Admin Özel:** +{pkg['fs']} FS Bakiyenize Eklendi!\nYeni Bakiyeniz: {user_balances[user_id]} FS"
                    )
            else:
                prices = [LabeledPrice(label=pkg["title"], amount=pkg["stars"])]
                await context.bot.send_invoice(
                    chat_id=user_id,
                    title=pkg["title"],
                    description=f"FACEİSTOKİS {pkg['title']} Paketi",
                    payload=pkg_key,
                    provider_token="",
                    currency="XTR",
                    prices=prices,
                )
        return

    if data == "profile":
        bal = user_balances.get(user_id, 0)
        await query.message.reply_text(
            f"👤 **PROFİL BİLGİLERİNİZ**\n\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"💰 **Bakiye:** `{bal} FS`\n"
            f"👑 **Rol:** `{'Admin' if user_id == ADMIN_ID else 'Kullanıcı'}`",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(),
        )
        return

    if data == "cat_beard":
        await query.message.reply_text(
            "🧔 **BIYIK & SAKAL KODLARI (10 FS):**\n"
            "• `BYK-01` : İnce/Pala Bıyık\n"
            "• `BYK-02` : Kalın Koyu Bıyık\n"
            "• `BYK-03` : Top Sakal & Bıyık\n"
            "• `SKL-01` : Kirli Sakal\n\n"
            "Kodu mesaj olarak gönderin."
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo_file = await update.message.photo[-1].get_file()
    user_last_photo[user_id] = await photo_file.download_as_bytearray()

    await update.message.reply_text(
        "📸 **Fotoğraf Kaydedildi!**\n\nŞimdi efekti seçin veya kodunu yazın (Örn: `BYK-01`, `BYK-02`):",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip().upper()

    is_admin = user_id == ADMIN_ID
    user_bal = user_balances.get(user_id, 0)

    # Adminler için bakiye kontrolü es geçilir
    if not is_admin and user_bal < 10:
        await update.message.reply_text(
            f"❌ **Bakiye Yetersiz!** İşlem için **10 FS** gerekiyor.\nMevcut Bakiyeniz: **{user_bal} FS**"
        )
        return

    if user_id not in user_last_photo or not user_last_photo[user_id]:
        await update.message.reply_text("⚠️ **Lütfen önce bir fotoğraf gönderin!**")
        return

    msg = await update.message.reply_text(f"⚡ `{text}` efekti uygulanıyor...", parse_mode="Markdown")

    try:
        processed_photo = apply_facial_effect(user_last_photo[user_id], text)

        if not is_admin:
            user_balances[user_id] -= 10

        await context.bot.send_photo(
            chat_id=user_id,
            photo=processed_photo,
            caption=f"✅ **{text}** efekti uygulandı!\nKalan Bakiye: {user_balances.get(user_id, 0)} FS",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown",
        )
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ Hata oluştu: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("⚡ FACEİSTOKİS AI Aktif!")
    app.run_polling()
            
