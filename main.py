import io
import os
import logging
import random
import requests
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
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
from telegram.error import BadRequest

# Logging Ayarı
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- CONFIG ---
BOT_TOKEN = "8635625101:AAENL_CKh30rP6aHQXlPMVeKSvLwILXunX4"
ADMIN_ID = 8520025523

# Veri Depoları
user_balances = {}
user_last_photo = {}
user_ai_mode = {}
user_ai_photo_mode = {}  # AI Foto Modu
user_referrals = {}
user_daily_claimed = {}

SHOP_PACKAGES = {
    "star_5k": {"title": "5.000 FS", "fs": 5000, "stars": 280},
    "star_37k": {"title": "37.028 FS", "fs": 37028, "stars": 1836},
    "star_63k": {"title": "63.951 FS", "fs": 63951, "stars": 4386},
    "star_103k": {"title": "103.926 FS", "fs": 103926, "stars": 6937},
    "star_289k": {"title": "289.959 FS", "fs": 289959, "stars": 12855},
    "star_vip": {
        "title": "👑 Gizemli VIP Paketi",
        "random_fs": True,
        "stars": 750,
    },
}

# --- HAAR CASCADE YÜZ MODELİ YÜKLEME ---
CASCADE_FILE = "haarcascade_frontalface_default.xml"
if not os.path.exists(CASCADE_FILE):
    url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
    r = requests.get(url)
    with open(CASCADE_FILE, "wb") as f:
        f.write(r.content)

face_cascade = cv2.CascadeClassifier(CASCADE_FILE)

