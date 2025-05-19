import os
import tempfile
from telegram import Update, Document
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from cryptography.fernet import Fernet

TOKEN = 7847599497:AAEzz4sg7cJyTKd6hqDg_V6O67d1DzPCoJg

user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли мне файл для шифровки.\nДля дешифровки напиши /decrypt")

async def decrypt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_states[update.effective_user.id] = 'decrypt_wait_file'
    await update.message.reply_text("Ок, пришли файл, который нужно расшифровать.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id, 'encrypt')

    file = await update.message.document.get_file()
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        await file.download_to_drive(tmp_file.name)
        filepath = tmp_file.name

    if state == 'decrypt_wait_file':
        user_states[user_id] = {'state': 'decrypt_wait_key', 'filepath': filepath}
        await update.message.reply_text("Теперь пришли ключ для расшифровки:")
    else:
        key = Fernet.generate_key()
        cipher = Fernet(key)

        with open(filepath, 'rb') as f:
            data = f.read()
        encrypted = cipher.encrypt(data)

        encrypted_path = filepath + '.enc'
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted)

        await update.message.reply_document(document=open(encrypted_path, 'rb'))
        await update.message.reply_text(f"Файл зашифрован.\n🔑 Сохрани этот ключ для дешифровки:\n`{key.decode()}`", parse_mode='Markdown')

        os.remove(filepath)
        os.remove(encrypted_path)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state_info = user_states.get(user_id)

    if isinstance(state_info, dict) and state_info.get('state') == 'decrypt_wait_key':
        key = update.message.text.strip()
        filepath = state_info['filepath']
        try:
            cipher = Fernet(key.encode())

            with open(filepath, 'rb') as f:
                encrypted_data = f.read()
            decrypted_data = cipher.decrypt(encrypted_data)

            decrypted_path = filepath + '.dec'
            with open(decrypted_path, 'wb') as f:
                f.write(decrypted_data)

            await update.message.reply_document(document=open(decrypted_path, 'rb'))
            await update.message.reply_text("✅ Файл успешно расшифрован.")

            os.remove(filepath)
            os.remove(decrypted_path)
        except Exception as e:
            await update.message.reply_text("❌ Ошибка при расшифровке. Убедись, что ключ правильный.")
        finally:
            user_states.pop(user_id, None)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("decrypt", decrypt_command))
app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()
