import io
import random
from PIL import Image, ImageEnhance, ImageOps
import g4f
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


# GÖRSEL İŞLEME MOTORU (Fotoğraf Düzenleme)
def process_image_effect(photo_bytes, effect_code):
    image = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    code = effect_code.upper().strip()

    if "RENK" in code or "SAC" in code:
        enhancer = ImageEnhance.Color(image)
        image = enhancer.enhance(2.5)
        if "01" in code:
            image = ImageOps.colorize(
                image.convert("L"), black="black", white="yellow"
            )
        elif "02" in code:
            image = ImageOps.colorize(
                image.convert("L"), black="black", white="red"
            )
        elif "03" in code:
            image = ImageOps.colorize(
                image.convert("L"), black="black", white="brown"
            )

    elif "YAS" in code:
        if "60" in code or "2" in code:
            image = ImageOps.grayscale(image)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.8)
        else:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.2)

    elif "GUL" in code or "BYK" in code or "SKL" in code:
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.3)

    else:
        image = ImageOps.autocontrast(image)

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=95)
    output.seek(0)
    return output


# AİOR-Aİ CEVAP MOTORU
async def get_aior_response(text):
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.gpt_35_turbo,
            messages=[
                {
                    "role": "system",
                    "content": "Sen FACEİSTOKİS AI botunun akıllı asistanı AİOR-Aİ'sin. Kullanıcıya kısa, zeki ve samimi cevap ver.",
                },
                {"role": "user", "content": text},
            ],
        )
        return response
    except Exception:
        return "🤖 AİOR-Aİ: Dinliyorum reis, nasıl yardımcı olabilirim?"