# --- DİNAMİK AI FOTOĞRAF İŞLEME MOTORU ---
def process_ai_custom_photo(photo_bytes, prompt_text):
    np_arr = np.frombuffer(photo_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    prompt = prompt_text.lower().strip()
    pil_img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")

    # SAÇ RENKLERİ ALGILAMA
    if "mavi" in prompt:
        pil_img = ImageOps.colorize(pil_img.convert("L"), black="black", white="blue")
    elif "sarı" in prompt:
        pil_img = ImageOps.colorize(pil_img.convert("L"), black="black", white="yellow")
    elif "kırmızı" in prompt or "kızıl" in prompt:
        pil_img = ImageOps.colorize(pil_img.convert("L"), black="black", white="red")
    elif "yeşil" in prompt:
        pil_img = ImageOps.colorize(pil_img.convert("L"), black="black", white="green")

    # YAŞLANDIRMA / GENÇLEŞTİRME ALGILAMA
    if any(word in prompt for word in ["yaş", "yaşlı", "yaşında", "ihtiyar"]):
        gray_face = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_face = cv2.equalizeHist(gray_face)
        img = cv2.cvtColor(gray_face, cv2.COLOR_GRAY2BGR)

    # BIYIK VE SAKAL ALGILAMA
    if len(faces) > 0 and any(word in prompt for word in ["bıyık", "bıyıklı", "sakal", "sakallı"]):
        for x, y, w, h in faces:
            mustache_y1 = int(y + h * 0.62)
            mustache_y2 = int(y + h * 0.74)
            mustache_x1 = int(x + w * 0.28)
            mustache_x2 = int(x + w * 0.72)
            
            # Rastgele veya isteğe uygun bıyık/sakal çizimi
            pts = np.array([
                [mustache_x1, mustache_y1 + random.randint(2, 6)],
                [int(x + w * 0.5), mustache_y1 - random.randint(3, 7)],
                [mustache_x2, mustache_y1 + random.randint(2, 6)],
                [int(x + w * 0.5), mustache_y2 - random.randint(5, 10)]
            ], np.int32)
            cv2.fillPoly(img, [pts], (10, 10, 10))

            if "sakal" in prompt:
                for _ in range(300):
                    rx = random.randint(int(x + w * 0.25), int(x + w * 0.75))
                    ry = random.randint(int(y + h * 0.65), int(y + h * 0.92))
                    cv2.line(img, (rx, ry), (rx + 1, ry + 3), (15, 15, 15), 1)

    # GÖZLÜK VEYA AKSESUAR ALGILAMA
    if len(faces) > 0 and any(word in prompt for word in ["gözlük", "gözlüklü", "güneş gözlüğü"]):
        for x, y, w, h in faces:
            gy1, gy2 = int(y + h * 0.32), int(y + h * 0.46)
            cv2.rectangle(img, (int(x + w * 0.15), gy1), (int(x + w * 0.85), gy2), (15, 15, 15), -1)

    # Eğer PIL tabanlı bir renk efekti uygulandıysa onu döndür
    if any(color in prompt for color in ["mavi", "sarı", "kırmızı", "kızıl", "yeşil"]):
        out = io.BytesIO()
        pil_img.save(out, format="JPEG", quality=95)
        return io.BytesIO(out.getvalue())

    # OpenCV ile işlenen resmi döndür
    _, encoded_img = cv2.imencode(".jpg", img)
    return io.BytesIO(encoded_img.tobytes())

# --- SABİT EFEKT MOTORU ---
def apply_facial_effect(photo_bytes, effect_code):
    np_arr = np.frombuffer(photo_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    code = effect_code.upper().strip()
    pil_img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")

    if "BOKEH" in code:
        blurred = pil_img.filter(ImageFilter.GaussianBlur(15))
        if len(faces) > 0:
            x, y, w, h = faces[0]
            mask = Image.new("L", pil_img.size, 0)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(mask)
            draw.ellipse((x - 20, y - 20, x + w + 20, y + h + 20), fill=255)
            pil_img = Image.composite(pil_img, blurred, mask)
        else:
            pil_img = blurred
        out = io.BytesIO()
        pil_img.save(out, format="JPEG", quality=95)
        return io.BytesIO(out.getvalue())

    for x, y, w, h in faces:
        if "BYK-01" in code:
            cv2.ellipse(img, (int(x + w * 0.5), int(y + h * 0.68)), (int(w * 0.22), int(h * 0.08)), 0, 0, 180, (10, 10, 10), -1)

    _, encoded_img = cv2.imencode(".jpg", img)
    return io.BytesIO(encoded_img.tobytes())

# --- KLAVYELER ---
def get_main_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✨ AI ile Foto Yap (22 FS)", callback_data="ai_photo_start"),
            ],
            [
                InlineKeyboardButton("🎨 Saç Rengi", callback_data="cat_hair_color"),
                InlineKeyboardButton("🧔 Bıyık & Sakal", callback_data="cat_beard"),
            ],
            [
                InlineKeyboardButton("👓 Aksesuar & Gözlük", callback_data="cat_acc"),
                InlineKeyboardButton("👁 Göz Rengi", callback_data="cat_eyes"),
            ],
            [
                InlineKeyboardButton("📸 Portre / Bokeh", callback_data="apply_BOKEH"),
                InlineKeyboardButton("👴 Yaş Değiştir", callback_data="cat_age"),
            ],
            [
                InlineKeyboardButton("🎁 Günlük Bonus (+14 FS)", callback_data="daily_bonus"),
                InlineKeyboardButton("🔗 Davet Et Kazan (+50 FS)", callback_data="referral"),
            ],
            [
                InlineKeyboardButton("🤖 AİOR-Aİ Sor", callback_data="ai_chat"),
                InlineKeyboardButton("👤 Profilim", callback_data="profile"),
            ],
            [
                InlineKeyboardButton("⭐ Yıldız Mağazası", callback_data="shop"),
            ],
        ]
    )

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_balances.setdefault(user_id, 0)

    args = context.args
    if args and len(args) > 0:
        referrer_id = int(args[0])
        if referrer_id != user_id and user_id not in user_referrals:
            user_referrals[user_id] = referrer_id
            user_balances[referrer_id] = user_balances.get(referrer_id, 0) + 50
            user_balances[user_id] = user_balances.get(user_id, 0) + 50
            await context.bot.send_message(chat_id=referrer_id, text="🎉 **Yeni bir arkadaşını davet ettin! +50 FS Hesabına Yattı!**")

    await update.message.reply_text(
        "🔥 **FACEİSTOKİS AI Botuna Hoşgeldiniz!**\n\n📸 Lütfen bir işlem seçin veya fotoğrafınızı gönderin:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )

async def safe_edit_text(query, text, reply_markup=None, parse_mode="Markdown"):
    try:
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest:
        pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "ai_photo_start":
        user_ai_photo_mode[user_id] = "WAITING_PHOTO"
        await safe_edit_text(
            query,
            "✨ **AI İLE FOTO YAP MODU (22 FS)**\n\n📸 Lütfen değiştirmek istediğiniz fotoğrafı gönderin:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ İptal Et", callback_data="main_menu")]])
        )
        return

    if data == "daily_bonus":
        if user_daily_claimed.get(user_id, False):
            await query.answer("❌ Bugünkünü zaten aldın! Yarın tekrar gel.", show_alert=True)
        else:
            user_daily_claimed[user_id] = True
            user_balances[user_id] = user_balances.get(user_id, 0) + 14
            await query.answer("🎉 Bugüne özel +14 FS Hesabına Eklendi!", show_alert=True)
            await safe_edit_text(query, f"✅ **Günlük bonus alındı!**\nYeni Bakiye: `{user_balances[user_id]} FS`", get_main_keyboard())
        return

    if data == "referral":
        bot_username = (await context.bot.get_me()).username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        await safe_edit_text(
            query,
            f"🔗 **DAVET ET KAZAN!**\n\nBu linki arkadaşlarına gönder, bota katılan her arkadaşın için **+50 FS** kazan!\n\n👉 `{ref_link}`",
            get_main_keyboard()
        )
        return

    if data == "shop":
        buttons = []
        is_admin = (user_id == ADMIN_ID)

        for key, pkg in SHOP_PACKAGES.items():
            if is_admin:
                btn_text = f"🎁 {pkg['title']} (ÜCRETSİZ - Admin)"
            else:
                btn_text = f"⭐ {pkg['title']} ({pkg['stars']} Yıldız)"
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"buy_{key}")])

        vip_desc = (
            "⭐ **FACEİSTOKİS MAĞAZASI**\n\n"
            "❓ **VIPIN içinde ne var sence?** Meraklanmak İSTEMİYORSAN 750 yıldıza al meraklanma sence ne var!?😀\n\n"
            "*(VIP Paketini alanlara 7.320 FS ile 189.402 FS arası RASTGELE bakiye hediye edilir!)*"
        )
        await safe_edit_text(query, vip_desc, InlineKeyboardMarkup(buttons))
        return

    if data.startswith("buy_"):
        pkg_key = data.replace("buy_", "")
        pkg = SHOP_PACKAGES.get(pkg_key)

        if pkg:
            if user_id == ADMIN_ID:
                if pkg.get("random_fs"):
                    won_fs = random.randint(7320, 189402)
                    user_balances[user_id] = user_balances.get(user_id, 0) + won_fs
                    await safe_edit_text(query, f"👑 **Admin VIP Özel:** Merakın bitti! Tam **+{won_fs:,} FS** hesabına yüklendi! 😀", get_main_keyboard())
                else:
                    user_balances[user_id] = user_balances.get(user_id, 0) + pkg["fs"]
                    await safe_edit_text(query, f"⚡ **Admin Özel:** +{pkg['fs']} FS Bakiyenize Eklendi!", get_main_keyboard())
            else:
                prices = [LabeledPrice(label=pkg["title"], amount=pkg["stars"])]
                await context.bot.send_invoice(
                    chat_id=user_id,
                    title=pkg["title"],
                    description=f"FACEİSTOKİS {pkg['title']}",
                    payload=pkg_key,
                    provider_token="",
                    currency="XTR",
                    prices=prices
                )
        return

    if data == "profile":
        bal = user_balances.get(user_id, 0)
        role = "Admin 👑" if user_id == ADMIN_ID else "Kullanıcı"
        await safe_edit_text(query, f"👤 **PROFİL BİLGİLERİNİZ**\n\n🆔 **ID:** `{user_id}`\n💰 **Bakiye:** `{bal} FS`\n👑 **Unvan:** `{role}`", get_main_keyboard())
        return

    if data == "main_menu":
        user_ai_photo_mode[user_id] = False
        await safe_edit_text(query, "📸 Lütfen bir işlem seçin:", get_main_keyboard())
        return

    if data == "ai_chat":
        user_ai_mode[user_id] = True
        await safe_edit_text(query, "🤖 **AİOR-Aİ Modu Aktif!**\n\nSorunuzu yazabilirsiniz (Çıkmak için `/cikis` yazın):")
        return

    if data.startswith("apply_"):
        effect_code = data.replace("apply_", "")
        await execute_effect(query.message, user_id, effect_code, context)
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo_file = await update.message.photo[-1].get_file()
    user_last_photo[user_id] = await photo_file.download_as_bytearray()

    # Eğer kullanıcı AI Foto butonuna basıp geldiyse
    if user_ai_photo_mode.get(user_id) == "WAITING_PHOTO":
        user_ai_photo_mode[user_id] = "WAITING_PROMPT"
        await update.message.reply_text(
            "📸 **Fotoğrafınız Alındı!**\n\n💬 Şimdi bu fotoğrafın nasıl olmasını istiyorsunuz? (Örn: *'bıyıklı olsun'*, *'saçı mavi olsun'*, *'45 yaşlarında olsun'*)"
        )
        return

    await update.message.reply_text(
        "📸 **Fotoğraf Kaydedildi!**\n\nAşağıdaki menüden efekti seçebilirsiniz:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown",
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    is_admin = (user_id == ADMIN_ID)

    if text == "/cikis":
        user_ai_mode[user_id] = False
        user_ai_photo_mode[user_id] = False
        await update.message.reply_text("🤖 **İşlemden çıkıldı.**", reply_markup=get_main_keyboard())
        return

    # AI Foto Modunda İstek Metni Geldiğinde
    if user_ai_photo_mode.get(user_id) == "WAITING_PROMPT":
        user_bal = user_balances.get(user_id, 0)
        if not is_admin and user_bal < 22:
            await update.message.reply_text(f"❌ **Bakiye Yetersiz!** AI ile Foto İşlemi **22 FS** gerektirir.\nBakiyeniz: **{user_bal} FS**")
            user_ai_photo_mode[user_id] = False
            return

        if user_id not in user_last_photo:
            await update.message.reply_text("⚠️ Fotoğraf bulunamadı, lütfen önce fotoğraf gönderin.")
            return

        msg = await update.message.reply_text("✨ `Yapay Zeka Fotoğrafınızı İşliyor...`", parse_mode="Markdown")

        try:
            processed_photo = process_ai_custom_photo(user_last_photo[user_id], text)
            if not is_admin:
                user_balances[user_id] -= 22

            user_ai_photo_mode[user_id] = False
            await context.bot.send_photo(
                chat_id=user_id,
                photo=processed_photo,
                caption=f"✅ **İsteğiniz Yapıldı:** *'{text}'*\n\n💰 Kalan Bakiye: **{user_balances.get(user_id, 0)} FS**",
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown",
            )
            await msg.delete()
        except Exception as e:
            await msg.edit_text(f"❌ Hata oluştu: {str(e)}")
        return

    if user_ai_mode.get(user_id, False):
        await update.message.reply_text(f"🤖 **AİOR-Aİ:** '{text}' sorunu düşündüm, cevap oldukça açık!")
        return

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    payload = update.message.successful_payment.invoice_payload
    pkg = SHOP_PACKAGES.get(payload)

    if pkg:
        if pkg.get("random_fs"):
            won_fs = random.randint(7320, 189402)
            user_balances[user_id] = user_balances.get(user_id, 0) + won_fs
            await update.message.reply_text(f"🎉 **ÖDEME BAŞARILI!**\n\nVIP Paketiniz açıldı! Şansınıza **+{won_fs:,} FS** yüklendi! 😀", reply_markup=get_main_keyboard())
        else:
            user_balances[user_id] = user_balances.get(user_id, 0) + pkg["fs"]
            await update.message.reply_text(f"🎉 **ÖDEME BAŞARILI!**\n\n+{pkg['fs']} FS hesabınıza eklendi!", reply_markup=get_main_keyboard())

async def execute_effect(message, user_id, effect_code, context):
    is_admin = (user_id == ADMIN_ID)
    user_bal = user_balances.get(user_id, 0)

    if not is_admin and user_bal < 10:
        await message.reply_text(f"❌ **Bakiye Yetersiz!** İşlem için **10 FS** gerekiyor.\nMevcut Bakiyeniz: **{user_bal} FS**")
        return

    if user_id not in user_last_photo or not user_last_photo[user_id]:
        await message.reply_text("⚠️ **Lütfen önce bir fotoğraf gönderin!**")
        return

    msg = await message.reply_text(f"⚡ `{effect_code}` efekti uygulanıyor...", parse_mode="Markdown")

    try:
        processed_photo = apply_facial_effect(user_last_photo[user_id], effect_code)
        if not is_admin:
            user_balances[user_id] -= 10

        await context.bot.send_photo(
            chat_id=user_id,
            photo=processed_photo,
            caption=f"✅ **{effect_code}** efekti uygulandı!\nKalan Bakiye: {user_balances.get(user_id, 0)} FS",
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
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("⚡ FACEİSTOKİS AI Aktif!")
    app.run_polling(drop_pending_updates=True)
        
