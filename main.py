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

# Veriler
user_balances = {}
user_vips = {}
user_spins = {}
user_discounts = {}
user_stats = {}
user_last_photo = {}
user_ai_mode = {}

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

# OpenCV Yüz ve Bıyık Çizim Motoru
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
        # Dudak/Bıyık Bölgesi (Yüzün alt-orta kısmı)
        mustache_y1 = int(y + h * 0.62)
        mustache_y2 = int(y + h * 0.75)
        mustache_x1 = int(x + w * 0.25)
        mustache_x2 = int(x + w * 0.75)

        if "BYK-01" in code:  # İnce / Pala Bıyık
            pts = np.array(
                [
                    [mustache_x1, mustache_y1 + 5],
                    [int(x + w * 0.5), mustache_y1 - 5],
                    [mustache_x2, mustache_y1 + 5],
                    [int(x + w * 0.5), mustache_y2 - 10],
                ],
                np.int32,
            )
            cv2.fillPoly(img, [pts], (20, 20, 20))

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

        elif "BYK-03" in code:  # Top Sakal + Bıyık
            cv2.ellipse(
                img,
                (int(x + w * 0.5), int(mustache_y1)),
                (int(w * 0.22), int(h * 0.07)),
                0,
                0,
                180,
                (15, 15, 15),
                -1,
            )
            cv2.ellipse(
                img,
                (int(x + w * 0.5), int(y + h * 0.85)),
                (int(w * 0.15), int(h * 0.1)),
                0,
                0,
                360,
                (15, 15, 15),
                -1,
            )

        elif "SKL-01" in code:  # Kirli Sakal
            for _ in range(300):
                rx = random.randint(int(x + w * 0.2), int(x + w * 0.8))
                ry = random.randint(int(y + h * 0.65), int(y + h * 0.92))
                cv2.line(
                    img, (rx, ry), (rx + 2, ry + 4), (30, 30, 30), 1
                )

        elif "YAS-60" in code:  # Yaşlandırma
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.equalizeHist(img)
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

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
    user_discounts.setdefault(user_id, [])

    await update.message.reply_text(
        "🔥 **FACEİSTOKİS AI Botuna Hoşgeldiniz!**\n\n📸 İşlemek istediğiniz fotoğrafı gönderin.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )

# Admin FS Verme Komutu: /ver <user_id> <miktar>
async def give_fs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != ADMIN_ID:
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        user_balances[target_id] = user_balances.get(target_id, 0) + amount
        await update.message.reply_text(
            f"✅ `{target_id}` kullanıcısına **{amount} FS** başarıyla hediye edildi!\nYeni Bakiye: {user_balances[target_id]} FS"
        )
    except Exception:
        await update.message.reply_text("Kullanım: `/ver <kullanici_id> <miktar>`")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "cat_beard":
        await query.message.reply_text(
            "🧔 **BIYIK & SAKAL KODLARI (10 FS):**\n"
            "• `BYK-01` : İnce/Pala Bıyık\n"
            "• `BYK-02` : Kalın Koyu Bıyık\n"
            "• `BYK-03` : Top Sakal & Bıyık\n"
            "• `SKL-01` : Kirli Sakal\n\n"
            "Kodu mesaj olarak gönderin."
        )
    elif data == "cat_age":
        await query.message.reply_text(
            "👶👴 **YAŞ KODLARI (10 FS):**\n• `YAS-60` : Yaşlandır\n\nKodu mesaj olarak gönderin."
        )
    elif data == "profile":
        bal = user_balances.get(user_id, 0)
        await query.message.reply_text(
            f"👤 **PROFİL BİLGİLERİNİZ**\n\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"💰 **Bakiye:** `{bal} FS`",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(),
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    user_last_photo[user_id] = photo_bytes

    await update.message.reply_text(
        "📸 **Fotoğraf Kaydedildi!**\n\nŞimdi efekti seçin veya kodunu yazın (Örn: `BYK-01`, `BYK-02`):",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip().upper()

    # Bakiye / FS Kontrolü (Sıkı Kontrol)
    user_bal = user_balances.get(user_id, 0)
    is_vip = user_vips.get(user_id, False) or user_id == ADMIN_ID

    if not is_vip and user_bal < 10:
        await update.message.reply_text(
            f"❌ **Bakiye Yetersiz!** Bu işlem için **10 FS** gerekiyor.\nMevcut Bakiyeniz: **{user_bal} FS**\nYıldız Mağazasından bakiye alabilirsiniz."
        )
        return

    if user_id not in user_last_photo or not user_last_photo[user_id]:
        await update.message.reply_text("⚠️ **Lütfen önce bir fotoğraf gönderin!**")
        return

    msg = await update.message.reply_text(
        f"⚡ `{text}` efekti fotoğrafa uygulanıyor...", parse_mode="Markdown"
    )

    try:
        processed_photo = apply_facial_effect(user_last_photo[user_id], text)

        # İşlem başarılı olursa 10 FS düş
        if not is_vip:
            user_balances[user_id] -= 10

        await context.bot.send_photo(
            chat_id=user_id,
            photo=processed_photo,
            caption=f"✅ **{text}** efekti başarıyla uygulandı!\nKalan Bakiye: {user_balances.get(user_id, 0)} FS",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown",
        )
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ İşlem sırasında bir hata oluştu: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ver", give_fs))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("⚡ FACEİSTOKİS AI Aktif!")
    app.run_polling()
                