def get_main_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎨 Saç Rengi (ÜCRETSİZ)", callback_data="cat_hair_color"
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
    user_ai_mode[user_id] = False

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
        ]
    )
    await update.message.reply_text(
        "🔥 **FACEİSTOKİS AI Botuna Hoşgeldiniz!**\n\nLütfen bir dil seçin:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("lang_"):
        await query.message.reply_text(
            "✅ **Dil seçimi başarılı!**\n\n📸 Lütfen işlenmesini istediğiniz fotoğrafı gönderin.",
            parse_mode="Markdown",
        )
        return

    if data == "ai_chat":
        user_ai_mode[user_id] = True
        await query.message.reply_text(
            "🤖 **AİOR-Aİ Modu Aktifleşti!**\n\nBana istediğin soruyu sorabilirsin. (Çıkmak için `/cikis` yazabilirsin)",
            parse_mode="Markdown",
        )
        return

    if data == "profile":
        bal = user_balances.get(user_id, 0)
        done_photos = user_stats.get(user_id, 0)
        vip_status = (
            "🌟 982 Gün VIP"
            if user_vips.get(user_id) or user_id == ADMIN_ID
            else "🆓 Normal Üye"
        )
        discounts = user_discounts.get(user_id, [])
        disc_text = (
            ", ".join([f"%{d}" for d in discounts])
            if discounts
            else "Henüz yok"
        )

        await query.message.reply_text(
            f"👤 **PROFİL BİLGİLERİNİZ**\n\n"
            f"🆔 **ID:** `{user_id}`\n"
            f"💰 **Bakiye:** `{bal} FACEİSTOKİS`\n"
            f"🖼 **İşlenen Fotoğraf:** `{done_photos} Adet`\n"
            f"👑 **Üyelik:** `{vip_status}`\n"
            f"🎡 **Günlük Çark Hakkı:** `{user_spins.get(user_id, 8)}/8`\n"
            f"🏷 **İndirimleriniz:** `{disc_text}`",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(),
        )
        return

    if data == "shop":
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⭐ 5.000 FS (280 Yıldız)", callback_data="buy_star_5k"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⭐ 37.028 FS (1.836 Yıldız)",
                        callback_data="buy_star_37k",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⭐ 63.951 FS (4.386 Yıldız)",
                        callback_data="buy_star_63k",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⭐ 103.926 FS (6.937 Yıldız)",
                        callback_data="buy_star_103k",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⭐ 289.959 FS (12.855 Yıldız)",
                        callback_data="buy_star_289k",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "👑 982 GÜN VIP (19.496 Yıldız)",
                        callback_data="buy_star_vip",
                    )
                ],
            ]
        )
        await query.message.reply_text(
            "⭐ **FACEİSTOKİS YILDIZ MAĞAZASI**\n\nAlmak istediğiniz pakete tıklayarak Telegram Yıldızlarınız ile ödeme yapabilirsiniz:",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return

    if data.startswith("buy_"):
        pkg_key = data.replace("buy_", "")
        pkg = SHOP_PACKAGES.get(pkg_key)
        if pkg:
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

    if data == "wheel":
        spins = user_spins.get(user_id, 8)
        if spins <= 0:
            await query.message.reply_text(
                "❌ Günlük 8 çark çevirme hakkınız bitti!"
            )
            return
        user_spins[user_id] -= 1
        won = random.choice([25, 35, 50, 80])
        user_discounts[user_id].append(won)
        await query.message.reply_text(
            f"🎡 **ÇARK ÇEVRİLDİ!**\n\n🎉 **%{won} İndirim** kazandınız!\nKalan Hakkınız: {user_spins[user_id]}",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown",
        )
        return

    if data == "cat_beard":
        await query.message.reply_text(
            "🧔 **BIYIK & SAKAL KODLARI (10 FS):**\n• `BYK-01` : İnce Bıyık\n• `SKL-01` : Kirli Sakal\n\nKodu mesaj olarak yazıp gönderin."
        )
    elif data == "cat_age":
        await query.message.reply_text(
            "👶👴 **YAŞ KODLARI (10 FS):**\n• `YAS-25` : Gençleştir\n• `YAS-60` : Yaşlandır\n\nKodu mesaj olarak yazıp gönderin."
        )
    elif data == "cat_hair_color":
        await query.message.reply_text(
            "🎨 **SAÇ RENKLERİ (ÜCRETSİZ):**\n• `RENK-01` : Sarı Saç\n• `RENK-02` : Kızıl Saç\n• `RENK-03` : Kahve Saç\n\nKodu mesaj olarak yazıp gönderin."
        )
    elif data == "cat_smile":
        await query.message.reply_text(
            "😄 **GÜLME KODLARI (10 FS):**\n• `GUL-01` : Tebessüm\n• `GUL-02` : Kahkaha\n\nKodu mesaj olarak yazıp gönderin."
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    user_last_photo[user_id] = photo_bytes

    await update.message.reply_text(
        "📸 **Fotoğraf Kaydedildi!**\n\nŞimdi yapmak istediğin efekti seç veya kodunu yaz (Örn: `GUL-01`, `RENK-01`):",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if text == "/cikis":
        user_ai_mode[user_id] = False
        await update.message.reply_text(
            "🤖 **AİOR-Aİ Modundan Çıkıldı.**", reply_markup=get_main_keyboard()
        )
        return

    if user_ai_mode.get(user_id, False):
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )
        reply = await get_aior_response(text)
        await update.message.reply_text(
            f"🤖 **AİOR-Aİ:**\n{reply}", parse_mode="Markdown"
        )
        return

    if user_id not in user_last_photo or not user_last_photo[user_id]:
        await update.message.reply_text(
            "⚠️ **Lütfen önce bir fotoğraf gönderin!**"
        )
        return

    msg = await update.message.reply_text(
        f"⚡ `{text}` efekti fotoğrafa uygulanıyor, lütfen bekleyin...",
        parse_mode="Markdown",
    )

    try:
        processed_photo = process_image_effect(
            user_last_photo[user_id], text
        )
        await context.bot.send_photo(
            chat_id=user_id,
            photo=processed_photo,
            caption=f"✅ **{text}** efekti başarıyla uygulandı!",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown",
        )
        await msg.delete()
        user_stats[user_id] = user_stats.get(user_id, 0) + 1
    except Exception as e:
        await msg.edit_text(
            f"❌ Efekt uygulanırken bir hata oluştu: {str(e)}"
        )


async def precheckout_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    user_id = update.message.from_user.id
    payload = update.message.successful_payment.invoice_payload
    pkg = SHOP_PACKAGES.get(payload)
    if pkg:
        if pkg.get("vip"):
            user_vips[user_id] = True
            await update.message.reply_text(
                "🎉 **VIP Aktif Edildi!**", reply_markup=get_main_keyboard()
            )
        else:
            user_balances[user_id] = (
                user_balances.get(user_id, 0) + pkg["fs"]
            )
            await update.message.reply_text(
                f"🎉 **+{pkg['fs']} FS Bakiye Eklendi!**",
                reply_markup=get_main_keyboard(),
            )


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("⚡ FACEİSTOKİS AI Aktif!")
    app.run_polling()
  
